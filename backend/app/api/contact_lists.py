"""Contact list and folder management endpoints."""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Contact, ContactList, ContactListFolder, ContactListMembership, User
from app.schemas import (
    ContactListCreate,
    ContactListFolderCreate,
    ContactListFolderResponse,
    ContactListFolderUpdate,
    ContactListResponse,
    ContactListUpdate,
    ContactResponse,
    MoveFolderRequest,
    MoveListRequest,
    PaginatedResponse,
    SuccessResponse,
)
from app.services.auth import get_current_user
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/contact-lists", tags=["contact-lists"])


# ============================================================================
# Folder Endpoints
# ============================================================================

@router.post("/folders", response_model=ContactListFolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_data: ContactListFolderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactListFolderResponse:
    """Create a new contact list folder.
    
    Args:
        folder_data: Folder information.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Created folder.
    """
    # Validate parent folder exists and belongs to user
    if folder_data.parent_folder_id:
        result = await db.execute(
            select(ContactListFolder).where(
                ContactListFolder.id == folder_data.parent_folder_id,
                ContactListFolder.user_id == current_user.id
            )
        )
        parent_folder = result.scalar_one_or_none()
        if not parent_folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent folder not found",
            )
    
    folder = ContactListFolder(
        **folder_data.model_dump(),
        user_id=current_user.id
    )
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    
    logger.info(f"Created folder {folder.id} for user {current_user.id}")
    return ContactListFolderResponse(
        **folder_data.model_dump(),
        id=folder.id,
        user_id=folder.user_id,
        lists_count=0,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
    )


@router.get("/folders", response_model=list[ContactListFolderResponse])
async def get_folders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ContactListFolderResponse]:
    """Get all folders for the current user (tree structure).
    
    Args:
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        List of folders with list counts.
    """
    result = await db.execute(
        select(ContactListFolder)
        .options(selectinload(ContactListFolder.lists))
        .where(ContactListFolder.user_id == current_user.id)
        .order_by(ContactListFolder.name)
    )
    folders = result.scalars().all()
    
    # Calculate list counts
    folder_responses = []
    for folder in folders:
        list_count = len(folder.lists) if folder.lists else 0
        folder_responses.append(ContactListFolderResponse(
            id=folder.id,
            user_id=folder.user_id,
            name=folder.name,
            description=folder.description,
            color=folder.color,
            parent_folder_id=folder.parent_folder_id,
            lists_count=list_count,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
        ))
    
    return folder_responses


@router.get("/folders/{folder_id}", response_model=ContactListFolderResponse)
async def get_folder(
    folder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactListFolderResponse:
    """Get a specific folder by ID.
    
    Args:
        folder_id: The folder ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Folder details.
    """
    result = await db.execute(
        select(ContactListFolder)
        .options(selectinload(ContactListFolder.lists))
        .where(
            ContactListFolder.id == folder_id,
            ContactListFolder.user_id == current_user.id
        )
    )
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found",
        )
    
    list_count = len(folder.lists) if folder.lists else 0
    return ContactListFolderResponse(
        id=folder.id,
        user_id=folder.user_id,
        name=folder.name,
        description=folder.description,
        color=folder.color,
        parent_folder_id=folder.parent_folder_id,
        lists_count=list_count,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
    )


@router.patch("/folders/{folder_id}", response_model=ContactListFolderResponse)
async def update_folder(
    folder_id: int,
    folder_data: ContactListFolderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactListFolderResponse:
    """Update a folder.
    
    Args:
        folder_id: The folder ID.
        folder_data: Updated folder information.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Updated folder.
    """
    result = await db.execute(
        select(ContactListFolder).where(
            ContactListFolder.id == folder_id,
            ContactListFolder.user_id == current_user.id
        )
    )
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found",
        )
    
    # Validate parent folder if changing
    if folder_data.parent_folder_id is not None and folder_data.parent_folder_id != folder.parent_folder_id:
        if folder_data.parent_folder_id:
            parent_result = await db.execute(
                select(ContactListFolder).where(
                    ContactListFolder.id == folder_data.parent_folder_id,
                    ContactListFolder.user_id == current_user.id
                )
            )
            parent_folder = parent_result.scalar_one_or_none()
            if not parent_folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent folder not found",
                )
            # Prevent circular reference
            if folder_data.parent_folder_id == folder_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot set folder as its own parent",
                )
    
    # Update folder
    update_data = folder_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(folder, key, value)
    
    folder.updated_at = datetime.now()
    await db.commit()
    await db.refresh(folder)
    
    # Get list count
    result = await db.execute(
        select(func.count(ContactList.id)).where(ContactList.folder_id == folder_id)
    )
    list_count = result.scalar() or 0
    
    logger.info(f"Updated folder {folder_id} for user {current_user.id}")
    return ContactListFolderResponse(
        id=folder.id,
        user_id=folder.user_id,
        name=folder.name,
        description=folder.description,
        color=folder.color,
        parent_folder_id=folder.parent_folder_id,
        lists_count=list_count,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
    )


