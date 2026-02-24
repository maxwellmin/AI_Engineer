"""
File storage service for document management.

Provides abstraction over file storage operations with support
for local filesystem storage, designed for future S3 compatibility.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from core.exceptions import DocumentProcessingError, ValidationError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StorageResult:
    """Immutable result of file storage operation."""

    file_path: str  # Relative path from MEDIA_ROOT
    absolute_path: Path  # Absolute filesystem path
    file_size: int
    file_type: str


def get_storage_path(*, filename: str, date_prefix: date | None = None) -> Path:
    """
    Generate storage path with date-based directory structure.

    Args:
        filename: Original filename (will be sanitized).
        date_prefix: Date for path structure (defaults to today).

    Returns:
        Path relative to MEDIA_ROOT.

    Example:
        >>> get_storage_path(filename="report.pdf")
        Path("documents/2026/02/24/report.pdf")
    """
    config = getattr(settings, "DOCUMENT_STORAGE_CONFIG", {})
    base_dir = config.get("upload_to", "documents")

    # Use provided date or today
    date_val = date_prefix or date.today()

    # Sanitize filename: remove path separators and traversal sequences
    safe_filename = _sanitize_filename(filename)

    # Generate unique filename to avoid collisions
    unique_filename = _generate_unique_filename(safe_filename)

    return Path(base_dir) / str(date_val.year) / f"{date_val.month:02d}" / f"{date_val.day:02d}" / unique_filename


def validate_file(*, uploaded_file: UploadedFile) -> str:
    """
    Validate uploaded file against configuration constraints.

    Args:
        uploaded_file: Django UploadedFile instance.

    Returns:
        Sanitized file extension (lowercase, without dot).

    Raises:
        ValidationError: If file extension not allowed.
        ValidationError: If file size exceeds limit.
    """
    config = getattr(settings, "DOCUMENT_STORAGE_CONFIG", {})
    allowed_extensions = config.get("allowed_extensions", ["pdf", "docx", "doc", "txt", "md"])
    max_file_size = config.get("max_file_size", 100 * 1024 * 1024)

    # Get file extension
    filename = uploaded_file.name or "unknown"
    ext = Path(filename).suffix.lower().lstrip(".")

    if not ext or ext not in allowed_extensions:
        raise ValidationError(
            detail=f"File extension '.{ext}' is not allowed. Allowed extensions: {', '.join(allowed_extensions)}"
        )

    # Check file size
    if uploaded_file.size and uploaded_file.size > max_file_size:
        max_size_mb = max_file_size / (1024 * 1024)
        raise ValidationError(detail=f"File size exceeds maximum allowed size of {max_size_mb:.0f}MB")

    return ext


def save_file(*, uploaded_file: UploadedFile, user_id: str) -> StorageResult:
    """
    Save uploaded file to storage with date-based path structure.

    Args:
        uploaded_file: Django UploadedFile instance.
        user_id: User UUID for potential future user-based organization.

    Returns:
        StorageResult with file metadata.

    Raises:
        DocumentProcessingError: If file save fails.
        ValidationError: If file validation fails.
    """
    # Validate file first
    file_type = validate_file(uploaded_file=uploaded_file)

    # Generate storage path
    filename = uploaded_file.name or f"document.{file_type}"
    relative_path = get_storage_path(filename=filename)
    absolute_path = Path(settings.MEDIA_ROOT) / relative_path

    # Create directory structure
    absolute_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    try:
        with open(absolute_path, "wb") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
    except Exception as e:
        logger.error(f"Failed to save file {filename}: {e}")
        raise DocumentProcessingError(detail=f"Failed to save file: {e}")

    # Get file size
    file_size = absolute_path.stat().st_size

    logger.info(f"Saved file {filename} to {relative_path} for user {user_id}")

    return StorageResult(
        file_path=str(relative_path),
        absolute_path=absolute_path,
        file_size=file_size,
        file_type=file_type,
    )


def delete_file(*, file_path: str) -> bool:
    """
    Delete file from storage.

    Args:
        file_path: Relative path from MEDIA_ROOT.

    Returns:
        True if file was deleted, False if it didn't exist.

    Raises:
        DocumentProcessingError: If deletion fails unexpectedly.
    """
    absolute_path = Path(settings.MEDIA_ROOT) / file_path

    if not absolute_path.exists():
        return False

    try:
        absolute_path.unlink()
        logger.info(f"Deleted file: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete file {file_path}: {e}")
        raise DocumentProcessingError(detail=f"Failed to delete file: {e}")


def file_exists(*, file_path: str) -> bool:
    """
    Check if file exists in storage.

    Args:
        file_path: Relative path from MEDIA_ROOT.

    Returns:
        True if file exists, False otherwise.
    """
    absolute_path = Path(settings.MEDIA_ROOT) / file_path
    return absolute_path.exists()


def _sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other issues.

    Args:
        filename: Original filename.

    Returns:
        Sanitized filename.
    """
    # Remove any path separators and keep only the filename
    name = Path(filename).name

    # Remove any null bytes and other control characters
    name = re.sub(r"[\x00-\x1f]", "", name)

    # Remove path traversal sequences
    name = name.replace("..", "")

    # If name is empty after sanitization, generate a default
    if not name:
        name = "unnamed_file"

    return name


def _generate_unique_filename(filename: str) -> str:
    """
    Generate a unique filename by adding a UUID prefix.

    Args:
        filename: Original filename.

    Returns:
        Unique filename with UUID prefix.
    """
    name = Path(filename).stem
    ext = Path(filename).suffix

    # Add short UUID to prevent filename collisions
    unique_id = uuid.uuid4().hex[:8]

    return f"{name}_{unique_id}{ext}"
