"""Authentication endpoints."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import Token, UserCreate, UserLogin, UserResponse
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_user,
    get_current_user,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user.
    
    Args:
        user_data: User registration data.
        db: Database session.
    
    Returns:
        Created user.
    """
    user = await create_user(db, user_data)
    logger.info(f"New user registered: {user.username}")
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Login and get access token.
    
    Args:
        credentials: Login credentials.
        db: Database session.
    
    Returns:
        JWT access token.
    
    Raises:
        HTTPException: If authentication fails.
    """
    user = await authenticate_user(db, credentials.username, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(seconds=settings.jwt_expiration),
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_expiration,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get current authenticated user information.
    
    Args:
        current_user: Currently authenticated user.
    
    Returns:
        User information.
    """
    return UserResponse.model_validate(current_user)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_user),
) -> Token:
    """Refresh access token.
    
    Args:
        current_user: Currently authenticated user.
    
    Returns:
        New JWT access token.
    """
    access_token = create_access_token(
        subject=str(current_user.id),
        expires_delta=timedelta(seconds=settings.jwt_expiration),
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_expiration,
    )
