"""WhatsApp webhook endpoints."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db_context
from app.schemas import WhatsAppWebhookPayload
from app.services.message_processor import message_processor
from app.services.template import TemplateSyncService
from app.utils.logger import get_logger

logger = get_logger(__name__)

sync_service = TemplateSyncService()

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
) -> int:
    """Verify webhook endpoint for WhatsApp Cloud API.
    
    This endpoint is called by Meta when you register your webhook URL.
    It verifies that you own the webhook endpoint.
    
    Args:
        hub_mode: Should be "subscribe".
        hub_challenge: Challenge string to echo back.
        hub_verify_token: Your verification token.
    
    Returns:
        The hub_challenge value as an integer.
    
    Raises:
        HTTPException: If verification fails.
    """
    logger.info(f"Webhook verification request: mode={hub_mode}")
    
    # Verify the mode is subscribe
    if hub_mode != "subscribe":
        logger.warning(f"Invalid hub.mode: {hub_mode}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid hub.mode",
        )
    
    # Verify the token matches
    if hub_verify_token != settings.webhook_verify_token:
        logger.warning("Webhook verification token mismatch")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verification token mismatch",
        )
    
    logger.info("Webhook verified successfully")
    
    # Return the challenge to confirm the webhook
    return int(hub_challenge)


@router.post("")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    """Receive incoming webhook events from WhatsApp.
    
    This endpoint receives all webhook events including:
    - Incoming messages
    - Message status updates (sent, delivered, read)
    - Message errors
    
    The actual processing is done in the background to ensure
    we return a 200 response within 5 seconds (WhatsApp requirement).
    
    Args:
        request: FastAPI request object.
        background_tasks: Background task runner.
    
    Returns:
        Acknowledgment response.
    """
    # Get raw body for logging/debugging
    body = await request.json()
    
    logger.info(f"Webhook received: {body.get('object', 'unknown')}")
    logger.debug(f"Webhook payload: {body}")
    
    # Validate that this is a WhatsApp webhook
    if body.get("object") != "whatsapp_business_account":
        logger.warning(f"Ignoring non-WhatsApp webhook: {body.get('object')}")
        return {"status": "ignored"}
    
    try:
        # Parse the webhook payload
        payload = WhatsAppWebhookPayload(**body)
        
        # Check for template status updates
        for entry in payload.entry:
            for change in entry.changes:
                if change.field == "message_template_status_update":
                    # Handle template status update
                    background_tasks.add_task(
                        handle_template_status_update,
                        change.value,
                    )
                    logger.info("Template status update queued for processing")
                    continue
                
                # Process other webhook events (messages, etc.)
                if change.field == "messages":
                    background_tasks.add_task(
                        message_processor.process_webhook,
                        payload,
                    )
        
        logger.info("Webhook queued for processing")
        return {"status": "received"}
        
    except Exception as e:
        # Log error but still return 200 to prevent retries
        logger.error(f"Error parsing webhook payload: {e}")
        logger.error(f"Raw payload: {body}")
        return {"status": "error", "message": str(e)}


async def handle_template_status_update(webhook_data: dict) -> None:
    """Handle template status update from Meta webhook.
    
    Args:
        webhook_data: Webhook payload for template status update.
    """
    try:
        async with get_db_context() as db:
            template = await sync_service.handle_webhook_status_update(
                db=db,
                webhook_data=webhook_data,
            )
            
            if template:
                logger.info(f"Template {template.id} status updated to {template.status}")
                
                # Broadcast status update via WebSocket if manager is available
                if message_processor.ws_manager:
                    await message_processor.ws_manager.broadcast_json({
                        "type": "template_status_update",
                        "payload": {
                            "template_id": template.id,
                            "status": template.status,
                            "rejection_reason": template.rejection_reason,
                        },
                    })
    except Exception as e:
        logger.error(f"Error handling template status update: {e}", exc_info=True)


@router.get("/health")
async def webhook_health() -> dict:
    """Health check endpoint for the webhook.
    
    Returns:
        Health status information.
    """
    return {
        "status": "healthy",
        "service": "whatsapp-webhook",
        "webhook_configured": bool(settings.webhook_verify_token),
        "api_configured": bool(settings.whatsapp_api_token),
    }
