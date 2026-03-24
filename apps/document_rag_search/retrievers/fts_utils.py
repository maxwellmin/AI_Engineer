"""
Full-text search utility functions for document RAG search module.

This module provides PostgreSQL full-text search (FTS) utility functions
that can be used independently or by the KeywordRetriever.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import Q, QuerySet

from apps.document_rag_search.constants import DEFAULT_FTS_CONFIG, DEFAULT_TOP_K
from apps.documents_parser.models import DocumentChunk

logger = logging.getLogger(__name__)


def search_chunks_by_keyword(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    user_id: str | None = None,
    document_ids: list[str] | None = None,
    fts_config: str = DEFAULT_FTS_CONFIG,
    min_rank: float = 0.0,
) -> list[dict[str, Any]]:
    """Search chunks using PostgreSQL full-text search.

    This function performs full-text search on DocumentChunk content
    using the search_vector field with PostgreSQL's SearchRank for
    relevance scoring.

    Args:
        query: Search query string.
        top_k: Maximum number of results to return.
        user_id: Optional user ID to filter results.
        document_ids: Optional list of document IDs to filter.
        fts_config: PostgreSQL FTS configuration name.
            - 'simple': Minimal processing, good for mixed Chinese/English
            - 'english': English-specific stemming and stop words
            - 'chinese': Chinese-specific (requires zhparser extension)
        min_rank: Minimum rank threshold for results.

    Returns:
        List of chunk dictionaries with scores, each containing:
        - chunk_id: UUID of the chunk
        - document_id: UUID of the parent document
        - text: Chunk content
        - score: SearchRank score (0.0 to 1.0 typically)
        - source: Original document filename
        - metadata: Chunk metadata (index, page, etc.)

    Example:
        >>> results = search_chunks_by_keyword(
        ...     query="machine learning algorithms",
        ...     top_k=5,
        ...     user_id="user-uuid-here",
        ... )
        >>> for result in results:
        ...     print(f"{result['source']}: {result['score']:.3f}")
    """
    if not query or not query.strip():
        return []

    # Build search query
    search_query = SearchQuery(query, config=fts_config)

    # Build base queryset with rank annotation
    # Apply filters BEFORE slicing to avoid "Cannot filter a query once a slice has been taken"
    queryset = DocumentChunk.objects.annotate(
        rank=SearchRank("search_vector", search_query)
    ).filter(search_vector=search_query).filter(rank__gte=min_rank)

    # Apply user filter BEFORE slicing
    if user_id:
        queryset = queryset.filter(document__user_id=user_id)

    # Apply document filter BEFORE slicing
    if document_ids:
        queryset = queryset.filter(document_id__in=document_ids)

    # Apply select_related, ordering, and slicing AFTER filters
    queryset = queryset.select_related("document").order_by("-rank")[:top_k]

    # Convert to result items
    return [
        {
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "text": chunk.content,
            "score": float(chunk.rank),
            "source": chunk.document.original_name,
            "metadata": {
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "char_count": chunk.char_count,
            },
        }
        for chunk in queryset
    ]


def search_chunks_by_like(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    user_id: str | None = None,
    document_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Search chunks using LIKE pattern matching (fallback method).

    This is a fallback search method when search_vector field is not
    available or for simple substring matching. It uses case-insensitive
    LIKE matching with simple term frequency scoring.

    Args:
        query: Search query string.
        top_k: Maximum number of results to return.
        user_id: Optional user ID to filter results.
        document_ids: Optional list of document IDs to filter.

    Returns:
        List of chunk dictionaries with scores, each containing:
        - chunk_id: UUID of the chunk
        - document_id: UUID of the parent document
        - text: Chunk content
        - score: Term frequency score
        - source: Original document filename
        - metadata: Chunk metadata

    Note:
        This method is slower than FTS and does not support advanced
        features like stemming or ranking. Use only as fallback.
    """
    if not query or not query.strip():
        return []

    # Split query into terms for better matching
    terms = query.strip().split()
    if not terms:
        return []

    # Build queryset
    queryset = DocumentChunk.objects.select_related("document")

    # Apply user filter
    if user_id:
        queryset = queryset.filter(document__user_id=user_id)

    # Apply document filter
    if document_ids:
        queryset = queryset.filter(document_id__in=document_ids)

    # Build Q objects for term matching
    q_objects = Q()
    for term in terms[:5]:  # Limit to 5 terms to avoid complex queries
        if len(term) >= 2:  # Only match terms with 2+ characters
            q_objects |= Q(content__icontains=term)

    if not q_objects:
        return []

    # Execute query and calculate simple relevance score
    chunks = list(queryset.filter(q_objects).distinct()[: top_k * 2])

    # Calculate simple relevance score based on term frequency
    results = []
    for chunk in chunks:
        # Count term occurrences in content
        content_lower = chunk.content.lower()
        score = sum(
            content_lower.count(term.lower())
            for term in terms[:5]
            if len(term) >= 2
        )
        if score > 0:
            results.append(
                {
                    "chunk_id": str(chunk.id),
                    "document_id": str(chunk.document_id),
                    "text": chunk.content,
                    "score": float(score),
                    "source": chunk.document.original_name,
                    "metadata": {
                        "chunk_index": chunk.chunk_index,
                        "page_number": chunk.page_number,
                        "char_count": chunk.char_count,
                    },
                }
            )

    # Sort by score and limit to top_k
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def get_search_queryset(
    query: str,
    user_id: str | None = None,
    document_ids: list[str] | None = None,
    fts_config: str = DEFAULT_FTS_CONFIG,
    use_fts: bool = True,
) -> QuerySet[DocumentChunk]:
    """Get a queryset for full-text search without executing it.

    This function returns a QuerySet that can be further customized
    before execution, useful for complex queries or pagination.

    Args:
        query: Search query string.
        user_id: Optional user ID to filter results.
        document_ids: Optional list of document IDs to filter.
        fts_config: PostgreSQL FTS configuration name.
        use_fts: If True, use search_vector field. If False, use LIKE.

    Returns:
        QuerySet of DocumentChunk objects with rank annotation.

    Example:
        >>> qs = get_search_queryset("machine learning", user_id="user-uuid")
        >>> # Further customize the queryset
        >>> results = qs.filter(char_count__gt=100)[:10]
    """
    if not query or not query.strip():
        return DocumentChunk.objects.none()

    if use_fts and has_search_vector_field():
        # Use FTS with search_vector
        search_query = SearchQuery(query, config=fts_config)
        queryset = DocumentChunk.objects.annotate(
            rank=SearchRank("search_vector", search_query)
        ).filter(search_vector=search_query)
    else:
        # Fall back to LIKE search
        terms = query.strip().split()
        q_objects = Q()
        for term in terms[:5]:
            if len(term) >= 2:
                q_objects |= Q(content__icontains=term)

        if not q_objects:
            return DocumentChunk.objects.none()

        # For LIKE search, we don't have rank, so we use a constant
        queryset = DocumentChunk.objects.filter(q_objects).distinct()

    # Apply filters
    if user_id:
        queryset = queryset.filter(document__user_id=user_id)

    if document_ids:
        queryset = queryset.filter(document_id__in=document_ids)

    return queryset.select_related("document")


