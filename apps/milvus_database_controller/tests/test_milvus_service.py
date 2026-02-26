"""
Tests for MilvusService.

This module tests the high-level facade service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from apps.milvus_database_controller.constants import (
    DEFAULT_DENSE_DIMENSION,
    FieldName,
)
from apps.milvus_database_controller.dto import (
    CollectionInfo,
    DeleteResult,
    InsertResult,
    UpsertResult,
)
from apps.milvus_database_controller.exceptions import (
    CollectionAlreadyExistsError,
    CollectionNotFoundError,
)
from apps.milvus_database_controller.services.milvus_service import MilvusService

if TYPE_CHECKING:
    pass


@pytest.mark.unit
class TestMilvusService:
    """Test MilvusService class."""

    def test_init_with_client(self) -> None:
        """Test initialization with provided client."""
        mock_client = MagicMock()
        service = MilvusService(client=mock_client)
        assert service._client is mock_client

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_init_without_client(self, mock_wrapper: MagicMock) -> None:
        """Test initialization without client (uses singleton)."""
        mock_instance = MagicMock()
        mock_wrapper.get_instance.return_value = mock_instance

        service = MilvusService()
        assert service._client is mock_instance

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_service_initializes_managers(self, mock_wrapper: MagicMock) -> None:
        """Test that service initializes all managers."""
        mock_client = MagicMock()
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()

        assert service._collection_manager is not None
        assert service._index_manager is not None
        assert service._vector_manager is not None
        assert service._search_manager is not None


@pytest.mark.unit
class TestCollectionOperations:
    """Test collection operations through service."""

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_create_collection(self, mock_wrapper: MagicMock) -> None:
        """Test create_collection delegates to manager."""
        mock_client = MagicMock()
        # Setup has_collection to return False initially, then True after creation
        has_collection_states = [False, False, True]  # create check, index creation checks
        call_count = [0]

        def has_collection_side_effect(name):
            call_count[0] += 1
            if call_count[0] == 1:
                return False  # Initial check for collection creation
            return True  # After creation, return True

        mock_client.has_collection.side_effect = has_collection_side_effect
        mock_client.create_collection.return_value = True
        mock_client.create_index.return_value = True
        mock_client.load_collection.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.create_collection("test_collection")

        assert result is True

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_create_collection_with_indexes(self, mock_wrapper: MagicMock) -> None:
        """Test create_collection creates indexes when requested."""
        mock_client = MagicMock()
        # Setup has_collection to return False initially, then True after creation
        call_count = [0]

        def has_collection_side_effect(name):
            call_count[0] += 1
            if call_count[0] == 1:
                return False  # Initial check for collection creation
            return True  # After creation, return True

        mock_client.has_collection.side_effect = has_collection_side_effect
        mock_client.create_collection.return_value = True
        mock_client.create_index.return_value = True
        mock_client.load_collection.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.create_collection("test_collection", create_indexes=True)

        assert result is True

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_has_collection(self, mock_wrapper: MagicMock) -> None:
        """Test has_collection delegates to manager."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.has_collection("test_collection")

        assert result is True

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_list_collections(self, mock_wrapper: MagicMock) -> None:
        """Test list_collections returns collection names."""
        mock_client = MagicMock()
        mock_client.list_collections.return_value = ["col1", "col2"]
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.list_collections()

        assert result == ["col1", "col2"]

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_drop_collection(self, mock_wrapper: MagicMock) -> None:
        """Test drop_collection delegates to manager."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.drop_collection.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.drop_collection("test_collection")

        assert result is True

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_get_collection_info(self, mock_wrapper: MagicMock) -> None:
        """Test get_collection_info returns CollectionInfo."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.describe_collection.return_value = {
            "description": "Test",
            "num_entities": 100,
            "schema": {},
        }
        mock_client.get_load_state.return_value = "Loaded"
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.get_collection_info("test_collection")

        assert isinstance(result, CollectionInfo)
        assert result.name == "test_collection"

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_ensure_collection(self, mock_wrapper: MagicMock) -> None:
        """Test ensure_collection creates if not exists."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_client.create_collection.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.ensure_collection("test_collection")

        assert result is True


@pytest.mark.unit
class TestIndexOperations:
    """Test index operations through service."""

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_create_indexes(self, mock_wrapper: MagicMock) -> None:
        """Test create_indexes delegates to manager."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.create_index.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.create_indexes("test_collection")

        assert isinstance(result, dict)

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_load_collection(self, mock_wrapper: MagicMock) -> None:
        """Test load_collection delegates to manager."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.load_collection.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.load_collection("test_collection")

        assert result is True

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_is_collection_loaded(self, mock_wrapper: MagicMock) -> None:
        """Test is_collection_loaded returns correct state."""
        mock_client = MagicMock()
        mock_client.get_load_state.return_value = "Loaded"
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.is_collection_loaded("test_collection")

        assert result is True


@pytest.mark.unit
class TestVectorOperations:
    """Test vector operations through service."""

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_insert_vectors(self, mock_wrapper: MagicMock) -> None:
        """Test insert_vectors delegates to manager."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.insert.return_value = {"ids": ["id1"]}
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.insert_vectors(
            collection_name="test_collection",
            data=[{"pk": "id1", "text": "text1", "text_dense": [0.1] * 1536}],
        )

        assert isinstance(result, InsertResult)
        assert result.inserted_count == 1

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_upsert_vectors(self, mock_wrapper: MagicMock) -> None:
        """Test upsert_vectors delegates to manager."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.upsert.return_value = {"ids": ["id1"]}
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.upsert_vectors(
            collection_name="test_collection",
            data=[{"pk": "id1", "text": "text1", "text_dense": [0.1] * 1536}],
        )

        assert isinstance(result, UpsertResult)
        assert result.upserted_count == 1

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_delete_vectors(self, mock_wrapper: MagicMock) -> None:
        """Test delete_vectors delegates to manager."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.delete.return_value = {}
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.delete_vectors(
            collection_name="test_collection",
            ids=["id1", "id2"],
        )

        assert isinstance(result, DeleteResult)

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_delete_vectors_by_filter(self, mock_wrapper: MagicMock) -> None:
        """Test delete_vectors_by_filter delegates to manager."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.delete.return_value = {}
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.delete_vectors_by_filter(
            collection_name="test_collection",
            filter_expr='source == "test"',
        )

        assert isinstance(result, DeleteResult)

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_get_vector(self, mock_wrapper: MagicMock) -> None:
        """Test get_vector returns vector data."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.get.return_value = [{"pk": "id1", "text": "text1"}]
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.get_vector(
            collection_name="test_collection",
            pk="id1",
        )

        assert result is not None
        assert result["pk"] == "id1"

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_delete_document_chunks(self, mock_wrapper: MagicMock) -> None:
        """Test delete_document_chunks uses correct filter."""
        mock_client = MagicMock()
        # Setup has_collection to return True for all checks
        mock_client.has_collection.return_value = True
        mock_client.delete.return_value = {}
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.delete_document_chunks(
            collection_name="test_collection",
            document_id="doc-001",
        )

        # Verify filter was applied
        call_kwargs = mock_client.delete.call_args[1]
        assert "doc-001" in str(call_kwargs.get("filter", "")) or "doc-001" in str(call_kwargs)


