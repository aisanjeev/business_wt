"""Media handling service for downloading and storing WhatsApp media."""

import os
import uuid
from pathlib import Path
from typing import Optional, Tuple

import aiofiles
import httpx

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Media storage directory
MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(exist_ok=True)

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


async def download_and_store_media(
    whatsapp_media_url: str,
    mime_type: str,
    api_token: str,
    original_filename: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Download media from WhatsApp and store locally.
    
    Args:
        whatsapp_media_url: The temporary WhatsApp media URL.
        mime_type: The MIME type of the media.
        api_token: WhatsApp API token for authentication.
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
        
        file_path = MEDIA_DIR / subdir / filename
        
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
            
            # Save to file
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(response.content)
        
        # Return the local URL path (relative to media endpoint)
        local_url = f"/api/media/{subdir}/{filename}"
        
        logger.info(f"Media saved: {local_url}")
        return local_url, filename
        
    except Exception as e:
        logger.error(f"Failed to download and store media: {e}")
        return None, None


async def delete_media(media_url: str) -> bool:
    """Delete a media file.
    
    Args:
        media_url: The local media URL (e.g., /api/media/images/abc.jpg).
    
    Returns:
        True if deleted, False otherwise.
    """
    try:
        # Extract path from URL
        if media_url.startswith("/api/media/"):
            relative_path = media_url.replace("/api/media/", "")
            file_path = MEDIA_DIR / relative_path
            
            if file_path.exists():
                os.remove(file_path)
                logger.info(f"Media deleted: {media_url}")
                return True
        
        return False
    except Exception as e:
        logger.error(f"Failed to delete media: {e}")
        return False

