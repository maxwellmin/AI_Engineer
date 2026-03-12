"""
Tests for IndexManager.

This module tests index management operations including
creation, deletion, and collection loading.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from apps.milvus_database_controller.constants import (
    FieldName,
    HNSW_INDEX_PARAMS,
    IndexName,
    SPARSE_INDEX_PARAMS,
)
from apps.milvus_database_controller.exceptions import (
    CollectionNotFoundError,
    IndexCreationError,
)
from apps.milvus_database_controller.managers.index_manager import IndexManager

if TYPE_CHECKING:
    pass


@pytest.mark.unit
class TestIndexManager:
    """Test IndexManager class."""

    def test_init_with_client(self) -> None:
        """Test initialization with provided client."""
        mock_client = MagicMock()
        manager = IndexManager(client=mock_client)
        assert manager._client is mock_client

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_init_without_client(self, mock_wrapper: MagicMock) -> None:
        """Test initialization without client (uses singleton)."""
        mock_instance = MagicMock()
        mock_wrapper.get_instance.return_value = mock_instance

        manager = IndexManager()
        assert manager._client is mock_instance

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_create_dense_index_success(self, mock_wrapper: MagicMock) -> None:
        """Test successful dense index creation."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.create_index.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()
        result = manager.create_dense_index(
            collection_name="test_collection",
            field_name="summary_dense",
            index_name="summary_dense_index",
        )

        assert result is True
        mock_client.create_index.assert_called_once()
        call_kwargs = mock_client.create_index.call_args[1]
        assert call_kwargs["collection_name"] == "test_collection"
        assert call_kwargs["field_name"] == "summary_dense"
        assert call_kwargs["index_name"] == "summary_dense_index"

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_create_dense_index_auto_name(self, mock_wrapper: MagicMock) -> None:
        """Test dense index creation with auto-generated name."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.create_index.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()
        result = manager.create_dense_index(
            collection_name="test_collection",
            field_name="text_dense",
        )

        assert result is True
        call_kwargs = mock_client.create_index.call_args[1]
        assert call_kwargs["index_name"] == "text_dense_index"

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_create_dense_index_collection_not_found(self, mock_wrapper: MagicMock) -> None:
        """Test dense index creation raises error when collection not found."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()

        with pytest.raises(CollectionNotFoundError):
            manager.create_dense_index(
                collection_name="non_existent",
                field_name="summary_dense",
            )

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_create_dense_index_failure(self, mock_wrapper: MagicMock) -> None:
        """Test dense index creation raises error on failure."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.create_index.side_effect = Exception("Index creation failed")
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()

        with pytest.raises(IndexCreationError) as exc_info:
            manager.create_dense_index(
                collection_name="test_collection",
                field_name="summary_dense",
            )

        assert "Index creation failed" in exc_info.value.reason

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_create_sparse_index_success(self, mock_wrapper: MagicMock) -> None:
        """Test successful sparse index creation."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.create_index.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()
        result = manager.create_sparse_index(
            collection_name="test_collection",
        )

        assert result is True
        mock_client.create_index.assert_called_once()
        call_kwargs = mock_client.create_index.call_args[1]
        assert call_kwargs["field_name"] == FieldName.TEXT_SPARSE.value

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_create_sparse_index_collection_not_found(self, mock_wrapper: MagicMock) -> None:
        """Test sparse index creation raises error when collection not found."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()

        with pytest.raises(CollectionNotFoundError):
            manager.create_sparse_index(collection_name="non_existent")

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_create_all_indexes(self, mock_wrapper: MagicMock) -> None:
        """Test creating all indexes for a collection."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.create_index.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()
        results = manager.create_all_indexes(collection_name="test_collection")

        # Should create 3 indexes: summary_dense, text_dense, text_sparse
        assert results.get("summary_dense_index") is True
        assert results.get("text_dense_index") is True
        assert results.get(IndexName.TEXT_SPARSE.value) is True
        assert mock_client.create_index.call_count == 3

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_create_all_indexes_partial_failure(self, mock_wrapper: MagicMock) -> None:
        """Test create_all_indexes handles partial failures."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True

        # First call succeeds, second fails, third succeeds
        call_count = [0]

        def side_effect_create_index(**kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Index creation failed")
            return True

        mock_client.create_index.side_effect = side_effect_create_index
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()
        results = manager.create_all_indexes(collection_name="test_collection")

        # One should fail
        assert True in results.values()
        assert False in results.values()

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_list_indexes(self, mock_wrapper: MagicMock) -> None:
        """Test list_indexes returns index names."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.list_indexes.return_value = ["index1", "index2"]
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()
        result = manager.list_indexes("test_collection")

        assert result == ["index1", "index2"]
        mock_client.list_indexes.assert_called_once_with("test_collection")

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_list_indexes_collection_not_found(self, mock_wrapper: MagicMock) -> None:
        """Test list_indexes raises error when collection not found."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()

        with pytest.raises(CollectionNotFoundError):
            manager.list_indexes("non_existent")

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_drop_index_success(self, mock_wrapper: MagicMock) -> None:
        """Test successful index deletion."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.drop_index.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()
        result = manager.drop_index("test_collection", "test_index")

        assert result is True
        mock_client.drop_index.assert_called_once_with("test_collection", "test_index")

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_load_collection_success(self, mock_wrapper: MagicMock) -> None:
        """Test successful collection loading."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.load_collection.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()
        result = manager.load_collection("test_collection")

        assert result is True
        mock_client.load_collection.assert_called_once_with("test_collection")

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_load_collection_not_found(self, mock_wrapper: MagicMock) -> None:
        """Test load_collection raises error when collection not found."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()

        with pytest.raises(CollectionNotFoundError):
            manager.load_collection("non_existent")

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_release_collection_success(self, mock_wrapper: MagicMock) -> None:
        """Test successful collection release."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.release_collection.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()
        result = manager.release_collection("test_collection")

        assert result is True
        mock_client.release_collection.assert_called_once_with("test_collection")

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_get_load_state(self, mock_wrapper: MagicMock) -> None:
        """Test get_load_state returns correct state."""
        mock_client = MagicMock()
        mock_client.get_load_state.return_value = "Loaded"
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()
        result = manager.get_load_state("test_collection")

        assert result == "Loaded"

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_is_loaded_true(self, mock_wrapper: MagicMock) -> None:
        """Test is_loaded returns True when collection is loaded."""
        mock_client = MagicMock()
        mock_client.get_load_state.return_value = "Loaded"
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()
        result = manager.is_loaded("test_collection")

        assert result is True

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_is_loaded_false(self, mock_wrapper: MagicMock) -> None:
        """Test is_loaded returns False when collection is not loaded."""
        mock_client = MagicMock()
        mock_client.get_load_state.return_value = "NotLoad"
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()
        result = manager.is_loaded("test_collection")

        assert result is False

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_ensure_loaded_already_loaded(self, mock_wrapper: MagicMock) -> None:
        """Test ensure_loaded returns True when already loaded."""
        mock_client = MagicMock()
        mock_client.get_load_state.return_value = "Loaded"
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()
        result = manager.ensure_loaded("test_collection")

        assert result is True
        # load_collection should not be called
        mock_client.load_collection.assert_not_called()

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_ensure_loaded_loads_if_not(self, mock_wrapper: MagicMock) -> None:
        """Test ensure_loaded loads collection if not loaded."""
        mock_client = MagicMock()
        mock_client.get_load_state.return_value = "NotLoad"
        mock_client.load_collection.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()
        result = manager.ensure_loaded("test_collection")

        assert result is True
        mock_client.load_collection.assert_called_once_with("test_collection")

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_get_index_info_success(self, mock_wrapper: MagicMock) -> None:
        """Test get_index_info returns correct info."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.describe_collection.return_value = {
            "indexes": [
                {
                    "index_name": "summary_dense_index",
                    "field_name": "summary_dense",
                    "index_type": "HNSW",
                    "metric_type": "COSINE",
                    "params": {"M": 32, "efConstruction": 200},
                }
            ]
        }
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()
        result = manager.get_index_info("test_collection", "summary_dense_index")

        assert result.index_name == "summary_dense_index"
        assert result.field_name == "summary_dense"
        assert result.index_type == "HNSW"
        assert result.metric_type == "COSINE"

    @patch("apps.milvus_database_controller.managers.index_manager.MilvusClientWrapper")
    def test_get_index_info_not_found(self, mock_wrapper: MagicMock) -> None:
        """Test get_index_info raises error when index not found."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.describe_collection.return_value = {"indexes": []}
        mock_wrapper.get_instance.return_value = mock_client

        manager = IndexManager()

        from apps.milvus_database_controller.exceptions import IndexError

        with pytest.raises(IndexError):
            manager.get_index_info("test_collection", "non_existent_index")


@pytest.mark.unit
class TestSparseIndexParams:
    """Test sparse index parameters for BM25."""

    def test_sparse_index_params_has_bm25_metric(self) -> None:
        """Test SPARSE_INDEX_PARAMS uses BM25 metric type."""
        from apps.milvus_database_controller.constants import MetricType

        assert SPARSE_INDEX_PARAMS["metric_type"] == MetricType.BM25.value

    def test_sparse_index_params_has_sparse_wand_index_type(self) -> None:
        """Test SPARSE_INDEX_PARAMS uses SPARSE_WAND index type."""
        from apps.milvus_database_controller.constants import IndexType

        assert SPARSE_INDEX_PARAMS["index_type"] == IndexType.SPARSE_WAND.value

    def test_sparse_index_params_has_bm25_k1(self) -> None:
        """Test SPARSE_INDEX_PARAMS contains bm25_k1 parameter."""
        assert "bm25_k1" in SPARSE_INDEX_PARAMS["params"]
        assert SPARSE_INDEX_PARAMS["params"]["bm25_k1"] == 1.5

    def test_sparse_index_params_has_bm25_b(self) -> None:
        """Test SPARSE_INDEX_PARAMS contains bm25_b parameter."""
        assert "bm25_b" in SPARSE_INDEX_PARAMS["params"]
        assert SPARSE_INDEX_PARAMS["params"]["bm25_b"] == 0.8


@pytest.mark.integration
class TestIndexManagerIntegration:
    """Integration tests for IndexManager (requires running Milvus)."""

    def test_create_and_list_indexes(
        self,
        index_manager: IndexManager,
        test_collection: str,
    ) -> None:
        """Test creating and listing indexes."""
        # Create indexes
        results = index_manager.create_all_indexes(test_collection)

        # At least dense indexes should succeed
        assert results.get("summary_dense_index") is True
        assert results.get("text_dense_index") is True

        # List indexes
        indexes = index_manager.list_indexes(test_collection)
        assert len(indexes) >= 2

    def test_load_and_release_collection(
        self,
        index_manager: IndexManager,
        test_collection: str,
    ) -> None:
        """Test loading and releasing collection."""
        # Create indexes first
        index_manager.create_all_indexes(test_collection)

        # Load collection
        result = index_manager.load_collection(test_collection)
        assert result is True
        assert index_manager.is_loaded(test_collection) is True

        # Release collection
        result = index_manager.release_collection(test_collection)
        assert result is True
        assert index_manager.is_loaded(test_collection) is False

    def test_ensure_loaded(
        self,
        index_manager: IndexManager,
        test_collection: str,
    ) -> None:
        """Test ensure_loaded functionality."""
        # Create indexes first
        index_manager.create_all_indexes(test_collection)

        # Ensure loaded (should load)
        result = index_manager.ensure_loaded(test_collection)
        assert result is True

        # Ensure loaded again (should be no-op)
        result = index_manager.ensure_loaded(test_collection)
        assert result is True
