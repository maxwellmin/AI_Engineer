"""
Vector retriever for document RAG search module.

This retriever wraps MilvusService for vector similarity search,
supporting both single vector search and hybrid search across multiple vector fields.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from apps.document_rag_search.constants import (
    DEFAULT_TOP_K,
    RetrieverName,
)
from apps.document_rag_search.dto import (
    RetrieverResult,
    SearchQuery,
)
from apps.document_rag_search.exceptions import VectorRetrieverError
from apps.document_rag_search.retrievers.base import BaseRetriever
from apps.milvus_database_controller.constants import (
    COLLECTION_DOCUMENTS,
    FieldName,
)
from apps.milvus_database_controller.services.milvus_service import MilvusService

logger = logging.getLogger(__name__)


class VectorRetriever(BaseRetriever):
    """Retriever that uses Milvus vector similarity search.

    This retriever performs dense vector search using MilvusService.
    It supports:
    - Single vector field search (text_dense or summary_dense)
    - Hybrid search across multiple vector fields
    - Filter expressions for user/document filtering

    Example:
        >>> retriever = VectorRetriever()
        >>> result = retriever.retrieve(
        ...     query=SearchQuery(text="machine learning", embedding=[...]),
        ...     top_k=10,
        ... )
        >>> print(len(result.items))
        5
    """

    def __init__(
        self,
        milvus_service: MilvusService | None = None,
        collection_name: str = COLLECTION_DOCUMENTS,
        anns_field: str = FieldName.TEXT_DENSE.value,
    ) -> None:
        """Initialize the vector retriever.

        Args:
            milvus_service: Optional MilvusService instance.
            collection_name: Milvus collection to search.
            anns_field: Vector field to search (default: text_dense).
        """
        self._milvus_service = milvus_service or MilvusService()
        self._collection_name = collection_name
        self._anns_field = anns_field

    @property
    def name(self) -> str:
        """Return retriever name."""
        return RetrieverName.VECTOR.value

    def retrieve(
        self,
        query: SearchQuery,
        top_k: int = DEFAULT_TOP_K,
        **kwargs: Any,
    ) -> RetrieverResult:
        """Retrieve documents using vector similarity search.

        Args:
            query: Search query with text and optional embedding.
            top_k: Maximum number of results to return.
            **kwargs: Additional parameters:
                - anns_field: Override default vector field
                - filter_expr: Additional Milvus filter expression
                - use_hybrid: Use hybrid search (default: False)
                - document_ids: List of document IDs to filter

        Returns:
            RetrieverResult with matching documents.

        Raises:
            VectorRetrieverError: If search fails.
        """
        start_time = time.time()

        try:
            # Get query embedding
            if query.embedding is None:
                raise VectorRetrieverError(
                    reason="Query embedding is required for vector search"
                )

            # Build filter expression
            filter_expr = self._build_filter_expr(
                user_id=query.user_id,
                document_ids=kwargs.get("document_ids"),
            )

            # Append additional filter if provided
            additional_filter = kwargs.get("filter_expr", "")
            if additional_filter:
                if filter_expr:
                    filter_expr = f"({filter_expr}) and ({additional_filter})"
                else:
                    filter_expr = additional_filter

            # Determine vector field
            anns_field = kwargs.get("anns_field", self._anns_field)

            # Perform search
            use_hybrid = kwargs.get("use_hybrid", False)

            if use_hybrid:
                # Hybrid search across multiple vector fields
                result = self._perform_hybrid_search(
                    query_embedding=query.embedding,
                    query_text=query.text,
                    top_k=top_k,
                    filter_expr=filter_expr,
                )
            else:
                # Single vector field search
                result = self._perform_single_search(
                    query_embedding=query.embedding,
                    anns_field=anns_field,
                    top_k=top_k,
                    filter_expr=filter_expr,
                )

            query_time_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"Vector search completed in {query_time_ms:.2f}ms, "
                f"found {result.total} results"
            )

            return RetrieverResult(
                retriever_name=self.name,
                items=result.items,
                query_time_ms=query_time_ms,
                total=result.total,
            )

        except Exception as e:
            logger.error(f"Vector retriever failed: {e}")
            raise VectorRetrieverError(reason=str(e))

    def _perform_single_search(
        self,
        query_embedding: list[float],
        anns_field: str,
        top_k: int,
        filter_expr: str,
    ) -> RetrieverResult:
        """Perform single vector field search.

        Args:
            query_embedding: Query embedding vector.
            anns_field: Vector field to search.
            top_k: Maximum results.
            filter_expr: Filter expression.

        Returns:
            RetrieverResult with search results.
        """
        search_result = self._milvus_service.search(
            collection_name=self._collection_name,
            query_vector=query_embedding,
            anns_field=anns_field,
            top_k=top_k,
            filter_expr=filter_expr,
            output_fields=[
                FieldName.PK.value,
                FieldName.TEXT.value,
                FieldName.SUMMARY.value,
                FieldName.DOCUMENT.value,
                FieldName.SOURCE.value,
                FieldName.SOURCE_NAME.value,
                FieldName.LT_DOC_ID.value,
                FieldName.CHUNK_ID.value,
            ],
        )

        # Convert SearchResult items to dict format
        items = [
            {
                "chunk_id": item.id,
                "document_id": item.lt_doc_id,
                "text": item.text,
                "score": 1.0 - item.distance,  # Convert distance to similarity score
                "source": item.source_name,
                "metadata": {
                    "summary": item.summary,
                    "document": item.document,
                    "source_type": item.source,
                    "chunk_index": item.chunk_id,
                },
            }
            for item in search_result.items
        ]

        return RetrieverResult(
            retriever_name=self.name,
            items=items,
            query_time_ms=search_result.query_time_ms,
            total=search_result.total,
        )

    def _perform_hybrid_search(
        self,
        query_embedding: list[float],
        query_text: str,
        top_k: int,
        filter_expr: str,
    ) -> RetrieverResult:
        """Perform hybrid search across multiple vector fields.

        Uses both text_dense and summary_dense fields for better retrieval.

        Args:
            query_embedding: Query embedding vector.
            query_text: Original query text (for potential BM25 integration).
            top_k: Maximum results.
            filter_expr: Filter expression.

        Returns:
            RetrieverResult with fused results.
        """
        # Build query vectors for both fields
        query_vectors = {
            FieldName.TEXT_DENSE.value: query_embedding,
            FieldName.SUMMARY_DENSE.value: query_embedding,
        }

        hybrid_result = self._milvus_service.hybrid_search(
            collection_name=self._collection_name,
            query_text=query_text,
            query_vectors=query_vectors,
            top_k=top_k,
            filter_expr=filter_expr,
            rerank_method="rrf",
            rrf_k=60,
        )

        # Convert HybridSearchResult items to dict format
        items = [
            {
                "chunk_id": item.id,
                "document_id": item.lt_doc_id,
                "text": item.text,
                "score": item.distance,  # RRF score
                "source": item.source_name,
                "metadata": {
                    "summary": item.summary,
                    "document": item.document,
                    "source_type": item.source,
                    "chunk_index": item.chunk_id,
                },
            }
            for item in hybrid_result.items
        ]

        return RetrieverResult(
            retriever_name=self.name,
            items=items,
            query_time_ms=hybrid_result.query_time_ms,
            total=hybrid_result.total,
        )

    def health_check(self) -> bool:
        """Check if Milvus is healthy and collection is available.

        Returns:
            True if retriever is healthy, False otherwise.
        """
        try:
            health = self._milvus_service.health_check()
            if health.get("connected", False):
                # Check if collection exists
                return self._milvus_service.has_collection(self._collection_name)
            return False
        except Exception as e:
            logger.error(f"Vector retriever health check failed: {e}")
            return False
