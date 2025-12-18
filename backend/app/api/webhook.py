"""WhatsApp webhook endpoints."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status

from app.config import settings
from app.schemas import WhatsAppWebhookPayload
from app.services.message_processor import message_processor
from app.utils.logger import get_logger

logger = get_logger(__name__)

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
        
        # Process in background to ensure quick response
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
