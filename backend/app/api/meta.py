"""Meta OAuth endpoints for connecting customer Meta accounts."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MetaAccountConnection, User
from app.schemas import (
    ConnectionCompleteRequest,
    MetaAccountConnectionResponse,
    MetaAccountConnectionUpdate,
    OAuthExchangeRequest,
    OAuthExchangeResponse,
    SuccessResponse,
)
from app.services.auth import get_current_user
from app.services.meta_oauth import MetaOAuthError, meta_oauth_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Debug logging helper
DEBUG_LOG_PATH = Path(__file__).parent.parent.parent / ".cursor" / "debug.log"

def debug_log(location: str, message: str, data: dict = None, hypothesis_id: str = None):
    """Write debug log entry."""
    try:
        DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            entry = {
                "timestamp": int(datetime.now().timestamp() * 1000),
                "location": location,
                "message": message,
                "data": data or {},
                "hypothesisId": hypothesis_id,
                "sessionId": "debug-session",
            }
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Silently fail if logging fails

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/oauth/url")
async def get_oauth_url(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get Meta OAuth authorization URL.
    
    Args:
        current_user: Authenticated user.
    
    Returns:
        OAuth authorization URL and state.
    """
    import secrets
    
    state = secrets.token_urlsafe(32)
    auth_url = meta_oauth_service.get_oauth_url(state=state)
    
    return {
        "auth_url": auth_url,
        "state": state,
    }


