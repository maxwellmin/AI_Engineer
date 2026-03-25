"""
Base retriever for document RAG search module.

This module defines the abstract base class that all retrievers must implement,
 providing a consistent interface for retrieving documents from different sources.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from apps.document_rag_search.constants import RetrieverName
from apps.document_rag_search.dto import RetrieverResult, SearchQuery
from apps.document_rag_search.exceptions import RetrieverUnavailableError

logger = logging.getLogger(__name__)


class BaseRetriever(ABC):
    """Abstract base class for all retrievers.

    All retrievers (Vector, Keyword, Graph) must inherit from this base class
    and providing a consistent interface for retrieving documents from different sources
    (Milvus, PostgreSQL FTS, Neo4j).

    Subclasses must implement:
    - name property: Return the retriever name
    - retrieve method: Perform the actual retrieval
    - health_check method: Check if the retriever is available

    Example:
        >>> class MyRetriever(BaseRetriever):
        ...     @property
        ...     def name(self) -> str:
        ...         return "my_retriever"
        ...
        ...     def retrieve(self, query, top_k=10):
        ...         # Implementation here
        ...         return RetrieverResult(...)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the retriever name.

        This name is used for logging, metrics, and result identification.

        Returns:
            Retriever name as string.
        """
        ...

    @abstractmethod
    def retrieve(
        self,
        query: SearchQuery,
        top_k: int = 10,
        **kwargs: Any,
    ) -> RetrieverResult:
        """Retrieve relevant documents.

        Args:
            query: Search query with text and optional embedding.
            top_k: Maximum number of results to return.
            **kwargs: Additional retriever-specific parameters.

        Returns:
            RetrieverResult with ranked items.

        Raises:
            RetrieverUnavailableError: If retriever is not available.
            RetrieverError: If retrieval fails.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the retriever is healthy and available.

        This method should verify that the underlying service
        (Milvus, Neo4j, PostgreSQL) is properly connected and operational.

        Returns:
            True if retriever is healthy, False otherwise.
        """
        ...

    def _build_filter_expr(
        self,
        user_id: str | None,
        document_ids: list[str] | None = None,
    ) -> str:
        """Build Milvus filter expression from parameters.

        Args:
            user_id: Optional user ID filter.
                NOTE: The 'documents' collection does not have a user_id field.
                This parameter is kept for API compatibility but is not used
                for filtering. User-level access control should be handled
                at the application layer via document ownership.
            document_ids: Optional list of document IDs to filter.

        Returns:
            Milvus filter expression string.
        """
        filters = []

        # NOTE: user_id filtering is not supported in the documents collection
        # because the schema does not include a user_id field.
        # User-level access control is handled via document ownership in PostgreSQL.
        # If user-level filtering is needed, filter by document_ids instead.

        if document_ids:
            # Convert document IDs to quoted strings
            doc_ids_str = ", ".join(f'"{doc_id}"' for doc_id in document_ids)
            filters.append(f"lt_doc_id in [{doc_ids_str}]")

        if len(filters) == 0:
            return ""
        elif len(filters) == 1:
            return filters[0]
        else:
            return " and ".join(filters)
