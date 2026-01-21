"""Media handling service for downloading and storing WhatsApp media."""

import os
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple

import aiofiles
import httpx

from app.config import settings
from app.services.blob_storage import blob_storage
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Media storage directory
MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(exist_ok=True)

# Cache TTL in hours (default 24 hours)
MEDIA_CACHE_TTL_HOURS = 24
MEDIA_CACHE_TTL_SECONDS = MEDIA_CACHE_TTL_HOURS * 3600

# Subdirectories for different media types
for subdir in ["images", "documents", "audio", "video", "stickers"]:
    (MEDIA_DIR / subdir).mkdir(exist_ok=True)


def get_media_subdir(mime_type: str) -> str:
    """Get the appropriate subdirectory based on mime type."""
    if mime_type.startswith("image/"):
        return "images"
    elif mime_type.startswith("audio/"):
        return "audio"
    elif mime_type.startswith("video/"):
        return "video"
    elif mime_type.startswith("application/"):
        return "documents"
    else:
        return "documents"


def get_extension_from_mime(mime_type: str) -> str:
    """Get file extension from mime type."""
    mime_to_ext = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "audio/mpeg": ".mp3",
        "audio/ogg": ".ogg",
        "audio/aac": ".aac",
        "audio/amr": ".amr",
        "video/mp4": ".mp4",
        "video/3gpp": ".3gp",
        "application/pdf": ".pdf",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.ms-excel": ".xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "text/plain": ".txt",
    }
    return mime_to_ext.get(mime_type, "")


def is_cache_valid(file_path: Path) -> bool:
    """Check if a cached file is still valid (less than cache TTL old).
    
    Args:
        file_path: Path to the cached file.
    
    Returns:
        True if file exists and is less than cache TTL old, False otherwise.
    """
    if not file_path.exists():
        return False
    
    try:
        # Get file modification time
        file_mtime = os.path.getmtime(file_path)
        current_time = time.time()
        age_seconds = current_time - file_mtime
        
        # Check if file is within cache TTL
        is_valid = age_seconds < MEDIA_CACHE_TTL_SECONDS
        
        if not is_valid:
            logger.debug(f"Cache expired for {file_path}: {age_seconds / 3600:.2f} hours old")
        
        return is_valid
    except OSError as e:
        logger.warning(f"Error checking cache validity for {file_path}: {e}")
        return False


