"""MinIO storage service for file uploads."""

import logging
from io import BytesIO
from typing import BinaryIO, Optional
from urllib.parse import quote

from minio import Minio
from minio.error import S3Error

from app.core.config import minio_settings

logger = logging.getLogger(__name__)


class MinIOService:
    """Service for managing file uploads to MinIO."""
    
    def __init__(self):
        """Initialize MinIO client."""
        self.client = Minio(
            endpoint=minio_settings.ENDPOINT,
            access_key=minio_settings.ACCESS_KEY,
            secret_key=minio_settings.SECRET_KEY,
            secure=minio_settings.SECURE,
        )
        self.bucket_name = minio_settings.BUCKET_NAME
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if not."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")
                
                # Set public read policy for images bucket
                if self.bucket_name == "images":
                    policy = {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"AWS": "*"},
                                "Action": ["s3:GetObject"],
                                "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
                            }
                        ]
                    }
                    import json
                    self.client.set_bucket_policy(self.bucket_name, json.dumps(policy))
                    logger.info(f"Set public read policy for bucket: {self.bucket_name}")
            else:
                logger.debug(f"MinIO bucket exists: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            raise
    
    def upload_file(
        self,
        file_data: BinaryIO | bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Upload file to MinIO.
        
        Args:
            file_data: File data as BytesIO or bytes
            object_name: Path/name of object in bucket (e.g., "avatars/user_123.jpg")
            content_type: MIME type of file
            metadata: Optional metadata dict
        
        Returns:
            Public URL of uploaded file
        """
        try:
            # Convert bytes to BytesIO if needed
            if isinstance(file_data, bytes):
                file_data = BytesIO(file_data)
            
            # Get file size
            file_data.seek(0, 2)  # Seek to end
            file_size = file_data.tell()
            file_data.seek(0)  # Seek back to start
            
            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=content_type,
                metadata=metadata or {},
            )
            
            logger.info(f"Uploaded file to MinIO: {object_name}")
            
            # Return public URL
            return self.get_public_url(object_name)
        
        except S3Error as e:
            logger.error(f"Error uploading file to MinIO: {e}")
            raise
    
    def get_public_url(self, object_name: str) -> str:
        """
        Get public URL for object.
        
        Args:
            object_name: Object name/path in bucket
        
        Returns:
            Public URL
        """
        # URL-encode the object name for proper URL formatting
        encoded_name = quote(object_name, safe='/')
        
        if minio_settings.SECURE:
            protocol = "https"
        else:
            protocol = "http"
        
        return f"{protocol}://{minio_settings.ENDPOINT}/{self.bucket_name}/{encoded_name}"
    
    def get_presigned_url(
        self,
        object_name: str,
        expires: int = 3600,
    ) -> str:
        """
        Get presigned URL for temporary access.
        
        Args:
            object_name: Object name/path in bucket
            expires: URL expiration in seconds (default: 1 hour)
        
        Returns:
            Presigned URL
        """
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=expires),
            )
            return url
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise
    
    def delete_file(self, object_name: str) -> bool:
        """
        Delete file from MinIO.
        
        Args:
            object_name: Object name/path to delete
        
        Returns:
            True if successful
        """
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
            )
            logger.info(f"Deleted file from MinIO: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"Error deleting file from MinIO: {e}")
            return False
    
    def list_files(self, prefix: str = "") -> list[str]:
        """
        List files in bucket with optional prefix.
        
        Args:
            prefix: Optional prefix to filter objects
        
        Returns:
            List of object names
        """
        try:
            objects = self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=True,
            )
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"Error listing files from MinIO: {e}")
            return []
    
    def file_exists(self, object_name: str) -> bool:
        """
        Check if file exists in bucket.
        
        Args:
            object_name: Object name to check
        
        Returns:
            True if exists
        """
        try:
            self.client.stat_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
            )
            return True
        except S3Error:
            return False


# Singleton instance
_minio_service: Optional[MinIOService] = None


def get_minio_service() -> MinIOService:
    """Get or create MinIO service singleton."""
    global _minio_service
    if _minio_service is None:
        _minio_service = MinIOService()
    return _minio_service