@router.patch("/folders/{folder_id}/move", response_model=ContactListFolderResponse)
async def move_folder(
    folder_id: int,
    move_data: MoveFolderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactListFolderResponse:
    """Move a folder to another folder (or root).
    
    Args:
        folder_id: The folder ID to move.
        move_data: Move request with new parent folder ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Updated folder.
    """
    result = await db.execute(
        select(ContactListFolder).where(
            ContactListFolder.id == folder_id,
            ContactListFolder.user_id == current_user.id
        )
    )
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found",
        )
    
    # Validate new parent folder
    if move_data.parent_folder_id:
        parent_result = await db.execute(
            select(ContactListFolder).where(
                ContactListFolder.id == move_data.parent_folder_id,
                ContactListFolder.user_id == current_user.id
            )
        )
        parent_folder = parent_result.scalar_one_or_none()
        if not parent_folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent folder not found",
            )
        # Prevent circular reference
        if move_data.parent_folder_id == folder_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot move folder into itself",
            )
        # Prevent moving into own child
        # TODO: Add recursive check for nested folders
    
    folder.parent_folder_id = move_data.parent_folder_id
    folder.updated_at = datetime.now()
    await db.commit()
    await db.refresh(folder)
    
    # Get list count
    result = await db.execute(
        select(func.count(ContactList.id)).where(ContactList.folder_id == folder_id)
    )
    list_count = result.scalar() or 0
    
    logger.info(f"Moved folder {folder_id} to parent {move_data.parent_folder_id} for user {current_user.id}")
    return ContactListFolderResponse(
        id=folder.id,
        user_id=folder.user_id,
        name=folder.name,
        description=folder.description,
        color=folder.color,
        parent_folder_id=folder.parent_folder_id,
        lists_count=list_count,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
    )


