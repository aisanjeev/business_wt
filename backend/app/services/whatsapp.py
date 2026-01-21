"""WhatsApp Cloud API client service."""

from pathlib import Path
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.utils.constants import MessageType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WhatsAppAPIError(Exception):
    """Custom exception for WhatsApp API errors."""
    
    def __init__(self, message: str, status_code: int = 500, error_data: dict = None):
        self.message = message
        self.status_code = status_code
        self.error_data = error_data or {}
        super().__init__(self.message)


class WhatsAppClient:
    """Client for WhatsApp Cloud API."""
    
    def __init__(self, phone_number_id: Optional[str] = None, access_token: Optional[str] = None):
        """Initialize WhatsApp API client.
        
        Args:
            phone_number_id: WhatsApp phone number ID. If None, uses global settings.
            access_token: Access token. If None, uses global settings.
        """
        self.base_url = settings.whatsapp_api_base_url
        self.phone_number_id = phone_number_id or settings.whatsapp_phone_number_id
        self.api_token = access_token or settings.whatsapp_api_token
        self.api_version = settings.whatsapp_api_version
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
    
    @classmethod
    def for_user(cls, phone_number_id: str, access_token: str) -> "WhatsAppClient":
        """Create a WhatsApp client instance for a specific user's account.
        
        Args:
            phone_number_id: User's WhatsApp phone number ID.
            access_token: User's access token.
        
        Returns:
            WhatsAppClient instance configured for the user.
        """
        return cls(phone_number_id=phone_number_id, access_token=access_token)
    
    @property
    def messages_url(self) -> str:
        """Get the messages endpoint URL."""
        # base_url already includes api_version, so don't add it again
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        # #region agent log
        import json
        from pathlib import Path
        from datetime import datetime
        DEBUG_LOG_PATH = Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
        try:
            DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": int(datetime.now().timestamp() * 1000),
                    "location": "whatsapp.py:WhatsAppClient:messages_url",
                    "message": "Constructing messages API URL",
                    "data": {
                        "base_url": self.base_url,
                        "phone_number_id": self.phone_number_id,
                        "phone_number_id_type": type(self.phone_number_id).__name__,
                        "constructed_url": url,
                        "api_version": self.api_version
                    },
                    "sessionId": "debug-session",
                    "runId": "debug-run",
                    "hypothesisId": "D"
                }) + "\n")
        except Exception:
            pass
        # #endregion
        
        return url
    
    @property
    def media_url(self) -> str:
        """Get the media endpoint URL."""
        # base_url already includes api_version, so don't add it again
        return f"{self.base_url}/{self.phone_number_id}/media"
    
    async def _make_request(
        self,
        method: str,
        url: str,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Make an HTTP request to the WhatsApp API.
        
        Args:
            method: HTTP method (GET, POST, etc.).
            url: Request URL.
            json_data: JSON body data.
            params: Query parameters.
        
        Returns:
            Response JSON data.
        
        Raises:
            WhatsAppAPIError: If the request fails.
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=json_data,
                    params=params,
                    timeout=30.0,
                )
                
                response_data = response.json()
                
                if response.status_code >= 400:
                    error_message = response_data.get("error", {}).get("message", "Unknown error")
                    logger.error(f"WhatsApp API error: {error_message}")
                    raise WhatsAppAPIError(
                        message=error_message,
                        status_code=response.status_code,
                        error_data=response_data,
                    )
                
                return response_data
                
            except httpx.RequestError as e:
                logger.error(f"WhatsApp API request failed: {e}")
                raise WhatsAppAPIError(
                    message=f"Request failed: {str(e)}",
                    status_code=500,
                )
    
    async def send_text_message(
        self,
        to: str,
        message: str,
        preview_url: bool = False,
    ) -> dict:
        """Send a text message to a WhatsApp user.
        
        Args:
            to: Recipient phone number (with country code, no +).
            message: Text message content.
            preview_url: Whether to show URL previews.
        
        Returns:
            API response with message ID.
        """
        # #region agent log
        import json
        from pathlib import Path
        from datetime import datetime
        DEBUG_LOG_PATH = Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
        try:
            DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": int(datetime.now().timestamp() * 1000),
                    "location": "whatsapp.py:WhatsAppClient:send_text_message:entry",
                    "message": "Sending text message - before API call",
                    "data": {
                        "messages_url": self.messages_url,
                        "phone_number_id": self.phone_number_id,
                        "to": to,
                        "access_token_prefix": self.api_token[:20] + "..." if self.api_token else None,
                        "access_token_length": len(self.api_token) if self.api_token else 0
                    },
                    "sessionId": "debug-session",
                    "runId": "debug-run",
                    "hypothesisId": "E"
                }) + "\n")
        except Exception:
            pass
        # #endregion
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": message,
            },
        }
        
        logger.info(f"Sending text message to {to}")
        response = await self._make_request("POST", self.messages_url, json_data=payload)
        
        message_id = response.get("messages", [{}])[0].get("id")
        logger.info(f"Message sent successfully. ID: {message_id}")
        
        return response
    
    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "en",
        components: Optional[list] = None,
    ) -> dict:
        """Send a template message to a WhatsApp user.
        
        Args:
            to: Recipient phone number.
            template_name: Name of the approved template.
            language_code: Template language code.
            components: Template components (header, body, buttons).
        
        Returns:
            API response with message ID.
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code,
                },
            },
        }
        
        if components:
            payload["template"]["components"] = components
        
        logger.info(f"Sending template '{template_name}' to {to}")
        response = await self._make_request("POST", self.messages_url, json_data=payload)
        
        message_id = response.get("messages", [{}])[0].get("id")
        logger.info(f"Template message sent successfully. ID: {message_id}")
        
        return response
    
    async def send_image_message(
        self,
        to: str,
        image_url: Optional[str] = None,
        image_id: Optional[str] = None,
        caption: Optional[str] = None,
    ) -> dict:
        """Send an image message to a WhatsApp user.
        
        Args:
            to: Recipient phone number.
            image_url: URL of the image (if using link).
            image_id: Media ID (if previously uploaded).
            caption: Optional image caption.
        
        Returns:
            API response with message ID.
        """
        image_data: dict[str, Any] = {}
        
        if image_id:
            image_data["id"] = image_id
        elif image_url:
            image_data["link"] = image_url
        else:
            raise WhatsAppAPIError("Either image_url or image_id is required")
        
        if caption:
            image_data["caption"] = caption
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": image_data,
        }
        
        logger.info(f"Sending image message to {to}")
        return await self._make_request("POST", self.messages_url, json_data=payload)
    
    async def send_document_message(
        self,
        to: str,
        document_url: Optional[str] = None,
        document_id: Optional[str] = None,
        caption: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> dict:
        """Send a document message to a WhatsApp user.
        
        Args:
            to: Recipient phone number.
            document_url: URL of the document.
            document_id: Media ID (if previously uploaded).
            caption: Optional document caption.
            filename: Display filename.
        
        Returns:
            API response with message ID.
        """
        document_data: dict[str, Any] = {}
        
        if document_id:
            document_data["id"] = document_id
        elif document_url:
            document_data["link"] = document_url
        else:
            raise WhatsAppAPIError("Either document_url or document_id is required")
        
        if caption:
            document_data["caption"] = caption
        if filename:
            document_data["filename"] = filename
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "document",
            "document": document_data,
        }
        
        logger.info(f"Sending document message to {to}")
        return await self._make_request("POST", self.messages_url, json_data=payload)
    
    async def send_audio_message(
        self,
        to: str,
        audio_url: Optional[str] = None,
        audio_id: Optional[str] = None,
    ) -> dict:
        """Send an audio message to a WhatsApp user.
        
        Args:
            to: Recipient phone number.
            audio_url: URL of the audio file.
            audio_id: Media ID (if previously uploaded).
        
        Returns:
            API response with message ID.
        """
        audio_data: dict[str, Any] = {}
        
        if audio_id:
            audio_data["id"] = audio_id
        elif audio_url:
            audio_data["link"] = audio_url
        else:
            raise WhatsAppAPIError("Either audio_url or audio_id is required")
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "audio",
            "audio": audio_data,
        }
        
        logger.info(f"Sending audio message to {to}")
        return await self._make_request("POST", self.messages_url, json_data=payload)
    
    async def send_video_message(
        self,
        to: str,
        video_url: Optional[str] = None,
        video_id: Optional[str] = None,
        caption: Optional[str] = None,
    ) -> dict:
        """Send a video message to a WhatsApp user.
        
        Args:
            to: Recipient phone number.
            video_url: URL of the video.
            video_id: Media ID (if previously uploaded).
            caption: Optional video caption.
        
        Returns:
            API response with message ID.
        """
        video_data: dict[str, Any] = {}
        
        if video_id:
            video_data["id"] = video_id
        elif video_url:
            video_data["link"] = video_url
        else:
            raise WhatsAppAPIError("Either video_url or video_id is required")
        
        if caption:
            video_data["caption"] = caption
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "video",
            "video": video_data,
        }
        
        logger.info(f"Sending video message to {to}")
        return await self._make_request("POST", self.messages_url, json_data=payload)
    
    async def send_location_message(
        self,
        to: str,
        latitude: float,
        longitude: float,
        name: Optional[str] = None,
        address: Optional[str] = None,
    ) -> dict:
        """Send a location message to a WhatsApp user.
        
        Args:
            to: Recipient phone number.
            latitude: Location latitude.
            longitude: Location longitude.
            name: Optional location name.
            address: Optional location address.
        
        Returns:
            API response with message ID.
        """
        location_data: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
        }
        
        if name:
            location_data["name"] = name
        if address:
            location_data["address"] = address
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "location",
            "location": location_data,
        }
        
        logger.info(f"Sending location message to {to}")
        return await self._make_request("POST", self.messages_url, json_data=payload)
    
    async def send_interactive_message(
        self,
        to: str,
        interactive_type: str,
        body_text: str,
        action: dict,
        header: Optional[dict] = None,
        footer: Optional[str] = None,
    ) -> dict:
        """Send an interactive message (buttons, list).
        
        Args:
            to: Recipient phone number.
            interactive_type: Type of interactive message (button, list).
            body_text: Body text content.
            action: Action configuration (buttons, sections).
            header: Optional header configuration.
            footer: Optional footer text.
        
        Returns:
            API response with message ID.
        """
        interactive_data: dict[str, Any] = {
            "type": interactive_type,
            "body": {"text": body_text},
            "action": action,
        }
        
        if header:
            interactive_data["header"] = header
        if footer:
            interactive_data["footer"] = {"text": footer}
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive_data,
        }
        
        logger.info(f"Sending interactive message to {to}")
        return await self._make_request("POST", self.messages_url, json_data=payload)
    
    async def mark_message_as_read(self, message_id: str) -> dict:
        """Mark a message as read.
        
        Args:
            message_id: The WhatsApp message ID to mark as read.
        
        Returns:
            API response.
        """
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        
        logger.info(f"Marking message {message_id} as read")
        return await self._make_request("POST", self.messages_url, json_data=payload)
    
    async def get_media_url(self, media_id: str) -> str:
        """Get the download URL for a media file.
        
        Args:
            media_id: The WhatsApp media ID.
        
        Returns:
            Media download URL.
        """
        # base_url already includes api_version
        url = f"{self.base_url}/{media_id}"
        response = await self._make_request("GET", url)
        return response.get("url", "")
    
    async def download_media(self, media_url: str) -> bytes:
        """Download media content from WhatsApp.
        
        Args:
            media_url: The media URL to download.
        
        Returns:
            Media content as bytes.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                media_url,
                headers={"Authorization": f"Bearer {self.api_token}"},
                timeout=60.0,
            )
            response.raise_for_status()
            return response.content
    
    async def upload_media(
        self,
        file_path: str,
        mime_type: str,
    ) -> str:
        """Upload media to WhatsApp and get media ID.
        
        Args:
            file_path: Path to the local file to upload.
            mime_type: MIME type of the file.
        
        Returns:
            Media ID from WhatsApp.
        
        Raises:
            WhatsAppAPIError: If upload fails.
        """
        import aiofiles
        
        # Read file
        async with aiofiles.open(file_path, "rb") as f:
            file_content = await f.read()
        
        # Upload to WhatsApp
        # WhatsApp requires messaging_product as a form field along with the file
        files = {"file": (Path(file_path).name, file_content, mime_type)}
        data = {"messaging_product": "whatsapp"}
        headers = {"Authorization": f"Bearer {self.api_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.media_url,
                headers=headers,
                files=files,
                data=data,
                timeout=60.0,
            )
            
            if response.status_code >= 400:
                error_message = response.json().get("error", {}).get("message", "Unknown error")
                logger.error(f"WhatsApp media upload error: {error_message}")
                raise WhatsAppAPIError(
                    message=error_message,
                    status_code=response.status_code,
                    error_data=response.json(),
                )
            
            response_data = response.json()
            media_id = response_data.get("id")
            
            if not media_id:
                raise WhatsAppAPIError("No media ID returned from WhatsApp")
            
            logger.info(f"Media uploaded successfully. ID: {media_id}")
            return media_id


