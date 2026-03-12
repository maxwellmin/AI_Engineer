"""
Milvus client wrapper with connection management.

This module provides a singleton MilvusClient wrapper that manages connections
to the Milvus server and provides a thread-safe interface for all Milvus operations.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any

from django.conf import settings
from pymilvus import MilvusClient as PyMilvusClient
from pymilvus import AnnSearchRequest, RRFRanker, WeightedRanker
from pymilvus import exceptions as milvus_exceptions

from apps.milvus_database_controller.constants import (
    DEFAULT_SEARCH_TIMEOUT,
)
from apps.milvus_database_controller.exceptions import (
    CollectionNotFoundError,
    ConfigurationError,
    MilvusConnectionError,
    MilvusConnectionTimeoutError,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class MilvusClientWrapper:
    """Singleton wrapper for MilvusClient with connection management.

    This class provides:
    - Singleton pattern for connection reuse
    - Thread-safe client access
    - Automatic reconnection on failure
    - Configuration from Django settings

    Example:
        >>> client = MilvusClientWrapper.get_instance()
        >>> collections = client.list_collections()
    """

    _instance: MilvusClientWrapper | None = None
    _lock: threading.Lock = threading.Lock()
    _client: PyMilvusClient | None = None

    def __new__(cls) -> MilvusClientWrapper:
        """Create or return the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the MilvusClient wrapper."""
        # Only initialize once
        if not hasattr(self, "_initialized"):
            self._initialized = False
            self._config = self._load_config()
            self._initialized = True

    @classmethod
    def get_instance(cls) -> MilvusClientWrapper:
        """Get the singleton instance of MilvusClientWrapper.

        Returns:
            The singleton MilvusClientWrapper instance.
        """
        return cls()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance.

        This is useful for testing or when reconnecting with new configuration.
        """
        with cls._lock:
            if cls._instance is not None:
                try:
                    if cls._instance._client is not None:
                        cls._instance._client.close()
                except Exception as e:
                    logger.warning(f"Error closing Milvus client: {e}")
                finally:
                    cls._instance._client = None
            cls._instance = None

    def _load_config(self) -> dict[str, Any]:
        """Load Milvus configuration from Django settings.

        Returns:
            Dictionary containing Milvus configuration.

        Raises:
            ConfigurationError: If required configuration is missing.
        """
        milvus_config = getattr(settings, "MILVUS_CONFIG", {})

        # Get connection settings
        host = milvus_config.get("host", settings.MILVUS_HOST)
        port = milvus_config.get("port", settings.MILVUS_PORT)

        # Build URI
        uri = milvus_config.get("uri")
        if not uri:
            uri = f"http://{host}:{port}"

        # Get token (optional)
        token = milvus_config.get("token", getattr(settings, "MILVUS_TOKEN", ""))

        config = {
            "uri": uri,
            "token": token,
            "host": host,
            "port": port,
            "timeout": milvus_config.get("timeout", DEFAULT_SEARCH_TIMEOUT),
        }

        logger.debug(f"Loaded Milvus configuration: uri={uri}, timeout={config['timeout']}")
        return config

    def _get_client(self) -> PyMilvusClient:
        """Get or create the underlying MilvusClient.

        Returns:
            PyMilvusClient instance.

        Raises:
            MilvusConnectionError: If connection fails.
        """
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._connect()
        return self._client

    def _connect(self) -> None:
        """Establish connection to Milvus server.

        Raises:
            MilvusConnectionError: If connection fails.
            MilvusConnectionTimeoutError: If connection times out.
        """
        try:
            logger.info(f"Connecting to Milvus server at {self._config['uri']}")
            self._client = PyMilvusClient(
                uri=self._config["uri"],
                token=self._config.get("token", ""),
                timeout=self._config.get("timeout", DEFAULT_SEARCH_TIMEOUT),
            )
            logger.info("Successfully connected to Milvus server")
        except milvus_exceptions.MilvusException as e:
            error_msg = str(e)
            logger.error(f"Failed to connect to Milvus: {error_msg}")
            if "timeout" in error_msg.lower():
                raise MilvusConnectionTimeoutError(
                    timeout=self._config.get("timeout", DEFAULT_SEARCH_TIMEOUT)
                )
            raise MilvusConnectionError(reason=error_msg)
        except Exception as e:
            logger.error(f"Unexpected error connecting to Milvus: {e}")
            raise MilvusConnectionError(reason=str(e))

    def _ensure_connected(self) -> None:
        """Ensure connection to Milvus server.

        Raises:
            MilvusConnectionError: If connection fails.
        """
        self._get_client()

    def reconnect(self) -> bool:
        """Reconnect to Milvus server.

        Returns:
            True if reconnection successful, False otherwise.
        """
        logger.info("Attempting to reconnect to Milvus server")
        self.close()
        try:
            self._connect()
            return True
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            return False

    def close(self) -> None:
        """Close the connection to Milvus server."""
        if self._client is not None:
            try:
                self._client.close()
                logger.info("Closed connection to Milvus server")
            except Exception as e:
                logger.warning(f"Error closing Milvus connection: {e}")
            finally:
                self._client = None

    # =========================================================================
    # Collection Operations
    # =========================================================================

    def create_collection(
        self,
        collection_name: str,
        dimension: int = 1536,
        schema: Any | None = None,
        **kwargs: Any,
    ) -> bool:
        """Create a new collection.

        Args:
            collection_name: Name of the collection.
            dimension: Dimension of dense vectors (used only if schema is None).
            schema: Optional CollectionSchema for custom schema.
            **kwargs: Additional collection parameters.

        Returns:
            True if collection created successfully.
        """
        self._ensure_connected()
        try:
            if schema is not None:
                # Create with custom schema
                self._get_client().create_collection(
                    collection_name=collection_name,
                    schema=schema,
                    **kwargs,
                )
            else:
                # Create with simple API (single vector field)
                self._get_client().create_collection(
                    collection_name=collection_name,
                    dimension=dimension,
                    **kwargs,
                )
            logger.info(f"Created collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection '{collection_name}': {e}")
            raise

    def has_collection(self, collection_name: str) -> bool:
        """Check if a collection exists.

        Args:
            collection_name: Name of the collection.

        Returns:
            True if collection exists.
        """
        self._ensure_connected()
        try:
            return self._get_client().has_collection(collection_name)
        except Exception as e:
            logger.error(f"Failed to check collection '{collection_name}': {e}")
            raise

    def list_collections(self) -> list[str]:
        """List all collections.

        Returns:
            List of collection names.
        """
        self._ensure_connected()
        try:
            return self._get_client().list_collections()
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise

    def drop_collection(self, collection_name: str) -> bool:
        """Drop a collection.

        Args:
            collection_name: Name of the collection to drop.

        Returns:
            True if collection dropped successfully.
        """
        self._ensure_connected()
        try:
            self._get_client().drop_collection(collection_name)
            logger.info(f"Dropped collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to drop collection '{collection_name}': {e}")
            raise

    def describe_collection(self, collection_name: str) -> dict[str, Any]:
        """Get collection description.

        Args:
            collection_name: Name of the collection.

        Returns:
            Collection description dictionary.
        """
        self._ensure_connected()
        try:
            return self._get_client().describe_collection(collection_name)
        except milvus_exceptions.MilvusException as e:
            if "not found" in str(e).lower() or "doesn't exist" in str(e).lower():
                raise CollectionNotFoundError(collection_name)
            logger.error(f"Failed to describe collection '{collection_name}': {e}")
            raise

    # =========================================================================
    # Index Operations
    # =========================================================================

    def create_index(
        self,
        collection_name: str,
        field_name: str,
        index_params: dict[str, Any],
        index_name: str = "",
        **kwargs: Any,
    ) -> bool:
        """Create an index on a vector field.

        Args:
            collection_name: Name of the collection.
            field_name: Name of the vector field.
            index_params: Index parameters dict containing:
                - metric_type: Similarity metric (e.g., "COSINE", "L2", "IP")
                - index_type: Index type (e.g., "HNSW", "IVF_FLAT")
                - params: Additional index parameters
            index_name: Name of the index.
            **kwargs: Additional parameters.

        Returns:
            True if index created successfully.
        """
        self._ensure_connected()
        try:
            from pymilvus.milvus_client.index import IndexParams as MilvusIndexParams

            # Build IndexParams object from dict
            milvus_index_params = MilvusIndexParams()
            milvus_index_params.add_index(
                field_name=field_name,
                index_name=index_name,
                index_type=index_params.get("index_type", ""),
                metric_type=index_params.get("metric_type", "COSINE"),
                params=index_params.get("params", {}),
            )

            self._get_client().create_index(
                collection_name=collection_name,
                index_params=milvus_index_params,
                **kwargs,
            )
            logger.info(f"Created index on '{field_name}' in '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to create index on '{field_name}': {e}")
            raise

    def list_indexes(self, collection_name: str) -> list[str]:
        """List all indexes in a collection.

        Args:
            collection_name: Name of the collection.

        Returns:
            List of index names.
        """
        self._ensure_connected()
        try:
            return self._get_client().list_indexes(collection_name)
        except Exception as e:
            logger.error(f"Failed to list indexes for '{collection_name}': {e}")
            raise

    def drop_index(
        self,
        collection_name: str,
        index_name: str,
    ) -> bool:
        """Drop an index.

        Args:
            collection_name: Name of the collection.
            index_name: Name of the index.

        Returns:
            True if index dropped successfully.
        """
        self._ensure_connected()
        try:
            self._get_client().drop_index(
                collection_name=collection_name,
                index_name=index_name,
            )
            logger.info(f"Dropped index '{index_name}' from '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to drop index '{index_name}': {e}")
            raise

    # =========================================================================
    # Collection Load/Release Operations
    # =========================================================================

    def load_collection(self, collection_name: str) -> bool:
        """Load a collection into memory.

        Args:
            collection_name: Name of the collection.

        Returns:
            True if collection loaded successfully.
        """
        self._ensure_connected()
        try:
            self._get_client().load_collection(collection_name)
            logger.info(f"Loaded collection '{collection_name}' into memory")
            return True
        except Exception as e:
            logger.error(f"Failed to load collection '{collection_name}': {e}")
            raise

    def release_collection(self, collection_name: str) -> bool:
        """Release a collection from memory.

        Args:
            collection_name: Name of the collection.

        Returns:
            True if collection released successfully.
        """
        self._ensure_connected()
        try:
            self._get_client().release_collection(collection_name)
            logger.info(f"Released collection '{collection_name}' from memory")
            return True
        except Exception as e:
            logger.error(f"Failed to release collection '{collection_name}': {e}")
            raise

    def get_load_state(self, collection_name: str) -> str:
        """Get the load state of a collection.

        Args:
            collection_name: Name of the collection.

        Returns:
            Load state string ("Loaded", "Loading", or "NotLoad").
        """
        self._ensure_connected()
        try:
            result = self._get_client().get_load_state(collection_name)
            state = result.get("state", None)
            if state is None:
                return "NotLoad"
            # Convert LoadState enum to string
            return str(state).replace("LoadState.", "")
        except Exception as e:
            logger.error(f"Failed to get load state for '{collection_name}': {e}")
            raise

    # =========================================================================
    # Vector CRUD Operations
    # =========================================================================

    def insert(
        self,
        collection_name: str,
        data: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Insert vectors into a collection.

        Args:
            collection_name: Name of the collection.
            data: List of vector records.
            **kwargs: Additional parameters.

        Returns:
            Insert result with IDs.
        """
        self._ensure_connected()
        try:
            result = self._get_client().insert(
                collection_name=collection_name,
                data=data,
                **kwargs,
            )
            logger.debug(f"Inserted {len(data)} vectors into '{collection_name}'")
            return result
        except Exception as e:
            logger.error(f"Failed to insert vectors into '{collection_name}': {e}")
            raise

    def upsert(
        self,
        collection_name: str,
        data: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Upsert vectors into a collection.

        Args:
            collection_name: Name of the collection.
            data: List of vector records.
            **kwargs: Additional parameters.

        Returns:
            Upsert result with IDs.
        """
        self._ensure_connected()
        try:
            result = self._get_client().upsert(
                collection_name=collection_name,
                data=data,
                **kwargs,
            )
            logger.debug(f"Upserted {len(data)} vectors into '{collection_name}'")
            return result
        except Exception as e:
            logger.error(f"Failed to upsert vectors into '{collection_name}': {e}")
            raise

    def delete(
        self,
        collection_name: str,
        ids: list[str] | None = None,
        filter_expr: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Delete vectors from a collection.

        Args:
            collection_name: Name of the collection.
            ids: List of primary keys to delete.
            filter_expr: Filter expression for deletion.
            **kwargs: Additional parameters.

        Returns:
            Delete result.
        """
        self._ensure_connected()
        try:
            if ids:
                result = self._get_client().delete(
                    collection_name=collection_name,
                    ids=ids,
                    **kwargs,
                )
            else:
                result = self._get_client().delete(
                    collection_name=collection_name,
                    filter=filter_expr,
                    **kwargs,
                )
            logger.debug(f"Deleted vectors from '{collection_name}'")
            return result
        except Exception as e:
            logger.error(f"Failed to delete vectors from '{collection_name}': {e}")
            raise

    # =========================================================================
    # Search Operations
    # =========================================================================

    def search(
        self,
        collection_name: str,
        data: list[list[float]],
        anns_field: str,
        limit: int = 10,
        filter_expr: str = "",
        output_fields: list[str] | None = None,
        search_params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[list[dict[str, Any]]]:
        """Search for similar vectors.

        Args:
            collection_name: Name of the collection.
            data: Query vectors.
            anns_field: Vector field to search.
            limit: Number of results per query.
            filter_expr: Filter expression.
            output_fields: Fields to return.
            search_params: Search parameters.
            **kwargs: Additional parameters.

        Returns:
            Search results.
        """
        self._ensure_connected()
        try:
            result = self._get_client().search(
                collection_name=collection_name,
                data=data,
                anns_field=anns_field,
                limit=limit,
                filter=filter_expr if filter_expr else None,
                output_fields=output_fields,
                search_params=search_params,
                **kwargs,
            )
            return result
        except Exception as e:
            logger.error(f"Search failed in '{collection_name}': {e}")
            raise

    def query(
        self,
        collection_name: str,
        filter_expr: str,
        output_fields: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Query vectors by filter expression.

        Args:
            collection_name: Name of the collection.
            filter_expr: Filter expression.
            output_fields: Fields to return.
            limit: Maximum number of results.
            offset: Offset for pagination.
            **kwargs: Additional parameters.

        Returns:
            Query results.
        """
        self._ensure_connected()
        try:
            result = self._get_client().query(
                collection_name=collection_name,
                filter=filter_expr,
                output_fields=output_fields,
                limit=limit,
                offset=offset,
                **kwargs,
            )
            return result
        except Exception as e:
            logger.error(f"Query failed in '{collection_name}': {e}")
            raise

    def get(
        self,
        collection_name: str,
        ids: list[str],
        output_fields: list[str] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Get vectors by IDs.

        Args:
            collection_name: Name of the collection.
            ids: List of primary keys.
            output_fields: Fields to return.
            **kwargs: Additional parameters.

        Returns:
            Retrieved vectors.
        """
        self._ensure_connected()
        try:
            result = self._get_client().get(
                collection_name=collection_name,
                ids=ids,
                output_fields=output_fields,
                **kwargs,
            )
            return result
        except Exception as e:
            logger.error(f"Get failed in '{collection_name}': {e}")
            raise

    def hybrid_search(
        self,
        collection_name: str,
        reqs: list[AnnSearchRequest],
        ranker: RRFRanker | WeightedRanker,
        limit: int = 10,
        output_fields: list[str] | None = None,
        **kwargs: Any,
    ) -> list[list[dict[str, Any]]]:
        """Perform hybrid search across multiple vector fields.

        This method supports dense + sparse hybrid search using Milvus 2.5+ API.

        Args:
            collection_name: Name of the collection.
            reqs: List of AnnSearchRequest objects for each vector field.
                - For dense vectors: AnnSearchRequest(data=[dense_vector], anns_field="text_dense", ...)
                - For BM25/sparse: AnnSearchRequest(data=[query_text], anns_field="text_sparse", ...)
            ranker: Ranker for result fusion (RRFRanker or WeightedRanker).
            limit: Number of results to return.
            output_fields: Fields to return.
            **kwargs: Additional parameters.

        Returns:
            Hybrid search results.

        Example:
            >>> from pymilvus import AnnSearchRequest, RRFRanker
            >>> # Dense search request
            >>> dense_req = AnnSearchRequest(
            ...     data=[dense_vector],
            ...     anns_field="text_dense",
            ...     param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            ...     limit=10
            ... )
            >>> # BM25 search request (pass query text directly)
            >>> sparse_req = AnnSearchRequest(
            ...     data=[query_text],
            ...     anns_field="text_sparse",
            ...     param={"metric_type": "BM25"},
            ...     limit=10
            ... )
            >>> # RRF fusion
            >>> ranker = RRFRanker(k=100)
            >>> results = client.hybrid_search(
            ...     collection_name="documents",
            ...     reqs=[dense_req, sparse_req],
            ...     ranker=ranker,
            ...     limit=10
            ... )
        """
        self._ensure_connected()
        try:
            result = self._get_client().hybrid_search(
                collection_name=collection_name,
                reqs=reqs,
                ranker=ranker,
                limit=limit,
                output_fields=output_fields,
                **kwargs,
            )
            logger.debug(
                f"Hybrid search in '{collection_name}' with {len(reqs)} requests"
            )
            return result
        except Exception as e:
            logger.error(f"Hybrid search failed in '{collection_name}': {e}")
            raise

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Get collection statistics.

        Args:
            collection_name: Name of the collection.

        Returns:
            Collection statistics.
        """
        self._ensure_connected()
        try:
            return self._get_client().get_collection_stats(collection_name)
        except Exception as e:
            logger.error(f"Failed to get stats for '{collection_name}': {e}")
            raise

    @property
    def config(self) -> dict[str, Any]:
        """Get current configuration."""
        return self._config.copy()

    def __enter__(self) -> MilvusClientWrapper:
        """Context manager entry."""
        self._ensure_connected()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        # Don't close connection on exit - maintain singleton
        pass