@router.delete("/folders/{folder_id}", response_model=SuccessResponse)
async def delete_folder(
    folder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Delete a folder (lists will be moved to root or parent).
    
    Args:
        folder_id: The folder ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Success response.
    """
    result = await db.execute(
        select(ContactListFolder).where(
            ContactListFolder.id == folder_id,
            ContactListFolder.user_id == current_user.id
        )
    )
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found",
        )
    
    # Move all lists in this folder to the folder's parent (or root if no parent)
    await db.execute(
        ContactList.__table__.update()
        .where(ContactList.folder_id == folder_id)
        .values(folder_id=folder.parent_folder_id)
    )
    
    # Move child folders to parent (or root)
    await db.execute(
        ContactListFolder.__table__.update()
        .where(ContactListFolder.parent_folder_id == folder_id)
        .values(parent_folder_id=folder.parent_folder_id)
    )
    
    # Delete folder
    await db.delete(folder)
    await db.commit()
    
    logger.info(f"Deleted folder {folder_id} for user {current_user.id}")
    return SuccessResponse(message="Folder deleted successfully")


# ============================================================================
# List Endpoints
# ============================================================================

@router.post("", response_model=ContactListResponse, status_code=status.HTTP_201_CREATED)
async def create_list(
    list_data: ContactListCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactListResponse:
    """Create a new contact list.
    
    Args:
        list_data: List information.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Created list.
    """
    # Validate folder exists and belongs to user
    if list_data.folder_id:
        result = await db.execute(
            select(ContactListFolder).where(
                ContactListFolder.id == list_data.folder_id,
                ContactListFolder.user_id == current_user.id
            )
        )
        folder = result.scalar_one_or_none()
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found",
            )
    
    contact_list = ContactList(
        **list_data.model_dump(),
        user_id=current_user.id
    )
    db.add(contact_list)
    await db.commit()
    await db.refresh(contact_list)
    
    logger.info(f"Created list {contact_list.id} for user {current_user.id}")
    return ContactListResponse(
        **list_data.model_dump(),
        id=contact_list.id,
        user_id=contact_list.user_id,
        contacts_count=0,
        created_at=contact_list.created_at,
        updated_at=contact_list.updated_at,
    )


@router.get("", response_model=PaginatedResponse)
async def get_lists(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    folder_id: Optional[int] = Query(None, description="Filter by folder ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    """Get all contact lists for the current user.
    
    Args:
        page: Page number.
        page_size: Items per page.
        folder_id: Optional filter by folder ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Paginated list of contact lists.
    """
    # Build query
    query = select(ContactList).where(ContactList.user_id == current_user.id)
    count_query = select(func.count(ContactList.id)).where(ContactList.user_id == current_user.id)
    
    # Apply folder filter
    if folder_id is not None:
        query = query.where(ContactList.folder_id == folder_id)
        count_query = count_query.where(ContactList.folder_id == folder_id)
    
    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size
    
    # Get lists with contact counts
    result = await db.execute(
        query.options(selectinload(ContactList.memberships))
        .order_by(ContactList.name)
        .offset(offset)
        .limit(page_size)
    )
    lists = result.scalars().all()
    
    list_responses = []
    for contact_list in lists:
        contact_count = len(contact_list.memberships) if contact_list.memberships else 0
        list_responses.append(ContactListResponse(
            id=contact_list.id,
            user_id=contact_list.user_id,
            name=contact_list.name,
            description=contact_list.description,
            color=contact_list.color,
            folder_id=contact_list.folder_id,
            contacts_count=contact_count,
            created_at=contact_list.created_at,
            updated_at=contact_list.updated_at,
        ))
    
    return PaginatedResponse(
        items=list_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{list_id}", response_model=ContactListResponse)
async def get_list(
    list_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactListResponse:
    """Get a specific contact list by ID.
    
    Args:
        list_id: The list ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        List details with contact count.
    """
    result = await db.execute(
        select(ContactList)
        .options(selectinload(ContactList.memberships))
        .where(
            ContactList.id == list_id,
            ContactList.user_id == current_user.id
        )
    )
    contact_list = result.scalar_one_or_none()
    
    if not contact_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact list not found",
        )
    
    contact_count = len(contact_list.memberships) if contact_list.memberships else 0
    return ContactListResponse(
        id=contact_list.id,
        user_id=contact_list.user_id,
        name=contact_list.name,
        description=contact_list.description,
        color=contact_list.color,
        folder_id=contact_list.folder_id,
        contacts_count=contact_count,
        created_at=contact_list.created_at,
        updated_at=contact_list.updated_at,
    )


@router.patch("/{list_id}", response_model=ContactListResponse)
async def update_list(
    list_id: int,
    list_data: ContactListUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactListResponse:
    """Update a contact list.
    
    Args:
        list_id: The list ID.
        list_data: Updated list information.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Updated list.
    """
    result = await db.execute(
        select(ContactList).where(
            ContactList.id == list_id,
            ContactList.user_id == current_user.id
        )
    )
    contact_list = result.scalar_one_or_none()
    
    if not contact_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact list not found",
        )
    
    # Validate folder if changing
    if list_data.folder_id is not None and list_data.folder_id != contact_list.folder_id:
        if list_data.folder_id:
            folder_result = await db.execute(
                select(ContactListFolder).where(
                    ContactListFolder.id == list_data.folder_id,
                    ContactListFolder.user_id == current_user.id
                )
            )
            folder = folder_result.scalar_one_or_none()
            if not folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Folder not found",
                )
    
    # Update list
    update_data = list_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(contact_list, key, value)
    
    contact_list.updated_at = datetime.now()
    await db.commit()
    await db.refresh(contact_list)
    
    # Get contact count
    result = await db.execute(
        select(func.count(ContactListMembership.contact_id)).where(
            ContactListMembership.contact_list_id == list_id
        )
    )
    contact_count = result.scalar() or 0
    
    logger.info(f"Updated list {list_id} for user {current_user.id}")
    return ContactListResponse(
        id=contact_list.id,
        user_id=contact_list.user_id,
        name=contact_list.name,
        description=contact_list.description,
        color=contact_list.color,
        folder_id=contact_list.folder_id,
        contacts_count=contact_count,
        created_at=contact_list.created_at,
        updated_at=contact_list.updated_at,
    )


@router.patch("/{list_id}/move", response_model=ContactListResponse)
async def move_list(
    list_id: int,
    move_data: MoveListRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactListResponse:
    """Move a list to another folder (or root).
    
    Args:
        list_id: The list ID to move.
        move_data: Move request with new folder ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Updated list.
    """
    result = await db.execute(
        select(ContactList).where(
            ContactList.id == list_id,
            ContactList.user_id == current_user.id
        )
    )
    contact_list = result.scalar_one_or_none()
    
    if not contact_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact list not found",
        )
    
    # Validate new folder
    if move_data.folder_id:
        folder_result = await db.execute(
            select(ContactListFolder).where(
                ContactListFolder.id == move_data.folder_id,
                ContactListFolder.user_id == current_user.id
            )
        )
        folder = folder_result.scalar_one_or_none()
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found",
            )
    
    contact_list.folder_id = move_data.folder_id
    contact_list.updated_at = datetime.now()
    await db.commit()
    await db.refresh(contact_list)
    
    # Get contact count
    result = await db.execute(
        select(func.count(ContactListMembership.contact_id)).where(
            ContactListMembership.contact_list_id == list_id
        )
    )
    contact_count = result.scalar() or 0
    
    logger.info(f"Moved list {list_id} to folder {move_data.folder_id} for user {current_user.id}")
    return ContactListResponse(
        id=contact_list.id,
        user_id=contact_list.user_id,
        name=contact_list.name,
        description=contact_list.description,
        color=contact_list.color,
        folder_id=contact_list.folder_id,
        contacts_count=contact_count,
        created_at=contact_list.created_at,
        updated_at=contact_list.updated_at,
    )


@router.delete("/{list_id}", response_model=SuccessResponse)
async def delete_list(
    list_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Delete a contact list.
    
    Args:
        list_id: The list ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Success response.
    """
    result = await db.execute(
        select(ContactList).where(
            ContactList.id == list_id,
            ContactList.user_id == current_user.id
        )
    )
    contact_list = result.scalar_one_or_none()
    
    if not contact_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact list not found",
        )
    
    # Delete memberships (cascade will handle this, but explicit for clarity)
    await db.execute(
        ContactListMembership.__table__.delete().where(
            ContactListMembership.contact_list_id == list_id
        )
    )
    
    # Delete list
    await db.delete(contact_list)
    await db.commit()
    
    logger.info(f"Deleted list {list_id} for user {current_user.id}")
    return SuccessResponse(message="Contact list deleted successfully")


