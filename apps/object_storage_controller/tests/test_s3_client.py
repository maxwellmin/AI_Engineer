"""Tests for S3 client service."""

from __future__ import annotations

import io

import pytest
from moto import mock_aws

from django.conf import settings

from apps.object_storage_controller.exceptions import FileNotFoundError, S3UploadError
from apps.object_storage_controller.services.s3_client import S3Client


class TestS3Client:
    """Test S3Client functionality."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_s3_settings, reset_storage_backend):
        """Setup test environment."""
        pass

    @mock_aws
    def test_singleton_pattern(self):
        """Test that S3Client uses singleton pattern."""
        client1 = S3Client()
        client2 = S3Client()

        assert client1 is client2

    @mock_aws
    def test_ensure_bucket_exists_creates_bucket(self):
        """Test bucket creation."""
        import boto3

        # Reset singleton to pick up test settings
        S3Client.reset_instance()
        client = S3Client()

        # Create bucket
        created = client.ensure_bucket_exists()
        assert created is True

        # Verify bucket exists
        s3 = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
        )
        response = s3.list_buckets()
        assert "test-bucket" in [b["Name"] for b in response["Buckets"]]

    @mock_aws
    def test_ensure_bucket_exists_already_exists(self):
        """Test that bucket exists check works."""
        S3Client.reset_instance()
        client = S3Client()

        # Create bucket first time
        client.ensure_bucket_exists()

        # Try again - should return False
        created = client.ensure_bucket_exists()
        assert created is False

    @mock_aws
    def test_upload_and_download_file(self, sample_file_content):
        """Test file upload and download."""
        S3Client.reset_instance()
        client = S3Client()
        client.ensure_bucket_exists()

        # Upload file
        file_path = "test/file.txt"
        content = io.BytesIO(sample_file_content)

        etag = client.upload_file(
            file_path=file_path,
            content=content,
            content_type="text/plain",
        )

        assert etag is not None

        # Download file
        downloaded = client.download_file(file_path)
        assert downloaded == sample_file_content

    @mock_aws
    def test_object_exists(self, sample_file_content):
        """Test object existence check."""
        S3Client.reset_instance()
        client = S3Client()
        client.ensure_bucket_exists()

        file_path = "test/exists.txt"

        # Should not exist initially
        assert client.object_exists(file_path) is False

        # Upload file
        content = io.BytesIO(sample_file_content)
        client.upload_file(file_path=file_path, content=content)

        # Should exist now
        assert client.object_exists(file_path) is True

    @mock_aws
    def test_delete_file(self, sample_file_content):
        """Test file deletion."""
        S3Client.reset_instance()
        client = S3Client()
        client.ensure_bucket_exists()

        file_path = "test/delete.txt"

        # Upload file
        content = io.BytesIO(sample_file_content)
        client.upload_file(file_path=file_path, content=content)

        # Verify exists
        assert client.object_exists(file_path) is True

        # Delete file
        result = client.delete_file(file_path)
        assert result is True

        # Verify deleted
        assert client.object_exists(file_path) is False

    @mock_aws
    def test_download_nonexistent_file_raises_error(self):
        """Test that downloading nonexistent file raises FileNotFoundError."""
        S3Client.reset_instance()
        client = S3Client()
        client.ensure_bucket_exists()

        with pytest.raises(FileNotFoundError):
            client.download_file("nonexistent/file.txt")

    @mock_aws
    def test_head_object(self, sample_file_content):
        """Test head object metadata retrieval."""
        S3Client.reset_instance()
        client = S3Client()
        client.ensure_bucket_exists()

        file_path = "test/metadata.txt"
        content = io.BytesIO(sample_file_content)

        client.upload_file(
            file_path=file_path,
            content=content,
            content_type="text/plain",
        )

        metadata = client.head_object(file_path)

        assert metadata["size"] == len(sample_file_content)
        assert metadata["content_type"] == "text/plain"
        assert metadata["etag"] != ""

    @mock_aws
    def test_generate_presigned_url_get(self):
        """Test presigned URL generation for download."""
        S3Client.reset_instance()
        client = S3Client()
        client.ensure_bucket_exists()

        url = client.generate_presigned_url(
            file_path="test/download.txt",
            expires_in=3600,
            http_method="GET",
        )

        assert url is not None
        assert "test/download.txt" in url
        assert "X-Amz" in url or "Signature" in url

    @mock_aws
    def test_generate_presigned_url_put(self):
        """Test presigned URL generation for upload."""
        S3Client.reset_instance()
        client = S3Client()
        client.ensure_bucket_exists()

        url = client.generate_presigned_url(
            file_path="test/upload.txt",
            expires_in=3600,
            http_method="PUT",
        )

        assert url is not None
        assert "test/upload.txt" in url

    @mock_aws
    def test_list_objects(self, sample_file_content):
        """Test listing objects in bucket."""
        S3Client.reset_instance()
        client = S3Client()
        client.ensure_bucket_exists()

        # Upload multiple files
        for i in range(3):
            content = io.BytesIO(sample_file_content)
            client.upload_file(file_path=f"test/file{i}.txt", content=content)

        # List objects
        objects = client.list_objects(prefix="test/")

        assert len(objects) == 3
        assert all("test/file" in obj["key"] for obj in objects)
