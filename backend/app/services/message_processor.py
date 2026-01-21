"""Message processing service for handling WhatsApp webhooks."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_context
from app.models import Contact, Conversation, Message, MetaAccountConnection
from app.schemas import (
    MessageResponse,
    WhatsAppEntry,
    WhatsAppMessage,
    WhatsAppStatus,
    WhatsAppWebhookPayload,
    WSNewMessage,
    WSStatusUpdate,
)
from app.services.whatsapp import whatsapp_client
from app.utils.constants import MessageStatus, MessageType, SenderType
from app.utils.logger import get_logger
from app.utils.phone import normalize_phone_number, get_phone_number_variants

logger = get_logger(__name__)


class MessageProcessor:
    """Service for processing incoming WhatsApp messages and status updates."""
    
    def __init__(self, websocket_manager=None):
        """Initialize message processor.
        
        Args:
            websocket_manager: Optional WebSocket manager for broadcasting.
        """
        self.ws_manager = websocket_manager
    
    def set_websocket_manager(self, manager):
        """Set the WebSocket manager for broadcasting.
        
        Args:
            manager: WebSocket connection manager.
        """
        self.ws_manager = manager
    
    async def process_webhook(self, payload: WhatsAppWebhookPayload) -> None:
        """Process incoming webhook payload.
        
        Args:
            payload: The webhook payload from WhatsApp.
        """
        logger.info(f"Processing webhook: {payload.object}")
        
        for entry in payload.entry:
            await self._process_entry(entry)
    
    async def _process_entry(self, entry: WhatsAppEntry) -> None:
        """Process a single webhook entry.
        
        Args:
            entry: Webhook entry containing changes.
        """
        for change in entry.changes:
            if change.field != "messages":
                logger.debug(f"Ignoring non-message field: {change.field}")
                continue
            
            value = change.value
            
            # Extract phone_number_id from metadata to determine user
            phone_number_id = value.metadata.phone_number_id if value.metadata else None
            user_id = None
            
            if phone_number_id:
                # Look up user by phone_number_id
                async with get_db_context() as db:
                    result = await db.execute(
                        select(MetaAccountConnection).where(
                            MetaAccountConnection.phone_number_id == phone_number_id,
                            MetaAccountConnection.status == "connected"
                        )
                    )
                    connection = result.scalar_one_or_none()
                    if connection:
                        user_id = connection.user_id
                        logger.debug(f"Determined user_id {user_id} from phone_number_id {phone_number_id}")
                    else:
                        logger.warning(f"No MetaAccountConnection found for phone_number_id {phone_number_id}")
            
            # Process incoming messages
            if value.messages:
                for message in value.messages:
                    contact_info = None
                    if value.contacts:
                        # Find matching contact info
                        for contact in value.contacts:
                            if contact.wa_id == message.from_:
                                contact_info = contact
                                break
                    
                    await self._process_message(message, contact_info, user_id=user_id)
            
            # Process status updates
            if value.statuses:
                for status in value.statuses:
                    await self._process_status_update(status, user_id=user_id)
    
    async def _process_message(
        self,
        message: WhatsAppMessage,
        contact_info: Optional[Any] = None,
        user_id: Optional[int] = None,
    ) -> None:
        """Process an incoming WhatsApp message.
        
        Args:
            message: The incoming message.
            contact_info: Optional contact information.
            user_id: User ID from MetaAccountConnection (determined from webhook metadata).
        """
        logger.info(f"Processing message {message.id} from {message.from_}")
        
        if not user_id:
            logger.error("Cannot process message: user_id not determined from webhook metadata")
            return
        
        async with get_db_context() as db:
            # Get or create contact
            contact = await self._get_or_create_contact(
                db,
                phone_number=message.from_,
                name=contact_info.profile.get("name") if contact_info and contact_info.profile else None,
                user_id=user_id,
            )
            
            # Get or create conversation
            conversation = await self._get_or_create_conversation(db, contact.id, user_id=user_id)
            
            # Extract message content based on type
            content, media_url, media_mime_type, media_filename = await self._extract_message_content(message, user_id=user_id)
            
            # Create message record
            timestamp = datetime.fromtimestamp(int(message.timestamp), tz=timezone.utc)
            
            db_message = Message(
                conversation_id=conversation.id,
                message_id=message.id,
                sender_type=SenderType.INBOUND.value,
                message_type=message.type,
                content=content,
                media_url=media_url,
                media_mime_type=media_mime_type,
                media_filename=media_filename,
                status=MessageStatus.DELIVERED.value,
                timestamp=timestamp,
            )
            
            db.add(db_message)
            
            # Update conversation
            conversation.last_message_at = timestamp
            conversation.unread_count += 1
            
            await db.commit()
            await db.refresh(db_message)
            
            logger.info(f"Message {message.id} saved to database")
            
            # Broadcast to WebSocket clients
            await self._broadcast_new_message(db_message, conversation.id)
    
    async def _process_status_update(
        self,
        status: WhatsAppStatus,
        user_id: Optional[int] = None,
    ) -> None:
        """Process a message status update.
        
        Args:
            status: The status update.
            user_id: User ID (optional, for future use).
        """
        logger.info(f"Processing status update for message {status.id}: {status.status}")
        
        async with get_db_context() as db:
            # Update message status in database
            result = await db.execute(
                select(Message).where(Message.message_id == status.id)
            )
            message = result.scalar_one_or_none()
            
            if message:
                # Map WhatsApp status to our status
                status_mapping = {
                    "sent": MessageStatus.SENT.value,
                    "delivered": MessageStatus.DELIVERED.value,
                    "read": MessageStatus.READ.value,
                    "failed": MessageStatus.FAILED.value,
                }
                
                new_status = status_mapping.get(status.status, status.status)
                
                # Handle errors
                error_message = None
                if status.errors:
                    error_message = "; ".join(
                        e.get("message", "Unknown error") for e in status.errors
                    )
                
                await db.execute(
                    update(Message)
                    .where(Message.id == message.id)
                    .values(status=new_status, error_message=error_message)
                )
                
                await db.commit()
                
                logger.info(f"Updated message {status.id} status to {new_status}")
                
                # Broadcast status update
                await self._broadcast_status_update(
                    status.id,
                    new_status,
                    message.conversation_id,
                )
            else:
                logger.warning(f"Message {status.id} not found for status update")
    
    async def _get_or_create_contact(
        self,
        db: AsyncSession,
        phone_number: str,
        name: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Contact:
        """Get existing contact or create new one.
        
        Args:
            db: Database session.
            phone_number: Contact phone number.
            name: Optional contact name.
            user_id: User ID for multi-tenancy.
        
        Returns:
            Contact instance.
        """
        if not user_id:
            raise ValueError("user_id is required for multi-tenancy")
        
        # Normalize phone number
        normalized_phone = normalize_phone_number(phone_number)
        phone_variants = get_phone_number_variants(normalized_phone)
        
        # Find contact by normalized phone number or variants
        result = await db.execute(
            select(Contact).where(
                or_(Contact.phone_number == variant for variant in phone_variants),
                Contact.user_id == user_id
            )
        )
        contact = result.scalar_one_or_none()
        
        if contact:
            # Update phone number to normalized format if different
            if contact.phone_number != normalized_phone:
                logger.info(f"Updating contact {contact.id} phone number from {contact.phone_number} to {normalized_phone}")
                contact.phone_number = normalized_phone
                await db.flush()
            
            # Update name if provided and different
            if name and contact.name != name:
                contact.name = name
                await db.flush()
            return contact
        
        # Create new contact with normalized phone number
        contact = Contact(
            phone_number=normalized_phone,
            name=name,
            status="active",
            user_id=user_id,
            source="chat",  # Mark as chat contact (from incoming webhook)
        )
        db.add(contact)
        await db.flush()
        
        logger.info(f"Created new contact: {normalized_phone} for user {user_id} (source: chat)")
        return contact
    
    async def _get_or_create_conversation(
        self,
        db: AsyncSession,
        contact_id: int,
        user_id: Optional[int] = None,
    ) -> Conversation:
        """Get existing conversation or create new one.
        
        Args:
            db: Database session.
            contact_id: Contact ID.
            user_id: User ID for multi-tenancy.
        
        Returns:
            Conversation instance.
        """
        if not user_id:
            raise ValueError("user_id is required for multi-tenancy")
        
        result = await db.execute(
            select(Conversation).where(
                Conversation.contact_id == contact_id,
                Conversation.user_id == user_id,
                Conversation.is_active == True,  # noqa: E712
            )
        )
        conversation = result.scalar_one_or_none()
        
        if conversation:
            return conversation
        
        # Create new conversation
        conversation = Conversation(
            contact_id=contact_id,
            user_id=user_id,
            is_active=True,
        )
        db.add(conversation)
        await db.flush()
        
        logger.info(f"Created new conversation for contact {contact_id}, user {user_id}")
        return conversation
    
    async def _extract_message_content(
        self,
        message: WhatsAppMessage,
        user_id: Optional[int] = None,
    ) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Extract content and media info from message.
        
        Args:
            message: The WhatsApp message.
            user_id: User ID for media storage tracking.
        
        Returns:
            Tuple of (content, media_url, media_mime_type, media_filename).
        """
        content = None
        media_url = None
        media_mime_type = None
        media_filename = None
        
        if message.type == MessageType.TEXT.value and message.text:
            content = message.text.body
        
        elif message.type == MessageType.IMAGE.value and message.image:
            # #region agent log
            import json
            import os
            try:
                with open('d:\\project\\techpath\\business_wt\\.cursor\\debug.log', 'a') as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "image-receive",
                        "hypothesisId": "A",
                        "location": "message_processor.py:_extract_message_content:image",
                        "message": "Processing incoming image message",
                        "data": {
                            "message_id": message.id,
                            "image_id": message.image.id if message.image else None,
                            "mime_type": message.image.mime_type if message.image else None,
                            "has_caption": bool(message.image.caption if message.image else None)
                        },
                        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
                    }) + "\n")
            except: pass
            # #endregion
            
            media_mime_type = message.image.mime_type
            content = message.image.caption
            # Get media URL from WhatsApp and download it
            try:
                # #region agent log
                try:
                    with open('d:\\project\\techpath\\business_wt\\.cursor\\debug.log', 'a') as f:
                        f.write(json.dumps({
                            "sessionId": "debug-session",
                            "runId": "image-receive",
                            "hypothesisId": "B",
                            "location": "message_processor.py:_extract_message_content:before_get_media_url",
                            "message": "About to call get_media_url",
                            "data": {"image_id": message.image.id},
                            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
                        }) + "\n")
                except: pass
                # #endregion
                
                whatsapp_url = await whatsapp_client.get_media_url(message.image.id)
                
                # #region agent log
                try:
                    with open('d:\\project\\techpath\\business_wt\\.cursor\\debug.log', 'a') as f:
                        f.write(json.dumps({
                            "sessionId": "debug-session",
                            "runId": "image-receive",
                            "hypothesisId": "B",
                            "location": "message_processor.py:_extract_message_content:after_get_media_url",
                            "message": "Got media URL from WhatsApp",
                            "data": {
                                "whatsapp_url": whatsapp_url,
                                "url_length": len(whatsapp_url) if whatsapp_url else 0,
                                "has_url": bool(whatsapp_url)
                            },
                            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
                        }) + "\n")
                except: pass
                # #endregion
                
                if whatsapp_url:
                    from app.services.media import download_and_store_media
                    from app.config import settings
                    
                    # #region agent log
                    try:
                        with open('d:\\project\\techpath\\business_wt\\.cursor\\debug.log', 'a') as f:
                            f.write(json.dumps({
                                "sessionId": "debug-session",
                                "runId": "image-receive",
                                "hypothesisId": "C",
                                "location": "message_processor.py:_extract_message_content:before_download",
                                "message": "About to download and store media",
                                "data": {
                                    "whatsapp_url": whatsapp_url[:100] + "..." if len(whatsapp_url) > 100 else whatsapp_url,
                                    "mime_type": media_mime_type or "image/jpeg"
                                },
                                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
                            }) + "\n")
                    except: pass
                    # #endregion
                    
                    local_url, _ = await download_and_store_media(
                        whatsapp_url, 
                        media_mime_type or "image/jpeg",
                        settings.whatsapp_api_token,
                        user_id=user_id
                    )
                    
                    # #region agent log
                    try:
                        with open('d:\\project\\techpath\\business_wt\\.cursor\\debug.log', 'a') as f:
                            f.write(json.dumps({
                                "sessionId": "debug-session",
                                "runId": "image-receive",
                                "hypothesisId": "C",
                                "location": "message_processor.py:_extract_message_content:after_download",
                                "message": "Downloaded and stored media",
                                "data": {
                                    "local_url": local_url,
                                    "has_local_url": bool(local_url)
                                },
                                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
                            }) + "\n")
                    except: pass
                    # #endregion
                    
                    media_url = local_url
                    
                    # #region agent log
                    try:
                        with open('d:\\project\\techpath\\business_wt\\.cursor\\debug.log', 'a') as f:
                            f.write(json.dumps({
                                "sessionId": "debug-session",
                                "runId": "image-receive",
                                "hypothesisId": "D",
                                "location": "message_processor.py:_extract_message_content:final",
                                "message": "Final media_url value",
                                "data": {
                                    "media_url": media_url,
                                    "content": content,
                                    "media_mime_type": media_mime_type
                                },
                                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
                            }) + "\n")
                    except: pass
                    # #endregion
            except Exception as e:
                # #region agent log
                try:
                    with open('d:\\project\\techpath\\business_wt\\.cursor\\debug.log', 'a') as f:
                        f.write(json.dumps({
                            "sessionId": "debug-session",
                            "runId": "image-receive",
                            "hypothesisId": "E",
                            "location": "message_processor.py:_extract_message_content:error",
                            "message": "Error getting/downloading image",
                            "data": {
                                "error_type": type(e).__name__,
                                "error_message": str(e)
                            },
                            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
                        }) + "\n")
                except: pass
                # #endregion
                logger.error(f"Failed to get/download image: {e}")
        
        elif message.type == MessageType.DOCUMENT.value and message.document:
            media_mime_type = message.document.mime_type
            media_filename = message.document.filename
            content = message.document.caption
            try:
                whatsapp_url = await whatsapp_client.get_media_url(message.document.id)
                if whatsapp_url:
                    from app.services.media import download_and_store_media
                    from app.config import settings
                    local_url, _ = await download_and_store_media(
                        whatsapp_url,
                        media_mime_type or "application/octet-stream",
                        settings.whatsapp_api_token,
                        user_id=user_id,
                        original_filename=media_filename
                    )
                    media_url = local_url
            except Exception as e:
                logger.error(f"Failed to get/download document: {e}")
        
        elif message.type == MessageType.AUDIO.value and message.audio:
            media_mime_type = message.audio.mime_type
            try:
                whatsapp_url = await whatsapp_client.get_media_url(message.audio.id)
                if whatsapp_url:
                    from app.services.media import download_and_store_media
                    from app.config import settings
                    local_url, _ = await download_and_store_media(
                        whatsapp_url,
                        media_mime_type or "audio/ogg",
                        settings.whatsapp_api_token,
                        user_id=user_id
                    )
                    media_url = local_url
            except Exception as e:
                logger.error(f"Failed to get/download audio: {e}")
        
        elif message.type == MessageType.VIDEO.value and message.video:
            media_mime_type = message.video.mime_type
            content = message.video.caption
            try:
                whatsapp_url = await whatsapp_client.get_media_url(message.video.id)
                if whatsapp_url:
                    from app.services.media import download_and_store_media
                    from app.config import settings
                    local_url, _ = await download_and_store_media(
                        whatsapp_url,
                        media_mime_type or "video/mp4",
                        settings.whatsapp_api_token,
                        user_id=user_id
                    )
                    media_url = local_url
            except Exception as e:
                logger.error(f"Failed to get/download video: {e}")
        
        elif message.type == MessageType.STICKER.value and message.sticker:
            media_mime_type = message.sticker.mime_type
            try:
                whatsapp_url = await whatsapp_client.get_media_url(message.sticker.id)
                if whatsapp_url:
                    from app.services.media import download_and_store_media
                    from app.config import settings
                    local_url, _ = await download_and_store_media(
                        whatsapp_url,
                        media_mime_type or "image/webp",
                        settings.whatsapp_api_token,
                        user_id=user_id
                    )
                    media_url = local_url
            except Exception as e:
                logger.error(f"Failed to get/download sticker: {e}")
        
        return content, media_url, media_mime_type, media_filename
    
    async def _broadcast_new_message(
        self,
        message: Message,
        conversation_id: int,
    ) -> None:
        """Broadcast new message to WebSocket clients.
        
        Args:
            message: The message to broadcast.
            conversation_id: Conversation ID.
        """
        if not self.ws_manager:
            return
        
        message_response = MessageResponse(
            id=message.id,
            conversation_id=message.conversation_id,
            message_id=message.message_id,
            sender_type=message.sender_type,
            message_type=message.message_type,
            content=message.content,
            media_url=message.media_url,
            media_mime_type=message.media_mime_type,
            media_filename=message.media_filename,
            status=message.status,
            error_message=message.error_message,
            timestamp=message.timestamp,
            created_at=message.created_at,
        )
        
        event = WSNewMessage(
            type="new_message",
            message=message_response,
            conversation_id=conversation_id,
        )
        
        event_json = event.model_dump_json()
        
        logger.info(f"Broadcasting new message to conversation {conversation_id} and global")
        
        # Broadcast to conversation-specific connections
        await self.ws_manager.broadcast_to_conversation(
            conversation_id,
            event_json,
        )
        
        # Also broadcast to global connections (for notification/list updates)
        await self.ws_manager.broadcast_global(event_json)
        
        logger.info("Broadcast complete")
    
    async def _broadcast_status_update(
        self,
        message_id: str,
        status: str,
        conversation_id: int,
    ) -> None:
        """Broadcast status update to WebSocket clients.
        
        Args:
            message_id: The message ID.
            status: New status.
            conversation_id: Conversation ID.
        """
        if not self.ws_manager:
            return
        
        event = WSStatusUpdate(
            type="status_update",
            message_id=message_id,
            status=status,
            conversation_id=conversation_id,
        )
        
        await self.ws_manager.broadcast_to_conversation(
            conversation_id,
            event.model_dump_json(),
        )


# Singleton instance
message_processor = MessageProcessor()
