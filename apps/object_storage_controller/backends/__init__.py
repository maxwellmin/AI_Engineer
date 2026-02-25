"""Storage backend modules."""

from __future__ import annotations

from apps.object_storage_controller.backends.base import StorageBackend, StorageResult, PresignedUrlResult
from apps.object_storage_controller.backends.s3 import S3StorageBackend
from apps.object_storage_controller.backends.local import LocalStorageBackend

__all__ = [
    "StorageBackend",
    "StorageResult",
    "PresignedUrlResult",
    "S3StorageBackend",
    "LocalStorageBackend",
]