@pytest.mark.unit
class TestSearchOperations:
    """Test search operations through service."""

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_search(self, mock_wrapper: MagicMock) -> None:
        """Test search delegates to manager."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.search.return_value = [[
            {"id": "id1", "distance": 0.1, "text": "text1"}
        ]]
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.search(
            collection_name="test_collection",
            query_vector=[0.1] * 1536,
        )

        assert result.total == 1
        assert len(result.items) == 1

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_hybrid_search(self, mock_wrapper: MagicMock) -> None:
        """Test hybrid_search delegates to manager."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.search.return_value = [[
            {"id": "id1", "distance": 0.1, "text": "text1"}
        ]]
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.hybrid_search(
            collection_name="test_collection",
            query_text="test query",
            query_vectors={
                FieldName.TEXT_DENSE.value: [0.1] * 1536,
            },
        )

        assert result.total >= 0


@pytest.mark.unit
class TestUtilityMethods:
    """Test utility methods."""

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_count_vectors(self, mock_wrapper: MagicMock) -> None:
        """Test count_vectors returns count."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.get_collection_stats.return_value = {"row_count": 100}
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.count_vectors("test_collection")

        assert result == 100

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_get_collection_stats(self, mock_wrapper: MagicMock) -> None:
        """Test get_collection_stats returns stats."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.get_collection_stats.return_value = {"row_count": 100}
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.get_collection_stats("test_collection")

        assert result["row_count"] == 100

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_health_check_healthy(self, mock_wrapper: MagicMock) -> None:
        """Test health_check returns healthy status."""
        mock_client = MagicMock()
        mock_client.list_collections.return_value = ["col1", "col2"]
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.health_check()

        assert result["status"] == "healthy"
        assert result["connected"] is True
        assert result["collections_count"] == 2

    @patch("apps.milvus_database_controller.services.milvus_service.MilvusClientWrapper")
    def test_health_check_unhealthy(self, mock_wrapper: MagicMock) -> None:
        """Test health_check returns unhealthy status on error."""
        mock_client = MagicMock()
        mock_client.list_collections.side_effect = Exception("Connection failed")
        mock_wrapper.get_instance.return_value = mock_client

        service = MilvusService()
        result = service.health_check()

        assert result["status"] == "unhealthy"
        assert result["connected"] is False
        assert "Connection failed" in result["error"]