@router.post("/oauth/exchange", response_model=OAuthExchangeResponse)
async def exchange_oauth_code(
    exchange_request: OAuthExchangeRequest,
    current_user: User = Depends(get_current_user),
) -> OAuthExchangeResponse:
    """Exchange OAuth authorization code for access token and get business accounts/phone numbers.
    
    This endpoint is called by the frontend after Meta redirects with the authorization code.
    It exchanges the code for an access token and fetches available business accounts
    and phone numbers so the user can select which one to connect.
    
    Args:
        exchange_request: OAuth exchange request with authorization code.
        current_user: Authenticated user.
    
    Returns:
        OAuth exchange response with access token, business accounts, and phone numbers.
    
    Raises:
        HTTPException: If OAuth exchange fails.
    """
    # #region agent log
    debug_log(
        "meta.py:exchange_oauth_code:entry",
        "OAuth exchange endpoint called",
        {"user_id": current_user.id, "code_length": len(exchange_request.code) if exchange_request.code else 0},
        "A"
    )
    # #endregion
    
    try:
        code = exchange_request.code
        # #region agent log
        debug_log(
            "meta.py:exchange_oauth_code:before_token_exchange",
            "About to exchange code for token",
            {"code_present": bool(code), "code_prefix": code[:10] + "..." if code else None},
            "A"
        )
        # #endregion
        
        # Exchange code for short-lived token
        token_data = await meta_oauth_service.exchange_code_for_token(code)
        # #region agent log
        debug_log(
            "meta.py:exchange_oauth_code:after_token_exchange",
            "Code exchanged for short-lived token",
            {"has_access_token": "access_token" in token_data, "token_keys": list(token_data.keys())},
            "A"
        )
        # #endregion
        
        short_lived_token = token_data.get("access_token")
        
        # #region agent log
        debug_log(
            "meta.py:exchange_oauth_code:before_long_lived",
            "About to get long-lived token",
            {"short_token_present": bool(short_lived_token)},
            "B"
        )
        # #endregion
        
        # Exchange for long-lived token
        long_lived_data = await meta_oauth_service.get_long_lived_token(short_lived_token)
        # #region agent log
        debug_log(
            "meta.py:exchange_oauth_code:after_long_lived",
            "Got long-lived token",
            {"has_access_token": "access_token" in long_lived_data, "expires_in": long_lived_data.get("expires_in")},
            "B"
        )
        # #endregion
        
        access_token = long_lived_data.get("access_token")
        expires_in = long_lived_data.get("expires_in", 5184000)  # 60 days default
        
        # #region agent log
        debug_log(
            "meta.py:exchange_oauth_code:before_business_accounts",
            "About to get business accounts",
            {"access_token_present": bool(access_token)},
            "C"
        )
        # #endregion
        
        # Get business accounts
        business_accounts_data = await meta_oauth_service.get_business_accounts(access_token)
        # #region agent log
        debug_log(
            "meta.py:exchange_oauth_code:after_business_accounts",
            "Got business accounts",
            {"count": len(business_accounts_data) if business_accounts_data else 0},
            "C"
        )
        # #endregion
        
        if not business_accounts_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No business accounts found for this user",
            )
        
        # Convert to schema format
        business_accounts = [
            {
                "id": acc.get("id"),
                "name": acc.get("name"),
                "timezone_id": acc.get("timezone_id"),
                "primary_page_id": acc.get("primary_page_id"),
            }
            for acc in business_accounts_data
        ]
        
        # Get phone numbers from ALL business accounts and ALL WhatsApp Business Accounts
        # Collect phone numbers from all WhatsApp Business Accounts across all Business Accounts
        phone_numbers_data = []
        
        # #region agent log
        debug_log(
            "meta.py:exchange_oauth_code:before_collecting_phone_numbers",
            "About to collect phone numbers from all business accounts",
            {"business_accounts_count": len(business_accounts)},
            "D"
        )
        # #endregion
        
        for business_account in business_accounts:
            business_account_id = business_account.get("id")
            
            # Get WhatsApp Business Accounts for this business account
            # Skip if we don't have permission (403 error)
            try:
                whatsapp_business_accounts = await meta_oauth_service.get_whatsapp_business_accounts(
                    business_account_id, access_token
                )
            except MetaOAuthError as e:
                # If 403 (Forbidden), skip this business account - we don't have permission
                if e.status_code == 403:
                    logger.warning(f"Skipping business account {business_account_id}: Permission denied (403)")
                    continue
                # For other errors, log and continue
                logger.warning(f"Failed to get WhatsApp Business Accounts for {business_account_id}: {e.message}")
                continue
            except Exception as e:
                # Log but continue - some accounts might not be accessible
                logger.warning(f"Error getting WhatsApp Business Accounts for {business_account_id}: {e}")
                continue
            
            if whatsapp_business_accounts:
                # Get phone numbers from each WhatsApp Business Account
                for whatsapp_business_account in whatsapp_business_accounts:
                    whatsapp_business_account_id = whatsapp_business_account.get("id")
                    
                    # #region agent log
                    debug_log(
                        "meta.py:exchange_oauth_code:getting_phone_numbers",
                        "Getting phone numbers from WhatsApp Business Account",
                        {
                            "business_account_id": business_account_id,
                            "whatsapp_business_account_id": whatsapp_business_account_id
                        },
                        "E"
                    )
                    # #endregion
                    
                    try:
                        account_phone_numbers = await meta_oauth_service.get_phone_numbers(
                            whatsapp_business_account_id, access_token
                        )
                        if account_phone_numbers:
                            phone_numbers_data.extend(account_phone_numbers)
                    except MetaOAuthError as e:
                        # Log but continue - some accounts might not have phone numbers or permissions
                        logger.warning(f"Failed to get phone numbers for WhatsApp Business Account {whatsapp_business_account_id}: {e.message}")
                        continue
                    except Exception as e:
                        # Log but continue - some accounts might not have phone numbers
                        logger.warning(f"Error getting phone numbers for WhatsApp Business Account {whatsapp_business_account_id}: {e}")
                        continue
        
        # #region agent log
        debug_log(
            "meta.py:exchange_oauth_code:after_phone_numbers",
            "Got phone numbers",
            {"count": len(phone_numbers_data) if phone_numbers_data else 0},
            "E"
        )
        # #endregion
        
        # Convert to schema format
        phone_numbers = [
            {
                "id": pn.get("id"),
                "display_phone_number": pn.get("display_phone_number"),
                "verified_name": pn.get("verified_name"),
                "code_verification_status": pn.get("code_verification_status"),
                "eligibility_for_api_business_global_search": pn.get("eligibility_for_api_business_global_search"),
            }
            for pn in phone_numbers_data
        ]
        
        logger.info(
            f"OAuth exchange successful for user {current_user.id}. "
            f"Found {len(business_accounts)} business accounts and {len(phone_numbers)} phone numbers"
        )
        
        return OAuthExchangeResponse(
            access_token=access_token,
            expires_in=expires_in,
            business_accounts=business_accounts,
            phone_numbers=phone_numbers,
        )
        
    except MetaOAuthError as e:
        # #region agent log
        debug_log(
            "meta.py:exchange_oauth_code:MetaOAuthError",
            "Meta OAuth error caught",
            {"error_message": str(e.message), "status_code": e.status_code},
            "E"
        )
        # #endregion
        logger.error(f"Meta OAuth error in exchange: {e.message}")
        raise HTTPException(
            status_code=e.status_code or status.HTTP_400_BAD_REQUEST,
            detail=f"Meta OAuth error: {e.message}",
        )
    except Exception as e:
        # #region agent log
        debug_log(
            "meta.py:exchange_oauth_code:Exception",
            "Unexpected exception caught",
            {"error_type": type(e).__name__, "error_message": str(e), "error_str": str(e)},
            "F"
        )
        # #endregion
        logger.error(f"Unexpected error in OAuth exchange: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to exchange OAuth code",
        )


