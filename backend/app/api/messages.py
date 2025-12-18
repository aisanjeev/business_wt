"""Message management endpoints."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Contact, Conversation, Message, User
from app.schemas import (
    ErrorResponse,
    MessageResponse,
    MessageSend,
    PaginatedResponse,
    SuccessResponse,
)
from app.services.auth import get_current_user
from app.services.whatsapp import WhatsAppAPIError, whatsapp_client
from app.utils.constants import MessageStatus, SenderType
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("", response_model=PaginatedResponse)
async def get_messages(
    conversation_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    """Get messages for a conversation with pagination.
    
    Args:
        conversation_id: The conversation ID.
        page: Page number (1-indexed).
        page_size: Number of messages per page.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Paginated list of messages.
    """
    # Verify conversation exists
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    # Get total count
    count_result = await db.execute(
        select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id
        )
    )
    total = count_result.scalar() or 0
    
    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size
    
    # Get messages
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp.desc())
        .offset(offset)
        .limit(page_size)
    )
    messages = result.scalars().all()
    
    # Convert to response models (reverse to show oldest first)
    message_responses = [
        MessageResponse.model_validate(msg) for msg in reversed(messages)
    ]
    
    return PaginatedResponse(
        items=message_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Get a specific message by ID.
    
    Args:
        message_id: The message ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Message details.
    """
    result = await db.execute(
        select(Message).where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )
    
    return MessageResponse.model_validate(message)


@router.post("/send", response_model=MessageResponse)
async def send_message(
    message_data: MessageSend,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Send a message to a WhatsApp contact.
    
    Args:
        message_data: Message content and metadata.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Created message record.
    
    Raises:
        HTTPException: If conversation not found or sending fails.
    """
    # Get conversation with contact
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.contact))
        .where(Conversation.id == message_data.conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    phone_number = conversation.contact.phone_number
    
    # Create message record with pending status
    message = Message(
        conversation_id=conversation.id,
        sender_type=SenderType.OUTBOUND.value,
        message_type=message_data.message_type,
        content=message_data.content,
        status=MessageStatus.PENDING.value,
        timestamp=datetime.now(timezone.utc),
    )
    
    db.add(message)
    await db.flush()
    
    try:
        # Send message via WhatsApp API
        if message_data.template_name:
            # Send template message
            response = await whatsapp_client.send_template_message(
                to=phone_number,
                template_name=message_data.template_name,
                components=message_data.template_variables.get("components") if message_data.template_variables else None,
            )
        else:
            # Send text message
            response = await whatsapp_client.send_text_message(
                to=phone_number,
                message=message_data.content,
            )
        
        # Extract WhatsApp message ID
        wa_message_id = response.get("messages", [{}])[0].get("id")
        
        # Update message with WhatsApp ID and sent status
        message.message_id = wa_message_id
        message.status = MessageStatus.SENT.value
        
        # Update conversation last message time
        conversation.last_message_at = message.timestamp
        
        await db.commit()
        await db.refresh(message)
        
        logger.info(f"Message sent successfully: {wa_message_id}")
        
        return MessageResponse.model_validate(message)
        
    except WhatsAppAPIError as e:
        # Update message with error
        message.status = MessageStatus.FAILED.value
        message.error_message = e.message
        
        await db.commit()
        await db.refresh(message)
        
        logger.error(f"Failed to send message: {e.message}")
        
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"WhatsApp API error: {e.message}",
        )


@router.post("/send/{conversation_id}/template")
async def send_template_message(
    conversation_id: int,
    template_name: str,
    language: str = "en",
    variables: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Send a template message to a conversation.
    
    Args:
        conversation_id: The conversation ID.
        template_name: Name of the approved template.
        language: Template language code.
        variables: Template variables.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Created message record.
    """
    # Get conversation with contact
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
    
    phone_number = conversation.contact.phone_number
    
    # Create message record
    message = Message(
        conversation_id=conversation.id,
        sender_type=SenderType.OUTBOUND.value,
        message_type="template",
        content=f"[Template: {template_name}]",
        status=MessageStatus.PENDING.value,
        timestamp=datetime.now(timezone.utc),
    )
    
    db.add(message)
    await db.flush()
    
    try:
        # Build components from variables
        components = None
        if variables:
            components = variables.get("components", [])
        
        response = await whatsapp_client.send_template_message(
            to=phone_number,
            template_name=template_name,
            language_code=language,
            components=components,
        )
        
        wa_message_id = response.get("messages", [{}])[0].get("id")
        
        message.message_id = wa_message_id
        message.status = MessageStatus.SENT.value
        
        conversation.last_message_at = message.timestamp
        
        await db.commit()
        await db.refresh(message)
        
        return MessageResponse.model_validate(message)
        
    except WhatsAppAPIError as e:
        message.status = MessageStatus.FAILED.value
        message.error_message = e.message
        
        await db.commit()
        await db.refresh(message)
        
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"WhatsApp API error: {e.message}",
        )


@router.post("/{message_id}/mark-read", response_model=SuccessResponse)
async def mark_message_as_read(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Mark a message as read in WhatsApp.
    
    Args:
        message_id: The local message ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Success response.
    """
    result = await db.execute(
        select(Message).where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )
    
    if not message.message_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message has no WhatsApp ID",
        )
    
    # Only mark inbound messages as read
    if message.sender_type != SenderType.INBOUND.value:
        return SuccessResponse(message="Message is not an inbound message")
    
    try:
        await whatsapp_client.mark_message_as_read(message.message_id)
        return SuccessResponse(message="Message marked as read")
    except WhatsAppAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"WhatsApp API error: {e.message}",
        )


@router.post("/conversation/{conversation_id}/mark-all-read", response_model=SuccessResponse)
async def mark_conversation_as_read(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Mark all messages in a conversation as read.
    
    Args:
        conversation_id: The conversation ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Success response.
    """
    # Verify conversation exists
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    # Reset unread count
    conversation.unread_count = 0
    
    # Get latest inbound message to mark as read in WhatsApp
    result = await db.execute(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.sender_type == SenderType.INBOUND.value,
            Message.message_id.isnot(None),
        )
        .order_by(Message.timestamp.desc())
        .limit(1)
    )
    latest_message = result.scalar_one_or_none()
    
    if latest_message:
        try:
            await whatsapp_client.mark_message_as_read(latest_message.message_id)
        except WhatsAppAPIError as e:
            logger.warning(f"Failed to mark message as read in WhatsApp: {e.message}")
    
    await db.commit()
    
    return SuccessResponse(message="Conversation marked as read")
