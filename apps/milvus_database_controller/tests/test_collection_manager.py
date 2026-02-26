"""
Tests for CollectionManager.

This module tests collection lifecycle management operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from apps.milvus_database_controller.constants import (
    DEFAULT_DENSE_DIMENSION,
)
from apps.milvus_database_controller.dto import CreateCollectionRequest
from apps.milvus_database_controller.exceptions import (
    CollectionAlreadyExistsError,
    CollectionCreationError,
    CollectionNotFoundError,
)
from apps.milvus_database_controller.managers.collection_manager import CollectionManager

if TYPE_CHECKING:
    pass


@pytest.mark.unit
class TestCollectionManager:
    """Test CollectionManager class."""

    def test_init_with_client(self) -> None:
        """Test initialization with provided client."""
        mock_client = MagicMock()
        manager = CollectionManager(client=mock_client)
        assert manager._client is mock_client

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_init_without_client(self, mock_wrapper: MagicMock) -> None:
        """Test initialization without client (uses singleton)."""
        mock_instance = MagicMock()
        mock_wrapper.get_instance.return_value = mock_instance

        manager = CollectionManager()
        assert manager._client is mock_instance

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_has_collection_true(self, mock_wrapper: MagicMock) -> None:
        """Test has_collection returns True when collection exists."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        manager = CollectionManager()
        result = manager.has_collection("test_collection")

        assert result is True
        mock_client.has_collection.assert_called_once_with("test_collection")

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_has_collection_false(self, mock_wrapper: MagicMock) -> None:
        """Test has_collection returns False when collection does not exist."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_wrapper.get_instance.return_value = mock_client

        manager = CollectionManager()
        result = manager.has_collection("non_existent_collection")

        assert result is False
        mock_client.has_collection.assert_called_once_with("non_existent_collection")

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_has_collection_handles_exception(self, mock_wrapper: MagicMock) -> None:
        """Test has_collection returns False on exception."""
        mock_client = MagicMock()
        mock_client.has_collection.side_effect = Exception("Connection error")
        mock_wrapper.get_instance.return_value = mock_client

        manager = CollectionManager()
        result = manager.has_collection("test_collection")

        assert result is False

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_list_collections(self, mock_wrapper: MagicMock) -> None:
        """Test list_collections returns collection names."""
        mock_client = MagicMock()
        mock_client.list_collections.return_value = ["collection1", "collection2"]
        mock_wrapper.get_instance.return_value = mock_client

        manager = CollectionManager()
        result = manager.list_collections()

        assert result == ["collection1", "collection2"]
        mock_client.list_collections.assert_called_once()

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_create_collection_success(self, mock_wrapper: MagicMock) -> None:
        """Test successful collection creation."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_client.create_collection.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        manager = CollectionManager()
        request = CreateCollectionRequest(
            collection_name="new_collection",
            dimension=1536,
        )
        result = manager.create_collection(request)

        assert result is True
        mock_client.has_collection.assert_called_once_with("new_collection")
        mock_client.create_collection.assert_called_once()

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_create_collection_already_exists(self, mock_wrapper: MagicMock) -> None:
        """Test create_collection raises error when collection exists."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        manager = CollectionManager()
        request = CreateCollectionRequest(
            collection_name="existing_collection",
            dimension=1536,
        )

        with pytest.raises(CollectionAlreadyExistsError) as exc_info:
            manager.create_collection(request)

        assert exc_info.value.collection_name == "existing_collection"
        # create_collection should not be called
        mock_client.create_collection.assert_not_called()

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_create_collection_failure(self, mock_wrapper: MagicMock) -> None:
        """Test create_collection raises error on creation failure."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_client.create_collection.side_effect = Exception("Creation failed")
        mock_wrapper.get_instance.return_value = mock_client

        manager = CollectionManager()
        request = CreateCollectionRequest(
            collection_name="test_collection",
            dimension=1536,
        )

        with pytest.raises(CollectionCreationError) as exc_info:
            manager.create_collection(request)

        assert exc_info.value.collection_name == "test_collection"
        assert "Creation failed" in exc_info.value.reason

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_drop_collection_success(self, mock_wrapper: MagicMock) -> None:
        """Test successful collection deletion."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.drop_collection.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        manager = CollectionManager()
        result = manager.drop_collection("test_collection")

        assert result is True
        mock_client.has_collection.assert_called_once_with("test_collection")
        mock_client.drop_collection.assert_called_once_with("test_collection")

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_drop_collection_not_found(self, mock_wrapper: MagicMock) -> None:
        """Test drop_collection raises error when collection not found."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_wrapper.get_instance.return_value = mock_client

        manager = CollectionManager()

        with pytest.raises(CollectionNotFoundError) as exc_info:
            manager.drop_collection("non_existent_collection")

        assert exc_info.value.collection_name == "non_existent_collection"
        mock_client.drop_collection.assert_not_called()

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_describe_collection_success(self, mock_wrapper: MagicMock) -> None:
        """Test describe_collection returns collection info."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.describe_collection.return_value = {
            "description": "Test collection",
            "num_entities": 100,
            "schema": {"fields": []},
        }
        mock_client.get_load_state.return_value = "Loaded"
        mock_wrapper.get_instance.return_value = mock_client

        manager = CollectionManager()
        result = manager.describe_collection("test_collection")

        assert result.name == "test_collection"
        assert result.description == "Test collection"
        assert result.num_entities == 100
        assert result.loaded is True

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_describe_collection_not_loaded(self, mock_wrapper: MagicMock) -> None:
        """Test describe_collection with not loaded collection."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.describe_collection.return_value = {
            "description": "Test collection",
            "num_entities": 0,
            "schema": {"fields": []},
        }
        mock_client.get_load_state.return_value = "NotLoad"
        mock_wrapper.get_instance.return_value = mock_client

        manager = CollectionManager()
        result = manager.describe_collection("test_collection")

        assert result.loaded is False

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_describe_collection_not_found(self, mock_wrapper: MagicMock) -> None:
        """Test describe_collection raises error when collection not found."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_wrapper.get_instance.return_value = mock_client

        manager = CollectionManager()

        with pytest.raises(CollectionNotFoundError):
            manager.describe_collection("non_existent_collection")

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_get_collection_stats(self, mock_wrapper: MagicMock) -> None:
        """Test get_collection_stats returns statistics."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.get_collection_stats.return_value = {
            "row_count": 1000,
            "data_size": 1024000,
        }
        mock_wrapper.get_instance.return_value = mock_client

        manager = CollectionManager()
        result = manager.get_collection_stats("test_collection")

        assert result["row_count"] == 1000
        assert result["data_size"] == 1024000

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_ensure_collection_creates_if_not_exists(self, mock_wrapper: MagicMock) -> None:
        """Test ensure_collection creates collection if it does not exist."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_client.create_collection.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        manager = CollectionManager()
        result = manager.ensure_collection("new_collection", dimension=1536)

        assert result is True
        mock_client.create_collection.assert_called_once()

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_ensure_collection_returns_true_if_exists(self, mock_wrapper: MagicMock) -> None:
        """Test ensure_collection returns True if collection already exists."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        manager = CollectionManager()
        result = manager.ensure_collection("existing_collection")

        assert result is True
        mock_client.create_collection.assert_not_called()


