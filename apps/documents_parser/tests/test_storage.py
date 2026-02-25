"""
Tests for storage service.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents_parser.services import storage
from core.exceptions import ValidationError


class TestGetStoragePath:
    """Tests for get_storage_path function."""

    def test_generates_date_based_path(self):
        """Should generate path with year/month/day structure."""
        result = storage.get_storage_path(
            filename="test.pdf",
            date_prefix=date(2026, 2, 24),
        )
        # Path should contain date structure (filename has UUID prefix)
        assert "documents/2026/02/24" in str(result)
        assert str(result).endswith(".pdf")

    def test_uses_today_when_no_date_provided(self):
        """Should use current date when date_prefix not provided."""
        result = storage.get_storage_path(filename="report.pdf")
        today = date.today()
        expected_prefix = f"documents/{today.year}/{today.month:02d}/{today.day:02d}"
        assert expected_prefix in str(result)

    def test_sanitizes_path_traversal(self):
        """Should sanitize filename to prevent path traversal."""
        result = storage.get_storage_path(
            filename="../../../etc/passwd",
            date_prefix=date(2026, 2, 24),
        )
        # Should not contain path traversal sequences
        assert ".." not in str(result)
        # Should not contain 'etc' or 'passwd' in path traversal way
        assert "etc" not in str(result)


class TestValidateFile:
    """Tests for validate_file function."""

    def test_validates_allowed_extension(self, uploaded_pdf):
        """Should return sanitized extension for allowed files."""
        ext = storage.validate_file(uploaded_file=uploaded_pdf)
        assert ext == "pdf"

    def test_validates_txt_file(self, uploaded_txt):
        """Should validate txt files."""
        ext = storage.validate_file(uploaded_file=uploaded_txt)
        assert ext == "txt"

    def test_rejects_disallowed_extension(self, uploaded_invalid_extension):
        """Should raise ValidationError for disallowed extensions."""
        with pytest.raises(ValidationError):
            storage.validate_file(uploaded_file=uploaded_invalid_extension)

    def test_rejects_oversized_file(self, uploaded_large_file):
        """Should raise ValidationError for files exceeding size limit."""
        with pytest.raises(ValidationError):
            storage.validate_file(uploaded_file=uploaded_large_file)


@pytest.mark.django_db
class TestSaveFile:
    """Tests for save_file function."""

    def test_saves_file_to_correct_path(self, uploaded_pdf, mock_s3_storage, test_user):
        """Should save file to date-based path structure."""
        result = storage.save_file(
            uploaded_file=uploaded_pdf,
            user_id=str(test_user.id),
        )

        assert result.file_type == "pdf"
        assert result.file_size > 0
        assert "documents" in str(result.file_path)

    def test_returns_correct_metadata(self, uploaded_pdf, mock_s3_storage, test_user):
        """Should return correct file metadata."""
        result = storage.save_file(
            uploaded_file=uploaded_pdf,
            user_id=str(test_user.id),
        )

        assert isinstance(result.file_path, str)
        assert isinstance(result.file_size, int)
        assert isinstance(result.file_type, str)
        assert result.backend_type == "s3"  # Default is S3 in tests

    def test_saves_txt_file(self, uploaded_txt, mock_s3_storage, test_user):
        """Should save txt files correctly."""
        result = storage.save_file(
            uploaded_file=uploaded_txt,
            user_id=str(test_user.id),
        )

        assert result.file_type == "txt"


@pytest.mark.django_db
class TestDeleteFile:
    """Tests for delete_file function."""

    def test_deletes_existing_file(self, uploaded_pdf, mock_s3_storage, test_user):
        """Should delete file and return True."""
        # First save a file
        result = storage.save_file(
            uploaded_file=uploaded_pdf,
            user_id=str(test_user.id),
        )

        # Then delete it
        deleted = storage.delete_file(file_path=result.file_path)
        assert deleted is True

    def test_returns_false_for_nonexistent_file(self, mock_s3_storage):
        """Should return False for non-existent file."""
        deleted = storage.delete_file(file_path="nonexistent/file.pdf")
        assert deleted is False


@pytest.mark.django_db
class TestFileExists:
    """Tests for file_exists function."""

    def test_returns_true_for_existing_file(self, uploaded_pdf, mock_s3_storage, test_user):
        """Should return True for existing file."""
        result = storage.save_file(
            uploaded_file=uploaded_pdf,
            user_id=str(test_user.id),
        )

        assert storage.file_exists(file_path=result.file_path) is True

    def test_returns_false_for_nonexistent_file(self, mock_s3_storage):
        """Should return False for non-existent file."""
        assert storage.file_exists(file_path="nonexistent/file.pdf") is False
