"""
Signals for documents_parser app.

This module contains Django signals for the documents_parser app,
including automatic search_vector updates for DocumentChunk model.
"""

from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.documents_parser.models import DocumentChunk

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DocumentChunk)
def update_search_vector(sender, instance, created, **kwargs):
    """Update search_vector after DocumentChunk is saved.

    This signal automatically updates the search_vector field when a
    DocumentChunk is created or its content is changed. The search_vector
    is used for PostgreSQL full-text search (FTS).

    Note:
        This uses a deferred update approach via a separate query to avoid
        recursive signal triggering. The update is performed in a single
        SQL statement for efficiency.

    Args:
        sender: The model class (DocumentChunk).
        instance: The actual DocumentChunk instance being saved.
        created: True if a new record was created.
        **kwargs: Additional signal arguments.
    """
    # Skip if this is a bulk operation or if content hasn't changed
    if kwargs.get("raw", False):
        return

    # Use raw SQL to update search_vector to avoid triggering signals again
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE document_chunks
                SET search_vector = to_tsvector('simple', content)
                WHERE id = %s
                """,
                [str(instance.id)],
            )
        logger.debug(f"Updated search_vector for chunk {instance.id}")
    except Exception as e:
        logger.error(f"Failed to update search_vector for chunk {instance.id}: {e}")
