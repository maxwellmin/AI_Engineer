"""Storage backend factory for selecting the appropriate backend."""

from __future__ import annotations

import logging

from django.conf import settings

from apps.object_storage_controller.backends.base import StorageBackend
from apps.object_storage_controller.backends.local import LocalStorageBackend
from apps.object_storage_controller.backends.s3 import S3StorageBackend

logger = logging.getLogger(__name__)

# Cache for backend instances
_cached_backend: StorageBackend | None = None


def get_storage_backend() -> StorageBackend:
    """Get storage backend based on settings.

    Uses singleton pattern to reuse backend instance.

    Returns:
        StorageBackend instance (S3 or Local based on settings)
    """
    global _cached_backend

    if _cached_backend is not None:
        return _cached_backend

    if settings.USE_S3_STORAGE:
        logger.info("Using S3 storage backend")
        _cached_backend = S3StorageBackend()
    else:
        logger.info("Using local storage backend")
        _cached_backend = LocalStorageBackend()

    return _cached_backend


def reset_storage_backend() -> None:
    """Reset cached backend instance (useful for testing)."""
    global _cached_backend
    _cached_backend = None