# Singleton instance (uses global settings)
whatsapp_client = WhatsAppClient()


async def get_whatsapp_client_for_user(
    db: AsyncSession,
    user_id: int,
) -> WhatsAppClient:
    """Get WhatsApp client configured for a specific user.
    
    If the user has a connected Meta account, returns a client using their credentials.
    Otherwise, returns the global default client.
    
    Args:
        db: Database session.
        user_id: User ID.
    
    Returns:
        WhatsAppClient instance configured for the user.
    """
    from app.models import MetaAccountConnection
    
    # Try to get user's Meta connection
    from sqlalchemy import select
    result = await db.execute(
        select(MetaAccountConnection).where(
            MetaAccountConnection.user_id == user_id,
            MetaAccountConnection.status == "connected"
        )
    )
    meta_connection = result.scalar_one_or_none()
    
    # #region agent log
    import json
    from pathlib import Path
    from datetime import datetime
    DEBUG_LOG_PATH = Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
    try:
        DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": int(datetime.now().timestamp() * 1000),
                "location": "whatsapp.py:get_whatsapp_client_for_user:after_query",
                "message": "Meta connection query result",
                "data": {
                    "user_id": user_id,
                    "connection_found": meta_connection is not None,
                    "phone_number_id": str(meta_connection.phone_number_id) if meta_connection and meta_connection.phone_number_id else None,
                    "meta_business_account_id": str(meta_connection.meta_business_account_id) if meta_connection and meta_connection.meta_business_account_id else None,
                    "has_access_token": bool(meta_connection.access_token if meta_connection else False),
                    "access_token_prefix": (meta_connection.access_token[:20] + "...") if meta_connection and meta_connection.access_token else None,
                    "status": meta_connection.status if meta_connection else None
                },
                "sessionId": "debug-session",
                "runId": "debug-run",
                "hypothesisId": "A"
            }) + "\n")
    except Exception:
        pass
    # #endregion
    
    if meta_connection and meta_connection.phone_number_id and meta_connection.access_token:
        # Use user's credentials (tokens are currently stored unencrypted)
        logger.info(f"Using user {user_id}'s WhatsApp account (phone_number_id: {meta_connection.phone_number_id})")
        
        # #region agent log
        try:
            with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": int(datetime.now().timestamp() * 1000),
                    "location": "whatsapp.py:get_whatsapp_client_for_user:creating_client",
                    "message": "Creating WhatsAppClient with user credentials",
                    "data": {
                        "user_id": user_id,
                        "phone_number_id": str(meta_connection.phone_number_id),
                        "phone_number_id_length": len(str(meta_connection.phone_number_id)),
                        "access_token_length": len(meta_connection.access_token) if meta_connection.access_token else 0,
                        "meta_business_account_id": str(meta_connection.meta_business_account_id) if meta_connection.meta_business_account_id else None
                    },
                    "sessionId": "debug-session",
                    "runId": "debug-run",
                    "hypothesisId": "B"
                }) + "\n")
        except Exception:
            pass
        # #endregion
        
        return WhatsAppClient.for_user(
            phone_number_id=meta_connection.phone_number_id,
            access_token=meta_connection.access_token
        )
    else:
        # Fall back to global default
        logger.info(f"Using default WhatsApp account for user {user_id}")
        
        # #region agent log
        try:
            with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": int(datetime.now().timestamp() * 1000),
                    "location": "whatsapp.py:get_whatsapp_client_for_user:fallback",
                    "message": "Falling back to default WhatsApp client",
                    "data": {"user_id": user_id, "reason": "No connection or missing credentials"},
                    "sessionId": "debug-session",
                    "runId": "debug-run",
                    "hypothesisId": "C"
                }) + "\n")
        except Exception:
            pass
        # #endregion
        
        return whatsapp_client
