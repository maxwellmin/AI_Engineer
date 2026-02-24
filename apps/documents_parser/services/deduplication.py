"""
Deduplication service for document management.

Checks for duplicate files based on content hash per user.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeduplicationResult:
    """Immutable result of deduplication check."""

    is_duplicate: bool
    existing_document_id: str | None
    existing_document_name: str | None


def check_duplicate(*, user: User, file_hash: str) -> DeduplicationResult:
    """
    Check if a file with the given hash already exists for the user.

    The database has a unique constraint on (user, file_hash), so
    this check prevents duplicate uploads at the application level
    before attempting database insert.

    Args:
        user: User instance to check against.
        file_hash: SHA256 hash of file content (64 chars).

    Returns:
        DeduplicationResult with duplicate status and existing document info.

    Example:
        >>> result = check_duplicate(user=request.user, file_hash="abc123...")
        >>> if result.is_duplicate:
        ...     raise ValidationError(f"File already uploaded as: {result.existing_document_name}")
    """
    from apps.documents_parser.models import Document

    try:
        existing_doc = Document.objects.get(user=user, file_hash=file_hash)
        logger.info(f"Found duplicate document for user {user.id}: {existing_doc.id}")
        return DeduplicationResult(
            is_duplicate=True,
            existing_document_id=str(existing_doc.id),
            existing_document_name=existing_doc.original_name,
        )
    except Document.DoesNotExist:
        return DeduplicationResult(
            is_duplicate=False,
            existing_document_id=None,
            existing_document_name=None,
        )


def get_documents_by_hash(*, file_hash: str):
    """
    Get all documents with a given hash across all users.

    Useful for system-wide deduplication analysis.

    Args:
        file_hash: SHA256 hash to search for.

    Returns:
        QuerySet of Document instances.
    """
    from apps.documents_parser.models import Document

    return Document.objects.filter(file_hash=file_hash).select_related("user")


def get_user_documents_by_hash(*, user: User, file_hash: str):
    """
    Get user's documents with a given hash.

    Args:
        user: User instance.
        file_hash: SHA256 hash to search for.

    Returns:
        QuerySet of Document instances for the user.
    """
    from apps.documents_parser.models import Document

    return Document.objects.filter(user=user, file_hash=file_hash)
