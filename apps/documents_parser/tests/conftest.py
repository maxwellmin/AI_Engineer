"""
Shared pytest fixtures for documents_parser tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from moto import mock_aws
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.tests.factories import UserFactory


@pytest.fixture
def test_user():
    """Create a test user for document operations."""
    return UserFactory.create_user(
        username="docuser",
        email="docuser@example.com",
        password="docpass123",
    )


@pytest.fixture
def sample_pdf_content():
    """Return minimal valid PDF content for testing."""
    # Minimal valid PDF file content
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"


@pytest.fixture
def sample_txt_content():
    """Return sample text content for testing."""
    return b"This is a sample text file for testing."


@pytest.fixture
def uploaded_pdf(sample_pdf_content):
    """Create a valid UploadedFile for PDF testing."""
    return SimpleUploadedFile(
        name="test_document.pdf",
        content=sample_pdf_content,
        content_type="application/pdf",
    )


@pytest.fixture
def uploaded_txt(sample_txt_content):
    """Create a valid UploadedFile for TXT testing."""
    return SimpleUploadedFile(
        name="test_document.txt",
        content=sample_txt_content,
        content_type="text/plain",
    )


@pytest.fixture
def uploaded_large_file():
    """Create a file exceeding size limit for testing."""
    # Create content larger than 100MB limit
    large_content = b"x" * (101 * 1024 * 1024)  # 101MB
    return SimpleUploadedFile(
        name="large_file.pdf",
        content=large_content,
        content_type="application/pdf",
    )


@pytest.fixture
def uploaded_invalid_extension():
    """Create a file with invalid extension for testing."""
    return SimpleUploadedFile(
        name="test_file.exe",
        content=b"invalid content",
        content_type="application/octet-stream",
    )


@pytest.fixture
def temp_media_root(settings, tmp_path):
    """Override MEDIA_ROOT with temporary directory for isolation."""
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    return settings.MEDIA_ROOT


@pytest.fixture
def mock_s3_storage(settings, tmp_path):
    """Configure S3 storage with moto mock for testing."""
    # Use local storage for storage tests to avoid S3 complexity
    settings.USE_S3_STORAGE = False
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

    # Reset storage backend
    from apps.object_storage_controller.services.factory import reset_storage_backend
    from apps.object_storage_controller.services.s3_client import S3Client

    reset_storage_backend()
    S3Client.reset_instance()

    yield settings

    # Cleanup
    reset_storage_backend()
    S3Client.reset_instance()
