"""Pytest fixtures for object_storage_controller tests."""

from __future__ import annotations

import pytest
from moto import mock_aws

from django.conf import settings


@pytest.fixture
def mock_s3_settings(monkeypatch):
    """Configure settings for S3 storage."""
    monkeypatch.setattr(settings, "USE_S3_STORAGE", True)
    monkeypatch.setattr(settings, "S3_ENDPOINT_URL", "https://s3.amazonaws.com")
    monkeypatch.setattr(settings, "S3_ACCESS_KEY_ID", "testing")
    monkeypatch.setattr(settings, "S3_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setattr(settings, "S3_REGION_NAME", "us-east-1")
    monkeypatch.setattr(settings, "S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setattr(settings, "S3_USE_SSL", True)


@pytest.fixture
def mock_local_settings(monkeypatch):
    """Configure settings for local storage."""
    monkeypatch.setattr(settings, "USE_S3_STORAGE", False)


@pytest.fixture
def mock_s3_bucket(mock_s3_settings):
    """Mock S3 bucket with moto."""
    with mock_aws():
        import boto3

        # Create mock S3 client
        client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
        )

        # Create bucket
        client.create_bucket(Bucket="test-bucket")

        yield client


@pytest.fixture
def sample_file_content():
    """Sample file content for testing."""
    return b"Sample file content for testing purposes."


@pytest.fixture
def sample_file_path():
    """Sample file path for testing."""
    return "documents/2026/02/25/test-document.pdf"


@pytest.fixture
def reset_storage_backend():
    """Reset storage backend singleton."""
    yield

    # Reset after test
    from apps.object_storage_controller.services.factory import reset_storage_backend as _reset
    from apps.object_storage_controller.services.s3_client import S3Client

    _reset()
    S3Client.reset_instance()
