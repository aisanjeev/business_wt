"""API usage tracking endpoints."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ApiUsage, User
from app.schemas import (
    ApiUsageResponse,
    PaginatedResponse,
    UsageCostResponse,
    UsageStatsResponse,
)
from app.services.auth import get_current_user
from app.services.blob_storage import blob_storage
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/stats", response_model=UsageStatsResponse)
async def get_usage_stats(
    period_start: Optional[datetime] = Query(None, description="Start date for statistics"),
    period_end: Optional[datetime] = Query(None, description="End date for statistics"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UsageStatsResponse:
    """Get usage statistics for the current user.
    
    Args:
        period_start: Start date for statistics (defaults to 30 days ago).
        period_end: End date for statistics (defaults to now).
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Usage statistics.
    """
    # Default to last 30 days if not specified
    if not period_end:
        period_end = datetime.now()
    if not period_start:
        period_start = period_end - timedelta(days=30)
    
    # Get total API calls
    count_result = await db.execute(
        select(func.count(ApiUsage.id))
        .where(
            ApiUsage.user_id == current_user.id,
            ApiUsage.timestamp >= period_start,
            ApiUsage.timestamp <= period_end,
        )
    )
    total_api_calls = count_result.scalar() or 0
    
    # Get total messages (filter by message types)
    message_types = ["text", "template", "image", "document", "audio", "video", "sticker"]
    messages_result = await db.execute(
        select(func.count(ApiUsage.id))
        .where(
            ApiUsage.user_id == current_user.id,
            ApiUsage.message_type.in_(message_types),
            ApiUsage.timestamp >= period_start,
            ApiUsage.timestamp <= period_end,
        )
    )
    total_messages = messages_result.scalar() or 0
    
    # Get breakdown by type
    breakdown_result = await db.execute(
        select(
            ApiUsage.message_type,
            func.count(ApiUsage.id).label("count")
        )
        .where(
            ApiUsage.user_id == current_user.id,
            ApiUsage.timestamp >= period_start,
            ApiUsage.timestamp <= period_end,
        )
        .group_by(ApiUsage.message_type)
    )
    breakdown_by_type = {row.message_type: row.count for row in breakdown_result}
    
    return UsageStatsResponse(
        user_id=current_user.id,
        total_messages=total_messages,
        total_api_calls=total_api_calls,
        total_cost=0.0,  # Will be calculated in cost endpoint
        period_start=period_start,
        period_end=period_end,
        breakdown_by_type=breakdown_by_type,
    )


@router.get("/costs", response_model=UsageCostResponse)
async def get_usage_costs(
    period_start: Optional[datetime] = Query(None, description="Start date for costs"),
    period_end: Optional[datetime] = Query(None, description="End date for costs"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UsageCostResponse:
    """Get usage costs for the current user.
    
    Args:
        period_start: Start date for costs (defaults to 30 days ago).
        period_end: End date for costs (defaults to now).
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Usage costs.
    """
    from app.services.usage_calculator import usage_calculator
    
    # Default to last 30 days if not specified
    if not period_end:
        period_end = datetime.now()
    if not period_start:
        period_start = period_end - timedelta(days=30)
    
    # Get usage by message type
    breakdown_result = await db.execute(
        select(
            ApiUsage.message_type,
            func.count(ApiUsage.id).label("count")
        )
        .where(
            ApiUsage.user_id == current_user.id,
            ApiUsage.timestamp >= period_start,
            ApiUsage.timestamp <= period_end,
        )
        .group_by(ApiUsage.message_type)
    )
    
    total_cost = 0.0
    cost_breakdown = {}
    
    for row in breakdown_result:
        cost_per_message = usage_calculator.calculate_cost(row.message_type)
        type_cost = row.count * cost_per_message
        cost_breakdown[row.message_type] = type_cost
        total_cost += type_cost
    
    return UsageCostResponse(
        user_id=current_user.id,
        total_cost=total_cost,
        period_start=period_start,
        period_end=period_end,
        cost_breakdown=cost_breakdown,
    )


@router.get("/records", response_model=PaginatedResponse)
async def get_usage_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    message_type: Optional[str] = Query(None, description="Filter by message type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    """Get usage records with pagination.
    
    Args:
        page: Page number (1-indexed).
        page_size: Number of records per page.
        message_type: Optional filter by message type.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Paginated list of usage records.
    """
    # Build query - filter by user_id
    query = select(ApiUsage).where(ApiUsage.user_id == current_user.id)
    count_query = select(func.count(ApiUsage.id)).where(ApiUsage.user_id == current_user.id)
    
    # Apply message type filter
    if message_type:
        query = query.where(ApiUsage.message_type == message_type)
        count_query = count_query.where(ApiUsage.message_type == message_type)
    
    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size
    
    # Get records
    result = await db.execute(
        query.order_by(ApiUsage.timestamp.desc())
        .offset(offset)
        .limit(page_size)
    )
    records = result.scalars().all()
    
    usage_responses = [
        ApiUsageResponse.model_validate(record) for record in records
    ]
    
    return PaginatedResponse(
        items=usage_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/storage")
async def get_storage_usage(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get storage usage for the current user.
    
    Args:
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Storage usage information.
    """
    storage_used_bytes = await blob_storage.get_user_storage_usage(current_user.id, db)
    storage_formatted = blob_storage.format_storage_size(storage_used_bytes)
    
    return {
        "user_id": current_user.id,
        "storage_used_bytes": storage_used_bytes,
        "storage_formatted": storage_formatted,
    }


@router.get("/export")
async def export_usage_data(
    format: str = Query(default="csv", regex="^(csv|json)$"),
    period_start: Optional[datetime] = Query(None),
    period_end: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export usage data as CSV or JSON.
    
    Args:
        format: Export format (csv or json).
        period_start: Start date for export.
        period_end: End date for export.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Usage data in requested format.
    """
    from fastapi.responses import JSONResponse, StreamingResponse
    import csv
    import io
    
    # Default to last 30 days if not specified
    if not period_end:
        period_end = datetime.now()
    if not period_start:
        period_start = period_end - timedelta(days=30)
    
    # Get all records
    result = await db.execute(
        select(ApiUsage)
        .where(
            ApiUsage.user_id == current_user.id,
            ApiUsage.timestamp >= period_start,
            ApiUsage.timestamp <= period_end,
        )
        .order_by(ApiUsage.timestamp.desc())
    )
    records = result.scalars().all()
    
    if format == "json":
        data = [ApiUsageResponse.model_validate(record).model_dump() for record in records]
        return JSONResponse(content=data)
    
    # CSV export
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Timestamp",
        "Message Type",
        "API Endpoint",
        "Response Status",
        "Estimated Cost",
        "Request ID",
    ])
    
    # Write rows
    for record in records:
        writer.writerow([
            record.timestamp.isoformat(),
            record.message_type,
            record.api_endpoint,
            record.response_status,
            record.estimated_cost or "",
            record.request_id or "",
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=usage_export_{current_user.id}_{period_start.date()}_{period_end.date()}.csv"
        }
    )
