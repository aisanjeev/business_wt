"""Media serving endpoints."""

import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

import aiofiles
import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.models import MediaFile, User
from app.services.blob_storage import blob_storage
from app.services.media import is_cache_valid
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/media", tags=["media"])

MEDIA_DIR = Path("media")

# Allowed subdirectories
ALLOWED_SUBDIRS = {"images", "documents", "audio", "video", "stickers"}


@router.get("/{subdir}/{filename}")
async def get_media(
    subdir: str,
    filename: str,
    db: AsyncSession = Depends(get_db),
):
    """Serve media files from Azure Blob Storage or local filesystem.
    
    Args:
        subdir: Media subdirectory (images, documents, etc.).
        filename: The filename.
        db: Database session.
    
    Returns:
        The media file.
    """
    # Validate subdirectory
    if subdir not in ALLOWED_SUBDIRS:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = MEDIA_DIR / subdir / filename
    
    # Check local cache first (if valid and exists)
    if file_path.exists() and is_cache_valid(file_path):
        # Serve from cache
        logger.debug(f"Serving media from cache: {file_path}")
        
        # Determine media type from extension
        ext = file_path.suffix.lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".mp3": "audio/mpeg",
            ".ogg": "audio/ogg",
            ".aac": "audio/aac",
            ".amr": "audio/amr",
            ".mp4": "video/mp4",
            ".3gp": "video/3gpp",
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".txt": "text/plain",
        }
        media_type = media_types.get(ext, "application/octet-stream")
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename,
        )
    
    # Cache expired or missing - try Azure Blob Storage
    if blob_storage.connection_string:
        # Search for MediaFile record matching this filename
        result = await db.execute(
            select(MediaFile).where(MediaFile.blob_name.like(f"%/{subdir}/{filename}"))
        )
        media_file = result.scalar_one_or_none()
        
        if media_file:
            # Download from Azure
            file_content = await blob_storage.download_file(media_file.blob_name)
            if file_content:
                # Optionally re-cache locally for future requests
                try:
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    async with aiofiles.open(file_path, "wb") as f:
                        await f.write(file_content)
                    logger.debug(f"Re-cached media from Azure: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to re-cache media: {e}")
                
                # Determine media type
                media_type = media_file.mime_type or "application/octet-stream"
                return Response(
                    content=file_content,
                    media_type=media_type,
                    headers={"Content-Disposition": f'inline; filename="{filename}"'},
                )
    
    # Fallback to local filesystem (even if expired, serve it)
    if file_path.exists():
        logger.debug(f"Serving expired cache (fallback): {file_path}")
    else:
        logger.warning(f"Media not found: {file_path}")
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Determine media type from extension
    ext = file_path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".aac": "audio/aac",
        ".amr": "audio/amr",
        ".mp4": "video/mp4",
        ".3gp": "video/3gpp",
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".txt": "text/plain",
    }
    
    media_type = media_types.get(ext, "application/octet-stream")
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
    )


@router.get("/proxy")
async def proxy_whatsapp_media(url: str = Query(..., description="WhatsApp media URL to proxy")):
    """Proxy WhatsApp media downloads.
    
    This endpoint proxies requests to WhatsApp media URLs,
    adding the required authentication headers.
    
    Args:
        url: The WhatsApp media URL to proxy.
    
    Returns:
        The media content.
    """
    # Only allow proxying from Facebook domains
    allowed_domains = ["lookaside.fbsbx.com", "scontent.whatsapp.net", "mmg.whatsapp.net"]
    
    from app.config import settings
    from urllib.parse import urlparse
    parsed = urlparse(url)
    
    if not any(domain in parsed.netloc for domain in allowed_domains):
        raise HTTPException(status_code=400, detail="Invalid media URL - only WhatsApp media URLs are allowed")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {settings.whatsapp_api_token}"},
                follow_redirects=True,
                timeout=60.0,
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to proxy media: HTTP {response.status_code}")
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch media")
            
            # Get content type from response
            content_type = response.headers.get("content-type", "application/octet-stream")
            
            return Response(
                content=response.content,
                media_type=content_type,
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Media download timeout")
    except Exception as e:
        logger.error(f"Error proxying media: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch media")


async def _upload_to_azure_background(
    user_id: int,
    file_path: Path,
    blob_name: str,
    mime_type: str,
    original_filename: Optional[str],
):
    """Background task to upload file to Azure Blob Storage.
    
    Args:
        user_id: User ID.
        file_path: Local file path.
        blob_name: Azure blob name.
        mime_type: MIME type.
        original_filename: Original filename.
    """
    try:
        # Read file content
        async with aiofiles.open(file_path, "rb") as f:
            content = await f.read()
        
        # Upload to Azure
        success = await blob_storage.upload_file(
            user_id=user_id,
            file_content=content,
            blob_name=blob_name,
            mime_type=mime_type,
            original_filename=original_filename,
        )
        
        if success:
            logger.info(f"Background Azure upload successful: {blob_name}")
        else:
            logger.warning(f"Background Azure upload failed: {blob_name}")
    except Exception as e:
        logger.error(f"Background Azure upload error: {e}")


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Upload a media file - optimized: store locally first, then upload to Azure in background.
    
    This approach is faster because:
    1. Local storage is immediate (no network delay)
    2. File is immediately available for sending
    3. Azure upload happens in background (non-blocking)
    
    Args:
        file: The file to upload.
        current_user: Authenticated user.
        background_tasks: FastAPI background task runner.
    
    Returns:
        The uploaded file URL.
    """
    # Determine media type and subdirectory
    content_type = file.content_type or "application/octet-stream"
    
    if content_type.startswith("image/"):
        subdir = "images"
    elif content_type.startswith("audio/"):
        subdir = "audio"
    elif content_type.startswith("video/"):
        subdir = "video"
    else:
        subdir = "documents"
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix if file.filename else ""
    unique_filename = f"{uuid.uuid4().hex[:8]}{file_ext}"
    
    try:
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # OPTIMIZED: Store locally first (fast, immediate)
        file_path = MEDIA_DIR / subdir / unique_filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        
        local_url = f"/api/media/{subdir}/{unique_filename}"
        logger.info(f"Media stored locally: {local_url} by user {current_user.id} ({file_size} bytes)")
        
        # OPTIMIZED: Upload to Azure in background (non-blocking)
        if blob_storage.connection_string:
            blob_name = f"{current_user.id}/{subdir}/{unique_filename}"
            background_tasks.add_task(
                _upload_to_azure_background,
                current_user.id,
                file_path,
                blob_name,
                content_type,
                file.filename,
            )
            logger.debug(f"Queued Azure upload in background: {blob_name}")
        
        # Return immediately (file is ready for use)
        return {
            "url": local_url,
            "filename": unique_filename,
            "content_type": content_type,
            "size": file_size,
        }
    except Exception as e:
        logger.error(f"Failed to upload media: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload media",
        )

