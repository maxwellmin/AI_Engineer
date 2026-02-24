"""
Document parser services package.

Provides file storage, hash calculation, and deduplication services.
"""

from __future__ import annotations

from .deduplication import (
    DeduplicationResult,
    check_duplicate,
    get_documents_by_hash,
    get_user_documents_by_hash,
)
from .hash import (
    calculate_content_hash,
    calculate_file_hash,
    calculate_uploaded_file_hash,
)
from .storage import (
    StorageResult,
    delete_file,
    file_exists,
    get_storage_path,
    save_file,
    validate_file,
)

__all__ = [
    # Storage
    "StorageResult",
    "delete_file",
    "file_exists",
    "get_storage_path",
    "save_file",
    "validate_file",
    # Hash
    "calculate_content_hash",
    "calculate_file_hash",
    "calculate_uploaded_file_hash",
    # Deduplication
    "DeduplicationResult",
    "check_duplicate",
    "get_documents_by_hash",
    "get_user_documents_by_hash",
]