@router.post("/connection/complete", response_model=MetaAccountConnectionResponse)
async def complete_connection(
    complete_request: ConnectionCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MetaAccountConnectionResponse:
    """Complete Meta connection with selected business account and phone number.
    
    This endpoint is called by the frontend after the user selects which phone number
    to connect. It creates or updates the MetaAccountConnection record.
    
    Args:
        complete_request: Connection completion request with selected IDs.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Created/updated Meta account connection details.
    
    Raises:
        HTTPException: If connection creation/update fails.
    """
    try:
        # #region agent log
        import json
        from pathlib import Path
        DEBUG_LOG_PATH = Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
        try:
            DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": int(datetime.now().timestamp() * 1000),
                    "location": "meta.py:complete_connection:entry",
                    "message": "Connection completion request received",
                    "data": {
                        "user_id": current_user.id,
                        "phone_number_id": complete_request.phone_number_id,
                        "business_account_id": complete_request.business_account_id,
                        "has_access_token": bool(complete_request.access_token),
                        "access_token_prefix": complete_request.access_token[:20] + "..." if complete_request.access_token else None
                    },
                    "sessionId": "debug-session",
                    "runId": "debug-run",
                    "hypothesisId": "A"
                }) + "\n")
        except Exception:
            pass
        # #endregion
        
        # Encrypt tokens (simplified - use proper encryption in production)
        encrypted_access_token = complete_request.access_token  # TODO: Implement proper encryption
        encrypted_refresh_token = None  # TODO: Store refresh token if available
        
        # Get phone number details for display
        business_phone_number = complete_request.business_phone_number
        if not business_phone_number:
            # Try to get from Meta API
            try:
                phone_numbers = await meta_oauth_service.get_phone_numbers(
                    complete_request.business_account_id, complete_request.access_token
                )
                
                # #region agent log
                try:
                    with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                        f.write(json.dumps({
                            "timestamp": int(datetime.now().timestamp() * 1000),
                            "location": "meta.py:complete_connection:phone_numbers_fetched",
                            "message": "Phone numbers fetched from Meta API",
                            "data": {
                                "business_account_id": complete_request.business_account_id,
                                "phone_numbers_count": len(phone_numbers),
                                "phone_numbers": [{"id": pn.get("id"), "display_phone_number": pn.get("display_phone_number")} for pn in phone_numbers],
                                "requested_phone_number_id": complete_request.phone_number_id
                            },
                            "sessionId": "debug-session",
                            "runId": "debug-run",
                            "hypothesisId": "B"
                        }) + "\n")
                except Exception:
                    pass
                # #endregion
                
                for pn in phone_numbers:
                    if pn.get("id") == complete_request.phone_number_id:
                        business_phone_number = pn.get("display_phone_number") or pn.get("verified_name")
                        break
            except Exception as e:
                logger.warning(f"Could not fetch phone number details: {e}")
        
        # Check if connection already exists
        result = await db.execute(
            select(MetaAccountConnection).where(MetaAccountConnection.user_id == current_user.id)
        )
        existing_connection = result.scalar_one_or_none()
        
        if existing_connection:
            # Update existing connection
            existing_connection.meta_business_account_id = complete_request.business_account_id
            existing_connection.phone_number_id = complete_request.phone_number_id
            existing_connection.business_phone_number = business_phone_number
            existing_connection.access_token = encrypted_access_token
            existing_connection.refresh_token = encrypted_refresh_token
            existing_connection.status = "connected"
            existing_connection.connected_at = datetime.now(timezone.utc)
            existing_connection.updated_at = datetime.now(timezone.utc)
            
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "timestamp": int(datetime.now().timestamp() * 1000),
                        "location": "meta.py:complete_connection:updating",
                        "message": "Updating existing Meta connection",
                        "data": {
                            "user_id": current_user.id,
                            "phone_number_id": existing_connection.phone_number_id,
                            "meta_business_account_id": existing_connection.meta_business_account_id
                        },
                        "sessionId": "debug-session",
                        "runId": "debug-run",
                        "hypothesisId": "C"
                    }) + "\n")
            except Exception:
                pass
            # #endregion
            
            await db.commit()
            await db.refresh(existing_connection)
            
            logger.info(f"Updated Meta connection for user {current_user.id}")
            return MetaAccountConnectionResponse.model_validate(existing_connection)
        else:
            # Create new connection
            connection = MetaAccountConnection(
                user_id=current_user.id,
                meta_business_account_id=complete_request.business_account_id,
                phone_number_id=complete_request.phone_number_id,
                business_phone_number=business_phone_number,
                access_token=encrypted_access_token,
                refresh_token=encrypted_refresh_token,
                status="connected",
                connected_at=datetime.now(timezone.utc),
            )
            
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "timestamp": int(datetime.now().timestamp() * 1000),
                        "location": "meta.py:complete_connection:creating",
                        "message": "Creating new Meta connection",
                        "data": {
                            "user_id": current_user.id,
                            "phone_number_id": connection.phone_number_id,
                            "meta_business_account_id": connection.meta_business_account_id
                        },
                        "sessionId": "debug-session",
                        "runId": "debug-run",
                        "hypothesisId": "C"
                    }) + "\n")
            except Exception:
                pass
            # #endregion
            
            db.add(connection)
            await db.commit()
            await db.refresh(connection)
            
            logger.info(f"Created Meta connection for user {current_user.id}")
            return MetaAccountConnectionResponse.model_validate(connection)
            
    except MetaOAuthError as e:
        logger.error(f"Meta OAuth error in connection complete: {e.message}")
        raise HTTPException(
            status_code=e.status_code or status.HTTP_400_BAD_REQUEST,
            detail=f"Meta OAuth error: {e.message}",
        )
    except Exception as e:
        logger.error(f"Unexpected error in connection complete: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete connection",
        )


