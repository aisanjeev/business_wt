"""Message management endpoints."""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Contact, Conversation, Message, MetaAccountConnection, User
from app.schemas import (
    ErrorResponse,
    MessageResponse,
    MessageSend,
    MessageSendByPhone,
    PaginatedResponse,
    SuccessResponse,
)
from app.services.auth import get_current_user
from app.services.media import delete_media
from app.services.whatsapp import WhatsAppAPIError, get_whatsapp_client_for_user
from app.utils.constants import MessageStatus, SenderType
from app.utils.logger import get_logger
from app.utils.phone import normalize_phone_number, get_phone_number_variants

logger = get_logger(__name__)

# Retry configuration for media uploads
MAX_RETRY_ATTEMPTS = 3
INITIAL_RETRY_DELAY = 1  # seconds
MAX_RETRY_DELAY = 10  # seconds

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
    # Verify conversation exists and belongs to user
    result = await db.execute(
        select(Conversation).where(
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


@router.delete("/{message_id}", response_model=SuccessResponse)
async def delete_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Delete a message and its associated media if any.
    
    Args:
        message_id: The message ID to delete.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Success response.
    """
    # Get message with conversation to verify ownership
    result = await db.execute(
        select(Message)
        .join(Conversation)
        .where(Message.id == message_id)
        .where(Conversation.user_id == current_user.id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or you don't have permission to delete it",
        )
    
    # Delete associated media if exists
    if message.media_url:
        try:
            media_deleted = await delete_media(message.media_url, user_id=current_user.id)
            if media_deleted:
                logger.info(f"Deleted media for message {message_id}: {message.media_url}")
            else:
                logger.warning(f"Failed to delete media for message {message_id}: {message.media_url}")
        except Exception as e:
            logger.error(f"Error deleting media for message {message_id}: {e}")
            # Continue with message deletion even if media deletion fails
    
    # Delete message from database
    await db.delete(message)
    await db.commit()
    
    logger.info(f"Message {message_id} deleted by user {current_user.id}")
    
    return SuccessResponse(message="Message deleted successfully")


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
    # Get conversation with contact - verify user ownership
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.contact))
        .where(
            Conversation.id == message_data.conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    phone_number = conversation.contact.phone_number
    
    # Get WhatsApp client configured for this user
    whatsapp_client = await get_whatsapp_client_for_user(db, current_user.id)
    
    # #region agent log
    import json
    import os
    try:
        with open('d:\\project\\techpath\\business_wt\\.cursor\\debug.log', 'a') as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "image-send",
                "hypothesisId": "F",
                "location": "messages.py:send_message:entry",
                "message": "Send message endpoint called",
                "data": {
                    "conversation_id": message_data.conversation_id,
                    "message_type": message_data.message_type,
                    "has_content": bool(message_data.content),
                    "content_length": len(message_data.content) if message_data.content else 0,
                    "has_template": bool(message_data.template_name)
                },
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }) + "\n")
    except: pass
    # #endregion
    
    # Create message record with pending status
    message = Message(
        conversation_id=conversation.id,
        sender_type=SenderType.OUTBOUND.value,
        message_type=message_data.message_type,
        content=message_data.content,
        media_url=message_data.media_url,
        media_mime_type=message_data.media_mime_type,
        status=MessageStatus.PENDING.value,
        timestamp=datetime.now(timezone.utc),
    )
    
    db.add(message)
    await db.flush()
    
    try:
        # Send message via WhatsApp API
        if message_data.template_name:
            # Send template message with retry
            for send_attempt in range(MAX_RETRY_ATTEMPTS):
                try:
                    response = await whatsapp_client.send_template_message(
                        to=phone_number,
                        template_name=message_data.template_name,
                        components=message_data.template_variables.get("components") if message_data.template_variables else None,
                    )
                    logger.info(f"Template message sent successfully (attempt {send_attempt + 1})")
                    break  # Success, exit retry loop
                except Exception as e:
                    is_last_attempt = (send_attempt == MAX_RETRY_ATTEMPTS - 1)
                    if is_last_attempt:
                        logger.error(f"Failed to send template message after {MAX_RETRY_ATTEMPTS} attempts: {e}")
                        raise
                    else:
                        delay = min(INITIAL_RETRY_DELAY * (2 ** send_attempt), MAX_RETRY_DELAY)
                        logger.warning(f"Template message send attempt {send_attempt + 1} failed: {e}. Retrying in {delay} seconds...")
                        await asyncio.sleep(delay)
        elif message_data.message_type == "image" and message_data.media_url:
            # Send image message
            # If it's a local file, upload it to WhatsApp first
            if message_data.media_url.startswith("/api/media/"):
                # Media file - use local filesystem directly (optimized: local first, Azure in background)
                from pathlib import Path
                import os
                
                # Extract subdir and filename from URL
                # /api/media/images/filename.jpg -> media/images/filename.jpg
                media_path = message_data.media_url.replace("/api/media/", "media/")
                file_path = Path(media_path)
                
                logger.info(f"Using local media file: {file_path}")
                
                if not file_path.exists():
                    logger.error(f"Media file not found: {file_path}")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Media file not found",
                    )
                
                temp_file_path = str(file_path)
                
                # Upload to WhatsApp and get media ID with retry logic
                image_id = None
                last_error = None
                
                for attempt in range(MAX_RETRY_ATTEMPTS):
                    try:
                        image_id = await whatsapp_client.upload_media(
                            temp_file_path,
                            message_data.media_mime_type or "image/jpeg",
                        )
                        logger.info(f"Media uploaded to WhatsApp. Media ID: {image_id} (attempt {attempt + 1})")
                        break  # Success, exit retry loop
                    except Exception as e:
                        last_error = e
                        is_last_attempt = (attempt == MAX_RETRY_ATTEMPTS - 1)
                        
                        if is_last_attempt:
                            logger.error(f"Failed to upload media to WhatsApp after {MAX_RETRY_ATTEMPTS} attempts: {e}")
                        else:
                            # Calculate exponential backoff delay
                            delay = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                            logger.warning(
                                f"Media upload attempt {attempt + 1} failed: {e}. "
                                f"Retrying in {delay} seconds..."
                            )
                            await asyncio.sleep(delay)
                
                # If all retries failed, raise error
                if image_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Failed to upload media to WhatsApp after {MAX_RETRY_ATTEMPTS} attempts: {str(last_error)}",
                    )
                
                # Send using media ID with retry
                for send_attempt in range(MAX_RETRY_ATTEMPTS):
                    try:
                        response = await whatsapp_client.send_image_message(
                            to=phone_number,
                            image_id=image_id,
                            caption=message_data.content if message_data.content else None,
                        )
                        logger.info(f"Image message sent successfully (attempt {send_attempt + 1})")
                        break  # Success, exit retry loop
                    except Exception as e:
                        is_last_attempt = (send_attempt == MAX_RETRY_ATTEMPTS - 1)
                        if is_last_attempt:
                            logger.error(f"Failed to send image message after {MAX_RETRY_ATTEMPTS} attempts: {e}")
                            raise
                        else:
                            delay = min(INITIAL_RETRY_DELAY * (2 ** send_attempt), MAX_RETRY_DELAY)
                            logger.warning(f"Image message send attempt {send_attempt + 1} failed: {e}. Retrying in {delay} seconds...")
                            await asyncio.sleep(delay)
            else:
                # External URL - use directly with retry
                for send_attempt in range(MAX_RETRY_ATTEMPTS):
                    try:
                        response = await whatsapp_client.send_image_message(
                            to=phone_number,
                            image_url=message_data.media_url,
                            caption=message_data.content if message_data.content else None,
                        )
                        logger.info(f"Image message sent successfully (attempt {send_attempt + 1})")
                        break  # Success, exit retry loop
                    except Exception as e:
                        is_last_attempt = (send_attempt == MAX_RETRY_ATTEMPTS - 1)
                        if is_last_attempt:
                            logger.error(f"Failed to send image message after {MAX_RETRY_ATTEMPTS} attempts: {e}")
                            raise
                        else:
                            delay = min(INITIAL_RETRY_DELAY * (2 ** send_attempt), MAX_RETRY_DELAY)
                            logger.warning(f"Image message send attempt {send_attempt + 1} failed: {e}. Retrying in {delay} seconds...")
                            await asyncio.sleep(delay)
        else:
            # Send text message with retry
            for send_attempt in range(MAX_RETRY_ATTEMPTS):
                try:
                    response = await whatsapp_client.send_text_message(
                        to=phone_number,
                        message=message_data.content,
                    )
                    logger.info(f"Text message sent successfully (attempt {send_attempt + 1})")
                    break  # Success, exit retry loop
                except Exception as e:
                    is_last_attempt = (send_attempt == MAX_RETRY_ATTEMPTS - 1)
                    if is_last_attempt:
                        logger.error(f"Failed to send text message after {MAX_RETRY_ATTEMPTS} attempts: {e}")
                        raise
                    else:
                        delay = min(INITIAL_RETRY_DELAY * (2 ** send_attempt), MAX_RETRY_DELAY)
                        logger.warning(f"Text message send attempt {send_attempt + 1} failed: {e}. Retrying in {delay} seconds...")
                        await asyncio.sleep(delay)
        
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
    # Get conversation with contact - verify user ownership
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
    
    phone_number = conversation.contact.phone_number
    
    # Get WhatsApp client configured for this user
    whatsapp_client = await get_whatsapp_client_for_user(db, current_user.id)
    
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
    # Get message via conversation to verify user ownership
    result = await db.execute(
        select(Message)
        .join(Conversation)
        .where(
            Message.id == message_id,
            Conversation.user_id == current_user.id
        )
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
    # Verify conversation exists and belongs to user
    result = await db.execute(
        select(Conversation).where(
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


@router.post("/send-by-phone", response_model=MessageResponse)
async def send_message_by_phone(
    message_data: MessageSendByPhone,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Send a message to a WhatsApp phone number.
    
    This endpoint will find or create a contact and conversation for the given phone number,
    then send the message. Phone numbers are normalized (e.g., Indian numbers get +91 prefix).
    If multiple conversations exist for the same normalized phone number, they are merged.
    
    Args:
        message_data: Message content and phone number.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Created message record.
    
    Raises:
        HTTPException: If sending fails.
    """
    # Normalize phone number
    normalized_phone = normalize_phone_number(message_data.phone_number)
    phone_variants = get_phone_number_variants(normalized_phone)
    
    logger.info(f"Normalized phone number: {message_data.phone_number} -> {normalized_phone}")
    
    # Find contact by normalized phone number or variants
    result = await db.execute(
        select(Contact).where(
            or_(Contact.phone_number == variant for variant in phone_variants),
            Contact.user_id == current_user.id
        )
    )
    contacts = result.scalars().all()
    
    if contacts:
        # If multiple contacts found (duplicates with different formats), use the first one
        # that already has the normalized phone number, or the first one if none do
        # Then merge all duplicates into it
        
        # Find the contact that already has the normalized phone number (if any)
        primary_contact = None
        for c in contacts:
            if c.phone_number == normalized_phone:
                primary_contact = c
                break
        
        # If no contact has the normalized phone number, use the first one
        if not primary_contact:
            primary_contact = contacts[0]
        
        contact = primary_contact
        
        # If there are duplicate contacts, merge them FIRST (before updating phone number)
        # This prevents unique constraint violations
        if len(contacts) > 1:
            logger.warning(f"Found {len(contacts)} duplicate contacts for phone {normalized_phone}, merging into contact {contact.id}")
            other_contacts = [c for c in contacts if c.id != contact.id]
            other_contact_ids = [c.id for c in other_contacts]
            
            # Get all conversations for duplicate contacts
            dup_conv_result = await db.execute(
                select(Conversation).where(Conversation.contact_id.in_(other_contact_ids))
            )
            duplicate_conversations = dup_conv_result.scalars().all()
            
            # Get or create primary conversation for the main contact
            primary_conv_result = await db.execute(
                select(Conversation).where(
                    Conversation.contact_id == contact.id,
                    Conversation.user_id == current_user.id,
                    Conversation.is_active == True  # noqa: E712
                ).order_by(Conversation.last_message_at.desc(), Conversation.created_at.desc())
            )
            primary_conversation = primary_conv_result.scalar_one_or_none()
            
            if not primary_conversation:
                # Create primary conversation if it doesn't exist
                primary_conversation = Conversation(
                    user_id=current_user.id,
                    contact_id=contact.id,
                    is_active=True,
                )
                db.add(primary_conversation)
                await db.flush()
            
            # Move messages from duplicate conversations to primary conversation
            for dup_conv in duplicate_conversations:
                await db.execute(
                    Message.__table__.update()
                    .where(Message.conversation_id == dup_conv.id)
                    .values(conversation_id=primary_conversation.id)
                )
                # Deactivate duplicate conversation
                dup_conv.is_active = False
            
            # Update conversations to point to primary contact
            await db.execute(
                Conversation.__table__.update()
                .where(Conversation.contact_id.in_(other_contact_ids))
                .values(contact_id=contact.id)
            )
            
            await db.flush()
            
            # Delete duplicate contacts (do this AFTER updating conversations to avoid foreign key issues)
            await db.execute(
                delete(Contact).where(Contact.id.in_(other_contact_ids))
            )
            
            await db.commit()
            await db.refresh(contact)
            
            logger.info(f"Merged {len(contacts) - 1} duplicate contacts into contact {contact.id}")
        
        # Now safely update contact phone number to normalized format if different
        # (duplicates are already deleted, so no constraint violation)
        if contact.phone_number != normalized_phone:
            logger.info(f"Updating contact {contact.id} phone number from {contact.phone_number} to {normalized_phone}")
            contact.phone_number = normalized_phone
            await db.flush()
        
        # Update contact name if provided
        if message_data.contact_name and message_data.contact_name != contact.name:
            contact.name = message_data.contact_name
            await db.flush()
    else:
        # Create new contact with normalized phone number
        contact = Contact(
            user_id=current_user.id,
            phone_number=normalized_phone,
            name=message_data.contact_name or normalized_phone,
            status="active",
            source="chat",  # Mark as chat contact
        )
        db.add(contact)
        await db.flush()
        logger.info(f"Created new contact for phone number: {normalized_phone} (source: chat)")
    
    # Find all active conversations for this contact
    result = await db.execute(
        select(Conversation).where(
            Conversation.contact_id == contact.id,
            Conversation.user_id == current_user.id,
            Conversation.is_active == True  # noqa: E712
        ).order_by(Conversation.last_message_at.desc(), Conversation.created_at.desc())
    )
    conversations = result.scalars().all()
    
    if conversations:
        # Use the most recent conversation (first one after ordering)
        conversation = conversations[0]
        
        # If there are multiple conversations, merge them by moving messages to the primary one
        if len(conversations) > 1:
            logger.info(f"Found {len(conversations)} conversations for contact {contact.id}, merging into conversation {conversation.id}")
            
            # Move messages from other conversations to the primary one
            other_conversation_ids = [c.id for c in conversations[1:]]
            
            # Update messages to point to primary conversation
            await db.execute(
                Message.__table__.update()
                .where(Message.conversation_id.in_(other_conversation_ids))
                .values(conversation_id=conversation.id)
            )
            
            # Deactivate other conversations
            for other_conv in conversations[1:]:
                other_conv.is_active = False
                logger.info(f"Deactivated conversation {other_conv.id}")
            
            await db.flush()
    else:
        # Create new conversation
        conversation = Conversation(
            user_id=current_user.id,
            contact_id=contact.id,
            is_active=True,
        )
        db.add(conversation)
        await db.flush()
        logger.info(f"Created new conversation for contact: {contact.id}")
    
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
    
    # Get WhatsApp client configured for this user
    whatsapp_client = await get_whatsapp_client_for_user(db, current_user.id)
    
    try:
        # Send message via WhatsApp API (use normalized phone number)
        response = await whatsapp_client.send_text_message(
            to=normalized_phone,
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
        
        logger.info(f"Message sent successfully to {normalized_phone}: {wa_message_id}")
        
        return MessageResponse.model_validate(message)
        
    except WhatsAppAPIError as e:
        # Update message with error
        message.status = MessageStatus.FAILED.value
        message.error_message = e.message
        
        await db.commit()
        await db.refresh(message)
        
        logger.error(f"Failed to send message to {normalized_phone}: {e.message}")
        
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"WhatsApp API error: {e.message}",
        )
