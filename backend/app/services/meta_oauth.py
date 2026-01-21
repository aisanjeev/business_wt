"""Meta OAuth service for connecting customer Meta accounts."""

import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MetaOAuthError(Exception):
    """Custom exception for Meta OAuth errors."""
    
    def __init__(self, message: str, status_code: int = 500, error_data: dict = None):
        self.message = message
        self.status_code = status_code
        self.error_data = error_data or {}
        super().__init__(self.message)


class MetaOAuthService:
    """Service for handling Meta OAuth flow."""
    
    def __init__(self):
        """Initialize Meta OAuth service."""
        import json
        from pathlib import Path
        from datetime import datetime
        
        DEBUG_LOG_PATH = Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
        def debug_log(location: str, message: str, data: dict = None):
            try:
                DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                    entry = {
                        "timestamp": int(datetime.now().timestamp() * 1000),
                        "location": location,
                        "message": message,
                        "data": data or {},
                        "sessionId": "debug-session",
                    }
                    f.write(json.dumps(entry) + "\n")
            except Exception:
                pass
        
        # #region agent log
        debug_log(
            "meta_oauth.py:__init__",
            "Initializing MetaOAuthService",
            {
                "app_id_present": bool(settings.meta_app_id),
                "app_secret_present": bool(settings.meta_app_secret),
                "redirect_uri_present": bool(settings.meta_oauth_redirect_uri),
                "redirect_uri": settings.meta_oauth_redirect_uri or "NOT_SET",
            },
        )
        # #endregion
        
        self.app_id = settings.meta_app_id
        self.app_secret = settings.meta_app_secret
        self.redirect_uri = settings.meta_oauth_redirect_uri
        self.api_version = settings.whatsapp_api_version
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
    
    def get_oauth_url(self, state: Optional[str] = None) -> str:
        """Generate OAuth authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection.
        
        Returns:
            OAuth authorization URL.
        """
        if not state:
            state = secrets.token_urlsafe(32)
        
        scopes = [
            "whatsapp_business_management",
            "whatsapp_business_messaging",
            "business_management",
        ]
        
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "scope": ",".join(scopes),
            "response_type": "code",
            "state": state,
        }
        
        auth_url = f"https://www.facebook.com/{self.api_version}/dialog/oauth?{urlencode(params)}"
        logger.info(f"Generated OAuth URL for state: {state[:8]}...")
        
        return auth_url
    
    async def exchange_code_for_token(self, code: str) -> dict:
        """Exchange authorization code for access token.
        
        Args:
            code: Authorization code from OAuth callback.
        
        Returns:
            Token response with access_token, token_type, expires_in, etc.
        
        Raises:
            MetaOAuthError: If token exchange fails.
        """
        token_url = f"{self.base_url}/oauth/access_token"
        
        params = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "redirect_uri": self.redirect_uri,
            "code": code,
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(token_url, params=params, timeout=30.0)
                response.raise_for_status()
                token_data = response.json()
                
                if "error" in token_data:
                    error_msg = token_data["error"].get("message", "Unknown error")
                    logger.error(f"Meta OAuth error: {error_msg}")
                    raise MetaOAuthError(
                        message=error_msg,
                        status_code=token_data["error"].get("code", 500),
                        error_data=token_data,
                    )
                
                logger.info("Successfully exchanged code for access token")
                return token_data
                
        except httpx.RequestError as e:
            logger.error(f"Meta OAuth request failed: {e}")
            raise MetaOAuthError(
                message=f"Request failed: {str(e)}",
                status_code=500,
            )
    
    async def get_long_lived_token(self, short_lived_token: str) -> dict:
        """Exchange short-lived token for long-lived token.
        
        Args:
            short_lived_token: Short-lived access token (1-2 hours).
        
        Returns:
            Long-lived token response (60 days).
        
        Raises:
            MetaOAuthError: If token exchange fails.
        """
        token_url = f"{self.base_url}/oauth/access_token"
        
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": short_lived_token,
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(token_url, params=params, timeout=30.0)
                response.raise_for_status()
                token_data = response.json()
                
                if "error" in token_data:
                    error_msg = token_data["error"].get("message", "Unknown error")
                    logger.error(f"Meta long-lived token error: {error_msg}")
                    raise MetaOAuthError(
                        message=error_msg,
                        status_code=token_data["error"].get("code", 500),
                        error_data=token_data,
                    )
                
                logger.info("Successfully exchanged for long-lived token")
                return token_data
                
        except httpx.RequestError as e:
            logger.error(f"Meta long-lived token request failed: {e}")
            raise MetaOAuthError(
                message=f"Request failed: {str(e)}",
                status_code=500,
            )
    
    async def get_business_accounts(self, access_token: str) -> list[dict]:
        """Get Meta Business Accounts associated with the access token.
        
        Args:
            access_token: Meta access token.
        
        Returns:
            List of business account information.
        
        Raises:
            MetaOAuthError: If API call fails.
        """
        url = f"{self.base_url}/me/businesses"
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    error_msg = data["error"].get("message", "Unknown error")
                    logger.error(f"Meta API error: {error_msg}")
                    raise MetaOAuthError(
                        message=error_msg,
                        status_code=data["error"].get("code", 500),
                        error_data=data,
                    )
                
                business_accounts = data.get("data", [])
                logger.info(f"Retrieved {len(business_accounts)} business accounts")
                return business_accounts
                
        except httpx.RequestError as e:
            logger.error(f"Meta API request failed: {e}")
            raise MetaOAuthError(
                message=f"Request failed: {str(e)}",
                status_code=500,
            )
    
    async def get_whatsapp_business_accounts(self, business_account_id: str, access_token: str) -> list[dict]:
        """Get WhatsApp Business Accounts for a Meta Business Account.
        
        Args:
            business_account_id: Meta Business Account ID.
            access_token: Meta access token.
        
        Returns:
            List of WhatsApp Business Account information.
        
        Raises:
            MetaOAuthError: If API call fails.
        """
        url = f"{self.base_url}/{business_account_id}/owned_whatsapp_business_accounts"
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            async with httpx.AsyncClient() as client:
                # Use shorter timeout for individual API calls to fail fast (15s instead of 30s)
                response = await client.get(url, headers=headers, timeout=15.0)
                
                # Check for HTTP errors before parsing JSON
                if response.status_code == 403:
                    # Permission denied - this is expected for some accounts
                    logger.warning(f"Permission denied (403) for business account {business_account_id}")
                    raise MetaOAuthError(
                        message="Permission denied for this business account",
                        status_code=403,
                        error_data={"business_account_id": business_account_id},
                    )
                
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    error_msg = data["error"].get("message", "Unknown error")
                    error_code = data["error"].get("code", 500)
                    logger.error(f"Meta API error: {error_msg}")
                    raise MetaOAuthError(
                        message=error_msg,
                        status_code=error_code,
                        error_data=data,
                    )
                
                whatsapp_business_accounts = data.get("data", [])
                logger.info(f"Retrieved {len(whatsapp_business_accounts)} WhatsApp Business Accounts")
                return whatsapp_business_accounts
                
        except httpx.HTTPStatusError as e:
            # Handle HTTP errors (including 403)
            if e.response.status_code == 403:
                logger.warning(f"Permission denied (403) for business account {business_account_id}")
                raise MetaOAuthError(
                    message="Permission denied for this business account",
                    status_code=403,
                    error_data={"business_account_id": business_account_id},
                )
            logger.error(f"Meta API HTTP error: {e}")
            raise MetaOAuthError(
                message=f"HTTP error: {e.response.status_code}",
                status_code=e.response.status_code,
            )
        except httpx.RequestError as e:
            logger.error(f"Meta API request failed: {e}")
            raise MetaOAuthError(
                message=f"Request failed: {str(e)}",
                status_code=500,
            )
    
    async def get_phone_numbers(self, whatsapp_business_account_id: str, access_token: str) -> list[dict]:
        """Get WhatsApp phone numbers for a WhatsApp Business Account.
        
        Args:
            whatsapp_business_account_id: WhatsApp Business Account ID (not Meta Business Account ID).
            access_token: Meta access token.
        
        Returns:
            List of phone number information.
        
        Raises:
            MetaOAuthError: If API call fails.
        """
        url = f"{self.base_url}/{whatsapp_business_account_id}/phone_numbers"
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            async with httpx.AsyncClient() as client:
                # Use shorter timeout for individual API calls to fail fast (15s instead of 30s)
                response = await client.get(url, headers=headers, timeout=15.0)
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    error_msg = data["error"].get("message", "Unknown error")
                    logger.error(f"Meta API error: {error_msg}")
                    raise MetaOAuthError(
                        message=error_msg,
                        status_code=data["error"].get("code", 500),
                        error_data=data,
                    )
                
                phone_numbers = data.get("data", [])
                logger.info(f"Retrieved {len(phone_numbers)} phone numbers")
                return phone_numbers
                
        except httpx.RequestError as e:
            logger.error(f"Meta API request failed: {e}")
            raise MetaOAuthError(
                message=f"Request failed: {str(e)}",
                status_code=500,
            )


# Singleton instance
meta_oauth_service = MetaOAuthService()