@router.get("/oauth/callback")
async def oauth_callback(
    code: str = Query(..., description="Authorization code from Meta"),
    state: Optional[str] = Query(None, description="State parameter"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MetaAccountConnectionResponse:
    """Handle OAuth callback from Meta.
    
    Args:
        code: Authorization code from Meta.
        state: Optional state parameter.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Meta account connection details.
    
    Raises:
        HTTPException: If OAuth flow fails.
    """
    try:
        # Exchange code for short-lived token
        token_data = await meta_oauth_service.exchange_code_for_token(code)
        short_lived_token = token_data.get("access_token")
        
        # Exchange for long-lived token
        long_lived_data = await meta_oauth_service.get_long_lived_token(short_lived_token)
        access_token = long_lived_data.get("access_token")
        expires_in = long_lived_data.get("expires_in", 5184000)  # 60 days default
        
        # Get business accounts
        business_accounts = await meta_oauth_service.get_business_accounts(access_token)
        
        if not business_accounts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No business accounts found for this user",
            )
        
        # Use first business account (in production, user would select)
        business_account = business_accounts[0]
        business_account_id = business_account.get("id")
        
        # Get phone numbers for this business account
        phone_numbers = await meta_oauth_service.get_phone_numbers(
            business_account_id, access_token
        )
        
        if not phone_numbers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No phone numbers found for this business account",
            )
        
        # Use first phone number (in production, user would select)
        phone_number = phone_numbers[0]
        phone_number_id = phone_number.get("id")
        business_phone_number = phone_number.get("display_phone_number") or phone_number.get("verified_name")
        
        # Check if connection already exists
        result = await db.execute(
            select(MetaAccountConnection).where(MetaAccountConnection.user_id == current_user.id)
        )
        existing_connection = result.scalar_one_or_none()
        
        # Encrypt tokens (simplified - use proper encryption in production)
        encrypted_access_token = access_token  # TODO: Implement proper encryption
        encrypted_refresh_token = None  # TODO: Store refresh token if available
        
        if existing_connection:
            # Update existing connection
            existing_connection.meta_business_account_id = business_account_id
            existing_connection.phone_number_id = phone_number_id
            existing_connection.business_phone_number = business_phone_number
            existing_connection.access_token = encrypted_access_token
            existing_connection.refresh_token = encrypted_refresh_token
            existing_connection.status = "connected"
            existing_connection.connected_at = datetime.now(timezone.utc)
            existing_connection.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            await db.refresh(existing_connection)
            
            logger.info(f"Updated Meta connection for user {current_user.id}")
            return MetaAccountConnectionResponse.model_validate(existing_connection)
        else:
            # Create new connection
            connection = MetaAccountConnection(
                user_id=current_user.id,
                meta_business_account_id=business_account_id,
                phone_number_id=phone_number_id,
                business_phone_number=business_phone_number,
                access_token=encrypted_access_token,
                refresh_token=encrypted_refresh_token,
                status="connected",
                connected_at=datetime.now(timezone.utc),
            )
            
            db.add(connection)
            await db.commit()
            await db.refresh(connection)
            
            logger.info(f"Created Meta connection for user {current_user.id}")
            return MetaAccountConnectionResponse.model_validate(connection)
            
    except MetaOAuthError as e:
        logger.error(f"Meta OAuth error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or status.HTTP_400_BAD_REQUEST,
            detail=f"Meta OAuth error: {e.message}",
        )
    except Exception as e:
        logger.error(f"Unexpected error in OAuth callback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete OAuth flow",
        )


