"""
Vector manager for Milvus database controller.

This module provides vector CRUD operations including
insertion, upsertion, deletion, and retrieval.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from apps.milvus_database_controller.client import MilvusClientWrapper
from apps.milvus_database_controller.constants import (
    DEFAULT_BATCH_SIZE,
    FieldName,
)
from apps.milvus_database_controller.dto import (
    DeleteResult,
    DeleteVectorsByFilterRequest,
    DeleteVectorsRequest,
    GetVectorRequest,
    InsertResult,
    InsertVectorsRequest,
    QueryRequest,
    QueryResult,
    UpsertResult,
    UpsertVectorsRequest,
    VectorRecord,
)
from apps.milvus_database_controller.exceptions import (
    CollectionNotFoundError,
    InvalidVectorDataError,
    InvalidVectorDimensionError,
    VectorDeleteError,
    VectorInsertError,
    VectorUpsertError,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class VectorManager:
    """Manager for Milvus vector CRUD operations.

    This class handles:
    - Batch vector insertion
    - Vector upsertion (insert or update)
    - Vector deletion by ID or filter
    - Vector retrieval by ID or filter

    Example:
        >>> manager = VectorManager()
        >>> result = manager.insert_vectors("documents", [vector_data])
        >>> manager.delete_vectors("documents", ["id1", "id2"])
    """

    def __init__(self, client: MilvusClientWrapper | None = None) -> None:
        """Initialize the vector manager.

        Args:
            client: Optional MilvusClientWrapper instance.
        """
        self._client = client or MilvusClientWrapper.get_instance()

    def _validate_collection(self, collection_name: str) -> None:
        """Validate that collection exists.

        Args:
            collection_name: Name of the collection.

        Raises:
            CollectionNotFoundError: If collection does not exist.
        """
        if not self._client.has_collection(collection_name):
            raise CollectionNotFoundError(collection_name)

    def _validate_vector_data(
        self,
        data: list[dict[str, Any]],
        expected_dimension: int = 1536,
    ) -> None:
        """Validate vector data before insertion.

        Args:
            data: List of vector records.
            expected_dimension: Expected vector dimension.

        Raises:
            InvalidVectorDataError: If data is invalid.
            InvalidVectorDimensionError: If vector dimension is wrong.
        """
        if not data:
            raise InvalidVectorDataError("Empty data list")

        for i, record in enumerate(data):
            # Check required fields
            if FieldName.PK.value not in record:
                raise InvalidVectorDataError(f"Record {i} missing primary key 'pk'")

            # Check dense vector dimensions
            for field in [FieldName.SUMMARY_DENSE.value, FieldName.TEXT_DENSE.value]:
                if field in record:
                    vector = record[field]
                    if isinstance(vector, list) and len(vector) != expected_dimension:
                        raise InvalidVectorDimensionError(
                            expected=expected_dimension,
                            actual=len(vector),
                            field_name=field,
                        )

    def insert_vectors(self, request: InsertVectorsRequest) -> InsertResult:
        """Insert vectors into a collection.

        Args:
            request: Insert request with collection name and data.

        Returns:
            InsertResult with count and IDs.

        Raises:
            CollectionNotFoundError: If collection does not exist.
            VectorInsertError: If insertion fails.
        """
        self._validate_collection(request.collection_name)
        self._validate_vector_data(request.data)

        try:
            logger.info(
                f"Inserting {len(request.data)} vectors into '{request.collection_name}'"
            )

            result = self._client.insert(
                collection_name=request.collection_name,
                data=request.data,
            )

            inserted_ids = result.get("ids", [])
            # Convert IDs to strings if needed
            inserted_ids = [str(id_) for id_ in inserted_ids]

            logger.info(f"Successfully inserted {len(inserted_ids)} vectors")

            return InsertResult(
                inserted_count=len(inserted_ids),
                inserted_ids=inserted_ids,
            )

        except Exception as e:
            logger.error(f"Failed to insert vectors: {e}")
            raise VectorInsertError(
                reason=str(e),
                count=len(request.data),
            )

    def insert_vectors_batch(
        self,
        collection_name: str,
        data: list[dict[str, Any]],
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> InsertResult:
        """Insert vectors in batches for large datasets.

        Args:
            collection_name: Name of the collection.
            data: List of vector records.
            batch_size: Number of vectors per batch.

        Returns:
            InsertResult with total count and all IDs.
        """
        self._validate_collection(collection_name)
        self._validate_vector_data(data)

        all_ids: list[str] = []
        total_inserted = 0

        for i in range(0, len(data), batch_size):
            batch = data[i : i + batch_size]
            result = self.insert_vectors(
                InsertVectorsRequest(
                    collection_name=collection_name,
                    data=batch,
                )
            )
            all_ids.extend(result.inserted_ids)
            total_inserted += result.inserted_count

        return InsertResult(
            inserted_count=total_inserted,
            inserted_ids=all_ids,
        )

    def upsert_vectors(self, request: UpsertVectorsRequest) -> UpsertResult:
        """Upsert (insert or update) vectors.

        Args:
            request: Upsert request with collection name and data.

        Returns:
            UpsertResult with count and IDs.
        """
        self._validate_collection(request.collection_name)
        self._validate_vector_data(request.data)

        try:
            logger.info(
                f"Upserting {len(request.data)} vectors into '{request.collection_name}'"
            )

            result = self._client.upsert(
                collection_name=request.collection_name,
                data=request.data,
            )

            upserted_ids = result.get("ids", [])
            upserted_ids = [str(id_) for id_ in upserted_ids]

            logger.info(f"Successfully upserted {len(upserted_ids)} vectors")

            return UpsertResult(
                upserted_count=len(upserted_ids),
                upserted_ids=upserted_ids,
            )

        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            raise VectorUpsertError(
                reason=str(e),
                count=len(request.data),
            )

    def delete_vectors(self, request: DeleteVectorsRequest) -> DeleteResult:
        """Delete vectors by primary key IDs.

        Args:
            request: Delete request with collection name and IDs.

        Returns:
            DeleteResult with count.
        """
        self._validate_collection(request.collection_name)

        try:
            logger.info(
                f"Deleting {len(request.ids)} vectors from '{request.collection_name}'"
            )

            result = self._client.delete(
                collection_name=request.collection_name,
                ids=request.ids,
            )

            # Get delete count from result
            deleted_count = len(request.ids)

            logger.info(f"Successfully deleted {deleted_count} vectors")

            return DeleteResult(deleted_count=deleted_count)

        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            raise VectorDeleteError(
                reason=str(e),
                count=len(request.ids),
            )

    def delete_vectors_by_filter(
        self,
        request: DeleteVectorsByFilterRequest,
    ) -> DeleteResult:
        """Delete vectors by filter expression.

        Args:
            request: Delete request with collection name and filter.

        Returns:
            DeleteResult with count.
        """
        self._validate_collection(request.collection_name)

        try:
            logger.info(
                f"Deleting vectors from '{request.collection_name}' "
                f"with filter: {request.filter_expr}"
            )

            result = self._client.delete(
                collection_name=request.collection_name,
                filter_expr=request.filter_expr,
            )

            # Note: Actual count may not be available from delete result
            deleted_count = 0

            logger.info("Successfully deleted vectors by filter")

            return DeleteResult(deleted_count=deleted_count)

        except Exception as e:
            logger.error(f"Failed to delete vectors by filter: {e}")
            raise VectorDeleteError(reason=str(e))

    def get_vector(self, request: GetVectorRequest) -> dict[str, Any] | None:
        """Get a single vector by primary key.

        Args:
            request: Get request with collection name and PK.

        Returns:
            Vector data dictionary or None if not found.
        """
        self._validate_collection(request.collection_name)

        try:
            output_fields = request.output_fields or [
                FieldName.TEXT.value,
                FieldName.SUMMARY.value,
                FieldName.DOCUMENT.value,
                FieldName.SOURCE.value,
                FieldName.SOURCE_NAME.value,
                FieldName.LT_DOC_ID.value,
                FieldName.CHUNK_ID.value,
            ]

            result = self._client.get(
                collection_name=request.collection_name,
                ids=[request.pk],
                output_fields=output_fields,
            )

            if result and len(result) > 0:
                return result[0]
            return None

        except Exception as e:
            logger.error(f"Failed to get vector: {e}")
            raise

    def query_vectors(self, request: QueryRequest) -> QueryResult:
        """Query vectors by filter expression.

        Args:
            request: Query request with filter and output fields.

        Returns:
            QueryResult with matching items.
        """
        self._validate_collection(request.collection_name)

        try:
            output_fields = request.output_fields or [
                FieldName.PK.value,
                FieldName.TEXT.value,
                FieldName.SUMMARY.value,
                FieldName.SOURCE.value,
                FieldName.LT_DOC_ID.value,
            ]

            result = self._client.query(
                collection_name=request.collection_name,
                filter_expr=request.filter_expr,
                output_fields=output_fields,
                limit=request.limit,
                offset=request.offset,
            )

            return QueryResult(
                items=result,
                total=len(result),
            )

        except Exception as e:
            logger.error(f"Failed to query vectors: {e}")
            raise

    def query_by_document_id(
        self,
        collection_name: str,
        document_id: str,
        output_fields: list[str] | None = None,
    ) -> QueryResult:
        """Query all chunks belonging to a document.

        Args:
            collection_name: Name of the collection.
            document_id: PostgreSQL document ID.
            output_fields: Fields to return.

        Returns:
            QueryResult with document chunks.
        """
        filter_expr = f'{FieldName.LT_DOC_ID.value} == "{document_id}"'

        return self.query_vectors(
            QueryRequest(
                collection_name=collection_name,
                filter_expr=filter_expr,
                output_fields=output_fields,
                limit=10000,  # Adjust as needed
            )
        )

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
        self._validate_collection(collection_name)

        try:
            if filter_expr:
                result = self._client.query(
                    collection_name=collection_name,
                    filter_expr=filter_expr,
                    output_fields=["count(*)"],
                )
                # Parse count from result
                return result[0].get("count(*)", 0) if result else 0
            else:
                stats = self._client.get_collection_stats(collection_name)
                return stats.get("row_count", 0)

        except Exception as e:
            logger.error(f"Failed to count vectors: {e}")
            raise
