"""Bulk message campaign endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import BulkMessageCampaign, CampaignRecipientLog, Contact, User
from app.schemas import (
    BulkMessageCampaignCreate,
    BulkMessageCampaignResponse,
    BulkMessageCampaignUpdate,
    CampaignStatusResponse,
    PaginatedResponse,
    SuccessResponse,
)
from app.services.auth import get_current_user
from app.services.bulk_messaging import bulk_messaging_service
from app.services.whatsapp import whatsapp_client
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=BulkMessageCampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_data: BulkMessageCampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkMessageCampaignResponse:
    """Create a new bulk message campaign.
    
    Args:
        campaign_data: Campaign details.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Created campaign.
    """
    # Verify template exists if specified
    if campaign_data.template_id:
        from app.models import MessageTemplate
        result = await db.execute(
            select(MessageTemplate).where(
                MessageTemplate.id == campaign_data.template_id,
                MessageTemplate.user_id == current_user.id
            )
        )
        template = result.scalar_one_or_none()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found",
            )
    
    # Resolve contacts from lists/tags/contact_ids
    from app.models import Contact, ContactList, ContactListMembership
    from sqlalchemy import or_
    from sqlalchemy.orm import selectinload
    
    contact_ids_set = set()
    
    # Get contacts from lists
    if campaign_data.list_ids:
        result = await db.execute(
            select(ContactListMembership.contact_id)
            .join(ContactList, ContactListMembership.contact_list_id == ContactList.id)
            .where(
                ContactList.id.in_(campaign_data.list_ids),
                ContactList.user_id == current_user.id
            )
        )
        list_contact_ids = [row[0] for row in result.all()]
        contact_ids_set.update(list_contact_ids)
    
    # Get contacts from tags
    if campaign_data.tag_names:
        # Filter contacts that have any of the specified tags
        tag_conditions = []
        for tag in campaign_data.tag_names:
            from sqlalchemy import func
            tag_conditions.append(
                func.json_contains(Contact.tags, f'"{tag}"')  # type: ignore
            )
        if tag_conditions:
            result = await db.execute(
                select(Contact.id).where(
                    Contact.user_id == current_user.id,
                    or_(*tag_conditions)
                )
            )
            tag_contact_ids = [row[0] for row in result.all()]
            contact_ids_set.update(tag_contact_ids)
    
    # Add direct contact IDs
    if campaign_data.contact_ids:
        # Verify contacts belong to user
        result = await db.execute(
            select(Contact.id).where(
                Contact.id.in_(campaign_data.contact_ids),
                Contact.user_id == current_user.id
            )
        )
        direct_contact_ids = [row[0] for row in result.all()]
        contact_ids_set.update(direct_contact_ids)
    
    # Calculate total recipients
    total_recipients = len(contact_ids_set)
    
    # Build target_contacts dict for backward compatibility
    target_contacts_dict = {
        "contact_ids": list(contact_ids_set),
    }
    if campaign_data.list_ids:
        target_contacts_dict["list_ids"] = campaign_data.list_ids
    if campaign_data.tag_names:
        target_contacts_dict["tag_names"] = campaign_data.tag_names
    
    # Create campaign
    campaign = BulkMessageCampaign(
        user_id=current_user.id,
        name=campaign_data.name,
        template_id=campaign_data.template_id,
        target_contacts=target_contacts_dict if target_contacts_dict.get("contact_ids") else campaign_data.target_contacts,
        message_content=campaign_data.message_content,
        status="draft",
        total_recipients=total_recipients,
        scheduled_at=campaign_data.scheduled_at,
    )
    
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    
    logger.info(f"Created campaign {campaign.id} for user {current_user.id} with {total_recipients} recipients")
    
    return BulkMessageCampaignResponse.model_validate(campaign)


@router.get("", response_model=PaginatedResponse)
async def get_campaigns(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    """Get campaigns for the current user.
    
    Args:
        page: Page number (1-indexed).
        page_size: Number of campaigns per page.
        status_filter: Optional filter by status.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Paginated list of campaigns.
    """
    # Build query - filter by user_id
    query = select(BulkMessageCampaign).where(BulkMessageCampaign.user_id == current_user.id)
    count_query = select(func.count(BulkMessageCampaign.id)).where(BulkMessageCampaign.user_id == current_user.id)
    
    # Apply status filter
    if status_filter:
        query = query.where(BulkMessageCampaign.status == status_filter)
        count_query = count_query.where(BulkMessageCampaign.status == status_filter)
    
    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size
    
    # Get campaigns
    result = await db.execute(
        query.order_by(BulkMessageCampaign.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    campaigns = result.scalars().all()
    
    campaign_responses = [
        BulkMessageCampaignResponse.model_validate(campaign) for campaign in campaigns
    ]
    
    return PaginatedResponse(
        items=campaign_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{campaign_id}", response_model=BulkMessageCampaignResponse)
async def get_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkMessageCampaignResponse:
    """Get a specific campaign.
    
    Args:
        campaign_id: Campaign ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Campaign details.
    """
    result = await db.execute(
        select(BulkMessageCampaign).where(
            BulkMessageCampaign.id == campaign_id,
            BulkMessageCampaign.user_id == current_user.id
        )
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    
    return BulkMessageCampaignResponse.model_validate(campaign)


@router.patch("/{campaign_id}", response_model=BulkMessageCampaignResponse)
async def update_campaign(
    campaign_id: int,
    campaign_data: BulkMessageCampaignUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkMessageCampaignResponse:
    """Update a campaign (only draft campaigns can be updated).
    
    Args:
        campaign_id: Campaign ID.
        campaign_data: Updated campaign data.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Updated campaign.
    """
    result = await db.execute(
        select(BulkMessageCampaign).where(
            BulkMessageCampaign.id == campaign_id,
            BulkMessageCampaign.user_id == current_user.id
        )
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    
    # Only allow updating draft campaigns
    if campaign.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft campaigns can be updated",
        )
    
    # Update fields
    update_data = campaign_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(campaign, field, value)
    
    campaign.updated_at = datetime.now()
    
    await db.commit()
    await db.refresh(campaign)
    
    logger.info(f"Updated campaign {campaign_id}")
    
    return BulkMessageCampaignResponse.model_validate(campaign)


@router.post("/{campaign_id}/start", response_model=SuccessResponse)
async def start_campaign(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Start a campaign (begin sending messages).
    
    Args:
        campaign_id: Campaign ID.
        background_tasks: Background task runner.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Success response.
    """
    result = await db.execute(
        select(BulkMessageCampaign).where(
            BulkMessageCampaign.id == campaign_id,
            BulkMessageCampaign.user_id == current_user.id
        )
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    
    # Only allow starting draft or scheduled campaigns
    if campaign.status not in ("draft", "scheduled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign can only be started if it's in draft or scheduled status",
        )
    
    # Check if scheduled time has passed
    if campaign.scheduled_at and campaign.scheduled_at > datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduled time has not arrived yet",
        )
    
    # Start campaign in background
    background_tasks.add_task(
        _run_campaign,
        campaign_id=campaign_id,
        user_id=current_user.id,
    )
    
    logger.info(f"Started campaign {campaign_id} for user {current_user.id}")
    
    return SuccessResponse(message="Campaign started successfully")


