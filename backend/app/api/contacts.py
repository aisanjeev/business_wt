"""Contact management endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Contact, Conversation, Message, User
from app.schemas import (
    ContactCreate,
    ContactResponse,
    ContactUpdate,
    ContactWithConversation,
    ConversationListItem,
    ConversationResponse,
    ConversationWithContact,
    PaginatedResponse,
    SuccessResponse,
)
from app.services.auth import get_current_user
from app.utils.constants import SenderType
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=PaginatedResponse)
async def get_contacts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    """Get all contacts with optional filtering.
    
    Args:
        page: Page number.
        page_size: Items per page.
        search: Search query for name or phone.
        status_filter: Filter by status.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Paginated list of contacts.
    """
    # Build query
    query = select(Contact)
    count_query = select(func.count(Contact.id))
    
    # Apply search filter
    if search:
        search_filter = or_(
            Contact.name.ilike(f"%{search}%"),
            Contact.phone_number.ilike(f"%{search}%"),
            Contact.email.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Apply status filter
    if status_filter:
        query = query.where(Contact.status == status_filter)
        count_query = count_query.where(Contact.status == status_filter)
    
    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size
    
    # Get contacts
    result = await db.execute(
        query.order_by(Contact.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    contacts = result.scalars().all()
    
    contact_responses = [
        ContactResponse.model_validate(contact) for contact in contacts
    ]
    
    return PaginatedResponse(
        items=contact_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{contact_id}", response_model=ContactWithConversation)
async def get_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactWithConversation:
    """Get a specific contact by ID.
    
    Args:
        contact_id: The contact ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Contact details with conversation info.
    """
    result = await db.execute(
        select(Contact)
        .options(selectinload(Contact.conversations))
        .where(Contact.id == contact_id)
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )
    
    # Get latest conversation info
    last_message = None
    last_message_at = None
    unread_count = 0
    
    if contact.conversations:
        latest_conv = max(
            contact.conversations,
            key=lambda c: c.last_message_at or c.created_at,
        )
        last_message_at = latest_conv.last_message_at
        unread_count = latest_conv.unread_count
        
        # Get last message content
        msg_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == latest_conv.id)
            .order_by(Message.timestamp.desc())
            .limit(1)
        )
        msg = msg_result.scalar_one_or_none()
        if msg:
            last_message = msg.content
    
    return ContactWithConversation(
        id=contact.id,
        phone_number=contact.phone_number,
        name=contact.name,
        email=contact.email,
        avatar_url=contact.avatar_url,
        business_account_id=contact.business_account_id,
        status=contact.status,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
        last_message=last_message,
        last_message_at=last_message_at,
        unread_count=unread_count,
    )


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    contact_data: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactResponse:
    """Create a new contact.
    
    Args:
        contact_data: Contact information.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Created contact.
    """
    # Check if phone number already exists
    result = await db.execute(
        select(Contact).where(Contact.phone_number == contact_data.phone_number)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact with this phone number already exists",
        )
    
    contact = Contact(**contact_data.model_dump())
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    
    logger.info(f"Created contact: {contact.phone_number}")
    
    return ContactResponse.model_validate(contact)


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: int,
    contact_data: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactResponse:
    """Update a contact.
    
    Args:
        contact_id: The contact ID.
        contact_data: Updated contact information.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Updated contact.
    """
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id)
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )
    
    # Update fields
    update_data = contact_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)
    
    await db.commit()
    await db.refresh(contact)
    
    logger.info(f"Updated contact: {contact.phone_number}")
    
    return ContactResponse.model_validate(contact)


@router.delete("/{contact_id}", response_model=SuccessResponse)
async def delete_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Delete a contact and all associated conversations.
    
    Args:
        contact_id: The contact ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Success response.
    """
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id)
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )
    
    await db.delete(contact)
    await db.commit()
    
    logger.info(f"Deleted contact: {contact.phone_number}")
    
    return SuccessResponse(message="Contact deleted successfully")


@router.get("/{contact_id}/conversations", response_model=list[ConversationResponse])
async def get_contact_conversations(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConversationResponse]:
    """Get all conversations for a contact.
    
    Args:
        contact_id: The contact ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        List of conversations.
    """
    # Verify contact exists
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id)
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )
    
    # Get conversations
    result = await db.execute(
        select(Conversation)
        .where(Conversation.contact_id == contact_id)
        .order_by(Conversation.last_message_at.desc().nullsfirst())
    )
    conversations = result.scalars().all()
    
    return [
        ConversationResponse.model_validate(conv) for conv in conversations
    ]


# Conversation endpoints (could be separate file)

@router.get("/conversations/list", response_model=list[ConversationListItem])
async def get_conversation_list(
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConversationListItem]:
    """Get list of conversations with contact info for sidebar.
    
    Args:
        limit: Maximum number of conversations to return.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        List of conversation summaries.
    """
    # Get active conversations with contact info
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.contact))
        .where(Conversation.is_active == True)  # noqa: E712
        .order_by(Conversation.last_message_at.desc().nullsfirst())
        .limit(limit)
    )
    conversations = result.scalars().all()
    
    items = []
    for conv in conversations:
        # Get last message
        msg_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.timestamp.desc())
            .limit(1)
        )
        last_msg = msg_result.scalar_one_or_none()
        
        items.append(ConversationListItem(
            id=conv.id,
            contact_id=conv.contact_id,
            contact_name=conv.contact.name,
            contact_phone=conv.contact.phone_number,
            contact_avatar=conv.contact.avatar_url,
            last_message=last_msg.content if last_msg else None,
            last_message_at=conv.last_message_at,
            last_message_type=last_msg.message_type if last_msg else "text",
            unread_count=conv.unread_count,
            is_active=conv.is_active,
        ))
    
    return items


@router.get("/conversations/{conversation_id}", response_model=ConversationWithContact)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationWithContact:
    """Get a specific conversation with contact info.
    
    Args:
        conversation_id: The conversation ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Conversation with contact details.
    """
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.contact))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    return ConversationWithContact(
        id=conversation.id,
        contact_id=conversation.contact_id,
        thread_id=conversation.thread_id,
        is_active=conversation.is_active,
        assigned_to=conversation.assigned_to,
        tags=conversation.tags,
        last_message_at=conversation.last_message_at,
        unread_count=conversation.unread_count,
        created_at=conversation.created_at,
        contact=ContactResponse.model_validate(conversation.contact),
    )
