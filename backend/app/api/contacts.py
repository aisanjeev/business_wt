"""Contact management endpoints."""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Contact, ContactImport, ContactListMembership, Conversation, Message, User
from app.schemas import (
    ContactCreate,
    ContactImportResponse,
    ContactImportStatus,
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
from app.utils.phone import normalize_phone_number, get_phone_number_variants

logger = get_logger(__name__)

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=PaginatedResponse)
async def get_contacts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    source_filter: Optional[str] = Query(default=None, alias="source"),
    tag_names: Optional[list[str]] = Query(default=None, alias="tags"),
    list_ids: Optional[list[int]] = Query(default=None, alias="lists"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    """Get all contacts with optional filtering.
    
    Args:
        page: Page number.
        page_size: Items per page.
        search: Search query for name or phone.
        status_filter: Filter by status.
        source_filter: Filter by source (imported, chat, manual, or all).
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Paginated list of contacts.
    """
    # Build query - filter by user_id for multi-tenancy
    query = select(Contact).where(Contact.user_id == current_user.id)
    count_query = select(func.count(Contact.id)).where(Contact.user_id == current_user.id)
    
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
    
    # Apply source/category filter
    if source_filter and source_filter != "all":
        query = query.where(Contact.source == source_filter)
        count_query = count_query.where(Contact.source == source_filter)
    
    # Apply tags filter
    if tag_names:
        # Filter contacts that have any of the specified tags
        tag_conditions = []
        for tag in tag_names:
            # JSON contains check (works for PostgreSQL, MySQL 5.7+, etc.)
            tag_conditions.append(
                func.json_contains(Contact.tags, f'"{tag}"')  # type: ignore
            )
        if tag_conditions:
            query = query.where(or_(*tag_conditions))
            count_query = count_query.where(or_(*tag_conditions))
    
    # Apply list_ids filter
    if list_ids:
        # Filter contacts that belong to any of the specified lists
        query = query.join(ContactListMembership).where(
            ContactListMembership.contact_list_id.in_(list_ids)
        )
        count_query = count_query.join(ContactListMembership).where(
            ContactListMembership.contact_list_id.in_(list_ids)
        )
    
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
        .where(Contact.id == contact_id, Contact.user_id == current_user.id)
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
    # Normalize phone number
    normalized_phone = normalize_phone_number(contact_data.phone_number)
    phone_variants = get_phone_number_variants(normalized_phone)
    
    # Check if phone number already exists for this user (check all variants)
    result = await db.execute(
        select(Contact).where(
            or_(Contact.phone_number == variant for variant in phone_variants),
            Contact.user_id == current_user.id
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contact with this phone number already exists",
        )
    
    # Create contact with normalized phone number
    contact_data_dict = contact_data.model_dump()
    contact_data_dict['phone_number'] = normalized_phone
    # Ensure source is set (default to "manual" for manually created contacts)
    contact_data_dict = contact_data.model_dump(exclude={"phone_number"})
    contact_data_dict["phone_number"] = normalized_phone
    if "source" not in contact_data_dict or not contact_data_dict["source"]:
        contact_data_dict["source"] = "manual"
    
    contact = Contact(**contact_data_dict, user_id=current_user.id)
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    
    logger.info(f"Created contact: {contact.phone_number} (source: {contact.source})")
    
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
        select(Contact).where(Contact.id == contact_id, Contact.user_id == current_user.id)
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
        select(Contact).where(Contact.id == contact_id, Contact.user_id == current_user.id)
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
    # Verify contact exists and belongs to user
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.user_id == current_user.id)
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
    # Get active conversations with contact info - filter by user_id
    # Note: MySQL doesn't support NULLS FIRST, so we order by descending
    # (NULLs will be sorted last by default in MySQL with DESC)
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.contact))
        .where(
            Conversation.is_active == True,  # noqa: E712
            Conversation.user_id == current_user.id
        )
        .order_by(Conversation.last_message_at.desc())
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
            last_message_sender_type=last_msg.sender_type if last_msg else None,
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
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
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


