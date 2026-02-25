"""Storage services."""

from __future__ import annotations

from apps.object_storage_controller.services.s3_client import S3Client
from apps.object_storage_controller.services.factory import get_storage_backend

__all__ = [
    "S3Client",
    "get_storage_backend",
]
