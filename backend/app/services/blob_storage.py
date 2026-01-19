"""Azure Blob Storage service for media file operations."""

import io
from typing import Optional

from azure.core.exceptions import AzureError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db_context
from app.models import MediaFile
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BlobStorageService:
    """Service for Azure Blob Storage operations."""
    
    def __init__(self):
        """Initialize blob storage service."""
        self.connection_string = settings.azure_storage_connection_string
        self.container_name = settings.azure_storage_container_name
        self._blob_service_client: Optional[BlobServiceClient] = None
    
    def _get_blob_service_client(self) -> BlobServiceClient:
        """Get or create blob service client."""
        if not self.connection_string:
            raise ValueError("Azure storage connection string not configured")
        
        if self._blob_service_client is None:
            self._blob_service_client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
        return self._blob_service_client
    
    def _get_container_client(self):
        """Get container client, creating container if it doesn't exist."""
        blob_service_client = self._get_blob_service_client()
        container_client = blob_service_client.get_container_client(self.container_name)
        
        # Create container if it doesn't exist
        try:
            container_client.create_container()
            logger.info(f"Created Azure container: {self.container_name}")
        except AzureError as e:
            # Container might already exist, which is fine
            if "ContainerAlreadyExists" not in str(e):
                logger.warning(f"Error creating container (may already exist): {e}")
        
        return container_client
    
    async def upload_file(
        self,
        user_id: int,
        file_content: bytes,
        blob_name: str,
        mime_type: str,
        original_filename: Optional[str] = None,
    ) -> bool:
        """Upload a file to Azure Blob Storage.
        
        Args:
            user_id: User ID who owns the file.
            file_content: File content as bytes.
            blob_name: Blob name/path in Azure (e.g., "123/images/abc.jpg").
            mime_type: MIME type of the file.
            original_filename: Original filename if available.
        
        Returns:
            True if successful, False otherwise.
        """
        if not self.connection_string:
            logger.warning("Azure storage not configured, skipping upload")
            return False
        
        try:
            container_client = self._get_container_client()
            blob_client = container_client.get_blob_client(blob_name)
            
            # Upload file with content settings
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                content_settings=ContentSettings(content_type=mime_type),
            )
            
            # Create MediaFile record in database
            async with get_db_context() as db:
                media_file = MediaFile(
                    user_id=user_id,
                    blob_name=blob_name,
                    file_size_bytes=len(file_content),
                    mime_type=mime_type,
                    original_filename=original_filename,
                )
                db.add(media_file)
                await db.commit()
            
            logger.info(f"Uploaded file to Azure: {blob_name} ({len(file_content)} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload file to Azure: {e}")
            return False
    
    async def download_file(self, blob_name: str) -> Optional[bytes]:
        """Download a file from Azure Blob Storage.
        
        Args:
            blob_name: Blob name/path in Azure.
        
        Returns:
            File content as bytes, or None if not found.
        """
        if not self.connection_string:
            return None
        
        try:
            container_client = self._get_container_client()
            blob_client = container_client.get_blob_client(blob_name)
            
            # Download file
            download_stream = blob_client.download_blob()
            file_content = download_stream.readall()
            
            return file_content
            
        except ResourceNotFoundError:
            logger.warning(f"Blob not found in Azure: {blob_name}")
            return None
        except Exception as e:
            logger.error(f"Failed to download file from Azure: {e}")
            return None
    
    async def delete_file(self, blob_name: str) -> bool:
        """Delete a file from Azure Blob Storage.
        
        Args:
            blob_name: Blob name/path in Azure.
        
        Returns:
            True if deleted, False otherwise.
        """
        if not self.connection_string:
            return False
        
        try:
            container_client = self._get_container_client()
            blob_client = container_client.get_blob_client(blob_name)
            
            # Delete blob
            blob_client.delete_blob()
            
            # Remove MediaFile record from database
            async with get_db_context() as db:
                result = await db.execute(
                    select(MediaFile).where(MediaFile.blob_name == blob_name)
                )
                media_file = result.scalar_one_or_none()
                if media_file:
                    await db.delete(media_file)
                    await db.commit()
            
            logger.info(f"Deleted file from Azure: {blob_name}")
            return True
            
        except ResourceNotFoundError:
            logger.warning(f"Blob not found in Azure: {blob_name}")
            # Still try to remove from database
            async with get_db_context() as db:
                result = await db.execute(
                    select(MediaFile).where(MediaFile.blob_name == blob_name)
                )
                media_file = result.scalar_one_or_none()
                if media_file:
                    await db.delete(media_file)
                    await db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete file from Azure: {e}")
            return False
    
    async def get_user_storage_usage(self, user_id: int, db: AsyncSession) -> int:
        """Get total storage usage for a user in bytes.
        
        Args:
            user_id: User ID.
            db: Database session.
        
        Returns:
            Total storage used in bytes.
        """
        result = await db.execute(
            select(func.sum(MediaFile.file_size_bytes))
            .where(MediaFile.user_id == user_id)
        )
        total_bytes = result.scalar() or 0
        return int(total_bytes)
    
    def format_storage_size(self, bytes: int) -> str:
        """Format storage size in human-readable format.
        
        Args:
            bytes: Size in bytes.
        
        Returns:
            Formatted string (e.g., "1.5 MB", "500 KB").
        """
        if bytes < 1024:
            return f"{bytes} B"
        elif bytes < 1024 * 1024:
            return f"{bytes / 1024:.2f} KB"
        elif bytes < 1024 * 1024 * 1024:
            return f"{bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{bytes / (1024 * 1024 * 1024):.2f} GB"


# Global instance
blob_storage = BlobStorageService()
