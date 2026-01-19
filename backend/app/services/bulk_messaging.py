"""Bulk messaging service for sending messages to multiple contacts."""

import asyncio
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BulkMessageCampaign, CampaignRecipientLog, Contact, Conversation
from app.schemas import MessageResponse, WSNewMessage
from app.services.whatsapp import WhatsAppAPIError, WhatsAppClient
from app.utils.constants import MessageStatus, SenderType
from app.config import settings
from app.utils.logger import get_logger
from app.websocket.manager import ws_manager

logger = get_logger(__name__)


class BulkMessagingError(Exception):
    """Custom exception for bulk messaging errors."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class BulkMessagingService:
    """Service for handling bulk message campaigns."""
    
    # Meta rate limit: 15 messages per second
    RATE_LIMIT_PER_SECOND = 15
    
    def __init__(self):
        """Initialize bulk messaging service."""
        pass
    
    async def get_contacts_for_campaign(
        self,
        db: AsyncSession,
        campaign: BulkMessageCampaign,
    ) -> List[Contact]:
        """Get contacts for a campaign based on target criteria.
        
        Args:
            db: Database session.
            campaign: Campaign with target_contacts criteria.
        
        Returns:
            List of contacts to send to.
        """
        # If target_contacts is a list of contact IDs
        if campaign.target_contacts and isinstance(campaign.target_contacts, dict):
            if "contact_ids" in campaign.target_contacts:
                contact_ids = campaign.target_contacts["contact_ids"]
                result = await db.execute(
                    select(Contact).where(
                        Contact.id.in_(contact_ids),
                        Contact.user_id == campaign.user_id,
                        Contact.status == "active"
                    )
                )
                return list(result.scalars().all())
            
            # If target_contacts has filter criteria
            if "filters" in campaign.target_contacts:
                filters = campaign.target_contacts["filters"]
                query = select(Contact).where(Contact.user_id == campaign.user_id)
                
                # Apply filters (status, tags, etc.)
                if "status" in filters:
                    query = query.where(Contact.status == filters["status"])
                
                # Add more filter logic as needed
                
                result = await db.execute(query)
                return list(result.scalars().all())
        
        # If no specific criteria, return all active contacts for user
        result = await db.execute(
            select(Contact).where(
                Contact.user_id == campaign.user_id,
                Contact.status == "active"
            )
        )
        return list(result.scalars().all())
    
    async def send_campaign_messages(
        self,
        db: AsyncSession,
        campaign: BulkMessageCampaign,
        contacts: List[Contact],
        whatsapp_client: WhatsAppClient,
    ) -> tuple[int, int]:
        """Send campaign messages to contacts with rate limiting.
        
        Args:
            db: Database session.
            campaign: Campaign to send.
            contacts: List of contacts to send to.
            whatsapp_client: WhatsApp API client.
        
        Returns:
            Tuple of (sent_count, failed_count).
        """
        sent_count = 0
        failed_count = 0
        
        # Update campaign status
        campaign.status = "sending"
        campaign.started_at = datetime.now()
        campaign.total_recipients = len(contacts)
        await db.commit()
        
        # Rate limiting: send in batches
        batch_size = self.RATE_LIMIT_PER_SECOND
        total_batches = (len(contacts) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(contacts))
            batch = contacts[start_idx:end_idx]
            
            # Send batch
            tasks = [
                self._send_to_contact(db, campaign, contact, whatsapp_client)
                for contact in batch
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count results
            for result in results:
                if isinstance(result, Exception):
                    failed_count += 1
                    logger.error(f"Failed to send message: {result}")
                elif isinstance(result, tuple):
                    success, log_id = result
                    if success:
                        sent_count += 1
                    else:
                        failed_count += 1
                elif result:
                    sent_count += 1
                else:
                    failed_count += 1
            
            # Update campaign progress
            campaign.sent_count = sent_count
            campaign.failed_count = failed_count
            await db.commit()
            
            # Rate limiting: wait 1 second between batches (except last batch)
            if batch_idx < total_batches - 1:
                await asyncio.sleep(1)
            
            logger.info(f"Campaign {campaign.id} progress: {sent_count + failed_count}/{len(contacts)}")
        
        return sent_count, failed_count
    
    def _build_template_components(
        self,
        template,
        template_variables: Optional[dict],
    ) -> Optional[list]:
        """Build Meta API components format from template and variables.
        
        Args:
            template: MessageTemplate instance.
            template_variables: Dictionary of variable values (e.g., {"1": "value1", "2": "value2"}).
        
        Returns:
            List of components in Meta API format, or None if no variables.
        """
        if not template_variables:
            return None
        
        components = []
        
        # Build header component if header has variables
        if template.header_type == "TEXT" and template.header_content:
            # Check if header contains variables
            import re
            header_vars = re.findall(r'\{\{(\d+)\}\}', template.header_content)
            if header_vars:
                # Get variable values in order
                header_params = []
                for var_num in header_vars:
                    if var_num in template_variables:
                        header_params.append({
                            "type": "text",
                            "text": template_variables[var_num]
                        })
                if header_params:
                    components.append({
                        "type": "header",
                        "parameters": header_params
                    })
        
        # Build body component - always check body for variables
        if template.body_text:
            import re
            body_vars = re.findall(r'\{\{(\d+)\}\}', template.body_text)
            if body_vars:
                # Get variable values in order (sorted by number)
                body_params = []
                for var_num in sorted(set(body_vars), key=int):
                    if var_num in template_variables:
                        body_params.append({
                            "type": "text",
                            "text": template_variables[var_num]
                        })
                if body_params:
                    components.append({
                        "type": "body",
                        "parameters": body_params
                    })
        
        # Build button components if buttons exist
        if template.buttons and isinstance(template.buttons, dict):
            buttons = template.buttons.get("buttons", [])
            for idx, button in enumerate(buttons):
                if button.get("type") == "QUICK_REPLY" and "text" in button:
                    # Check if button text has variables
                    import re
                    button_vars = re.findall(r'\{\{(\d+)\}\}', button["text"])
                    if button_vars:
                        button_params = []
                        for var_num in button_vars:
                            if var_num in template_variables:
                                button_params.append({
                                    "type": "text",
                                    "text": template_variables[var_num]
                                })
                        if button_params:
                            components.append({
                                "type": "button",
                                "sub_type": "quick_reply",
                                "index": idx,
                                "parameters": button_params
                            })
        
        return components if components else None
    
    async def _send_to_contact(
        self,
        db: AsyncSession,
        campaign: BulkMessageCampaign,
        contact: Contact,
        whatsapp_client: WhatsAppClient,
    ) -> tuple[bool, Optional[int]]:
        """Send campaign message to a single contact.
        
        Args:
            db: Database session.
            campaign: Campaign details.
            contact: Contact to send to.
            whatsapp_client: WhatsApp API client.
        
        Returns:
            Tuple of (success: bool, log_id: Optional[int]).
        """
        from app.models import Message
        
        try:
            # Get or create conversation
            result = await db.execute(
                select(Conversation).where(
                    Conversation.contact_id == contact.id,
                    Conversation.user_id == campaign.user_id,
                    Conversation.is_active == True,  # noqa: E712
                )
            )
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                conversation = Conversation(
                    contact_id=contact.id,
                    user_id=campaign.user_id,
                    is_active=True,
                )
                db.add(conversation)
                await db.flush()
            
            # Prepare message content
            message_content = campaign.message_content
            message_type = "text"
            
            # If using template, resolve template content with variables
            if campaign.template_id:
                from app.models import MessageTemplate
                template_result = await db.execute(
                    select(MessageTemplate).where(MessageTemplate.id == campaign.template_id)
                )
                template = template_result.scalar_one_or_none()
                
                if template:
                    # Resolve template body with variables for display in chat
                    resolved_body = template.body_text or template.content or ""
                    if campaign.template_variables:
                        import re
                        # Replace variables in body text
                        for var_num, var_value in campaign.template_variables.items():
                            resolved_body = resolved_body.replace(f"{{{{{var_num}}}}}", var_value)
                        message_content = resolved_body
                    else:
                        message_content = resolved_body
                    message_type = "template"
            
            # Create message record
            message = Message(
                conversation_id=conversation.id,
                sender_type=SenderType.OUTBOUND.value,
                message_type=message_type,
                content=message_content,
                status=MessageStatus.PENDING.value,
                timestamp=datetime.now(),
            )
            db.add(message)
            await db.flush()
            
            # Create recipient log entry
            cost = settings.meta_cost_per_text_message if message_type == "text" else settings.meta_cost_per_template_message
            recipient_log = CampaignRecipientLog(
                campaign_id=campaign.id,
                contact_id=contact.id,
                phone_number=contact.phone_number,
                status="pending",
                cost=str(round(cost, 4)),
            )
            db.add(recipient_log)
            await db.flush()
            
            # Send via WhatsApp API
            if campaign.template_id:
                # Load template from database (already loaded above)
                if not template:
                    raise ValueError(f"Template {campaign.template_id} not found")
                
                # Build template components
                components = self._build_template_components(
                    template,
                    campaign.template_variables
                )
                
                # Send template message
                response = await whatsapp_client.send_template_message(
                    to=contact.phone_number,
                    template_name=template.name,
                    language_code=template.language or "en",
                    components=components,
                )
            else:
                # Send text message
                response = await whatsapp_client.send_text_message(
                    to=contact.phone_number,
                    message=message_content,
                )
            
            # Update message with WhatsApp ID
            wa_message_id = response.get("messages", [{}])[0].get("id")
            message.message_id = wa_message_id
            message.status = MessageStatus.SENT.value
            
            # Update recipient log
            recipient_log.message_id = message.id
            recipient_log.status = "sent"
            recipient_log.sent_at = datetime.now()
            
            # Update conversation - ensure it's marked as active and has latest message time
            conversation.is_active = True
            conversation.last_message_at = datetime.now()
            
            await db.commit()
            
            # Broadcast message via WebSocket so it appears in chat history
            try:
                await self._broadcast_new_message(message, conversation.id)
            except Exception as e:
                logger.warning(f"Failed to broadcast campaign message via WebSocket: {e}")
            
            logger.debug(f"Sent campaign message to {contact.phone_number}")
            return True, recipient_log.id
            
        except WhatsAppAPIError as e:
            logger.error(f"WhatsApp API error sending to {contact.phone_number}: {e.message}")
            # Update message and log with error
            if 'message' in locals():
                message.status = MessageStatus.FAILED.value
                message.error_message = e.message
            if 'recipient_log' in locals():
                recipient_log.status = "failed"
                recipient_log.failed_at = datetime.now()
                recipient_log.error_message = e.message
            await db.commit()
            return False, recipient_log.id if 'recipient_log' in locals() else None
        except Exception as e:
            logger.error(f"Unexpected error sending to {contact.phone_number}: {e}", exc_info=True)
            if 'message' in locals():
                message.status = MessageStatus.FAILED.value
                message.error_message = str(e)
            if 'recipient_log' in locals():
                recipient_log.status = "failed"
                recipient_log.failed_at = datetime.now()
                recipient_log.error_message = str(e)
            await db.commit()
            return False, recipient_log.id if 'recipient_log' in locals() else None
    
    async def _broadcast_new_message(
        self,
        message,
        conversation_id: int,
    ) -> None:
        """Broadcast new message to WebSocket clients.
        
        Args:
            message: The message to broadcast.
            conversation_id: Conversation ID.
        """
        if not ws_manager:
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
        
        logger.debug(f"Broadcasting campaign message to conversation {conversation_id}")
        
        # Broadcast to conversation-specific connections
        await ws_manager.broadcast_to_conversation(
            conversation_id,
            event_json,
        )
        
        # Also broadcast to global connections (for notification/list updates)
        await ws_manager.broadcast_global(event_json)


# Singleton instance
bulk_messaging_service = BulkMessagingService()
