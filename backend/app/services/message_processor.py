"""Message processing service for handling WhatsApp webhooks."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_context
from app.models import Contact, Conversation, Message
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
                    
                    await self._process_message(message, contact_info)
            
            # Process status updates
            if value.statuses:
                for status in value.statuses:
                    await self._process_status_update(status)
    
    async def _process_message(
        self,
        message: WhatsAppMessage,
        contact_info: Optional[Any] = None,
    ) -> None:
        """Process an incoming WhatsApp message.
        
        Args:
            message: The incoming message.
            contact_info: Optional contact information.
        """
        logger.info(f"Processing message {message.id} from {message.from_}")
        
        async with get_db_context() as db:
            # Get or create contact
            contact = await self._get_or_create_contact(
                db,
                phone_number=message.from_,
                name=contact_info.profile.get("name") if contact_info and contact_info.profile else None,
            )
            
            # Get or create conversation
            conversation = await self._get_or_create_conversation(db, contact.id)
            
            # Extract message content based on type
            content, media_url, media_mime_type, media_filename = await self._extract_message_content(message)
            
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
    
    async def _process_status_update(self, status: WhatsAppStatus) -> None:
        """Process a message status update.
        
        Args:
            status: The status update.
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
    ) -> Contact:
        """Get existing contact or create new one.
        
        Args:
            db: Database session.
            phone_number: Contact phone number.
            name: Optional contact name.
        
        Returns:
            Contact instance.
        """
        result = await db.execute(
            select(Contact).where(Contact.phone_number == phone_number)
        )
        contact = result.scalar_one_or_none()
        
        if contact:
            # Update name if provided and different
            if name and contact.name != name:
                contact.name = name
            return contact
        
        # Create new contact
        contact = Contact(
            phone_number=phone_number,
            name=name,
            status="active",
        )
        db.add(contact)
        await db.flush()
        
        logger.info(f"Created new contact: {phone_number}")
        return contact
    
    async def _get_or_create_conversation(
        self,
        db: AsyncSession,
        contact_id: int,
    ) -> Conversation:
        """Get existing conversation or create new one.
        
        Args:
            db: Database session.
            contact_id: Contact ID.
        
        Returns:
            Conversation instance.
        """
        result = await db.execute(
            select(Conversation).where(
                Conversation.contact_id == contact_id,
                Conversation.is_active == True,  # noqa: E712
            )
        )
        conversation = result.scalar_one_or_none()
        
        if conversation:
            return conversation
        
        # Create new conversation
        conversation = Conversation(
            contact_id=contact_id,
            is_active=True,
        )
        db.add(conversation)
        await db.flush()
        
        logger.info(f"Created new conversation for contact {contact_id}")
        return conversation
    
    async def _extract_message_content(
        self,
        message: WhatsAppMessage,
    ) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Extract content and media info from message.
        
        Args:
            message: The WhatsApp message.
        
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
            media_mime_type = message.image.mime_type
            content = message.image.caption
            # Get media URL from WhatsApp and download it
            try:
                whatsapp_url = await whatsapp_client.get_media_url(message.image.id)
                if whatsapp_url:
                    from app.services.media import download_and_store_media
                    from app.config import settings
                    local_url, _ = await download_and_store_media(
                        whatsapp_url, 
                        media_mime_type or "image/jpeg",
                        settings.whatsapp_api_token
                    )
                    media_url = local_url
            except Exception as e:
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
                        media_filename
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
                        settings.whatsapp_api_token
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
                        settings.whatsapp_api_token
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
                        settings.whatsapp_api_token
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
