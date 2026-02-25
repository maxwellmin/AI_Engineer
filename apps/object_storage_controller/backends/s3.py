"""S3 storage backend implementation."""

from __future__ import annotations

import logging
from typing import BinaryIO

from apps.object_storage_controller.backends.base import (
    PresignedUrlResult,
    StorageBackend,
    StorageResult,
)
from apps.object_storage_controller.exceptions import FileNotFoundError, StorageError
from apps.object_storage_controller.services.s3_client import S3Client

logger = logging.getLogger(__name__)


class S3StorageBackend(StorageBackend):
    """S3-compatible storage backend using boto3.

    Supports both MinIO (development) and AWS S3 (production).
    """

    @property
    def backend_type(self) -> str:
        """Return the backend type identifier."""
        return "s3"

    def __init__(self) -> None:
        """Initialize S3 storage backend."""
        self._client = S3Client()

    def save(self, file_path: str, content: BinaryIO, content_type: str = "") -> StorageResult:
        """Save file content to S3.

        Args:
            file_path: Object key/path for the file in S3
            content: Binary file content stream
            content_type: MIME type of the file

        Returns:
            StorageResult with file metadata
        """
        # Get file extension
        file_type = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

        # Upload to S3
        etag = self._client.upload_file(
            file_path=file_path,
            content=content,
            content_type=content_type or "application/octet-stream",
        )

        # Get file size from S3
        metadata = self._client.head_object(file_path)
        file_size = metadata["size"]

        logger.info(f"Saved file to S3: '{file_path}' ({file_size} bytes)")

        return StorageResult(
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            etag=etag,
            backend_type="s3",
        )

    def read(self, file_path: str) -> bytes:
        """Read file content from S3.

        Args:
            file_path: Object key/path of the file

        Returns:
            File content as bytes
        """
        return self._client.download_file(file_path)

    def delete(self, file_path: str) -> bool:
        """Delete file from S3.

        Args:
            file_path: Object key/path of the file

        Returns:
            True if file was deleted
        """
        return self._client.delete_file(file_path)

    def exists(self, file_path: str) -> bool:
        """Check if file exists in S3.

        Args:
            file_path: Object key/path of the file

        Returns:
            True if file exists, False otherwise
        """
        return self._client.object_exists(file_path)

    def get_presigned_url(
        self, file_path: str, expires_in: int = 3600, method: str = "GET"
    ) -> PresignedUrlResult:
        """Generate presigned URL for upload/download.

        Args:
            file_path: Object key/path of the file
            expires_in: URL expiry time in seconds
            method: HTTP method ('GET' for download, 'PUT' for upload)

        Returns:
            PresignedUrlResult with URL and expiry info
        """
        url = self._client.generate_presigned_url(
            file_path=file_path,
            expires_in=expires_in,
            http_method=method,
        )

        return PresignedUrlResult(
            url=url,
            expires_in=expires_in,
            method=method,
            backend_type="s3",
            is_presigned=True,
        )

    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes.

        Args:
            file_path: Object key/path of the file

        Returns:
            File size in bytes
        """
        metadata = self._client.head_object(file_path)
        return metadata["size"]

    def get_file_metadata(self, file_path: str) -> dict:
        """Get file metadata.

        Args:
            file_path: Object key/path of the file

        Returns:
            Dictionary containing file metadata
        """
        return self._client.head_object(file_path)
