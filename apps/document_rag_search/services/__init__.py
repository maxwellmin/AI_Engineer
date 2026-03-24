"""Services for document RAG search module.

This module provides high-level service classes for search operations.

Available Classes:
    SearchService: High-level facade for all search operations.
"""

from apps.document_rag_search.services.search_service import SearchService

__all__ = [
    "SearchService",
]
