"""Django app configuration for object_storage_controller."""

from __future__ import annotations

from django.apps import AppConfig


class ObjectStorageControllerConfig(AppConfig):
    """Configuration for object_storage_controller app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.object_storage_controller"
    verbose_name = "Object Storage Controller"

    def ready(self) -> None:
        """Initialize app when Django starts."""
        # Import and initialize S3 client to verify connection
        try:
            from django.conf import settings

            if settings.USE_S3_STORAGE:
                from apps.object_storage_controller.services.s3_client import S3Client

                # Initialize singleton to verify connection
                S3Client()
        except Exception:
            # Silently fail during migrations or initial setup
            pass