@router.get("/connection", response_model=MetaAccountConnectionResponse)
async def get_connection(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MetaAccountConnectionResponse:
    """Get current Meta account connection status.
    
    Args:
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Meta account connection details.
    
    Raises:
        HTTPException: If no connection found.
    """
    result = await db.execute(
        select(MetaAccountConnection).where(MetaAccountConnection.user_id == current_user.id)
    )
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Meta account connection found. Please connect your Meta account first.",
        )
    
    return MetaAccountConnectionResponse.model_validate(connection)


@router.patch("/connection", response_model=MetaAccountConnectionResponse)
async def update_connection(
    connection_data: MetaAccountConnectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MetaAccountConnectionResponse:
    """Update Meta account connection.
    
    Args:
        connection_data: Updated connection information.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Updated connection details.
    
    Raises:
        HTTPException: If connection not found.
    """
    result = await db.execute(
        select(MetaAccountConnection).where(MetaAccountConnection.user_id == current_user.id)
    )
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Meta account connection found",
        )
    
    # Update fields
    update_data = connection_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(connection, field, value)
    
    connection.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(connection)
    
    logger.info(f"Updated Meta connection for user {current_user.id}")
    
    return MetaAccountConnectionResponse.model_validate(connection)


@router.delete("/connection", response_model=SuccessResponse)
async def disconnect(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Disconnect Meta account.
    
    Args:
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Success response.
    
    Raises:
        HTTPException: If connection not found.
    """
    result = await db.execute(
        select(MetaAccountConnection).where(MetaAccountConnection.user_id == current_user.id)
    )
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Meta account connection found",
        )
    
    await db.delete(connection)
    await db.commit()
    
    logger.info(f"Disconnected Meta account for user {current_user.id}")
    
    return SuccessResponse(message="Meta account disconnected successfully")
