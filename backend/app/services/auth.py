"""Authentication service with JWT support."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import TokenPayload, UserCreate, UserResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token security
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password.
    
    Args:
        plain_password: The plain text password.
        hashed_password: The hashed password to compare against.
    
    Returns:
        True if password matches, False otherwise.
    
    Note:
        bcrypt has a 72-byte limit, so we truncate if necessary.
    """
    # bcrypt has a 72-byte password limit, truncate if necessary
    password_bytes = plain_password.encode('utf-8')[:72]
    return pwd_context.verify(password_bytes.decode('utf-8'), hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt.
    
    Args:
        password: The plain text password.
    
    Returns:
        The hashed password.
    
    Note:
        bcrypt has a 72-byte limit, so we truncate if necessary.
    """
    # bcrypt has a 72-byte password limit, truncate if necessary
    password_bytes = password.encode('utf-8')[:72]
    return pwd_context.hash(password_bytes.decode('utf-8'))


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token.
    
    Args:
        subject: The subject (user ID or username) for the token.
        expires_delta: Optional expiration time delta.
    
    Returns:
        Encoded JWT token string.
    """
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(seconds=settings.jwt_expiration)
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenPayload]:
    """Decode and validate a JWT access token.
    
    Args:
        token: The JWT token string.
    
    Returns:
        TokenPayload if valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        
        return TokenPayload(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
        )
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


async def get_user_by_username(
    db: AsyncSession,
    username: str,
) -> Optional[User]:
    """Get a user by username.
    
    Args:
        db: Database session.
        username: The username to search for.
    
    Returns:
        User if found, None otherwise.
    """
    result = await db.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> Optional[User]:
    """Get a user by email.
    
    Args:
        db: Database session.
        email: The email to search for.
    
    Returns:
        User if found, None otherwise.
    """
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(
    db: AsyncSession,
    user_id: int,
) -> Optional[User]:
    """Get a user by ID.
    
    Args:
        db: Database session.
        user_id: The user ID.
    
    Returns:
        User if found, None otherwise.
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> Optional[User]:
    """Authenticate a user by username and password.
    
    Args:
        db: Database session.
        username: The username.
        password: The plain text password.
    
    Returns:
        User if authentication successful, None otherwise.
    """
    user = await get_user_by_username(db, username)
    
    if not user:
        logger.warning(f"Authentication failed: User '{username}' not found")
        return None
    
    if not verify_password(password, user.hashed_password):
        logger.warning(f"Authentication failed: Invalid password for '{username}'")
        return None
    
    if not user.is_active:
        logger.warning(f"Authentication failed: User '{username}' is inactive")
        return None
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    
    logger.info(f"User '{username}' authenticated successfully")
    return user


async def authenticate_user_by_email(
    db: AsyncSession,
    email: str,
    password: str,
) -> Optional[User]:
    """Authenticate a user by email and password.
    
    Args:
        db: Database session.
        email: The email address.
        password: The plain text password.
    
    Returns:
        User if authentication successful, None otherwise.
    """
    user = await get_user_by_email(db, email)
    
    if not user:
        logger.warning(f"Authentication failed: User with email '{email}' not found")
        return None
    
    if not verify_password(password, user.hashed_password):
        logger.warning(f"Authentication failed: Invalid password for '{email}'")
        return None
    
    if not user.is_active:
        logger.warning(f"Authentication failed: User '{email}' is inactive")
        return None
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    
    logger.info(f"User '{email}' authenticated successfully")
    return user


async def create_user(
    db: AsyncSession,
    user_data: UserCreate,
) -> User:
    """Create a new user.
    
    Args:
        db: Database session.
        user_data: User creation data.
    
    Returns:
        Created user.
    
    Raises:
        HTTPException: If username or email already exists.
    """
    # Check if username exists
    existing = await get_user_by_username(db, user_data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    
    # Check if email exists
    existing = await get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create user
    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info(f"Created new user: {user.username}")
    return user


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token.
    
    This is a FastAPI dependency for protected endpoints.
    
    Args:
        credentials: HTTP Bearer credentials.
        db: Database session.
    
    Returns:
        Current authenticated user.
    
    Raises:
        HTTPException: If token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    token_payload = decode_access_token(credentials.credentials)
    
    if not token_payload:
        raise credentials_exception
    
    # Get user from database
    try:
        user_id = int(token_payload.sub)
        user = await get_user_by_id(db, user_id)
    except ValueError:
        # sub might be username instead of ID
        user = await get_user_by_username(db, token_payload.sub)
    
    if not user:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Get the current user if authenticated, otherwise None.
    
    This is useful for endpoints that can work with or without authentication.
    
    Args:
        credentials: HTTP Bearer credentials.
        db: Database session.
    
    Returns:
        Current user if authenticated, None otherwise.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def verify_websocket_token(token: str) -> Optional[str]:
    """Verify a JWT token for WebSocket connections.
    
    Args:
        token: The JWT token string.
    
    Returns:
        User ID/username if valid, None otherwise.
    """
    payload = decode_access_token(token)
    if payload:
        return payload.sub
    return None
