"""
Tests for hash service.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents_parser.services import hash as hash_service


class TestCalculateFileHash:
    """Tests for calculate_file_hash function."""

    def test_calculates_sha256_hash(self, tmp_path):
        """Should calculate correct SHA256 hash."""
        # Create a test file with known content
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")

        result = hash_service.calculate_file_hash(file_path=test_file)

        # SHA256 hash should be 64 characters (hex)
        assert len(result) == 64
        assert result.islower()

    def test_consistent_hash_for_same_content(self, tmp_path):
        """Should return same hash for same content."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")

        hash1 = hash_service.calculate_file_hash(file_path=test_file)
        hash2 = hash_service.calculate_file_hash(file_path=test_file)

        assert hash1 == hash2

    def test_different_hash_for_different_content(self, tmp_path):
        """Should return different hash for different content."""
        file1 = tmp_path / "file1.txt"
        file1.write_bytes(b"content 1")
        file2 = tmp_path / "file2.txt"
        file2.write_bytes(b"content 2")

        hash1 = hash_service.calculate_file_hash(file_path=file1)
        hash2 = hash_service.calculate_file_hash(file_path=file2)

        assert hash1 != hash2

    def test_raises_for_nonexistent_file(self, tmp_path):
        """Should raise FileNotFoundError for non-existent file."""
        nonexistent = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            hash_service.calculate_file_hash(file_path=nonexistent)


class TestCalculateUploadedFileHash:
    """Tests for calculate_uploaded_file_hash function."""

    def test_calculates_hash_for_uploaded_file(self):
        """Should calculate hash for UploadedFile."""
        uploaded = SimpleUploadedFile(
            name="test.txt",
            content=b"test content",
        )

        result = hash_service.calculate_uploaded_file_hash(uploaded_file=uploaded)

        assert len(result) == 64
        assert result.islower()

    def test_resets_file_pointer(self):
        """Should reset file pointer after reading."""
        uploaded = SimpleUploadedFile(
            name="test.txt",
            content=b"test content",
        )

        hash_service.calculate_uploaded_file_hash(uploaded_file=uploaded)

        # File pointer should be at start
        assert uploaded.tell() == 0

    def test_consistent_with_file_hash(self, tmp_path):
        """Should produce same hash as calculate_file_hash."""
        content = b"test content"

        # Calculate via UploadedFile
        uploaded = SimpleUploadedFile(name="test.txt", content=content)
        hash_uploaded = hash_service.calculate_uploaded_file_hash(uploaded_file=uploaded)

        # Calculate via file path
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(content)
        hash_file = hash_service.calculate_file_hash(file_path=test_file)

        assert hash_uploaded == hash_file


class TestCalculateContentHash:
    """Tests for calculate_content_hash function."""

    def test_calculates_hash_for_string(self):
        """Should calculate hash for string content."""
        result = hash_service.calculate_content_hash(content="test string")

        assert len(result) == 64
        assert result.islower()

    def test_calculates_hash_for_bytes(self):
        """Should calculate hash for bytes content."""
        result = hash_service.calculate_content_hash(content=b"test bytes")

        assert len(result) == 64
        assert result.islower()

    def test_consistent_hash_for_same_content(self):
        """Should return same hash for same content."""
        content = "same content"

        hash1 = hash_service.calculate_content_hash(content=content)
        hash2 = hash_service.calculate_content_hash(content=content)

        assert hash1 == hash2

    def test_same_hash_for_string_and_bytes(self):
        """Should return same hash for equivalent string and bytes."""
        text = "test content"

        hash_str = hash_service.calculate_content_hash(content=text)
        hash_bytes = hash_service.calculate_content_hash(content=text.encode("utf-8"))

        assert hash_str == hash_bytes
