"""
Milvus service - High-level facade for Milvus operations.

This module provides a unified service interface that coordinates
all Milvus operations through a single entry point.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from apps.milvus_database_controller.client import MilvusClientWrapper
from apps.milvus_database_controller.constants import (
    COLLECTION_DOCUMENTS,
    DEFAULT_DENSE_DIMENSION,
    DEFAULT_TOP_K,
    FieldName,
)
from apps.milvus_database_controller.dto import (
    BM25SearchRequest,
    CollectionInfo,
    CreateCollectionRequest,
    DeleteResult,
    DeleteVectorsByFilterRequest,
    DeleteVectorsRequest,
    GetVectorRequest,
    HybridSearchRequest,
    HybridSearchResult,
    InsertResult,
    InsertVectorsRequest,
    QueryRequest,
    QueryResult,
    SearchRequest,
    SearchResult,
    UpsertResult,
    UpsertVectorsRequest,
)
from apps.milvus_database_controller.exceptions import MilvusError
from apps.milvus_database_controller.managers.collection_manager import CollectionManager
from apps.milvus_database_controller.managers.index_manager import IndexManager
from apps.milvus_database_controller.managers.search_manager import SearchManager
from apps.milvus_database_controller.managers.vector_manager import VectorManager

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class MilvusService:
    """High-level facade service for Milvus operations.

    This service provides a unified interface for all Milvus operations,
    coordinating between CollectionManager, IndexManager, VectorManager,
    and SearchManager.

    Example:
        >>> service = MilvusService()
        >>> # Create collection
        >>> service.create_collection("documents")
        >>> # Insert vectors
        >>> result = service.insert_vectors("documents", data)
        >>> # Search
        >>> results = service.search("documents", query_vector)
    """

    def __init__(self, client: MilvusClientWrapper | None = None) -> None:
        """Initialize the Milvus service.

        Args:
            client: Optional MilvusClientWrapper instance.
        """
        self._client = client or MilvusClientWrapper.get_instance()
        self._collection_manager = CollectionManager(self._client)
        self._index_manager = IndexManager(self._client)
        self._vector_manager = VectorManager(self._client)
        self._search_manager = SearchManager(self._client)

    # =========================================================================
    # Collection Management
    # =========================================================================

    def create_collection(
        self,
        collection_name: str,
        dimension: int = DEFAULT_DENSE_DIMENSION,
        description: str = "",
        create_indexes: bool = True,
    ) -> bool:
        """Create a new collection with optional indexes.

        Args:
            collection_name: Name of the collection.
            dimension: Vector dimension.
            description: Collection description.
            create_indexes: Whether to create indexes automatically.

        Returns:
            True if collection created successfully.
        """
        request = CreateCollectionRequest(
            collection_name=collection_name,
            dimension=dimension,
            description=description,
        )

        result = self._collection_manager.create_collection(request)

        if create_indexes and result:
            # Create indexes after collection creation
            self._index_manager.create_all_indexes(collection_name)
            # Load collection into memory
            self._index_manager.load_collection(collection_name)

        return result

    def has_collection(self, collection_name: str) -> bool:
        """Check if a collection exists.

        Args:
            collection_name: Name of the collection.

        Returns:
            True if collection exists.
        """
        return self._collection_manager.has_collection(collection_name)

    def list_collections(self) -> list[str]:
        """List all collections.

        Returns:
            List of collection names.
        """
        return self._collection_manager.list_collections()

    def drop_collection(self, collection_name: str) -> bool:
        """Drop a collection.

        Args:
            collection_name: Name of the collection.

        Returns:
            True if collection dropped successfully.
        """
        return self._collection_manager.drop_collection(collection_name)

    def get_collection_info(self, collection_name: str) -> CollectionInfo:
        """Get collection information.

        Args:
            collection_name: Name of the collection.

        Returns:
            CollectionInfo with details.
        """
        return self._collection_manager.describe_collection(collection_name)

    def ensure_collection(
        self,
        collection_name: str = COLLECTION_DOCUMENTS,
        dimension: int = DEFAULT_DENSE_DIMENSION,
    ) -> bool:
        """Ensure a collection exists.

        Args:
            collection_name: Name of the collection.
            dimension: Vector dimension.

        Returns:
            True if collection exists or was created.
        """
        return self._collection_manager.ensure_collection(collection_name, dimension)

    # =========================================================================
    # Index Management
    # =========================================================================

    def create_indexes(self, collection_name: str) -> dict[str, bool]:
        """Create all indexes for a collection.

        Args:
            collection_name: Name of the collection.

        Returns:
            Dictionary mapping index names to creation status.
        """
        return self._index_manager.create_all_indexes(collection_name)

    def load_collection(self, collection_name: str) -> bool:
        """Load a collection into memory.

        Args:
            collection_name: Name of the collection.

        Returns:
            True if collection loaded successfully.
        """
        return self._index_manager.load_collection(collection_name)

    def release_collection(self, collection_name: str) -> bool:
        """Release a collection from memory.

        Args:
            collection_name: Name of the collection.

        Returns:
            True if collection released successfully.
        """
        return self._index_manager.release_collection(collection_name)

    def is_collection_loaded(self, collection_name: str) -> bool:
        """Check if a collection is loaded into memory.

        Args:
            collection_name: Name of the collection.

        Returns:
            True if collection is loaded.
        """
        return self._index_manager.is_loaded(collection_name)

    # =========================================================================
    # Vector Operations
    # =========================================================================

    def insert_vectors(
        self,
        collection_name: str,
        data: list[dict[str, Any]],
    ) -> InsertResult:
        """Insert vectors into a collection.

        Args:
            collection_name: Name of the collection.
            data: List of vector records.

        Returns:
            InsertResult with count and IDs.
        """
        request = InsertVectorsRequest(
            collection_name=collection_name,
            data=data,
        )
        return self._vector_manager.insert_vectors(request)

    def insert_vectors_batch(
        self,
        collection_name: str,
        data: list[dict[str, Any]],
        batch_size: int = 1000,
    ) -> InsertResult:
        """Insert vectors in batches.

        Args:
            collection_name: Name of the collection.
            data: List of vector records.
            batch_size: Number of vectors per batch.

        Returns:
            InsertResult with total count and all IDs.
        """
        return self._vector_manager.insert_vectors_batch(
            collection_name=collection_name,
            data=data,
            batch_size=batch_size,
        )

    def upsert_vectors(
        self,
        collection_name: str,
        data: list[dict[str, Any]],
    ) -> UpsertResult:
        """Upsert (insert or update) vectors.

        Args:
            collection_name: Name of the collection.
            data: List of vector records.

        Returns:
            UpsertResult with count and IDs.
        """
        request = UpsertVectorsRequest(
            collection_name=collection_name,
            data=data,
        )
        return self._vector_manager.upsert_vectors(request)

    def delete_vectors(
        self,
        collection_name: str,
        ids: list[str],
    ) -> DeleteResult:
        """Delete vectors by IDs.

        Args:
            collection_name: Name of the collection.
            ids: List of primary keys to delete.

        Returns:
            DeleteResult with count.
        """
        request = DeleteVectorsRequest(
            collection_name=collection_name,
            ids=ids,
        )
        return self._vector_manager.delete_vectors(request)

    def delete_vectors_by_filter(
        self,
        collection_name: str,
        filter_expr: str,
    ) -> DeleteResult:
        """Delete vectors by filter expression.

        Args:
            collection_name: Name of the collection.
            filter_expr: Filter expression.

        Returns:
            DeleteResult with count.
        """
        request = DeleteVectorsByFilterRequest(
            collection_name=collection_name,
            filter_expr=filter_expr,
        )
        return self._vector_manager.delete_vectors_by_filter(request)

    def get_vector(
        self,
        collection_name: str,
        pk: str,
        output_fields: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Get a single vector by primary key.

        Args:
            collection_name: Name of the collection.
            pk: Primary key.
            output_fields: Fields to return.

        Returns:
            Vector data or None if not found.
        """
        request = GetVectorRequest(
            collection_name=collection_name,
            pk=pk,
            output_fields=output_fields,
        )
        return self._vector_manager.get_vector(request)

    def query_vectors(
        self,
        collection_name: str,
        filter_expr: str,
        output_fields: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> QueryResult:
        """Query vectors by filter expression.

        Args:
            collection_name: Name of the collection.
            filter_expr: Filter expression.
            output_fields: Fields to return.
            limit: Maximum number of results.
            offset: Offset for pagination.

        Returns:
            QueryResult with matching items.
        """
        request = QueryRequest(
            collection_name=collection_name,
            filter_expr=filter_expr,
            output_fields=output_fields,
            limit=limit,
            offset=offset,
        )
        return self._vector_manager.query_vectors(request)

    def delete_document_chunks(
        self,
        collection_name: str,
        document_id: str,
    ) -> DeleteResult:
        """Delete all chunks belonging to a document.

        Args:
            collection_name: Name of the collection.
            document_id: PostgreSQL document ID.

        Returns:
            DeleteResult with count.
        """
        filter_expr = f'{FieldName.LT_DOC_ID.value} == "{document_id}"'
        return self.delete_vectors_by_filter(collection_name, filter_expr)

    # =========================================================================
    # Search Operations
    # =========================================================================

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        anns_field: str = FieldName.TEXT_DENSE.value,
        top_k: int = DEFAULT_TOP_K,
        filter_expr: str = "",
        output_fields: list[str] | None = None,
    ) -> SearchResult:
        """Perform vector similarity search.

        Args:
            collection_name: Name of the collection.
            query_vector: Query embedding vector.
            anns_field: Vector field to search.
            top_k: Number of results.
            filter_expr: Optional filter expression.
            output_fields: Fields to return.

        Returns:
            SearchResult with matching items.
        """
        request = SearchRequest(
            collection_name=collection_name,
            query_vector=query_vector,
            anns_field=anns_field,
            top_k=top_k,
            filter_expr=filter_expr,
            output_fields=output_fields,
        )
        return self._search_manager.search(request)

    def hybrid_search(
        self,
        collection_name: str,
        query_text: str,
        query_vectors: dict[str, list[float]],
        top_k: int = DEFAULT_TOP_K,
        filter_expr: str = "",
        output_fields: list[str] | None = None,
        rerank_method: str = "rrf",
        rrf_k: int = 60,
        weights: list[float] | None = None,
    ) -> HybridSearchResult:
        """Perform hybrid search across multiple vector fields.

        Args:
            collection_name: Name of the collection.
            query_text: Original query text.
            query_vectors: Query vectors keyed by field name.
            top_k: Number of results.
            filter_expr: Optional filter expression.
            output_fields: Fields to return.
            rerank_method: Reranking method ("rrf" or "weighted").
            rrf_k: RRF parameter.
            weights: Weights for weighted reranking.

        Returns:
            HybridSearchResult with combined results.
        """
        request = HybridSearchRequest(
            collection_name=collection_name,
            query_text=query_text,
            query_vectors=query_vectors,
            top_k=top_k,
            filter_expr=filter_expr,
            output_fields=output_fields,
            rerank_method=rerank_method,
            rrf_k=rrf_k,
            weights=weights,
        )
        return self._search_manager.hybrid_search(request)

    def search_by_document(
        self,
        collection_name: str,
        document_id: str,
        query_vector: list[float],
        top_k: int = 5,
    ) -> SearchResult:
        """Search within a specific document's chunks.

        Args:
            collection_name: Name of the collection.
            document_id: PostgreSQL document ID.
            query_vector: Query embedding vector.
            top_k: Number of results.

        Returns:
            SearchResult with matching chunks.
        """
        return self._search_manager.search_by_document(
            collection_name=collection_name,
            document_id=document_id,
            query_vector=query_vector,
            top_k=top_k,
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def count_vectors(
        self,
        collection_name: str,
        filter_expr: str = "",
    ) -> int:
        """Count vectors in a collection.

        Args:
            collection_name: Name of the collection.
            filter_expr: Optional filter expression.

        Returns:
            Number of matching vectors.
        """
        return self._vector_manager.count_vectors(collection_name, filter_expr)

    def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Get collection statistics.

        Args:
            collection_name: Name of the collection.

        Returns:
            Dictionary with statistics.
        """
        return self._collection_manager.get_collection_stats(collection_name)

    def health_check(self) -> dict[str, Any]:
        """Perform health check on Milvus connection.

        Returns:
            Dictionary with health status.
        """
        try:
            collections = self.list_collections()
            return {
                "status": "healthy",
                "connected": True,
                "collections_count": len(collections),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
            }
