"""Local filesystem storage backend implementation.

This backend provides a fallback for local development without S3/MinIO.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import BinaryIO

from django.conf import settings

from apps.object_storage_controller.backends.base import (
    PresignedUrlResult,
    StorageBackend,
    StorageResult,
)
from apps.object_storage_controller.exceptions import FileNotFoundError, StorageError

logger = logging.getLogger(__name__)


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend.

    Stores files in MEDIA_ROOT directory. Useful for development without S3.
    """

    def __init__(self) -> None:
        """Initialize local storage backend."""
        self._root = Path(settings.MEDIA_ROOT)
        self._root.mkdir(parents=True, exist_ok=True)

    def _get_absolute_path(self, file_path: str) -> Path:
        """Get absolute path for file.

        Args:
            file_path: Relative file path

        Returns:
            Absolute Path object
        """
        return self._root / file_path

    def save(self, file_path: str, content: BinaryIO, content_type: str = "") -> StorageResult:
        """Save file content to local filesystem.

        Args:
            file_path: Relative path for the file
            content: Binary file content stream
            content_type: MIME type (ignored for local storage)

        Returns:
            StorageResult with file metadata
        """
        absolute_path = self._get_absolute_path(file_path)

        # Create parent directories
        absolute_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file content
        file_size = 0
        with open(absolute_path, "wb") as f:
            for chunk in iter(lambda: content.read(8192), b""):
                f.write(chunk)
                file_size += len(chunk)

        # Get file extension
        file_type = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

        logger.info(f"Saved file locally: '{file_path}' ({file_size} bytes)")

        return StorageResult(
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            etag="",  # No ETag for local storage
            backend_type="local",
        )

    def read(self, file_path: str) -> bytes:
        """Read file content from local filesystem.

        Args:
            file_path: Relative path of the file

        Returns:
            File content as bytes
        """
        absolute_path = self._get_absolute_path(file_path)

        if not absolute_path.exists():
            raise FileNotFoundError(f"File not found: '{file_path}'")

        with open(absolute_path, "rb") as f:
            return f.read()

    def delete(self, file_path: str) -> bool:
        """Delete file from local filesystem.

        Args:
            file_path: Relative path of the file

        Returns:
            True if file was deleted, False if didn't exist
        """
        absolute_path = self._get_absolute_path(file_path)

        if not absolute_path.exists():
            return False

        absolute_path.unlink()
        logger.info(f"Deleted local file: '{file_path}'")
        return True

    def exists(self, file_path: str) -> bool:
        """Check if file exists in local filesystem.

        Args:
            file_path: Relative path of the file

        Returns:
            True if file exists, False otherwise
        """
        absolute_path = self._get_absolute_path(file_path)
        return absolute_path.exists()

    def get_presigned_url(
        self, file_path: str, expires_in: int = 3600, method: str = "GET"
    ) -> PresignedUrlResult:
        """Generate presigned URL for local storage.

        For local storage, this returns a relative URL path that needs
        to be served through Django's media serving or a dedicated download API.

        Args:
            file_path: Relative path of the file
            expires_in: URL expiry (ignored for local storage)
            method: HTTP method (ignored for local storage)

        Returns:
            PresignedUrlResult with relative URL and is_presigned=False
        """
        # For local storage, return a relative URL
        url = f"{settings.MEDIA_URL}{file_path}"

        return PresignedUrlResult(
            url=url,
            expires_in=0,  # No expiry for local URLs
            method=method,
            backend_type="local",
            is_presigned=False,
        )

    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes.

        Args:
            file_path: Relative path of the file

        Returns:
            File size in bytes
        """
        absolute_path = self._get_absolute_path(file_path)

        if not absolute_path.exists():
            raise FileNotFoundError(f"File not found: '{file_path}'")

        return absolute_path.stat().st_size

    def get_file_metadata(self, file_path: str) -> dict:
        """Get file metadata.

        Args:
            file_path: Relative path of the file

        Returns:
            Dictionary containing file metadata
        """
        absolute_path = self._get_absolute_path(file_path)

        if not absolute_path.exists():
            raise FileNotFoundError(f"File not found: '{file_path}'")

        stat = absolute_path.stat()

        return {
            "size": stat.st_size,
            "content_type": "",  # Not tracked for local storage
            "etag": "",  # Not tracked for local storage
            "last_modified": stat.st_mtime,
            "metadata": {},
        }
