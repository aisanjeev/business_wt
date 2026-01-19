"""Admin API endpoints for managing users and platform statistics."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Numeric

from app.database import get_db
from app.models import ApiUsage, BulkMessageCampaign, Contact, Conversation, MetaAccountConnection, Message, User
from app.schemas import AdminUserCreate, PaginatedResponse, UserResponse
from app.services.auth import create_user, get_current_user
from app.services.blob_storage import blob_storage

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to require admin access."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_admin(
    user_data: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new user (admin only)."""
    # Extract admin-specific fields
    is_superuser = user_data.is_superuser
    is_active = user_data.is_active
    
    # Import needed functions
    from app.services.auth import get_user_by_email, get_user_by_username, get_password_hash
    from app.utils.logger import get_logger
    
    logger = get_logger(__name__)
    
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
    
    # Create user with admin flags
    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        is_superuser=is_superuser,
        is_active=is_active,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info(f"Admin {current_user.username} created new user: {user.username} (superuser: {is_superuser}, active: {is_active})")
    
    return UserResponse.model_validate(user)


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all users with pagination."""
    # Build query
    query = select(User)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_pattern)) |
            (User.name.ilike(search_pattern))
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination and ordering
    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Serialize users
    user_items = []
    for user in users:
        # Get Meta connection status
        conn_result = await db.execute(
            select(MetaAccountConnection).where(MetaAccountConnection.user_id == user.id)
        )
        connection = conn_result.scalar_one_or_none()
        
        # Get usage stats
        usage_result = await db.execute(
            select(
                func.count(ApiUsage.id).label('total_api_calls'),
                func.sum(cast(ApiUsage.estimated_cost, Numeric)).label('total_cost')
            ).where(ApiUsage.user_id == user.id)
        )
        usage = usage_result.first()
        
        # Get storage usage
        storage_used_bytes = await blob_storage.get_user_storage_usage(user.id, db)
        
        user_items.append({
            "id": user.id,
            "email": user.email,
            "name": user.full_name or user.username,
            "is_superuser": user.is_superuser,
            "is_active": user.is_active if hasattr(user, 'is_active') else True,
            "meta_connected": connection is not None and connection.status == "connected",
            "total_api_calls": usage.total_api_calls or 0,
            "total_cost": float(usage.total_cost or 0),
            "storage_used_bytes": storage_used_bytes,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        })
    
    return {
        "items": user_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": (page * page_size) < total,
    }


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get user details with usage and connection info."""
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get Meta connection
    conn_result = await db.execute(
        select(MetaAccountConnection).where(MetaAccountConnection.user_id == user_id)
    )
    connection = conn_result.scalar_one_or_none()
    
    # Get usage stats
    usage_result = await db.execute(
        select(
            func.count(ApiUsage.id).label('total_api_calls'),
            func.sum(cast(ApiUsage.estimated_cost, Numeric)).label('total_cost')
        ).where(ApiUsage.user_id == user_id)
    )
    usage = usage_result.first()
    
    # Get counts
    contacts_result = await db.execute(
        select(func.count(Contact.id)).where(Contact.user_id == user_id)
    )
    conversations_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
    )
    campaigns_result = await db.execute(
        select(func.count(BulkMessageCampaign.id)).where(BulkMessageCampaign.user_id == user_id)
    )
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.full_name or user.username,
        "is_superuser": user.is_superuser,
        "is_active": user.is_active if hasattr(user, 'is_active') else True,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "meta_connection": {
            "status": connection.status if connection else None,
            "business_phone_number": connection.business_phone_number if connection else None,
            "connected_at": connection.created_at.isoformat() if connection else None,
        } if connection else None,
        "usage": {
            "total_api_calls": usage.total_api_calls or 0,
            "total_cost": float(usage.total_cost or 0),
        },
        "storage_used_bytes": await blob_storage.get_user_storage_usage(user.id, db),
        "counts": {
            "contacts": contacts_result.scalar() or 0,
            "conversations": conversations_result.scalar() or 0,
            "campaigns": campaigns_result.scalar() or 0,
        },
    }


@router.get("/overview")
async def get_platform_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get platform-wide statistics."""
    # Total users
    users_result = await db.execute(select(func.count(User.id)))
    total_users = users_result.scalar() or 0
    
    # Active users (with Meta connection)
    active_users_result = await db.execute(
        select(func.count(func.distinct(MetaAccountConnection.user_id))).where(
            MetaAccountConnection.status == "connected"
        )
    )
    active_users = active_users_result.scalar() or 0
    
    # Total API calls
    api_calls_result = await db.execute(select(func.count(ApiUsage.id)))
    total_api_calls = api_calls_result.scalar() or 0
    
    # Total cost
    cost_result = await db.execute(
        select(func.sum(cast(ApiUsage.estimated_cost, Numeric)))
    )
    total_cost = float(cost_result.scalar() or 0)
    
    # Total messages
    messages_result = await db.execute(select(func.count(Message.id)))
    total_messages = messages_result.scalar() or 0
    
    # Total campaigns
    campaigns_result = await db.execute(select(func.count(BulkMessageCampaign.id)))
    total_campaigns = campaigns_result.scalar() or 0
    
    # Total storage (sum of all MediaFile sizes)
    from app.models import MediaFile
    storage_result = await db.execute(select(func.sum(MediaFile.file_size_bytes)))
    total_storage_bytes = int(storage_result.scalar() or 0)
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_storage_bytes": total_storage_bytes,
        "total_api_calls": total_api_calls,
        "total_cost": total_cost,
        "total_messages": total_messages,
        "total_campaigns": total_campaigns,
    }
