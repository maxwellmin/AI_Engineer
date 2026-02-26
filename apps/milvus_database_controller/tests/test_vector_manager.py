"""
Tests for VectorManager.

This module tests vector CRUD operations.
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
    DeleteVectorsByFilterRequest,
    DeleteVectorsRequest,
    GetVectorRequest,
    InsertVectorsRequest,
    QueryRequest,
    UpsertVectorsRequest,
)
from apps.milvus_database_controller.exceptions import (
    CollectionNotFoundError,
    InvalidVectorDataError,
    InvalidVectorDimensionError,
    VectorDeleteError,
    VectorInsertError,
)
from apps.milvus_database_controller.managers.vector_manager import VectorManager

if TYPE_CHECKING:
    pass


@pytest.mark.unit
class TestVectorManager:
    """Test VectorManager class."""

    def test_init_with_client(self) -> None:
        """Test initialization with provided client."""
        mock_client = MagicMock()
        manager = VectorManager(client=mock_client)
        assert manager._client is mock_client

    @patch("apps.milvus_database_controller.managers.vector_manager.MilvusClientWrapper")
    def test_init_without_client(self, mock_wrapper: MagicMock) -> None:
        """Test initialization without client (uses singleton)."""
        mock_instance = MagicMock()
        mock_wrapper.get_instance.return_value = mock_instance

        manager = VectorManager()
        assert manager._client is mock_instance


@pytest.mark.unit
class TestVectorValidation:
    """Test vector data validation."""

    def test_validate_empty_data(self) -> None:
        """Test validation fails for empty data."""
        mock_client = MagicMock()
        manager = VectorManager(client=mock_client)

        with pytest.raises(InvalidVectorDataError) as exc_info:
            manager._validate_vector_data([])

        assert "Empty" in str(exc_info.value)

    def test_validate_missing_pk(self) -> None:
        """Test validation fails for missing primary key."""
        mock_client = MagicMock()
        manager = VectorManager(client=mock_client)

        with pytest.raises(InvalidVectorDataError) as exc_info:
            manager._validate_vector_data([{"text": "test"}])

        assert "primary key" in str(exc_info.value).lower()

    def test_validate_wrong_dimension(self) -> None:
        """Test validation fails for wrong vector dimension."""
        mock_client = MagicMock()
        manager = VectorManager(client=mock_client)

        # Vector with wrong dimension (should be 1536)
        wrong_dim_vector = [0.1] * 100

        with pytest.raises(InvalidVectorDimensionError) as exc_info:
            manager._validate_vector_data([{
                "pk": "test-001",
                "text_dense": wrong_dim_vector,
            }])

        assert exc_info.value.expected == 1536
        assert exc_info.value.actual == 100

    def test_validate_correct_data(self) -> None:
        """Test validation passes for correct data."""
        mock_client = MagicMock()
        manager = VectorManager(client=mock_client)

        # Should not raise
        manager._validate_vector_data([{
            "pk": "test-001",
            "text": "test text",
            "text_dense": [0.1] * 1536,
        }])


@pytest.mark.unit
class TestInsertVectors:
    """Test vector insertion operations."""

    @patch("apps.milvus_database_controller.managers.vector_manager.MilvusClientWrapper")
    def test_insert_vectors_success(self, mock_wrapper: MagicMock) -> None:
        """Test successful vector insertion."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.insert.return_value = {"ids": ["id1", "id2"]}
        mock_wrapper.get_instance.return_value = mock_client

        manager = VectorManager()
        request = InsertVectorsRequest(
            collection_name="test_collection",
            data=[
                {"pk": "id1", "text": "text1", "text_dense": [0.1] * 1536},
                {"pk": "id2", "text": "text2", "text_dense": [0.1] * 1536},
            ],
        )

        result = manager.insert_vectors(request)

        assert result.inserted_count == 2
        assert result.inserted_ids == ["id1", "id2"]
        mock_client.insert.assert_called_once()

    @patch("apps.milvus_database_controller.managers.vector_manager.MilvusClientWrapper")
    def test_insert_vectors_collection_not_found(self, mock_wrapper: MagicMock) -> None:
        """Test insert raises error when collection not found."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_wrapper.get_instance.return_value = mock_client

        manager = VectorManager()
        request = InsertVectorsRequest(
            collection_name="non_existent",
            data=[{"pk": "id1", "text": "text1"}],
        )

        with pytest.raises(CollectionNotFoundError):
            manager.insert_vectors(request)

    @patch("apps.milvus_database_controller.managers.vector_manager.MilvusClientWrapper")
    def test_insert_vectors_failure(self, mock_wrapper: MagicMock) -> None:
        """Test insert raises error on failure."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.insert.side_effect = Exception("Insert failed")
        mock_wrapper.get_instance.return_value = mock_client

        manager = VectorManager()
        request = InsertVectorsRequest(
            collection_name="test_collection",
            data=[{"pk": "id1", "text": "text1", "text_dense": [0.1] * 1536}],
        )

        with pytest.raises(VectorInsertError) as exc_info:
            manager.insert_vectors(request)

        assert "Insert failed" in exc_info.value.reason

    @patch("apps.milvus_database_controller.managers.vector_manager.MilvusClientWrapper")
    def test_insert_vectors_batch(self, mock_wrapper: MagicMock) -> None:
        """Test batch insertion."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        # Return correct number of IDs based on input data
        def insert_side_effect(**kwargs):
            data = kwargs.get("data", [])
            return {"ids": [item["pk"] for item in data]}

        mock_client.insert.side_effect = insert_side_effect
        mock_wrapper.get_instance.return_value = mock_client

        manager = VectorManager()

        # Create 5 records, batch size 2
        data = [
            {"pk": f"id{i}", "text": f"text{i}", "text_dense": [0.1] * 1536}
            for i in range(5)
        ]

        result = manager.insert_vectors_batch(
            collection_name="test_collection",
            data=data,
            batch_size=2,
        )

        assert result.inserted_count == 5
        # Should be called 3 times (2 + 2 + 1)
        assert mock_client.insert.call_count == 3


@pytest.mark.unit


@pytest.mark.unit
class TestUpsertVectors:
    """Test vector upsertion operations."""

    @patch("apps.milvus_database_controller.managers.vector_manager.MilvusClientWrapper")
    def test_upsert_vectors_success(self, mock_wrapper: MagicMock) -> None:
        """Test successful vector upsertion."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.upsert.return_value = {"ids": ["id1"]}
        mock_wrapper.get_instance.return_value = mock_client

        manager = VectorManager()
        request = UpsertVectorsRequest(
            collection_name="test_collection",
            data=[{"pk": "id1", "text": "text1", "text_dense": [0.1] * 1536}],
        )

        result = manager.upsert_vectors(request)

        assert result.upserted_count == 1
        assert result.upserted_ids == ["id1"]

    @patch("apps.milvus_database_controller.managers.vector_manager.MilvusClientWrapper")
    def test_upsert_vectors_collection_not_found(self, mock_wrapper: MagicMock) -> None:
        """Test upsert raises error when collection not found."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_wrapper.get_instance.return_value = mock_client

        manager = VectorManager()
        request = UpsertVectorsRequest(
            collection_name="non_existent",
            data=[{"pk": "id1"}],
        )

        with pytest.raises(CollectionNotFoundError):
            manager.upsert_vectors(request)


@pytest.mark.unit
class TestDeleteVectors:
    """Test vector deletion operations."""

    @patch("apps.milvus_database_controller.managers.vector_manager.MilvusClientWrapper")
    def test_delete_vectors_by_ids(self, mock_wrapper: MagicMock) -> None:
        """Test deleting vectors by IDs."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.delete.return_value = {}
        mock_wrapper.get_instance.return_value = mock_client

        manager = VectorManager()
        request = DeleteVectorsRequest(
            collection_name="test_collection",
            ids=["id1", "id2"],
        )

        result = manager.delete_vectors(request)

        assert result.deleted_count == 2
        mock_client.delete.assert_called_once()

    @patch("apps.milvus_database_controller.managers.vector_manager.MilvusClientWrapper")
    def test_delete_vectors_by_filter(self, mock_wrapper: MagicMock) -> None:
        """Test deleting vectors by filter expression."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.delete.return_value = {}
        mock_wrapper.get_instance.return_value = mock_client

        manager = VectorManager()
        request = DeleteVectorsByFilterRequest(
            collection_name="test_collection",
            filter_expr=f'{FieldName.SOURCE.value} == "test"',
        )

        result = manager.delete_vectors_by_filter(request)

        # Count is 0 because Milvus doesn't return exact count
        assert result.deleted_count == 0
        mock_client.delete.assert_called_once()

    @patch("apps.milvus_database_controller.managers.vector_manager.MilvusClientWrapper")
    def test_delete_vectors_failure(self, mock_wrapper: MagicMock) -> None:
        """Test delete raises error on failure."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.delete.side_effect = Exception("Delete failed")
        mock_wrapper.get_instance.return_value = mock_client

        manager = VectorManager()
        request = DeleteVectorsRequest(
            collection_name="test_collection",
            ids=["id1"],
        )

        with pytest.raises(VectorDeleteError):
            manager.delete_vectors(request)


