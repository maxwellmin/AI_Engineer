"""
Index manager for Milvus database controller.

This module provides index management operations including
creation, deletion, and inspection of vector indexes.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from apps.milvus_database_controller.client import MilvusClientWrapper
from apps.milvus_database_controller.constants import (
    FieldName,
    HNSW_INDEX_PARAMS,
    IndexName,
    IndexType,
    MetricType,
    SPARSE_INDEX_PARAMS,
)
from apps.milvus_database_controller.dto import IndexInfo
from apps.milvus_database_controller.exceptions import (
    CollectionNotFoundError,
    IndexCreationError,
    IndexError,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class IndexManager:
    """Manager for Milvus index operations.

    This class handles:
    - Dense vector index creation (HNSW)
    - Sparse vector index creation (BM25)
    - Index deletion and inspection
    - Collection loading/release

    Example:
        >>> manager = IndexManager()
        >>> manager.create_dense_index("documents", "summary_dense")
        >>> manager.load_collection("documents")
    """

    def __init__(self, client: MilvusClientWrapper | None = None) -> None:
        """Initialize the index manager.

        Args:
            client: Optional MilvusClientWrapper instance.
        """
        self._client = client or MilvusClientWrapper.get_instance()

    def create_dense_index(
        self,
        collection_name: str,
        field_name: str,
        index_name: str = "",
        index_params: dict[str, Any] | None = None,
    ) -> bool:
        """Create a dense vector index (HNSW by default).

        Args:
            collection_name: Name of the collection.
            field_name: Name of the vector field.
            index_name: Name of the index. If empty, auto-generated.
            index_params: Custom index parameters. If None, uses default HNSW params.

        Returns:
            True if index created successfully.

        Raises:
            CollectionNotFoundError: If collection does not exist.
            IndexCreationError: If index creation fails.
        """
        # Validate collection exists
        if not self._client.has_collection(collection_name):
            raise CollectionNotFoundError(collection_name)

        # Use default HNSW params if not provided
        if index_params is None:
            index_params = HNSW_INDEX_PARAMS.copy()

        # Auto-generate index name if not provided
        if not index_name:
            index_name = f"{field_name}_index"

        try:
            logger.info(
                f"Creating dense index '{index_name}' on field '{field_name}' "
                f"in collection '{collection_name}'"
            )

            self._client.create_index(
                collection_name=collection_name,
                field_name=field_name,
                index_params=index_params,
                index_name=index_name,
            )

            logger.info(f"Successfully created dense index '{index_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to create dense index: {e}")
            raise IndexCreationError(index_name or field_name, str(e))

    def create_sparse_index(
        self,
        collection_name: str,
        field_name: str = FieldName.TEXT_SPARSE.value,
        index_name: str = "",
        index_params: dict[str, Any] | None = None,
    ) -> bool:
        """Create a sparse vector index for BM25 search.

        Args:
            collection_name: Name of the collection.
            field_name: Name of the sparse vector field.
            index_name: Name of the index.
            index_params: Custom index parameters.

        Returns:
            True if index created successfully.
        """
        if not self._client.has_collection(collection_name):
            raise CollectionNotFoundError(collection_name)

        if index_params is None:
            index_params = SPARSE_INDEX_PARAMS.copy()

        if not index_name:
            index_name = IndexName.TEXT_SPARSE.value

        try:
            logger.info(
                f"Creating sparse index '{index_name}' on field '{field_name}' "
                f"in collection '{collection_name}'"
            )

            self._client.create_index(
                collection_name=collection_name,
                field_name=field_name,
                index_params=index_params,
                index_name=index_name,
            )

            logger.info(f"Successfully created sparse index '{index_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to create sparse index: {e}")
            raise IndexCreationError(index_name or field_name, str(e))

    def create_all_indexes(
        self,
        collection_name: str,
        dense_index_params: dict[str, Any] | None = None,
        sparse_index_params: dict[str, Any] | None = None,
    ) -> dict[str, bool]:
        """Create all indexes for a collection.

        This creates:
        - HNSW index for summary_dense field
        - HNSW index for text_dense field
        - BM25 sparse index for text_sparse field (Milvus 2.5+)

        Args:
            collection_name: Name of the collection.
            dense_index_params: Parameters for dense indexes.
            sparse_index_params: Parameters for sparse index.

        Returns:
            Dictionary mapping index names to creation status.
        """
        results: dict[str, bool] = {}

        # Create dense indexes
        for field_name in [FieldName.SUMMARY_DENSE.value, FieldName.TEXT_DENSE.value]:
            index_name = f"{field_name}_index"
            try:
                results[index_name] = self.create_dense_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    index_name=index_name,
                    index_params=dense_index_params,
                )
            except Exception as e:
                logger.warning(f"Failed to create index '{index_name}': {e}")
                results[index_name] = False

        # Create sparse index for BM25 search (Milvus 2.5+)
        try:
            results[IndexName.TEXT_SPARSE.value] = self.create_sparse_index(
                collection_name=collection_name,
                index_params=sparse_index_params,
            )
        except Exception as e:
            logger.warning(f"Failed to create sparse index: {e}")
            results[IndexName.TEXT_SPARSE.value] = False

        return results

    def list_indexes(self, collection_name: str) -> list[str]:
        """List all indexes in a collection.

        Args:
            collection_name: Name of the collection.

        Returns:
            List of index names.
        """
        if not self._client.has_collection(collection_name):
            raise CollectionNotFoundError(collection_name)

        try:
            return self._client.list_indexes(collection_name)
        except Exception as e:
            logger.error(f"Failed to list indexes: {e}")
            raise

    def drop_index(self, collection_name: str, index_name: str) -> bool:
        """Drop an index.

        Args:
            collection_name: Name of the collection.
            index_name: Name of the index.

        Returns:
            True if index dropped successfully.
        """
        if not self._client.has_collection(collection_name):
            raise CollectionNotFoundError(collection_name)

        try:
            self._client.drop_index(collection_name, index_name)
            logger.info(f"Dropped index '{index_name}' from '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to drop index '{index_name}': {e}")
            raise

    def load_collection(self, collection_name: str) -> bool:
        """Load a collection into memory for search.

        Args:
            collection_name: Name of the collection.

        Returns:
            True if collection loaded successfully.
        """
        if not self._client.has_collection(collection_name):
            raise CollectionNotFoundError(collection_name)

        try:
            self._client.load_collection(collection_name)
            logger.info(f"Loaded collection '{collection_name}' into memory")
            return True
        except Exception as e:
            logger.error(f"Failed to load collection: {e}")
            raise

    def release_collection(self, collection_name: str) -> bool:
        """Release a collection from memory.

        Args:
            collection_name: Name of the collection.

        Returns:
            True if collection released successfully.
        """
        if not self._client.has_collection(collection_name):
            raise CollectionNotFoundError(collection_name)

        try:
            self._client.release_collection(collection_name)
            logger.info(f"Released collection '{collection_name}' from memory")
            return True
        except Exception as e:
            logger.error(f"Failed to release collection: {e}")
            raise

    def get_load_state(self, collection_name: str) -> str:
        """Get the load state of a collection.

        Args:
            collection_name: Name of the collection.

        Returns:
            Load state string (Loaded, Loading, NotLoad).
        """
        try:
            return self._client.get_load_state(collection_name)
        except Exception as e:
            logger.error(f"Failed to get load state: {e}")
            raise

    def is_loaded(self, collection_name: str) -> bool:
        """Check if a collection is loaded into memory.

        Args:
            collection_name: Name of the collection.

        Returns:
            True if collection is loaded.
        """
        return self.get_load_state(collection_name) == "Loaded"

    def ensure_loaded(self, collection_name: str) -> bool:
        """Ensure a collection is loaded into memory.

        Args:
            collection_name: Name of the collection.

        Returns:
            True if collection is loaded.
        """
        if self.is_loaded(collection_name):
            return True
        return self.load_collection(collection_name)

    def get_index_info(
        self,
        collection_name: str,
        index_name: str,
    ) -> IndexInfo:
        """Get information about an index.

        Args:
            collection_name: Name of the collection.
            index_name: Name of the index.

        Returns:
            IndexInfo with index details.
        """
        if not self._client.has_collection(collection_name):
            raise CollectionNotFoundError(collection_name)

        try:
            # Get collection description which includes index info
            info = self._client.describe_collection(collection_name)

            # Parse index information
            indexes = info.get("indexes", [])
            for idx in indexes:
                if idx.get("index_name") == index_name:
                    return IndexInfo(
                        index_name=index_name,
                        field_name=idx.get("field_name", ""),
                        index_type=idx.get("index_type", ""),
                        metric_type=idx.get("metric_type", ""),
                        params=idx.get("params", {}),
                    )

            raise IndexError(index_name, f"Index '{index_name}' not found")

        except IndexError:
            raise
        except Exception as e:
            logger.error(f"Failed to get index info: {e}")
            raise