@router.delete("/conversations/clear-all", response_model=SuccessResponse)
async def clear_all_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Clear all conversation history for the current user.
    
    This will delete all messages and conversations for the user.
    Contacts are preserved.
    
    Args:
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Success response with count of deleted items.
    """
    # Get count of conversations and messages before deletion
    conversations_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.user_id == current_user.id)
    )
    conversations_count = conversations_result.scalar() or 0
    
    messages_result = await db.execute(
        select(func.count(Message.id))
        .join(Conversation)
        .where(Conversation.user_id == current_user.id)
    )
    messages_count = messages_result.scalar() or 0
    
    # Delete all messages for this user's conversations
    await db.execute(
        delete(Message)
        .where(
            Message.conversation_id.in_(
                select(Conversation.id).where(Conversation.user_id == current_user.id)
            )
        )
    )
    
    # Delete all conversations for this user
    await db.execute(
        delete(Conversation).where(Conversation.user_id == current_user.id)
    )
    
    await db.commit()
    
    logger.info(
        f"Cleared all conversation history for user {current_user.id}: "
        f"{conversations_count} conversations and {messages_count} messages deleted"
    )
    
    return SuccessResponse(
        message=f"Cleared all conversation history. Deleted {conversations_count} conversations and {messages_count} messages."
    )


# Contact Import endpoints

@router.post("/import", response_model=ContactImportResponse, status_code=status.HTTP_201_CREATED)
async def import_contacts(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactImportResponse:
    """Import contacts from CSV, Excel, or JSON file.
    
    Args:
        file: File to import (CSV, Excel, or JSON).
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Import job details.
    """
    from app.services.contact_importer import contact_importer, ContactImportError
    
    # Determine file format
    filename = file.filename or ""
    file_extension = filename.split(".")[-1].lower() if "." in filename else ""
    
    if file_extension in ("csv", "txt"):
        file_format = "csv"
    elif file_extension in ("xlsx", "xls"):
        file_format = "excel"
    elif file_extension == "json":
        file_format = "json"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please use CSV, Excel (.xlsx), or JSON.",
        )
    
    # Validate contact_list_id if provided
    if contact_list_id:
        from app.models import ContactList
        list_result = await db.execute(
            select(ContactList).where(
                ContactList.id == contact_list_id,
                ContactList.user_id == current_user.id
            )
        )
        contact_list = list_result.scalar_one_or_none()
        if not contact_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact list not found",
            )
    
    # Read file content
    file_content = await file.read()
    
    # Create import record
    import_job = ContactImport(
        user_id=current_user.id,
        filename=filename,
        file_format=file_format,
        status="processing",
        total_rows=0,
        successful_rows=0,
        failed_rows=0,
        contact_list_id=contact_list_id,
    )
    db.add(import_job)
    await db.flush()
    
    try:
        # Parse file based on format
        if file_format == "csv":
            contacts_data = await contact_importer.parse_csv(file_content)
        elif file_format == "excel":
            contacts_data = await contact_importer.parse_excel(file_content)
        else:  # json
            contacts_data = await contact_importer.parse_json(file_content)
        
        import_job.total_rows = len(contacts_data)
        
        # Process contacts
        successful = 0
        failed = 0
        errors = []
        
        for idx, contact_data in enumerate(contacts_data, start=1):
            try:
                # Validate contact
                is_valid, error_msg = contact_importer.validate_contact(contact_data)
                if not is_valid:
                    failed += 1
                    errors.append({"row": idx, "error": error_msg})
                    continue
                
                # Extract and normalize data
                normalized_data = contact_importer.extract_contact_data(contact_data)
                phone_number = normalized_data["phone_number"]
                
                # Check if contact already exists for this user
                result = await db.execute(
                    select(Contact).where(
                        Contact.phone_number == phone_number,
                        Contact.user_id == current_user.id
                    )
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing contact
                    if normalized_data.get("name"):
                        existing.name = normalized_data["name"]
                    if normalized_data.get("email"):
                        existing.email = normalized_data["email"]
                    successful += 1
                else:
                    # Create new contact
                    new_contact = Contact(
                        user_id=current_user.id,
                        phone_number=phone_number,
                        name=normalized_data.get("name"),
                        email=normalized_data.get("email"),
                        status="active",
                    )
                    db.add(new_contact)
                    successful += 1
                
            except Exception as e:
                failed += 1
                errors.append({"row": idx, "error": str(e)})
                logger.error(f"Error processing contact row {idx}: {e}")
        
        # Update import job status
        import_job.successful_rows = successful
        import_job.failed_rows = failed
        import_job.error_log = errors if errors else None
        import_job.status = "completed" if failed == 0 else "completed"
        import_job.completed_at = datetime.now()
        
        await db.commit()
        await db.refresh(import_job)
        
        logger.info(f"Contact import completed: {successful} successful, {failed} failed")
        
        return ContactImportResponse.model_validate(import_job)
        
    except ContactImportError as e:
        import_job.status = "failed"
        import_job.error_log = [{"error": e.message}]
        import_job.completed_at = datetime.now()
        await db.commit()
        
        logger.error(f"Contact import failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Import failed: {e.message}",
        )
    except Exception as e:
        import_job.status = "failed"
        import_job.error_log = [{"error": str(e)}]
        import_job.completed_at = datetime.now()
        await db.commit()
        
        logger.error(f"Unexpected error during import: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Import failed due to unexpected error",
        )


@router.get("/import/{import_id}", response_model=ContactImportStatus)
async def get_import_status(
    import_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactImportStatus:
    """Get status of a contact import job.
    
    Args:
        import_id: Import job ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Import job status.
    """
    result = await db.execute(
        select(ContactImport).where(
            ContactImport.id == import_id,
            ContactImport.user_id == current_user.id
        )
    )
    import_job = result.scalar_one_or_none()
    
    if not import_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found",
        )
    
    progress = (import_job.successful_rows + import_job.failed_rows) / import_job.total_rows * 100 if import_job.total_rows > 0 else 0
    
    return ContactImportStatus(
        id=import_job.id,
        status=import_job.status,
        total_rows=import_job.total_rows,
        successful_rows=import_job.successful_rows,
        failed_rows=import_job.failed_rows,
        progress_percentage=progress,
    )