@pytest.mark.integration
class TestMilvusServiceIntegration:
    """Integration tests for MilvusService (requires running Milvus)."""

    def test_full_lifecycle(
        self,
        milvus_service: MilvusService,
        test_collection: str,
        sample_vector_records: list[dict],
    ) -> None:
        """Test full lifecycle: insert, search, delete."""
        import time

        # Verify collection exists (created by fixture)
        assert milvus_service.has_collection(test_collection) is True

        # Insert vectors
        insert_result = milvus_service.insert_vectors(
            collection_name=test_collection,
            data=sample_vector_records,
        )
        assert insert_result.inserted_count > 0

        # Wait for Milvus eventual consistency
        time.sleep(0.5)

        # Verify collection is loaded
        assert milvus_service.is_collection_loaded(test_collection) is True

        # Search
        import random
        query_vector = [random.random() for _ in range(1536)]

        search_result = milvus_service.search(
            collection_name=test_collection,
            query_vector=query_vector,
            top_k=5,
        )
        assert search_result.total > 0

        # Query vectors to verify data exists (more reliable than count_vectors)
        query_result = milvus_service.query_vectors(
            collection_name=test_collection,
            filter_expr=f'{FieldName.SOURCE.value} == "test"',
            limit=10,
        )
        assert query_result.total > 0

        # Health check
        health = milvus_service.health_check()
        assert health["status"] == "healthy"

        # Delete vectors by filter
        delete_result = milvus_service.delete_document_chunks(
            collection_name=test_collection,
            document_id=sample_vector_records[0]["lt_doc_id"],
        )
        assert delete_result.deleted_count >= 0

    def test_upsert_and_delete(
        self,
        milvus_service: MilvusService,
        test_collection: str,
        sample_vector_record: dict,
    ) -> None:
        """Test upsert and delete operations."""
        import time

        # Insert first
        insert_result = milvus_service.insert_vectors(
            collection_name=test_collection,
            data=[sample_vector_record],
        )
        assert insert_result.inserted_count == 1

        # Wait for Milvus eventual consistency
        time.sleep(0.5)

        # Update via upsert
        updated_record = sample_vector_record.copy()
        updated_record["text"] = "Updated text"

        upsert_result = milvus_service.upsert_vectors(
            collection_name=test_collection,
            data=[updated_record],
        )
        assert upsert_result.upserted_count == 1

        # Wait for Milvus eventual consistency
        time.sleep(0.5)

        # Verify update
        retrieved = milvus_service.get_vector(
            collection_name=test_collection,
            pk=sample_vector_record["pk"],
        )
        assert retrieved is not None
        assert retrieved["text"] == "Updated text"

        # Delete
        delete_result = milvus_service.delete_vectors(
            collection_name=test_collection,
            ids=[sample_vector_record["pk"]],
        )
        assert delete_result.deleted_count == 1

    def test_query_by_filter(
        self,
        milvus_service: MilvusService,
        test_collection: str,
        sample_vector_records: list[dict],
    ) -> None:
        """Test query with filter expression."""
        import time

        # Insert test data
        milvus_service.insert_vectors(
            collection_name=test_collection,
            data=sample_vector_records,
        )

        # Wait for Milvus eventual consistency
        time.sleep(0.5)

        # Query by source
        result = milvus_service.query_vectors(
            collection_name=test_collection,
            filter_expr=f'{FieldName.SOURCE.value} == "test"',
        )

        assert result.total > 0
