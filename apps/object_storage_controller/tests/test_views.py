"""Tests for storage API endpoints."""

from __future__ import annotations

import io

import pytest
from moto import mock_aws
from rest_framework import status
from rest_framework.test import APIClient

from django.conf import settings
from django.contrib.auth import get_user_model

from apps.object_storage_controller.services.s3_client import S3Client

User = get_user_model()


class TestPresignedUploadAPI:
    """Test presigned upload URL endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_s3_settings, reset_storage_backend):
        """Setup test environment."""
        S3Client.reset_instance()

    @pytest.mark.django_db
    def test_generate_presigned_upload_url(self):
        """Test generating presigned upload URL."""
        # Create user
        user = User.objects.create_user(username="testuser", password="testpass123")

        client = APIClient()
        client.force_authenticate(user=user)

        with mock_aws():
            S3Client.reset_instance()

            response = client.post(
                "/api/v1/storage/presigned-upload/",
                {
                    "file_name": "test.pdf",
                    "file_type": "application/pdf",
                    "file_size": 1024,
                },
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK
        assert "upload_url" in response.data
        assert "file_path" in response.data
        assert "expires_in" in response.data

    @pytest.mark.django_db
    def test_invalid_file_extension(self):
        """Test that invalid file extension is rejected."""
        user = User.objects.create_user(username="testuser", password="testpass123")

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            "/api/v1/storage/presigned-upload/",
            {
                "file_name": "test.exe",
                "file_type": "application/octet-stream",
                "file_size": 1024,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_file_size_too_large(self):
        """Test that oversized file is rejected."""
        user = User.objects.create_user(username="testuser", password="testpass123")

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(
            "/api/v1/storage/presigned-upload/",
            {
                "file_name": "large.pdf",
                "file_type": "application/pdf",
                "file_size": 200 * 1024 * 1024,  # 200MB
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_unauthenticated_access(self):
        """Test that unauthenticated access is rejected."""
        client = APIClient()

        response = client.post(
            "/api/v1/storage/presigned-upload/",
            {
                "file_name": "test.pdf",
                "file_type": "application/pdf",
                "file_size": 1024,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPresignedDownloadAPI:
    """Test presigned download URL endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_s3_settings, reset_storage_backend):
        """Setup test environment."""
        S3Client.reset_instance()

    @pytest.mark.django_db
    def test_generate_presigned_download_url(self, sample_file_content):
        """Test generating presigned download URL."""
        user = User.objects.create_user(username="testuser", password="testpass123")

        client = APIClient()
        client.force_authenticate(user=user)

        with mock_aws():
            S3Client.reset_instance()
            s3_client = S3Client()
            s3_client.ensure_bucket_exists()

            # Upload file first
            file_path = "documents/2026/02/25/test.pdf"
            content = io.BytesIO(sample_file_content)
            s3_client.upload_file(
                file_path=file_path,
                content=content,
                content_type="application/pdf",
            )

            response = client.get(
                f"/api/v1/storage/presigned-download/?file_path={file_path}"
            )

        assert response.status_code == status.HTTP_200_OK
        assert "download_url" in response.data
        assert "expires_in" in response.data

    @pytest.mark.django_db
    def test_file_not_found(self):
        """Test that nonexistent file returns 404."""
        user = User.objects.create_user(username="testuser", password="testpass123")

        client = APIClient()
        client.force_authenticate(user=user)

        with mock_aws():
            S3Client.reset_instance()
            S3Client().ensure_bucket_exists()

            response = client.get(
                "/api/v1/storage/presigned-download/?file_path=nonexistent.pdf"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUploadConfirmAPI:
    """Test upload confirmation endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_s3_settings, reset_storage_backend):
        """Setup test environment."""
        S3Client.reset_instance()

    @pytest.mark.django_db
    def test_confirm_upload(self, sample_file_content):
        """Test confirming uploaded file."""
        user = User.objects.create_user(username="testuser", password="testpass123")

        client = APIClient()
        client.force_authenticate(user=user)

        with mock_aws():
            S3Client.reset_instance()
            s3_client = S3Client()
            s3_client.ensure_bucket_exists()

            # Upload file first
            file_path = "documents/2026/02/25/confirmed.pdf"
            content = io.BytesIO(sample_file_content)
            s3_client.upload_file(
                file_path=file_path,
                content=content,
                content_type="application/pdf",
            )

            response = client.post(
                "/api/v1/storage/confirm-upload/",
                {
                    "file_path": file_path,
                    "file_name": "confirmed.pdf",
                    "file_size": len(sample_file_content),
                    "file_type": "pdf",
                    "title": "Test Document",
                    "description": "Test description",
                },
                format="json",
            )

        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response.data
        assert response.data["name"] == "confirmed.pdf"
        assert response.data["status"] == "uploaded"

    @pytest.mark.django_db
    def test_confirm_nonexistent_file(self):
        """Test that confirming nonexistent file returns error."""
        user = User.objects.create_user(username="testuser", password="testpass123")

        client = APIClient()
        client.force_authenticate(user=user)

        with mock_aws():
            S3Client.reset_instance()
            S3Client().ensure_bucket_exists()

            response = client.post(
                "/api/v1/storage/confirm-upload/",
                {
                    "file_path": "nonexistent.pdf",
                    "file_name": "nonexistent.pdf",
                    "file_size": 1024,
                    "file_type": "pdf",
                },
                format="json",
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
