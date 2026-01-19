"""Meta API client for WhatsApp message templates."""

import asyncio
from typing import Any, Optional

import httpx

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MetaTemplateAPIError(Exception):
    """Custom exception for Meta Template API errors."""
    
    def __init__(self, message: str, status_code: int = 500, error_data: dict = None):
        self.message = message
        self.status_code = status_code
        self.error_data = error_data or {}
        super().__init__(self.message)


class MetaTemplateAPIClient:
    """Client for Meta API v22.0 template operations."""
    
    def __init__(self, access_token: Optional[str] = None):
        """Initialize Meta Template API client.
        
        Args:
            access_token: Optional access token. If not provided, uses global token from settings.
        """
        self.base_url = settings.whatsapp_api_base_url
        self.api_token = access_token or settings.whatsapp_api_token
        self.api_version = settings.whatsapp_api_version
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
    
    def _get_templates_url(self, waba_id: str) -> str:
        """Get the templates endpoint URL for a WABA."""
        return f"{self.base_url}/{waba_id}/message_templates"
    
    async def _make_request(
        self,
        method: str,
        url: str,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> dict:
        """Make an HTTP request to the Meta API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, DELETE, etc.).
            url: Request URL.
            json_data: JSON body data.
            params: Query parameters.
            max_retries: Maximum number of retry attempts.
            retry_delay: Initial delay between retries (exponential backoff).
        
        Returns:
            Response JSON data.
        
        Raises:
            MetaTemplateAPIError: If the request fails after retries.
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
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
                        error_info = response_data.get("error", {})
                        error_message = error_info.get("message", "Unknown error")
                        error_code = error_info.get("code", response.status_code)
                        error_subcode = error_info.get("error_subcode")
                        
                        # Rate limiting - retry with exponential backoff
                        if response.status_code == 429 or error_code == 80007:
                            if attempt < max_retries - 1:
                                delay = retry_delay * (2 ** attempt)
                                logger.warning(
                                    f"Rate limited. Retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})"
                                )
                                await asyncio.sleep(delay)
                                continue
                        
                        # Don't retry on client errors (4xx) except rate limiting
                        if 400 <= response.status_code < 500 and response.status_code != 429:
                            raise MetaTemplateAPIError(
                                message=error_message,
                                status_code=response.status_code,
                                error_data={
                                    "code": error_code,
                                    "subcode": error_subcode,
                                    "full_error": error_info,
                                },
                            )
                        
                        # Retry on server errors (5xx)
                        if response.status_code >= 500:
                            if attempt < max_retries - 1:
                                delay = retry_delay * (2 ** attempt)
                                logger.warning(
                                    f"Server error {response.status_code}. Retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})"
                                )
                                await asyncio.sleep(delay)
                                continue
                        
                        raise MetaTemplateAPIError(
                            message=error_message,
                            status_code=response.status_code,
                            error_data={
                                "code": error_code,
                                "subcode": error_subcode,
                                "full_error": error_info,
                            },
                        )
                    
                    return response_data
                    
            except httpx.RequestError as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Request error: {e}. Retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Meta API request failed after {max_retries} attempts: {e}")
                    raise MetaTemplateAPIError(
                        message=f"Request failed: {str(e)}",
                        status_code=500,
                    )
            except MetaTemplateAPIError as e:
                # Don't retry MetaTemplateAPIError (already handled above)
                raise
        
        # If we get here, all retries failed
        if last_error:
            raise MetaTemplateAPIError(
                message=f"Request failed after {max_retries} attempts: {str(last_error)}",
                status_code=500,
            )
    
    async def get_templates(
        self,
        waba_id: str,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        name: Optional[str] = None,
        status: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict:
        """Fetch all templates from Meta API.
        
        Args:
            waba_id: WhatsApp Business Account ID.
            limit: Maximum number of templates to return.
            after: Cursor for pagination (after this template).
            before: Cursor for pagination (before this template).
            name: Filter by template name.
            status: Filter by status (APPROVED, PENDING, REJECTED, etc.).
            language: Filter by language code.
        
        Returns:
            Response with templates data and pagination info.
        """
        url = self._get_templates_url(waba_id)
        params = {}
        
        if limit:
            params["limit"] = limit
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        if name:
            params["name"] = name
        if status:
            params["status"] = status
        if language:
            params["language"] = language
        
        logger.info(f"Fetching templates from Meta API for WABA {waba_id}")
        response = await self._make_request("GET", url, params=params)
        
        return response
    
    async def get_template(
        self,
        waba_id: str,
        template_name: str,
        language: str = "en",
    ) -> dict:
        """Get a specific template from Meta API.
        
        Args:
            waba_id: WhatsApp Business Account ID.
            template_name: Template name.
            language: Template language code.
        
        Returns:
            Template data.
        """
        url = self._get_templates_url(waba_id)
        params = {
            "name": template_name,
            "language": language,
        }
        
        logger.info(f"Fetching template '{template_name}' (language: {language}) from Meta API")
        response = await self._make_request("GET", url, params=params)
        
        # Meta API returns a list, get the first item
        templates = response.get("data", [])
        if templates:
            return templates[0]
        
        raise MetaTemplateAPIError(
            message=f"Template '{template_name}' not found",
            status_code=404,
        )
    
    async def create_template(
        self,
        waba_id: str,
        template_data: dict,
    ) -> dict:
        """Submit a new template to Meta API for approval.
        
        Args:
            waba_id: WhatsApp Business Account ID.
            template_data: Template data in Meta API format:
                {
                    "name": "...",
                    "language": "...",
                    "category": "MARKETING" | "UTILITY" | "AUTHENTICATION",
                    "components": [
                        {"type": "HEADER", "format": "TEXT", "text": "..."},
                        {"type": "BODY", "text": "...", "example": {...}},
                        {"type": "FOOTER", "text": "..."},
                        {"type": "BUTTONS", "buttons": [...]}
                    ]
                }
        
        Returns:
            Created template data with status.
        """
        url = self._get_templates_url(waba_id)
        
        logger.info(f"Creating template '{template_data.get('name')}' in Meta API")
        response = await self._make_request("POST", url, json_data=template_data)
        
        return response
    
    async def delete_template(
        self,
        waba_id: str,
        template_name: str,
        hsm_id: Optional[str] = None,
    ) -> dict:
        """Delete a template from Meta API.
        
        Args:
            waba_id: WhatsApp Business Account ID.
            template_name: Template name to delete.
            hsm_id: Optional HSM ID for the template.
        
        Returns:
            Deletion confirmation.
        """
        url = self._get_templates_url(waba_id)
        params = {
            "name": template_name,
        }
        if hsm_id:
            params["hsm_id"] = hsm_id
        
        logger.info(f"Deleting template '{template_name}' from Meta API")
        response = await self._make_request("DELETE", url, params=params)
        
        return response
    
    def parse_template_from_meta(self, meta_template: dict) -> dict:
        """Parse a Meta API template response into our internal format.
        
        Args:
            meta_template: Template data from Meta API.
        
        Returns:
            Parsed template data in our format.
        """
        components = meta_template.get("components", [])
        
        header_type = None
        header_content = None
        body_text = None
        footer_text = None
        buttons = None
        
        for component in components:
            comp_type = component.get("type")
            
            if comp_type == "HEADER":
                format_type = component.get("format", "TEXT")
                if format_type == "TEXT":
                    header_type = "TEXT"
                    header_content = component.get("text", "")
                elif format_type in ("IMAGE", "VIDEO", "DOCUMENT"):
                    header_type = format_type
                    # For media, Meta provides example or media handle
                    header_content = component.get("example", {}).get("header_handle", [""])[0] if component.get("example") else None
            
            elif comp_type == "BODY":
                body_text = component.get("text", "")
            
            elif comp_type == "FOOTER":
                footer_text = component.get("text", "")
            
            elif comp_type == "BUTTONS":
                buttons_data = component.get("buttons", [])
                if buttons_data:
                    buttons = {
                        "type": "QUICK_REPLY" if any(b.get("type") == "QUICK_REPLY" for b in buttons_data) else "CALL_TO_ACTION",
                        "buttons": buttons_data,
                    }
        
        return {
            "name": meta_template.get("name"),
            "meta_template_id": meta_template.get("id"),
            "status": meta_template.get("status", "PENDING"),
            "category": meta_template.get("category"),
            "language": meta_template.get("language"),
            "header_type": header_type,
            "header_content": header_content,
            "body_text": body_text or "",
            "footer_text": footer_text,
            "buttons": buttons,
            "quality_score": meta_template.get("quality_score"),
        }
