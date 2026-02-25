"""Tests for storage factory."""

from __future__ import annotations

import pytest
from moto import mock_aws

from django.conf import settings

from apps.object_storage_controller.backends.local import LocalStorageBackend
from apps.object_storage_controller.backends.s3 import S3StorageBackend
from apps.object_storage_controller.services.factory import (
    get_storage_backend,
    reset_storage_backend,
)


class TestStorageFactory:
    """Test storage backend factory."""

    def test_get_local_storage_backend(self, mock_local_settings):
        """Test getting local storage backend."""
        from apps.object_storage_controller.services.factory import (
            get_storage_backend,
            reset_storage_backend as _reset,
        )
        from apps.object_storage_controller.services.s3_client import S3Client

        _reset()
        S3Client.reset_instance()

        backend = get_storage_backend()

        assert isinstance(backend, LocalStorageBackend)

    @mock_aws
    def test_get_s3_storage_backend(self, mock_s3_settings):
        """Test getting S3 storage backend."""
        from apps.object_storage_controller.services.factory import (
            get_storage_backend,
            reset_storage_backend as _reset,
        )
        from apps.object_storage_controller.services.s3_client import S3Client

        S3Client.reset_instance()
        _reset()

        backend = get_storage_backend()

        assert isinstance(backend, S3StorageBackend)

    def test_caching(self, mock_local_settings):
        """Test that backend is cached."""
        from apps.object_storage_controller.services.factory import (
            get_storage_backend,
            reset_storage_backend as _reset,
        )
        from apps.object_storage_controller.services.s3_client import S3Client

        _reset()
        S3Client.reset_instance()

        backend1 = get_storage_backend()
        backend2 = get_storage_backend()

        assert backend1 is backend2

    def test_reset_clears_cache(self, mock_local_settings):
        """Test that reset clears cached backend."""
        from apps.object_storage_controller.services.factory import (
            get_storage_backend,
            reset_storage_backend as _reset,
        )
        from apps.object_storage_controller.services.s3_client import S3Client

        _reset()
        S3Client.reset_instance()

        backend1 = get_storage_backend()
        _reset()
        backend2 = get_storage_backend()

        # They should be different instances after reset
        assert backend1 is not backend2