@router.get("/{campaign_id}/status", response_model=CampaignStatusResponse)
async def get_campaign_status(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CampaignStatusResponse:
    """Get campaign status and progress.
    
    Args:
        campaign_id: Campaign ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Campaign status and progress.
    """
    result = await db.execute(
        select(BulkMessageCampaign).where(
            BulkMessageCampaign.id == campaign_id,
            BulkMessageCampaign.user_id == current_user.id
        )
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    
    progress = 0.0
    if campaign.total_recipients > 0:
        progress = (campaign.sent_count + campaign.failed_count) / campaign.total_recipients * 100
    
    return CampaignStatusResponse(
        id=campaign.id,
        status=campaign.status,
        total_recipients=campaign.total_recipients,
        sent_count=campaign.sent_count,
        failed_count=campaign.failed_count,
        progress_percentage=progress,
        started_at=campaign.started_at,
        completed_at=campaign.completed_at,
    )


async def _run_campaign(campaign_id: int, user_id: int) -> None:
    """Background task to run a campaign.
    
    Args:
        campaign_id: Campaign ID.
        user_id: User ID.
    """
    from app.database import get_db_context
    
    async with get_db_context() as db:
        # Get campaign
        result = await db.execute(
            select(BulkMessageCampaign).where(
                BulkMessageCampaign.id == campaign_id,
                BulkMessageCampaign.user_id == user_id
            )
        )
        campaign = result.scalar_one_or_none()
        
        if not campaign:
            logger.error(f"Campaign {campaign_id} not found")
            return
        
        try:
            # Get contacts for campaign
            contacts = await bulk_messaging_service.get_contacts_for_campaign(db, campaign)
            
            if not contacts:
                campaign.status = "completed"
                campaign.completed_at = datetime.now()
                await db.commit()
                logger.warning(f"Campaign {campaign_id} has no contacts")
                return
            
            # Send messages
            sent_count, failed_count = await bulk_messaging_service.send_campaign_messages(
                db,
                campaign,
                contacts,
                whatsapp_client,
            )
            
            # Update campaign status
            campaign.status = "completed" if failed_count == 0 else "completed"
            campaign.completed_at = datetime.now()
            await db.commit()
            
            logger.info(f"Campaign {campaign_id} completed: {sent_count} sent, {failed_count} failed")
            
        except Exception as e:
            logger.error(f"Error running campaign {campaign_id}: {e}", exc_info=True)
            campaign.status = "failed"
            campaign.completed_at = datetime.now()
            await db.commit()


@router.get("/{campaign_id}/logs")
async def get_campaign_logs(
    campaign_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get campaign recipient logs with pagination and filters."""
    # Verify campaign belongs to user
    result = await db.execute(
        select(BulkMessageCampaign).where(
            BulkMessageCampaign.id == campaign_id,
            BulkMessageCampaign.user_id == current_user.id,
        )
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Build query
    query = select(CampaignRecipientLog).where(
        CampaignRecipientLog.campaign_id == campaign_id
    )
    
    # Apply filters
    if status:
        query = query.where(CampaignRecipientLog.status == status)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                CampaignRecipientLog.phone_number.ilike(search_pattern),
                Contact.name.ilike(search_pattern),
            )
        )
    
    # Join with Contact for name search
    query = query.join(Contact, CampaignRecipientLog.contact_id == Contact.id)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination and ordering
    query = query.order_by(CampaignRecipientLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Serialize logs with contact names
    log_items = []
    for log in logs:
        contact_result = await db.execute(
            select(Contact).where(Contact.id == log.contact_id)
        )
        contact = contact_result.scalar_one_or_none()
        
        log_items.append({
            "id": log.id,
            "campaign_id": log.campaign_id,
            "contact_id": log.contact_id,
            "message_id": log.message_id,
            "phone_number": log.phone_number,
            "contact_name": contact.name if contact else None,
            "status": log.status,
            "sent_at": log.sent_at.isoformat() if log.sent_at else None,
            "delivered_at": log.delivered_at.isoformat() if log.delivered_at else None,
            "read_at": log.read_at.isoformat() if log.read_at else None,
            "failed_at": log.failed_at.isoformat() if log.failed_at else None,
            "error_message": log.error_message,
            "cost": log.cost,
            "created_at": log.created_at.isoformat(),
        })
    
    return {
        "items": log_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": (page * page_size) < total,
    }


@router.get("/{campaign_id}/logs/export")
async def export_campaign_logs(
    campaign_id: int,
    format: str = Query("csv", regex="^(csv|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export campaign logs as CSV or JSON."""
    from fastapi.responses import Response
    
    # Verify campaign belongs to user
    result = await db.execute(
        select(BulkMessageCampaign).where(
            BulkMessageCampaign.id == campaign_id,
            BulkMessageCampaign.user_id == current_user.id,
        )
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get all logs
    query = select(CampaignRecipientLog).where(
        CampaignRecipientLog.campaign_id == campaign_id
    ).order_by(CampaignRecipientLog.created_at.desc())
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    if format == "csv":
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "ID", "Phone Number", "Contact Name", "Status", "Sent At",
            "Delivered At", "Read At", "Failed At", "Error", "Cost", "Created At"
        ])
        
        # Write rows
        for log in logs:
            contact_result = await db.execute(
                select(Contact).where(Contact.id == log.contact_id)
            )
            contact = contact_result.scalar_one_or_none()
            
            writer.writerow([
                log.id,
                log.phone_number,
                contact.name if contact else "",
                log.status,
                log.sent_at.isoformat() if log.sent_at else "",
                log.delivered_at.isoformat() if log.delivered_at else "",
                log.read_at.isoformat() if log.read_at else "",
                log.failed_at.isoformat() if log.failed_at else "",
                log.error_message or "",
                log.cost or "",
                log.created_at.isoformat(),
            ])
        
        output.seek(0)
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=campaign_{campaign_id}_logs.csv"}
        )
    
    else:  # JSON
        import json
        
        log_items = []
        for log in logs:
            contact_result = await db.execute(
                select(Contact).where(Contact.id == log.contact_id)
            )
            contact = contact_result.scalar_one_or_none()
            
            log_items.append({
                "id": log.id,
                "phone_number": log.phone_number,
                "contact_name": contact.name if contact else None,
                "status": log.status,
                "sent_at": log.sent_at.isoformat() if log.sent_at else None,
                "delivered_at": log.delivered_at.isoformat() if log.delivered_at else None,
                "read_at": log.read_at.isoformat() if log.read_at else None,
                "failed_at": log.failed_at.isoformat() if log.failed_at else None,
                "error_message": log.error_message,
                "cost": log.cost,
                "created_at": log.created_at.isoformat(),
            })
        
        return Response(
            content=json.dumps(log_items, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=campaign_{campaign_id}_logs.json"}
        )
