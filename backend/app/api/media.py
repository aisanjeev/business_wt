"""Media serving endpoints."""

from pathlib import Path
from urllib.parse import unquote

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/media", tags=["media"])

MEDIA_DIR = Path("media")

# Allowed subdirectories
ALLOWED_SUBDIRS = {"images", "documents", "audio", "video", "stickers"}


@router.get("/{subdir}/{filename}")
async def get_media(subdir: str, filename: str):
    """Serve media files.
    
    Args:
        subdir: Media subdirectory (images, documents, etc.).
        filename: The filename.
    
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
    
    if not file_path.exists():
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