# ============================================================================
# Membership Endpoints
# ============================================================================

@router.post("/{list_id}/contacts/{contact_id}", response_model=SuccessResponse)
async def add_contact_to_list(
    list_id: int,
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Add a contact to a list.
    
    Args:
        list_id: The list ID.
        contact_id: The contact ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Success response.
    """
    # Verify list belongs to user
    result = await db.execute(
        select(ContactList).where(
            ContactList.id == list_id,
            ContactList.user_id == current_user.id
        )
    )
    contact_list = result.scalar_one_or_none()
    if not contact_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact list not found",
        )
    
    # Verify contact belongs to user
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.user_id == current_user.id
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )
    
    # Check if membership already exists
    result = await db.execute(
        select(ContactListMembership).where(
            ContactListMembership.contact_list_id == list_id,
            ContactListMembership.contact_id == contact_id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return SuccessResponse(message="Contact already in list")
    
    # Create membership
    membership = ContactListMembership(
        contact_list_id=list_id,
        contact_id=contact_id
    )
    db.add(membership)
    await db.commit()
    
    logger.info(f"Added contact {contact_id} to list {list_id} for user {current_user.id}")
    return SuccessResponse(message="Contact added to list successfully")


@router.delete("/{list_id}/contacts/{contact_id}", response_model=SuccessResponse)
async def remove_contact_from_list(
    list_id: int,
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuccessResponse:
    """Remove a contact from a list.
    
    Args:
        list_id: The list ID.
        contact_id: The contact ID.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Success response.
    """
    # Verify list belongs to user
    result = await db.execute(
        select(ContactList).where(
            ContactList.id == list_id,
            ContactList.user_id == current_user.id
        )
    )
    contact_list = result.scalar_one_or_none()
    if not contact_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact list not found",
        )
    
    # Delete membership
    result = await db.execute(
        ContactListMembership.__table__.delete().where(
            ContactListMembership.contact_list_id == list_id,
            ContactListMembership.contact_id == contact_id
        )
    )
    await db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not in list",
        )
    
    logger.info(f"Removed contact {contact_id} from list {list_id} for user {current_user.id}")
    return SuccessResponse(message="Contact removed from list successfully")


@router.get("/{list_id}/contacts", response_model=PaginatedResponse)
async def get_list_contacts(
    list_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse:
    """Get contacts in a list.
    
    Args:
        list_id: The list ID.
        page: Page number.
        page_size: Items per page.
        db: Database session.
        current_user: Authenticated user.
    
    Returns:
        Paginated list of contacts.
    """
    # Verify list belongs to user
    result = await db.execute(
        select(ContactList).where(
            ContactList.id == list_id,
            ContactList.user_id == current_user.id
        )
    )
    contact_list = result.scalar_one_or_none()
    if not contact_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact list not found",
        )
    
    # Build query for contacts in this list
    query = (
        select(Contact)
        .join(ContactListMembership, Contact.id == ContactListMembership.contact_id)
        .where(
            ContactListMembership.contact_list_id == list_id,
            Contact.user_id == current_user.id
        )
    )
    count_query = (
        select(func.count(Contact.id))
        .join(ContactListMembership, Contact.id == ContactListMembership.contact_id)
        .where(
            ContactListMembership.contact_list_id == list_id,
            Contact.user_id == current_user.id
        )
    )
    
    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size
    
    # Get contacts
    result = await db.execute(
        query.order_by(Contact.name, Contact.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    contacts = result.scalars().all()
    
    contact_responses = [ContactResponse.model_validate(contact) for contact in contacts]
    
    return PaginatedResponse(
        items=contact_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