async def download_and_store_media(
    whatsapp_media_url: str,
    mime_type: str,
    api_token: str,
    user_id: Optional[int] = None,
    original_filename: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Download media from WhatsApp and store in Azure Blob Storage (or locally if Azure not configured).
    
    Args:
        whatsapp_media_url: The temporary WhatsApp media URL.
        mime_type: The MIME type of the media.
        api_token: WhatsApp API token for authentication.
        user_id: User ID who owns the media (required for Azure storage).
        original_filename: Optional original filename.
    
    Returns:
        Tuple of (local_url, stored_filename) or (None, None) on failure.
    """
    try:
        # Generate unique filename
        subdir = get_media_subdir(mime_type)
        ext = get_extension_from_mime(mime_type)
        
        if original_filename:
            # Use original filename with unique prefix
            unique_id = uuid.uuid4().hex[:8]
            filename = f"{unique_id}_{original_filename}"
        else:
            # Generate completely unique filename
            filename = f"{uuid.uuid4().hex}{ext}"
        
        # Download from WhatsApp
        async with httpx.AsyncClient() as client:
            response = await client.get(
                whatsapp_media_url,
                headers={"Authorization": f"Bearer {api_token}"},
                follow_redirects=True,
                timeout=60.0,
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to download media: HTTP {response.status_code}")
                return None, None
            
            file_content = response.content
        
        # OPTIMIZED: Store locally first (fast, immediate)
        file_path = MEDIA_DIR / subdir / filename
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)
        
        # Return the local URL path (relative to media endpoint)
        local_url = f"/api/media/{subdir}/{filename}"
        logger.info(f"Media saved locally: {local_url}")
        
        # OPTIMIZED: Upload to Azure in background (non-blocking)
        if user_id and settings.azure_storage_connection_string:
            blob_name = f"{user_id}/{subdir}/{filename}"
            # Use asyncio.create_task to run Azure upload in background
            import asyncio
            asyncio.create_task(
                _upload_to_azure_async(
                    user_id=user_id,
                    file_path=file_path,
                    blob_name=blob_name,
                    mime_type=mime_type,
                    original_filename=original_filename,
                )
            )
            logger.debug(f"Queued Azure upload in background: {blob_name}")
        
        return local_url, filename
        
    except Exception as e:
        logger.error(f"Failed to download and store media: {e}")
        return None, None


async def _upload_to_azure_async(
    user_id: int,
    file_path: Path,
    blob_name: str,
    mime_type: str,
    original_filename: Optional[str],
):
    """Background async task to upload file to Azure Blob Storage.
    
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


async def cleanup_expired_cache() -> dict:
    """Clean up expired cache files (older than cache TTL).
    
    Returns:
        Dictionary with cleanup statistics.
    """
    deleted_count = 0
    total_size_freed = 0
    errors = []
    
    try:
        # Scan all subdirectories
        for subdir in ["images", "documents", "audio", "video", "stickers"]:
            subdir_path = MEDIA_DIR / subdir
            
            if not subdir_path.exists():
                continue
            
            # Iterate through all files in subdirectory
            for file_path in subdir_path.iterdir():
                if not file_path.is_file():
                    continue
                
                try:
                    # Check if cache is expired
                    if not is_cache_valid(file_path):
                        # Get file size before deletion
                        file_size = file_path.stat().st_size
                        
                        # Delete expired file
                        file_path.unlink()
                        deleted_count += 1
                        total_size_freed += file_size
                        logger.debug(f"Deleted expired cache file: {file_path}")
                except OSError as e:
                    error_msg = f"Error deleting {file_path}: {e}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
        
        logger.info(
            f"Cache cleanup completed: {deleted_count} files deleted, "
            f"{total_size_freed / (1024 * 1024):.2f} MB freed"
        )
        
        return {
            "deleted_count": deleted_count,
            "total_size_freed_bytes": total_size_freed,
            "errors": errors,
        }
    except Exception as e:
        logger.error(f"Cache cleanup error: {e}")
        return {
            "deleted_count": deleted_count,
            "total_size_freed_bytes": total_size_freed,
            "errors": errors + [str(e)],
        }


async def delete_media(media_url: str, user_id: Optional[int] = None) -> bool:
    """Delete a media file from Azure Blob Storage and local cache.
    
    This function deletes the media from both Azure (if configured) and local cache.
    
    Args:
        media_url: The media URL (e.g., /api/media/images/abc.jpg).
        user_id: User ID who owns the media (required for Azure storage).
    
    Returns:
        True if deleted from at least one location, False otherwise.
    """
    try:
        # Extract path from URL
        if not media_url.startswith("/api/media/"):
            return False
        
        relative_path = media_url.replace("/api/media/", "")
        parts = relative_path.split("/", 1)
        
        if len(parts) < 2:
            return False
        
        subdir = parts[0]
        filename = parts[1]
        
        deleted_from_azure = False
        deleted_from_cache = False
        
        # Delete from Azure Blob Storage if configured
        if user_id and settings.azure_storage_connection_string:
            blob_name = f"{user_id}/{subdir}/{filename}"
            try:
                deleted_from_azure = await blob_storage.delete_file(blob_name)
                if deleted_from_azure:
                    logger.info(f"Media deleted from Azure: {blob_name}")
            except Exception as e:
                logger.warning(f"Failed to delete from Azure: {e}")
        
        # Delete from local cache
        file_path = MEDIA_DIR / relative_path
        if file_path.exists():
            try:
                file_path.unlink()
                deleted_from_cache = True
                logger.info(f"Media deleted from local cache: {media_url}")
            except OSError as e:
                logger.warning(f"Failed to delete from cache: {e}")
        
        # Return True if deleted from at least one location
        return deleted_from_azure or deleted_from_cache
        
    except Exception as e:
        logger.error(f"Failed to delete media: {e}")
        return False

