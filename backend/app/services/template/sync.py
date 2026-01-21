"""Template synchronization service for bidirectional sync with Meta API."""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MessageTemplate, MetaAccountConnection
from app.services.meta_oauth import MetaOAuthService
from app.services.template.meta_api import MetaTemplateAPIClient, MetaTemplateAPIError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TemplateSyncService:
    """Service for synchronizing templates between local database and Meta API."""
    
    def __init__(self):
        """Initialize sync service."""
        pass  # Don't create client here, create it per-request with user's token
    
    def _get_meta_client(self, access_token: Optional[str] = None) -> MetaTemplateAPIClient:
        """Get a Meta API client with the specified access token."""
        return MetaTemplateAPIClient(access_token=access_token)
    
    async def sync_from_meta(
        self,
        db: AsyncSession,
        user_id: int,
        waba_id: str,
    ) -> dict:
        """Sync templates from Meta API to local database.
        
        Args:
            db: Database session.
            user_id: User ID to associate templates with.
            waba_id: WhatsApp Business Account ID.
        
        Returns:
            Sync statistics: {
                "created": number of new templates,
                "updated": number of updated templates,
                "errors": list of error messages
            }
        """
        stats = {
            "created": 0,
            "updated": 0,
            "errors": [],
        }
        
        # Get user's access token from MetaAccountConnection
        conn_result = await db.execute(
            select(MetaAccountConnection).where(
                MetaAccountConnection.user_id == user_id,
                MetaAccountConnection.status == "connected"
            )
        )
        connection = conn_result.scalar_one_or_none()
        
        if not connection:
            return {
                "created": 0,
                "updated": 0,
                "errors": ["No connected Meta account found for user"],
            }
        
        # Use user's access token (assuming it's stored as-is, not encrypted in this case)
        # TODO: If tokens are encrypted, decrypt here
        access_token = connection.access_token
        
        # If waba_id is actually a Meta Business Account ID, we need to get the WABA ID
        # Try to get WABA from phone_number_id or fetch from API
        actual_waba_id = waba_id
        
        # If the provided ID looks like a Meta Business Account ID (starts with digits),
        # try to get the WhatsApp Business Account ID
        if waba_id == connection.meta_business_account_id:
            # This is a Meta Business Account ID, not a WABA ID
            # Try to get WABA from the phone_number_id's parent account, or fetch it
            try:
                oauth_service = MetaOAuthService()
                wabas = await oauth_service.get_whatsapp_business_accounts(
                    business_account_id=waba_id,
                    access_token=access_token
                )
                if wabas and len(wabas) > 0:
                    # Use the first WABA
                    actual_waba_id = wabas[0].get("id")
                    logger.info(f"Resolved WABA ID {actual_waba_id} from Business Account {waba_id}")
                else:
                    # If we can't get WABA, try using phone_number_id's account
                    # The phone_number_id endpoint might give us the WABA
                    logger.warning(f"Could not fetch WABA from Business Account {waba_id}, using provided ID")
            except Exception as e:
                logger.warning(f"Could not resolve WABA ID: {e}, using provided ID {waba_id}")
        
        # Create client with user's token
        meta_client = self._get_meta_client(access_token=access_token)
        
        try:
            # Fetch all templates from Meta
            response = await meta_client.get_templates(actual_waba_id)
            meta_templates = response.get("data", [])
            
            logger.info(f"Found {len(meta_templates)} templates in Meta API for WABA {waba_id}")
            
            for meta_template in meta_templates:
                try:
                    # Parse Meta template format
                    parsed = meta_client.parse_template_from_meta(meta_template)
                    
                    # Check if template exists locally by meta_template_id or name+language
                    meta_template_id = parsed.get("meta_template_id")
                    template_name = parsed.get("name")
                    language = parsed.get("language", "en")
                    
                    # Try to find existing template
                    existing = None
                    if meta_template_id:
                        result = await db.execute(
                            select(MessageTemplate).where(
                                MessageTemplate.meta_template_id == meta_template_id,
                                MessageTemplate.user_id == user_id,
                            )
                        )
                        existing = result.scalar_one_or_none()
                    
                    if not existing:
                        # Try by name and language
                        result = await db.execute(
                            select(MessageTemplate).where(
                                MessageTemplate.name == template_name,
                                MessageTemplate.language == language,
                                MessageTemplate.user_id == user_id,
                            )
                        )
                        existing = result.scalar_one_or_none()
                    
                    if existing:
                        # Update existing template
                        existing.meta_template_id = meta_template_id or existing.meta_template_id
                        existing.waba_id = waba_id
                        existing.status = parsed.get("status", existing.status)
                        existing.category = parsed.get("category", existing.category)
                        existing.header_type = parsed.get("header_type") or existing.header_type
                        existing.header_content = parsed.get("header_content") or existing.header_content
                        existing.body_text = parsed.get("body_text") or existing.body_text or existing.content
                        existing.footer_text = parsed.get("footer_text") or existing.footer_text
                        existing.buttons = parsed.get("buttons") or existing.buttons
                        existing.updated_at = datetime.utcnow()
                        
                        stats["updated"] += 1
                        logger.info(f"Updated template '{template_name}' from Meta")
                    else:
                        # Create new template
                        new_template = MessageTemplate(
                            user_id=user_id,
                            name=template_name,
                            meta_template_id=meta_template_id,
                            waba_id=waba_id,
                            category=parsed.get("category", "utility"),
                            language=language,
                            status=parsed.get("status", "PENDING"),
                            header_type=parsed.get("header_type"),
                            header_content=parsed.get("header_content"),
                            body_text=parsed.get("body_text", ""),
                            footer_text=parsed.get("footer_text"),
                            buttons=parsed.get("buttons"),
                            content=parsed.get("body_text", ""),  # Legacy field
                        )
                        db.add(new_template)
                        stats["created"] += 1
                        logger.info(f"Created template '{template_name}' from Meta")
                
                except Exception as e:
                    error_msg = f"Error syncing template '{meta_template.get('name', 'unknown')}': {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    stats["errors"].append(error_msg)
            
            await db.commit()
            logger.info(f"Sync from Meta completed: {stats['created']} created, {stats['updated']} updated")
            
        except MetaTemplateAPIError as e:
            error_msg = f"Meta API error during sync: {e.message}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during sync: {str(e)}"
            logger.error(error_msg, exc_info=True)
            stats["errors"].append(error_msg)
        
        return stats
    
    async def sync_to_meta(
        self,
        db: AsyncSession,
        user_id: int,
        template_id: int,
    ) -> dict:
        """Sync a local template to Meta API (create or update).
        
        Args:
            db: Database session.
            user_id: User ID (for verification).
            template_id: Local template ID.
        
        Returns:
            Result dict with success status and template data or error.
        """
        # Get template from database
        result = await db.execute(
            select(MessageTemplate).where(
                MessageTemplate.id == template_id,
                MessageTemplate.user_id == user_id,
            )
        )
        template = result.scalar_one_or_none()
        
        if not template:
            return {
                "success": False,
                "error": "Template not found",
            }
        
        # Get user's access token from MetaAccountConnection
        conn_result = await db.execute(
            select(MetaAccountConnection).where(
                MetaAccountConnection.user_id == user_id,
                MetaAccountConnection.status == "connected"
            )
        )
        connection = conn_result.scalar_one_or_none()
        
        if not connection:
            return {
                "success": False,
                "error": "No connected Meta account found for user",
            }
        
        # Use user's access token
        access_token = connection.access_token
        
        # Resolve WABA ID - check if template.waba_id is actually a Business Account ID
        waba_id = template.waba_id
        
        # If waba_id matches the Business Account ID, we need to get the actual WABA ID
        if not waba_id or waba_id == connection.meta_business_account_id:
            logger.info(f"Resolving WABA ID from Business Account {connection.meta_business_account_id}")
            try:
                oauth_service = MetaOAuthService()
                wabas = await oauth_service.get_whatsapp_business_accounts(
                    business_account_id=connection.meta_business_account_id,
                    access_token=access_token
                )
                if wabas and len(wabas) > 0:
                    # Use the first WABA
                    waba_id = wabas[0].get("id")
                    logger.info(f"Resolved WABA ID: {waba_id}")
                    
                    # Update template with correct WABA ID
                    template.waba_id = waba_id
                    await db.commit()
                else:
                    return {
                        "success": False,
                        "error": "Could not find WhatsApp Business Account. Please ensure your Meta account has a WhatsApp Business Account set up.",
                    }
            except Exception as e:
                logger.error(f"Error resolving WABA ID: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": f"Could not resolve WhatsApp Business Account ID: {str(e)}",
                }
        
        if not waba_id:
            return {
                "success": False,
                "error": "WABA ID not set for template and could not be resolved",
            }
        
        meta_client = self._get_meta_client(access_token=access_token)
        
        try:
            # Convert local template to Meta API format
            meta_template_data = self._convert_to_meta_format(template)
            
            logger.info(f"Submitting template '{template.name}' to Meta API with WABA ID: {waba_id}")
            
            if template.meta_template_id:
                # Template already exists in Meta - we can't update via API
                # Meta doesn't support template updates, only create/delete
                return {
                    "success": False,
                    "error": "Template already exists in Meta. Updates are not supported via API.",
                    "meta_template_id": template.meta_template_id,
                }
            else:
                # Create new template in Meta
                response = await meta_client.create_template(
                    waba_id=waba_id,
                    template_data=meta_template_data,
                )
                
                # Update local template with Meta response
                if response.get("id"):
                    template.meta_template_id = response.get("id")
                    template.status = response.get("status", "PENDING")
                    template.updated_at = datetime.utcnow()
                    await db.commit()
                
                return {
                    "success": True,
                    "meta_template_id": response.get("id"),
                    "status": response.get("status", "PENDING"),
                }
        
        except MetaTemplateAPIError as e:
            logger.error(f"Meta API error syncing template {template_id}: {e.message}")
            return {
                "success": False,
                "error": e.message,
                "error_code": e.status_code,
            }
        except Exception as e:
            logger.error(f"Unexpected error syncing template {template_id}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }
    
    async def handle_webhook_status_update(
        self,
        db: AsyncSession,
        webhook_data: dict,
    ) -> Optional[MessageTemplate]:
        """Handle template status update from Meta webhook.
        
        Args:
            db: Database session.
            webhook_data: Webhook payload from Meta:
                {
                    "event": "MESSAGE_TEMPLATE_STATUS_UPDATE",
                    "message_template_id": "...",
                    "message_template_name": "...",
                    "message_template_language": "...",
                    "status": "APPROVED" | "REJECTED" | "DISABLED" | "FLAGGED",
                    "reason": "..." (if rejected)
                }
        
        Returns:
            Updated template or None if not found.
        """
        template_id = webhook_data.get("message_template_id")
        template_name = webhook_data.get("message_template_name")
        language = webhook_data.get("message_template_language", "en")
        status = webhook_data.get("status")
        reason = webhook_data.get("reason")
        
        # Find template by meta_template_id or name+language
        template = None
        if template_id:
            result = await db.execute(
                select(MessageTemplate).where(
                    MessageTemplate.meta_template_id == template_id
                )
            )
            template = result.scalar_one_or_none()
        
        if not template and template_name:
            result = await db.execute(
                select(MessageTemplate).where(
                    MessageTemplate.name == template_name,
                    MessageTemplate.language == language,
                )
            )
            template = result.scalar_one_or_none()
        
        if not template:
            logger.warning(f"Template not found for webhook update: {template_id or template_name}")
            return None
        
        # Update template status
        template.status = status
        if reason:
            template.rejection_reason = reason
        template.updated_at = datetime.utcnow()
        
        await db.commit()
        logger.info(f"Updated template {template.id} status to {status} via webhook")
        
        return template
    
    def _convert_to_meta_format(self, template: MessageTemplate) -> dict:
        """Convert local template format to Meta API format.
        
        Args:
            template: Local MessageTemplate instance.
        
        Returns:
            Template data in Meta API format.
        """
        components = []
        
        # Header component
        if template.header_type:
            if template.header_type == "TEXT":
                components.append({
                    "type": "HEADER",
                    "format": "TEXT",
                    "text": template.header_content or "",
                })
            elif template.header_type in ("IMAGE", "VIDEO", "DOCUMENT"):
                components.append({
                    "type": "HEADER",
                    "format": template.header_type,
                    "example": {
                        "header_handle": [template.header_content] if template.header_content else [],
                    },
                })
        
        # Body component
        body_text = template.body_text or template.content or ""
        if body_text:
            # Extract variable examples from template.variables if available
            example = {}
            if template.variables:
                # Variables should be a dict like {"1": "John", "2": "Doe"}
                example = template.variables
            
            components.append({
                "type": "BODY",
                "text": body_text,
                "example": example if example else None,
            })
        
        # Footer component
        if template.footer_text:
            components.append({
                "type": "FOOTER",
                "text": template.footer_text,
            })
        
        # Buttons component
        if template.buttons:
            buttons_data = template.buttons.get("buttons", [])
            if buttons_data:
                components.append({
                    "type": "BUTTONS",
                    "buttons": buttons_data,
                })
        
        return {
            "name": template.name,
            "language": template.language,
            "category": template.category.upper(),
            "components": components,
        }
