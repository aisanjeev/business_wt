"""Template management API endpoints."""

import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MessageTemplate, MetaAccountConnection, User
from app.schemas import (
    PaginatedResponse,
    SuccessResponse,
    TemplateCreate,
    TemplatePreviewRequest,
    TemplatePreviewResponse,
    TemplateResponse,
    TemplateSyncResponse,
    TemplateUpdate,
)
from app.services.auth import get_current_user
from app.services.template import MetaTemplateAPIError, TemplateSyncService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/templates", tags=["templates"])

sync_service = TemplateSyncService()


def validate_template_name(name: str) -> bool:
    """Validate template name format (alphanumeric, lowercase, underscore only)."""
    return bool(re.match(r"^[a-z0-9_]+$", name))


def validate_variables(body_text: str) -> tuple[bool, Optional[str]]:
    """Validate that variables are sequential ({{1}}, {{2}}, etc., no skipping).
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not body_text:
        return True, None
    
    # Find all variable placeholders
    pattern = r'\{\{(\d+)\}\}'
    matches = re.findall(pattern, body_text)
    
    if not matches:
        return True, None
    
    # Convert to integers and sort
    var_numbers = sorted([int(m) for m in matches])
    
    # Check if sequential starting from 1
    expected = list(range(1, len(var_numbers) + 1))
    if var_numbers != expected:
        return False, f"Variables must be sequential starting from {{1}}. Found: {var_numbers}"
    
    # Check max variables (10)
    if len(var_numbers) > 10:
        return False, "Maximum 10 variables allowed"
    
    return True, None


@router.get("", response_model=PaginatedResponse)
async def list_templates(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    language: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    """List templates with optional filtering.
    
    Args:
        page: Page number.
        page_size: Items per page.
        category: Filter by category (marketing, utility, authentication).
        status_filter: Filter by status (PENDING, APPROVED, REJECTED, etc.).
        language: Filter by language code.
        search: Search in template name and body.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Paginated list of templates.
    """
    query = select(MessageTemplate).where(MessageTemplate.user_id == current_user.id)
    
    # Apply filters
    if category:
        query = query.where(MessageTemplate.category == category.lower())
    
    if status_filter:
        query = query.where(MessageTemplate.status == status_filter.upper())
    
    if language:
        query = query.where(MessageTemplate.language == language.lower())
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                MessageTemplate.name.ilike(search_pattern),
                MessageTemplate.body_text.ilike(search_pattern),
                MessageTemplate.content.ilike(search_pattern),
            )
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(MessageTemplate.created_at.desc()).offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    templates = result.scalars().all()
    
    # Convert to response format
    items = [TemplateResponse.model_validate(template) for template in templates]
    
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateResponse:
    """Get a single template by ID.
    
    Args:
        template_id: Template ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Template data.
    """
    result = await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.id == template_id,
            MessageTemplate.user_id == current_user.id,
        )
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    return TemplateResponse.model_validate(template)


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateResponse:
    """Create a new template.
    
    Args:
        template_data: Template creation data.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Created template.
    """
    # Validate template name
    if not validate_template_name(template_data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template name must contain only lowercase letters, numbers, and underscores",
        )
    
    # Validate body_text or use content as fallback
    body_text = template_data.body_text or template_data.content
    if not body_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template body text is required",
        )
    
    # Validate variables
    is_valid, error_msg = validate_variables(body_text)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
    
    # Check for duplicate name+language combination
    existing = await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.name == template_data.name,
            MessageTemplate.language == template_data.language,
            MessageTemplate.user_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template with name '{template_data.name}' and language '{template_data.language}' already exists",
        )
    
    # Create template
    new_template = MessageTemplate(
        user_id=current_user.id,
        name=template_data.name,
        category=template_data.category.lower(),
        language=template_data.language.lower(),
        status=template_data.status or "PENDING",
        header_type=template_data.header_type,
        header_content=template_data.header_content,
        body_text=body_text,
        footer_text=template_data.footer_text,
        buttons=template_data.buttons,
        waba_id=template_data.waba_id,
        variables=template_data.variables or {},
        content=body_text,  # Legacy field
    )
    
    # If waba_id not provided, try to get it from user's Meta connection
    if not new_template.waba_id:
        conn_result = await db.execute(
            select(MetaAccountConnection).where(
                MetaAccountConnection.user_id == current_user.id,
                MetaAccountConnection.status == "connected"
            )
        )
        connection = conn_result.scalar_one_or_none()
        if connection:
            # Try to resolve WABA ID from Business Account
            try:
                from app.services.meta_oauth import MetaOAuthService
                oauth_service = MetaOAuthService()
                wabas = await oauth_service.get_whatsapp_business_accounts(
                    business_account_id=connection.meta_business_account_id,
                    access_token=connection.access_token
                )
                if wabas and len(wabas) > 0:
                    # Use the first WABA
                    new_template.waba_id = wabas[0].get("id")
                    logger.info(f"Resolved WABA ID {new_template.waba_id} from Business Account")
                else:
                    # Fallback to Business Account ID (might work in some cases)
                    new_template.waba_id = connection.meta_business_account_id
                    logger.warning(f"Could not resolve WABA ID, using Business Account ID: {new_template.waba_id}")
            except Exception as e:
                logger.warning(f"Error resolving WABA ID: {e}, using Business Account ID")
                # Fallback to Business Account ID
                new_template.waba_id = connection.meta_business_account_id
    
    db.add(new_template)
    await db.commit()
    await db.refresh(new_template)
    
    logger.info(f"Created template '{new_template.name}' (ID: {new_template.id}) for user {current_user.id}")
    
    return TemplateResponse.model_validate(new_template)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    template_data: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateResponse:
    """Update an existing template.
    
    Args:
        template_id: Template ID.
        template_data: Template update data.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Updated template.
    """
    result = await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.id == template_id,
            MessageTemplate.user_id == current_user.id,
        )
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    # Check if template is approved - can't modify approved templates
    if template.status == "APPROVED" and template.meta_template_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify approved templates. Create a new template instead.",
        )
    
    # Update fields
    if template_data.name is not None:
        if not validate_template_name(template_data.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template name must contain only lowercase letters, numbers, and underscores",
            )
        template.name = template_data.name
    
    if template_data.category is not None:
        template.category = template_data.category.lower()
    
    if template_data.language is not None:
        template.language = template_data.language.lower()
    
    if template_data.status is not None:
        template.status = template_data.status.upper()
    
    if template_data.header_type is not None:
        template.header_type = template_data.header_type
    if template_data.header_content is not None:
        template.header_content = template_data.header_content
    
    # Update body_text
    body_text = template_data.body_text or template_data.content
    if body_text is not None:
        # Validate variables
        is_valid, error_msg = validate_variables(body_text)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )
        template.body_text = body_text
        template.content = body_text  # Legacy field
    
    if template_data.footer_text is not None:
        template.footer_text = template_data.footer_text
    
    if template_data.buttons is not None:
        template.buttons = template_data.buttons
    
    if template_data.variables is not None:
        template.variables = template_data.variables
    
    await db.commit()
    await db.refresh(template)
    
    logger.info(f"Updated template {template_id} for user {current_user.id}")
    
    return TemplateResponse.model_validate(template)


@router.delete("/{template_id}", response_model=SuccessResponse)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Delete a template.
    
    Args:
        template_id: Template ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Success response.
    """
    result = await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.id == template_id,
            MessageTemplate.user_id == current_user.id,
        )
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    # If template exists in Meta, try to delete it there
    if template.meta_template_id and template.waba_id:
        try:
            from app.services.template import MetaTemplateAPIClient
            meta_client = MetaTemplateAPIClient()
            await meta_client.delete_template(
                waba_id=template.waba_id,
                template_name=template.name,
                hsm_id=template.meta_template_id,
            )
            logger.info(f"Deleted template '{template.name}' from Meta API")
        except MetaTemplateAPIError as e:
            logger.warning(f"Failed to delete template from Meta API: {e.message}")
            # Continue with local deletion even if Meta deletion fails
    
    # Delete from local database
    await db.delete(template)
    await db.commit()
    
    logger.info(f"Deleted template {template_id} for user {current_user.id}")
    
    return SuccessResponse(message="Template deleted successfully")


