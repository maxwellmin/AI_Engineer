"""
Collection manager for Milvus database controller.

This module provides collection lifecycle management including
creation, deletion, and inspection of Milvus collections.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from apps.milvus_database_controller.client import MilvusClientWrapper
from apps.milvus_database_controller.constants import (
    COLLECTION_CHAT_HISTORY,
    COLLECTION_DOCUMENTS,
    DEFAULT_DENSE_DIMENSION,
    FieldName,
)
from apps.milvus_database_controller.dto import CollectionInfo, CreateCollectionRequest
from apps.milvus_database_controller.exceptions import (
    CollectionAlreadyExistsError,
    CollectionCreationError,
    CollectionNotFoundError,
)
from apps.milvus_database_controller.schemas.collection_schema import (
    ChatHistoryCollectionSchema,
    DocumentCollectionSchema,
    get_chat_history_collection_schema,
    get_document_collection_schema,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class CollectionManager:
    """Manager for Milvus collection operations.

    This class handles:
    - Collection creation with proper schema
    - Collection deletion
    - Collection inspection and listing
    - Collection loading into memory

    Example:
        >>> manager = CollectionManager()
        >>> manager.create_collection("documents", dimension=1536)
        >>> collections = manager.list_collections()
    """

    def __init__(self, client: MilvusClientWrapper | None = None) -> None:
        """Initialize the collection manager.

        Args:
            client: Optional MilvusClientWrapper instance. If not provided,
                   the singleton instance will be used.
        """
        self._client = client or MilvusClientWrapper.get_instance()

    def create_collection(
        self,
        request: CreateCollectionRequest,
        schema: DocumentCollectionSchema | ChatHistoryCollectionSchema | None = None,
    ) -> bool:
        """Create a new collection with the specified schema.

        Args:
            request: Collection creation request.
            schema: Optional custom schema. If not provided, uses default
                   DocumentCollectionSchema.

        Returns:
            True if collection created successfully.

        Raises:
            CollectionAlreadyExistsError: If collection already exists.
            CollectionCreationError: If creation fails.
        """
        collection_name = request.collection_name

        # Use provided schema or create default based on collection name
        if schema is None:
            if collection_name == COLLECTION_CHAT_HISTORY:
                schema = get_chat_history_collection_schema(
                    dimension=request.dimension,
                    enable_dynamic_field=request.enable_dynamic_field,
                )
            else:
                schema = get_document_collection_schema(
                    dimension=request.dimension,
                    enable_dynamic_field=request.enable_dynamic_field,
                )

        try:
            logger.info(f"Creating collection '{collection_name}' with dimension {request.dimension}")

            # Use create_collection_with_schema for full schema support
            # Note: has_collection check is done inside create_collection_with_schema
            self.create_collection_with_schema(
                collection_name=collection_name,
                schema=schema,
                description=request.description,
            )

            logger.info(f"Successfully created collection '{collection_name}'")
            return True

        except CollectionAlreadyExistsError:
            raise
        except Exception as e:
            logger.error(f"Failed to create collection '{collection_name}': {e}")
            raise CollectionCreationError(collection_name, str(e))

    def create_collection_with_schema(
        self,
        collection_name: str,
        schema: DocumentCollectionSchema | ChatHistoryCollectionSchema,
        description: str = "",
    ) -> bool:
        """Create a collection with a custom schema.

        This method creates a collection with full control over the schema,
        including multi-vector fields and BM25 sparse vectors.

        Args:
            collection_name: Name of the collection.
            schema: Schema definition.
            description: Collection description.

        Returns:
            True if collection created successfully.
        """
        if self.has_collection(collection_name):
            raise CollectionAlreadyExistsError(collection_name)

        try:
            # Use pymilvus CollectionSchema for complex schemas
            from pymilvus import CollectionSchema, FieldSchema, Function, FunctionType

            from apps.milvus_database_controller.constants import (
                DEFAULT_BM25_B,
                DEFAULT_BM25_K1,
            )

            fields = []
            for field_def in schema.fields:
                field_kwargs: dict[str, Any] = {
                    "name": field_def.name,
                    "dtype": field_def.dtype,
                }
                if field_def.is_primary:
                    field_kwargs["is_primary"] = True
                    field_kwargs["auto_id"] = field_def.auto_id
                if field_def.max_length is not None:
                    field_kwargs["max_length"] = field_def.max_length
                if field_def.dim is not None:
                    field_kwargs["dim"] = field_def.dim
                if field_def.description:
                    field_kwargs["description"] = field_def.description
                if field_def.nullable:
                    field_kwargs["nullable"] = True
                # BM25 Function support: enable_analyzer for text field
                if field_def.enable_analyzer:
                    field_kwargs["enable_analyzer"] = True
                if field_def.analyzer_params is not None:
                    field_kwargs["analyzer_params"] = field_def.analyzer_params
                if field_def.enable_match:
                    field_kwargs["enable_match"] = True

                fields.append(FieldSchema(**field_kwargs))

            collection_schema = CollectionSchema(
                fields=fields,
                description=description or f"Collection {collection_name}",
                enable_dynamic_field=schema.enable_dynamic_field,
            )

            # Check if schema has text_sparse field for BM25 Function
            # Only applies to DocumentCollectionSchema
            has_text_sparse = any(
                field.name == FieldName.TEXT_SPARSE.value for field in schema.fields
            )
            has_text_with_analyzer = any(
                field.name == FieldName.TEXT.value and field.enable_analyzer
                for field in schema.fields
            )

            # Add BM25 Function only if both text (with analyzer) and text_sparse fields exist
            if has_text_sparse and has_text_with_analyzer:
                bm25_function = Function(
                    name="bm25_text_to_sparse",
                    function_type=FunctionType.BM25,
                    input_field_names=[FieldName.TEXT.value],
                    output_field_names=[FieldName.TEXT_SPARSE.value],
                )
                collection_schema.add_function(bm25_function)
                logger.info("Added BM25 Function to schema")

            # Create collection using MilvusClient with schema
            self._client.create_collection(
                collection_name=collection_name,
                schema=collection_schema,
            )

            logger.info(f"Created collection '{collection_name}' with custom schema")
            return True

        except Exception as e:
            logger.error(f"Failed to create collection with schema: {e}")
            raise CollectionCreationError(collection_name, str(e))

    def has_collection(self, collection_name: str) -> bool:
        """Check if a collection exists.

        Args:
            collection_name: Name of the collection.

        Returns:
            True if collection exists.
        """
        try:
            return self._client.has_collection(collection_name)
        except Exception as e:
            logger.error(f"Failed to check collection existence: {e}")
            return False

    def list_collections(self) -> list[str]:
        """List all collections.

        Returns:
            List of collection names.
        """
        try:
            return self._client.list_collections()
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise

    def drop_collection(self, collection_name: str) -> bool:
        """Drop a collection.

        Args:
            collection_name: Name of the collection to drop.

        Returns:
            True if collection dropped successfully.

        Raises:
            CollectionNotFoundError: If collection does not exist.
        """
        if not self.has_collection(collection_name):
            raise CollectionNotFoundError(collection_name)

        try:
            self._client.drop_collection(collection_name)
            logger.info(f"Dropped collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to drop collection '{collection_name}': {e}")
            raise

    def describe_collection(self, collection_name: str) -> CollectionInfo:
        """Get detailed information about a collection.

        Args:
            collection_name: Name of the collection.

        Returns:
            CollectionInfo with collection details.

        Raises:
            CollectionNotFoundError: If collection does not exist.
        """
        if not self.has_collection(collection_name):
            raise CollectionNotFoundError(collection_name)

        try:
            info = self._client.describe_collection(collection_name)
            load_state = self._client.get_load_state(collection_name)

            return CollectionInfo(
                name=collection_name,
                description=info.get("description", ""),
                num_entities=info.get("num_entities", 0),
                schema=info.get("schema", {}),
                loaded=load_state == "Loaded",
            )
        except CollectionNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to describe collection '{collection_name}': {e}")
            raise

    def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Get collection statistics.

        Args:
            collection_name: Name of the collection.

        Returns:
            Dictionary with collection statistics.
        """
        if not self.has_collection(collection_name):
            raise CollectionNotFoundError(collection_name)

        try:
            return self._client.get_collection_stats(collection_name)
        except Exception as e:
            logger.error(f"Failed to get stats for '{collection_name}': {e}")
            raise

    def ensure_collection(
        self,
        collection_name: str = COLLECTION_DOCUMENTS,
        dimension: int = DEFAULT_DENSE_DIMENSION,
    ) -> bool:
        """Ensure a collection exists, creating it if necessary.

        Args:
            collection_name: Name of the collection.
            dimension: Vector dimension.

        Returns:
            True if collection exists or was created.
        """
        if self.has_collection(collection_name):
            logger.debug(f"Collection '{collection_name}' already exists")
            return True

        request = CreateCollectionRequest(
            collection_name=collection_name,
            dimension=dimension,
        )
        return self.create_collection(request)
