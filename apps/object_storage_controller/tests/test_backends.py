"""Tests for storage backends."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from moto import mock_aws

from django.conf import settings

from apps.object_storage_controller.backends.local import LocalStorageBackend
from apps.object_storage_controller.backends.s3 import S3StorageBackend
from apps.object_storage_controller.exceptions import FileNotFoundError


class TestS3StorageBackend:
    """Test S3StorageBackend functionality."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_s3_settings, reset_storage_backend):
        """Setup test environment."""
        pass

    @mock_aws
    def test_save_file(self, sample_file_content, sample_file_path):
        """Test saving file to S3."""
        from apps.object_storage_controller.services.s3_client import S3Client

        S3Client.reset_instance()
        backend = S3StorageBackend()

        # Ensure bucket exists
        backend._client.ensure_bucket_exists()

        # Save file
        content = io.BytesIO(sample_file_content)
        result = backend.save(
            file_path=sample_file_path,
            content=content,
            content_type="application/pdf",
        )

        assert result.file_path == sample_file_path
        assert result.file_size == len(sample_file_content)
        assert result.file_type == "pdf"
        assert result.etag != ""

    @mock_aws
    def test_read_file(self, sample_file_content, sample_file_path):
        """Test reading file from S3."""
        from apps.object_storage_controller.services.s3_client import S3Client

        S3Client.reset_instance()
        backend = S3StorageBackend()
        backend._client.ensure_bucket_exists()

        # Save file first
        content = io.BytesIO(sample_file_content)
        backend.save(file_path=sample_file_path, content=content)

        # Read file
        read_content = backend.read(sample_file_path)
        assert read_content == sample_file_content

    @mock_aws
    def test_delete_file(self, sample_file_content, sample_file_path):
        """Test deleting file from S3."""
        from apps.object_storage_controller.services.s3_client import S3Client

        S3Client.reset_instance()
        backend = S3StorageBackend()
        backend._client.ensure_bucket_exists()

        # Save file first
        content = io.BytesIO(sample_file_content)
        backend.save(file_path=sample_file_path, content=content)

        # Delete file
        result = backend.delete(sample_file_path)
        assert result is True

        # Verify deleted
        assert backend.exists(sample_file_path) is False

    @mock_aws
    def test_exists_true(self, sample_file_content, sample_file_path):
        """Test file existence check returns True."""
        from apps.object_storage_controller.services.s3_client import S3Client

        S3Client.reset_instance()
        backend = S3StorageBackend()
        backend._client.ensure_bucket_exists()

        # Save file first
        content = io.BytesIO(sample_file_content)
        backend.save(file_path=sample_file_path, content=content)

        assert backend.exists(sample_file_path) is True

    @mock_aws
    def test_exists_false(self, sample_file_path):
        """Test file existence check returns False."""
        from apps.object_storage_controller.services.s3_client import S3Client

        S3Client.reset_instance()
        backend = S3StorageBackend()
        backend._client.ensure_bucket_exists()

        assert backend.exists("nonexistent/file.txt") is False

    @mock_aws
    def test_get_presigned_url(self, sample_file_path):
        """Test presigned URL generation."""
        from apps.object_storage_controller.services.s3_client import S3Client

        S3Client.reset_instance()
        backend = S3StorageBackend()
        backend._client.ensure_bucket_exists()

        result = backend.get_presigned_url(
            file_path=sample_file_path,
            expires_in=3600,
            method="GET",
        )

        assert result.url is not None
        assert result.expires_in == 3600
        assert result.method == "GET"

    @mock_aws
    def test_get_file_size(self, sample_file_content, sample_file_path):
        """Test getting file size."""
        from apps.object_storage_controller.services.s3_client import S3Client

        S3Client.reset_instance()
        backend = S3StorageBackend()
        backend._client.ensure_bucket_exists()

        # Save file first
        content = io.BytesIO(sample_file_content)
        backend.save(file_path=sample_file_path, content=content)

        size = backend.get_file_size(sample_file_path)
        assert size == len(sample_file_content)

    @mock_aws
    def test_read_nonexistent_file_raises_error(self, sample_file_path):
        """Test reading nonexistent file raises FileNotFoundError."""
        from apps.object_storage_controller.services.s3_client import S3Client

        S3Client.reset_instance()
        backend = S3StorageBackend()
        backend._client.ensure_bucket_exists()

        with pytest.raises(FileNotFoundError):
            backend.read(sample_file_path)


class TestLocalStorageBackend:
    """Test LocalStorageBackend functionality."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_local_settings, tmp_path, monkeypatch):
        """Setup test environment with temporary directory."""
        monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path))

    def test_save_file(self, sample_file_content, sample_file_path):
        """Test saving file to local filesystem."""
        backend = LocalStorageBackend()

        content = io.BytesIO(sample_file_content)
        result = backend.save(
            file_path=sample_file_path,
            content=content,
            content_type="application/pdf",
        )

        assert result.file_path == sample_file_path
        assert result.file_size == len(sample_file_content)
        assert result.file_type == "pdf"

    def test_read_file(self, sample_file_content, sample_file_path):
        """Test reading file from local filesystem."""
        backend = LocalStorageBackend()

        # Save file first
        content = io.BytesIO(sample_file_content)
        backend.save(file_path=sample_file_path, content=content)

        # Read file
        read_content = backend.read(sample_file_path)
        assert read_content == sample_file_content

    def test_delete_file(self, sample_file_content, sample_file_path):
        """Test deleting file from local filesystem."""
        backend = LocalStorageBackend()

        # Save file first
        content = io.BytesIO(sample_file_content)
        backend.save(file_path=sample_file_path, content=content)

        # Delete file
        result = backend.delete(sample_file_path)
        assert result is True

        # Verify deleted
        assert backend.exists(sample_file_path) is False

    def test_exists_true(self, sample_file_content, sample_file_path):
        """Test file existence check returns True."""
        backend = LocalStorageBackend()

        # Save file first
        content = io.BytesIO(sample_file_content)
        backend.save(file_path=sample_file_path, content=content)

        assert backend.exists(sample_file_path) is True

    def test_exists_false(self):
        """Test file existence check returns False."""
        backend = LocalStorageBackend()

        assert backend.exists("nonexistent/file.txt") is False

    def test_get_file_size(self, sample_file_content, sample_file_path):
        """Test getting file size from local filesystem."""
        backend = LocalStorageBackend()

        # Save file first
        content = io.BytesIO(sample_file_content)
        backend.save(file_path=sample_file_path, content=content)

        size = backend.get_file_size(sample_file_path)
        assert size == len(sample_file_content)

    def test_read_nonexistent_file_raises_error(self):
        """Test reading nonexistent file raises FileNotFoundError."""
        backend = LocalStorageBackend()

        with pytest.raises(FileNotFoundError):
            backend.read("nonexistent/file.txt")