@router.post("/sync", response_model=TemplateSyncResponse)
async def sync_templates(
    waba_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateSyncResponse:
    """Sync templates from Meta API to local database.
    
    Args:
        waba_id: WhatsApp Business Account ID (uses user's default if not provided).
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Sync statistics.
    """
    # If waba_id not provided, get it from user's Meta connection
    if not waba_id:
        conn_result = await db.execute(
            select(MetaAccountConnection).where(
                MetaAccountConnection.user_id == current_user.id,
                MetaAccountConnection.status == "connected"
            )
        )
        connection = conn_result.scalar_one_or_none()
        if connection:
            waba_id = connection.meta_business_account_id
    
    if not waba_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="WABA ID is required. Please provide waba_id parameter or connect your Meta Business Account.",
        )
    
    stats = await sync_service.sync_from_meta(
        db=db,
        user_id=current_user.id,
        waba_id=waba_id,
    )
    
    return TemplateSyncResponse(
        success=len(stats["errors"]) == 0,
        created=stats["created"],
        updated=stats["updated"],
        errors=stats["errors"],
        message=f"Synced {stats['created']} new templates, updated {stats['updated']} existing templates",
    )


@router.post("/{template_id}/submit", response_model=TemplateResponse)
async def submit_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateResponse:
    """Submit a pending template to Meta API for approval.
    
    Args:
        template_id: Template ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Updated template with Meta API response.
    """
    result = await sync_service.sync_to_meta(
        db=db,
        user_id=current_user.id,
        template_id=template_id,
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to submit template to Meta API"),
        )
    
    # Get updated template
    template_result = await db.execute(
        select(MessageTemplate).where(MessageTemplate.id == template_id)
    )
    template = template_result.scalar_one()
    
    return TemplateResponse.model_validate(template)


@router.post("/{template_id}/preview", response_model=TemplatePreviewResponse)
async def preview_template(
    template_id: int,
    preview_request: Optional[TemplatePreviewRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplatePreviewResponse:
    """Generate a preview of a template with sample variables.
    
    Args:
        template_id: Template ID.
        preview_request: Optional preview request with sample variables.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Preview with variables replaced.
    """
    result = await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.id == template_id,
            MessageTemplate.user_id == current_user.id,
        )
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    body_text = template.body_text or template.content or ""
    sample_vars = (preview_request.sample_variables if preview_request else None) or template.variables or {}
    
    # Replace variables in body
    preview_body = body_text
    for var_num, var_value in sample_vars.items():
        preview_body = preview_body.replace(f"{{{{{var_num}}}}}", str(var_value))
    
    # Build preview response
    preview = TemplatePreviewResponse(
        header=template.header_content if template.header_type == "TEXT" else None,
        body=preview_body,
        footer=template.footer_text,
        buttons=template.buttons.get("buttons", []) if template.buttons else None,
    )
    
    return preview
