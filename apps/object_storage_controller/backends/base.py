"""Abstract storage backend interface for object storage operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO


@dataclass(frozen=True)
class StorageResult:
    """Immutable result of file storage operation."""

    file_path: str  # Object key in storage
    file_size: int  # File size in bytes
    file_type: str  # File extension (e.g., 'pdf', 'docx')
    etag: str = ""  # S3 ETag for verification (optional)
    backend_type: str = "s3"  # Storage backend type: "s3" or "local"


@dataclass(frozen=True)
class PresignedUrlResult:
    """Immutable result of presigned URL generation."""

    url: str  # Presigned URL or relative path
    expires_in: int  # Expiry time in seconds (0 for local)
    method: str  # HTTP method ('GET' or 'PUT')
    backend_type: str = "s3"  # Storage backend type: "s3" or "local"
    is_presigned: bool = True  # True for S3 presigned URL, False for local relative path


class StorageBackend(ABC):
    """Abstract base class for storage backends.

    This interface defines the contract for all storage backends,
    allowing seamless switching between local filesystem and S3-compatible storage.
    """

    @property
    @abstractmethod
    def backend_type(self) -> str:
        """Return the backend type identifier.

        Returns:
            's3' for S3 storage backend, 'local' for local filesystem backend.
        """
        pass

    @abstractmethod
    def save(self, file_path: str, content: BinaryIO, content_type: str = "") -> StorageResult:
        """Save file content to storage.

        Args:
            file_path: Object key/path for the file in storage
            content: Binary file content stream
            content_type: MIME type of the file

        Returns:
            StorageResult with file metadata

        Raises:
            StorageError: If save operation fails
        """
        pass

    @abstractmethod
    def read(self, file_path: str) -> bytes:
        """Read file content from storage.

        Args:
            file_path: Object key/path of the file

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If file does not exist
            StorageError: If read operation fails
        """
        pass

    @abstractmethod
    def delete(self, file_path: str) -> bool:
        """Delete file from storage.

        Args:
            file_path: Object key/path of the file

        Returns:
            True if file was deleted, False if file didn't exist

        Raises:
            StorageError: If delete operation fails
        """
        pass

    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """Check if file exists in storage.

        Args:
            file_path: Object key/path of the file

        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
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

        Raises:
            StorageError: If URL generation fails
        """
        pass

    @abstractmethod
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes.

        Args:
            file_path: Object key/path of the file

        Returns:
            File size in bytes

        Raises:
            FileNotFoundError: If file does not exist
            StorageError: If operation fails
        """
        pass

    @abstractmethod
    def get_file_metadata(self, file_path: str) -> dict:
        """Get file metadata.

        Args:
            file_path: Object key/path of the file

        Returns:
            Dictionary containing file metadata (size, content_type, etag, etc.)

        Raises:
            FileNotFoundError: If file does not exist
            StorageError: If operation fails
        """
        pass
