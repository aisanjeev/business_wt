"""WhatsApp Cloud API client service."""

from typing import Any, Optional

import httpx

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
    
    def __init__(self):
        """Initialize WhatsApp API client."""
        self.base_url = settings.whatsapp_api_base_url
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.api_token = settings.whatsapp_api_token
        self.api_version = settings.whatsapp_api_version
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
    
    @property
    def messages_url(self) -> str:
        """Get the messages endpoint URL."""
        return f"{self.base_url}/{self.api_version}/{self.phone_number_id}/messages"
    
    @property
    def media_url(self) -> str:
        """Get the media endpoint URL."""
        return f"{self.base_url}/{self.api_version}/{self.phone_number_id}/media"
    
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
        url = f"{self.base_url}/{self.api_version}/{media_id}"
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


# Singleton instance
whatsapp_client = WhatsAppClient()
