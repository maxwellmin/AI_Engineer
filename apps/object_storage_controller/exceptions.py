"""Custom exceptions for object storage operations."""

from __future__ import annotations


class StorageError(Exception):
    """Base exception for storage operations."""

    pass


class S3ConnectionError(StorageError):
    """Exception raised when S3 connection fails."""

    pass


class S3UploadError(StorageError):
    """Exception raised when S3 upload fails."""

    pass


class S3DownloadError(StorageError):
    """Exception raised when S3 download fails."""

    pass


class S3DeleteError(StorageError):
    """Exception raised when S3 delete fails."""

    pass


class S3BucketError(StorageError):
    """Exception raised when S3 bucket operations fail."""

    pass


class FileNotFoundError(StorageError):
    """Exception raised when file is not found in storage."""

    pass


class InvalidFilePathError(StorageError):
    """Exception raised when file path is invalid."""

    pass