@pytest.mark.unit
class TestCollectionManagerWithCustomSchema:
    """Test CollectionManager with custom schema operations."""

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_create_collection_with_schema_success(self, mock_wrapper: MagicMock) -> None:
        """Test create_collection_with_schema creates collection with custom schema."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_client.config = {"alias": "default"}
        mock_wrapper.get_instance.return_value = mock_client

        manager = CollectionManager()

        from apps.milvus_database_controller.schemas.collection_schema import (
            DocumentCollectionSchema,
        )

        schema = DocumentCollectionSchema(dimension=1536)
        result = manager.create_collection_with_schema(
            collection_name="custom_collection",
            schema=schema,
            description="Custom test collection",
        )

        assert result is True
        # Verify that create_collection was called with schema parameter
        mock_client.create_collection.assert_called_once()
        call_kwargs = mock_client.create_collection.call_args[1]
        assert "schema" in call_kwargs

    @patch("apps.milvus_database_controller.managers.collection_manager.MilvusClientWrapper")
    def test_create_collection_with_schema_already_exists(self, mock_wrapper: MagicMock) -> None:
        """Test create_collection_with_schema raises error when collection exists."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        manager = CollectionManager()

        from apps.milvus_database_controller.schemas.collection_schema import (
            DocumentCollectionSchema,
        )

        schema = DocumentCollectionSchema(dimension=1536)

        with pytest.raises(CollectionAlreadyExistsError):
            manager.create_collection_with_schema(
                collection_name="existing_collection",
                schema=schema,
            )


@pytest.mark.integration
class TestCollectionManagerIntegration:
    """Integration tests for CollectionManager (requires running Milvus)."""

    def test_create_and_drop_collection(
        self,
        collection_manager: CollectionManager,
        test_collection_name: str,
    ) -> None:
        """Test full lifecycle: create and drop collection."""
        # Create collection
        request = CreateCollectionRequest(
            collection_name=test_collection_name,
            dimension=DEFAULT_DENSE_DIMENSION,
        )
        result = collection_manager.create_collection(request)
        assert result is True

        # Verify collection exists
        assert collection_manager.has_collection(test_collection_name) is True

        # Get collection info
        info = collection_manager.describe_collection(test_collection_name)
        assert info.name == test_collection_name
        # Note: MilvusClient.create_collection auto-loads collection
        assert info.loaded is True

        # Drop collection
        result = collection_manager.drop_collection(test_collection_name)
        assert result is True

        # Verify collection is gone
        assert collection_manager.has_collection(test_collection_name) is False

    def test_list_collections(
        self,
        collection_manager: CollectionManager,
        test_collection: str,
    ) -> None:
        """Test list_collections returns created collections."""
        collections = collection_manager.list_collections()
        assert isinstance(collections, list)
        assert test_collection in collections

    def test_describe_collection(
        self,
        collection_manager: CollectionManager,
        test_collection: str,
    ) -> None:
        """Test describe_collection returns correct info."""
        info = collection_manager.describe_collection(test_collection)

        assert info.name == test_collection
        assert isinstance(info.num_entities, int)
        assert isinstance(info.schema, dict)

    def test_ensure_collection_idempotent(
        self,
        collection_manager: CollectionManager,
        test_collection: str,
    ) -> None:
        """Test ensure_collection is idempotent."""
        # Should return True without error
        result = collection_manager.ensure_collection(test_collection)
        assert result is True

        # Call again - should still return True
        result = collection_manager.ensure_collection(test_collection)
        assert result is True