def has_search_vector_field() -> bool:
    """Check if DocumentChunk model has search_vector field.

    Returns:
        True if search_vector field exists in DocumentChunk model.
    """
    try:
        return hasattr(DocumentChunk, "search_vector")
    except Exception:
        return False


def update_search_vector(chunk_id: str, fts_config: str = DEFAULT_FTS_CONFIG) -> bool:
    """Update search_vector for a specific chunk.

    This function triggers an update of the search_vector field
    for a single DocumentChunk, typically called after content changes.

    Args:
        chunk_id: UUID of the chunk to update.
        fts_config: PostgreSQL FTS configuration name.

    Returns:
        True if update was successful and a row was updated, False otherwise.

    Note:
        This uses a raw SQL update to set the search_vector based
        on the content field.
    """
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE document_chunks
                SET search_vector = to_tsvector(%s, content)
                WHERE id = %s
                """,
                [fts_config, chunk_id],
            )
            # Check if any row was actually updated
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Failed to update search_vector for chunk {chunk_id}: {e}")
        return False


def batch_update_search_vectors(
    chunk_ids: list[str] | None = None,
    fts_config: str = DEFAULT_FTS_CONFIG,
    batch_size: int = 100,
) -> int:
    """Batch update search_vector for multiple chunks.

    This function updates search_vector fields in batches,
    useful for initial population or bulk updates.

    Args:
        chunk_ids: Optional list of chunk UUIDs to update.
            If None, updates all chunks.
        fts_config: PostgreSQL FTS configuration name.
        batch_size: Number of chunks to update per batch.

    Returns:
        Total number of chunks updated.

    Example:
        >>> # Update all chunks
        >>> count = batch_update_search_vectors()
        >>> print(f"Updated {count} chunks")
        >>>
        >>> # Update specific chunks
        >>> count = batch_update_search_vectors(
        ...     chunk_ids=["uuid-1", "uuid-2"],
        ... )
    """
    from django.db import connection

    if chunk_ids:
        # Update specific chunks
        placeholders = ",".join(["%s"] * len(chunk_ids))
        sql = f"""
            UPDATE document_chunks
            SET search_vector = to_tsvector(%s, content)
            WHERE id IN ({placeholders})
        """
        params = [fts_config] + chunk_ids

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount
    else:
        # Update all chunks in batches
        total_updated = 0
        queryset = DocumentChunk.objects.all().only("id")

        chunk_ids_list = list(queryset.values_list("id", flat=True))

        for i in range(0, len(chunk_ids_list), batch_size):
            batch = chunk_ids_list[i : i + batch_size]
            batch_str = [str(cid) for cid in batch]
            updated = batch_update_search_vectors(
                chunk_ids=batch_str,
                fts_config=fts_config,
            )
            total_updated += updated
            logger.info(
                f"Updated search_vector for batch {i // batch_size + 1}: "
                f"{updated} chunks"
            )

        return total_updated


def get_fts_stats() -> dict[str, Any]:
    """Get statistics about FTS coverage.

    Returns:
        Dictionary with FTS statistics:
        - total_chunks: Total number of chunks
        - chunks_with_vector: Chunks with search_vector populated
        - coverage_percentage: Percentage of chunks with search_vector

    Example:
        >>> stats = get_fts_stats()
        >>> print(f"FTS coverage: {stats['coverage_percentage']:.1f}%")
    """
    total = DocumentChunk.objects.count()
    chunks_with_vector = DocumentChunk.objects.filter(
        search_vector__isnull=False
    ).count()

    coverage = (chunks_with_vector / total * 100) if total > 0 else 0.0

    return {
        "total_chunks": total,
        "chunks_with_vector": chunks_with_vector,
        "coverage_percentage": coverage,
    }
