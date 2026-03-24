"""
Keyword retriever for document RAG search module.

This retriever uses PostgreSQL full-text search (FTS) for keyword-based retrieval,
supporting both Chinese and English text search.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from apps.document_rag_search.constants import (
    DEFAULT_FTS_CONFIG,
    DEFAULT_TOP_K,
    RetrieverName,
)
from apps.document_rag_search.dto import (
    RetrieverResult,
    SearchQuery,
)
from apps.document_rag_search.exceptions import KeywordRetrieverError
from apps.document_rag_search.retrievers.base import BaseRetriever
from apps.documents_parser.models import Document, DocumentChunk

logger = logging.getLogger(__name__)


class KeywordRetriever(BaseRetriever):
    """Retriever that uses PostgreSQL full-text search.

    This retriever performs keyword-based search using PostgreSQL's built-in
    full-text search capabilities. It supports:
    - Basic full-text search using SearchVector
    - Filtering by user_id and document_ids
    - Mixed Chinese/English text support using 'simple' config

    Note:
        For optimal performance, the DocumentChunk model should have a
        search_vector field with a GIN index. This retriever will fall back
        to basic LIKE search if the search_vector field is not available.

    Example:
        >>> retriever = KeywordRetriever()
        >>> result = retriever.retrieve(
        ...     query=SearchQuery(text="machine learning algorithms"),
        ...     top_k=10,
        ... )
        >>> print(len(result.items))
        5
    """

    def __init__(
        self,
        fts_config: str = DEFAULT_FTS_CONFIG,
        use_search_vector: bool = True,
    ) -> None:
        """Initialize the keyword retriever.

        Args:
            fts_config: PostgreSQL FTS configuration name.
                - 'simple': Minimal processing, good for mixed Chinese/English
                - 'english': English-specific stemming and stop words
                - 'chinese': Chinese-specific (requires zhparser extension)
            use_search_vector: Whether to use search_vector field for FTS.
                If False, falls back to basic LIKE search.
        """
        self._fts_config = fts_config
        self._use_search_vector = use_search_vector

    @property
    def name(self) -> str:
        """Return retriever name."""
        return RetrieverName.KEYWORD.value

    def retrieve(
        self,
        query: SearchQuery,
        top_k: int = DEFAULT_TOP_K,
        **kwargs: Any,
    ) -> RetrieverResult:
        """Retrieve documents using PostgreSQL full-text search.

        Args:
            query: Search query with text.
            top_k: Maximum number of results to return.
            **kwargs: Additional parameters:
                - document_ids: List of document IDs to filter
                - min_rank: Minimum rank threshold (default: 0.0)

        Returns:
            RetrieverResult with matching documents.

        Raises:
            KeywordRetrieverError: If search fails.
        """
        start_time = time.time()

        try:
            if not query.text or not query.text.strip():
                return RetrieverResult(
                    retriever_name=self.name,
                    items=[],
                    query_time_ms=0.0,
                    total=0,
                )

            # Get filter parameters
            document_ids = kwargs.get("document_ids")
            min_rank = kwargs.get("min_rank", 0.0)

            # Try to use search_vector field if available and enabled
            if self._use_search_vector and self._has_search_vector_field():
                items = self._perform_fts_search(
                    query_text=query.text,
                    user_id=query.user_id,
                    document_ids=document_ids,
                    top_k=top_k,
                    min_rank=min_rank,
                )
            else:
                # Fall back to basic LIKE search
                items = self._perform_like_search(
                    query_text=query.text,
                    user_id=query.user_id,
                    document_ids=document_ids,
                    top_k=top_k,
                )

            query_time_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"Keyword search completed in {query_time_ms:.2f}ms, "
                f"found {len(items)} results"
            )

            return RetrieverResult(
                retriever_name=self.name,
                items=items,
                query_time_ms=query_time_ms,
                total=len(items),
            )

        except Exception as e:
            logger.error(f"Keyword retriever failed: {e}")
            raise KeywordRetrieverError(reason=str(e))

    def _has_search_vector_field(self) -> bool:
        """Check if DocumentChunk has search_vector field.

        Returns:
            True if search_vector field exists.
        """
        try:
            # Check if the field exists in the model
            return hasattr(DocumentChunk, "search_vector")
        except Exception:
            return False

    def _perform_fts_search(
        self,
        query_text: str,
        user_id: str | None,
        document_ids: list[str] | None,
        top_k: int,
        min_rank: float,
    ) -> list[dict[str, Any]]:
        """Perform full-text search using search_vector field.

        Args:
            query_text: Search query text.
            user_id: Optional user ID filter.
            document_ids: Optional list of document IDs to filter.
            top_k: Maximum results.
            min_rank: Minimum rank threshold.

        Returns:
            List of result items with chunk data and scores.
        """
        from django.contrib.postgres.search import SearchQuery, SearchRank

        # Build search query
        search_query = SearchQuery(query_text, config=self._fts_config)

        # Build base queryset with rank annotation
        queryset = (
            DocumentChunk.objects.annotate(
                rank=SearchRank("search_vector", search_query)
            )
            .filter(search_vector=search_query)
            .filter(rank__gte=min_rank)
            .select_related("document")
            .order_by("-rank")[:top_k]
        )

        # Apply user filter
        if user_id:
            queryset = queryset.filter(document__user_id=user_id)

        # Apply document filter
        if document_ids:
            queryset = queryset.filter(document_id__in=document_ids)

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

    def _perform_like_search(
        self,
        query_text: str,
        user_id: str | None,
        document_ids: list[str] | None,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Perform basic LIKE search as fallback.

        This is used when search_vector field is not available.
        Uses ilike for case-insensitive partial matching.

        Args:
            query_text: Search query text.
            user_id: Optional user ID filter.
            document_ids: Optional list of document IDs to filter.
            top_k: Maximum results.

        Returns:
            List of result items with chunk data and scores.
        """
        # Split query into terms for better matching
        terms = query_text.strip().split()
        if not terms:
            return []

        # Build queryset with OR conditions for each term
        queryset = DocumentChunk.objects.select_related("document")

        # Apply user filter
        if user_id:
            queryset = queryset.filter(document__user_id=user_id)

        # Apply document filter
        if document_ids:
            queryset = queryset.filter(document_id__in=document_ids)

        # Build Q objects for term matching
        from django.db.models import Q

        q_objects = Q()
        for term in terms[:5]:  # Limit to 5 terms to avoid complex queries
            if len(term) >= 2:  # Only match terms with 2+ characters
                q_objects |= Q(content__icontains=term)

        if not q_objects:
            return []

        # Execute query and calculate simple relevance score
        chunks = list(queryset.filter(q_objects).distinct()[:top_k * 2])

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

    def health_check(self) -> bool:
        """Check if PostgreSQL database is accessible.

        Returns:
            True if retriever is healthy, False otherwise.
        """
        try:
            # Simple database connectivity check
            DocumentChunk.objects.count()
            return True
        except Exception as e:
            logger.error(f"Keyword retriever health check failed: {e}")
            return False