@pytest.mark.unit
class TestGetAndQueryVectors:
    """Test vector retrieval operations."""

    @patch("apps.milvus_database_controller.managers.vector_manager.MilvusClientWrapper")
    def test_get_vector_found(self, mock_wrapper: MagicMock) -> None:
        """Test getting a single vector."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.get.return_value = [{
            "pk": "id1",
            "text": "test text",
            "source": "test",
        }]
        mock_wrapper.get_instance.return_value = mock_client

        manager = VectorManager()
        request = GetVectorRequest(
            collection_name="test_collection",
            pk="id1",
        )

        result = manager.get_vector(request)

        assert result is not None
        assert result["pk"] == "id1"
        assert result["text"] == "test text"

    @patch("apps.milvus_database_controller.managers.vector_manager.MilvusClientWrapper")
    def test_get_vector_not_found(self, mock_wrapper: MagicMock) -> None:
        """Test getting a non-existent vector."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.get.return_value = []
        mock_wrapper.get_instance.return_value = mock_client

        manager = VectorManager()
        request = GetVectorRequest(
            collection_name="test_collection",
            pk="non_existent",
        )

        result = manager.get_vector(request)

        assert result is None

    @patch("apps.milvus_database_controller.managers.vector_manager.MilvusClientWrapper")
    def test_query_vectors(self, mock_wrapper: MagicMock) -> None:
        """Test querying vectors by filter."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.query.return_value = [
            {"pk": "id1", "text": "text1"},
            {"pk": "id2", "text": "text2"},
        ]
        mock_wrapper.get_instance.return_value = mock_client

        manager = VectorManager()
        request = QueryRequest(
            collection_name="test_collection",
            filter_expr=f'{FieldName.SOURCE.value} == "test"',
            limit=10,
        )

        result = manager.query_vectors(request)

        assert result.total == 2
        assert len(result.items) == 2

    @patch("apps.milvus_database_controller.managers.vector_manager.MilvusClientWrapper")
    def test_query_by_document_id(self, mock_wrapper: MagicMock) -> None:
        """Test querying vectors by document ID."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.query.return_value = [
            {"pk": "id1", "lt_doc_id": "doc-001"},
            {"pk": "id2", "lt_doc_id": "doc-001"},
        ]
        mock_wrapper.get_instance.return_value = mock_client

        manager = VectorManager()
        result = manager.query_by_document_id(
            collection_name="test_collection",
            document_id="doc-001",
        )

        assert result.total == 2
        # Verify correct filter was used
        call_kwargs = mock_client.query.call_args[1]
        assert "lt_doc_id" in str(call_kwargs.get("filter_expr", ""))

    @patch("apps.milvus_database_controller.managers.vector_manager.MilvusClientWrapper")
    def test_count_vectors(self, mock_wrapper: MagicMock) -> None:
        """Test counting vectors."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.get_collection_stats.return_value = {"row_count": 100}
        mock_wrapper.get_instance.return_value = mock_client

        manager = VectorManager()
        result = manager.count_vectors("test_collection")

        assert result == 100


@pytest.mark.integration
class TestVectorManagerIntegration:
    """Integration tests for VectorManager (requires running Milvus)."""

    def test_insert_and_get_vector(
        self,
        vector_manager: VectorManager,
        index_manager: "IndexManager",
        test_collection: str,
        sample_vector_record: dict,
    ) -> None:
        """Test inserting and retrieving a vector."""
        import time

        from apps.milvus_database_controller.managers.index_manager import IndexManager

        # Load collection for search
        index_manager.load_collection(test_collection)

        # Insert vector
        request = InsertVectorsRequest(
            collection_name=test_collection,
            data=[sample_vector_record],
        )
        insert_result = vector_manager.insert_vectors(request)

        assert insert_result.inserted_count == 1
        assert sample_vector_record["pk"] in insert_result.inserted_ids

        # Wait for Milvus to persist data (eventually consistent)
        time.sleep(0.5)

        # Get vector
        get_request = GetVectorRequest(
            collection_name=test_collection,
            pk=sample_vector_record["pk"],
        )
        retrieved = vector_manager.get_vector(get_request)

        assert retrieved is not None
        assert retrieved["pk"] == sample_vector_record["pk"]
        assert retrieved["text"] == sample_vector_record["text"]

    def test_insert_and_delete_vector(
        self,
        vector_manager: VectorManager,
        index_manager: "IndexManager",
        test_collection: str,
        sample_vector_record: dict,
    ) -> None:
        """Test inserting and deleting a vector."""
        import time

        from apps.milvus_database_controller.managers.index_manager import IndexManager

        # Load collection
        index_manager.load_collection(test_collection)

        # Insert vector
        request = InsertVectorsRequest(
            collection_name=test_collection,
            data=[sample_vector_record],
        )
        insert_result = vector_manager.insert_vectors(request)
        assert insert_result.inserted_count == 1

        # Wait for Milvus to persist data
        time.sleep(0.5)

        # Delete vector
        delete_request = DeleteVectorsRequest(
            collection_name=test_collection,
            ids=[sample_vector_record["pk"]],
        )
        delete_result = vector_manager.delete_vectors(delete_request)
        assert delete_result.deleted_count == 1

        # Wait for deletion to take effect
        time.sleep(0.5)

        # Verify deleted
        get_request = GetVectorRequest(
            collection_name=test_collection,
            pk=sample_vector_record["pk"],
        )
        retrieved = vector_manager.get_vector(get_request)
        assert retrieved is None

    def test_upsert_vector(
        self,
        vector_manager: VectorManager,
        index_manager: "IndexManager",
        test_collection: str,
        sample_vector_record: dict,
    ) -> None:
        """Test upserting a vector."""
        import time

        from apps.milvus_database_controller.managers.index_manager import IndexManager

        # Load collection
        index_manager.load_collection(test_collection)

        # Insert first
        insert_request = InsertVectorsRequest(
            collection_name=test_collection,
            data=[sample_vector_record],
        )
        insert_result = vector_manager.insert_vectors(insert_request)
        assert insert_result.inserted_count == 1

        # Wait for Milvus to persist data
        time.sleep(0.5)

        # Update via upsert
        updated_record = sample_vector_record.copy()
        updated_record["text"] = "Updated text content"

        upsert_request = UpsertVectorsRequest(
            collection_name=test_collection,
            data=[updated_record],
        )
        upsert_result = vector_manager.upsert_vectors(upsert_request)
        assert upsert_result.upserted_count == 1

        # Wait for upsert to take effect
        time.sleep(0.5)

        # Verify updated
        get_request = GetVectorRequest(
            collection_name=test_collection,
            pk=sample_vector_record["pk"],
        )
        retrieved = vector_manager.get_vector(get_request)
        assert retrieved is not None
        assert retrieved["text"] == "Updated text content"
