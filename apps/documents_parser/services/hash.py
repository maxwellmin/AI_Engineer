"""
Hash calculation service for file deduplication.

Provides SHA256 hash calculation for file content.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def calculate_file_hash(*, file_path: Path, chunk_size: int = 8192) -> str:
    """
    Calculate SHA256 hash of file content.

    Uses chunked reading to handle large files efficiently.

    Args:
        file_path: Absolute path to the file.
        chunk_size: Size of chunks to read (default 8KB).

    Returns:
        Lowercase hexadecimal SHA256 hash string (64 characters).

    Raises:
        FileNotFoundError: If file does not exist.
        PermissionError: If file cannot be read.
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def calculate_uploaded_file_hash(*, uploaded_file, chunk_size: int = 8192) -> str:
    """
    Calculate SHA256 hash of UploadedFile content.

    Handles Django's UploadedFile which may be in-memory or temporary file.
    Resets file pointer after reading.

    Args:
        uploaded_file: Django UploadedFile instance.
        chunk_size: Size of chunks to read (default 8KB).

    Returns:
        Lowercase hexadecimal SHA256 hash string (64 characters).
    """
    sha256_hash = hashlib.sha256()

    # Ensure we're at the start of the file
    uploaded_file.seek(0)

    for chunk in iter(lambda: uploaded_file.read(chunk_size), b""):
        sha256_hash.update(chunk)

    # Reset file pointer for subsequent reads
    uploaded_file.seek(0)

    return sha256_hash.hexdigest()


def calculate_content_hash(*, content: str | bytes) -> str:
    """
    Calculate SHA256 hash of content string or bytes.

    Useful for hashing text chunks or metadata.

    Args:
        content: String or bytes to hash.

    Returns:
        Lowercase hexadecimal SHA256 hash string (64 characters).
    """
    if isinstance(content, str):
        content = content.encode("utf-8")

    sha256_hash = hashlib.sha256()
    sha256_hash.update(content)

    return sha256_hash.hexdigest()
