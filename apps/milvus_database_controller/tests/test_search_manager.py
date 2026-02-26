"""
Tests for SearchManager.

This module tests search operations including single vector search,
hybrid search, and BM25 text search.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from apps.milvus_database_controller.constants import (
    DEFAULT_TOP_K,
    FieldName,
)
from apps.milvus_database_controller.dto import (
    BM25SearchRequest,
    HybridSearchRequest,
    SearchRequest,
)
from apps.milvus_database_controller.exceptions import (
    CollectionNotFoundError,
    HybridSearchError,
    SearchError,
)
from apps.milvus_database_controller.managers.search_manager import SearchManager

if TYPE_CHECKING:
    pass


@pytest.mark.unit
class TestSearchManager:
    """Test SearchManager class."""

    def test_init_with_client(self) -> None:
        """Test initialization with provided client."""
        mock_client = MagicMock()
        manager = SearchManager(client=mock_client)
        assert manager._client is mock_client

    @patch("apps.milvus_database_controller.managers.search_manager.MilvusClientWrapper")
    def test_init_without_client(self, mock_wrapper: MagicMock) -> None:
        """Test initialization without client (uses singleton)."""
        mock_instance = MagicMock()
        mock_wrapper.get_instance.return_value = mock_instance

        manager = SearchManager()
        assert manager._client is mock_instance


@pytest.mark.unit
class TestSingleSearch:
    """Test single vector field search."""

    @patch("apps.milvus_database_controller.managers.search_manager.MilvusClientWrapper")
    def test_search_success(self, mock_wrapper: MagicMock) -> None:
        """Test successful search operation."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.search.return_value = [[
            {
                "id": "id1",
                "distance": 0.1,
                "text": "Sample text",
                "summary": "Sample summary",
                "source": "test",
            }
        ]]
        mock_wrapper.get_instance.return_value = mock_client

        manager = SearchManager()
        request = SearchRequest(
            collection_name="test_collection",
            query_vector=[0.1] * 1536,
            anns_field=FieldName.TEXT_DENSE.value,
            top_k=10,
        )

        result = manager.search(request)

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].id == "id1"
        assert result.items[0].distance == 0.1
        assert result.query_time_ms > 0

    @patch("apps.milvus_database_controller.managers.search_manager.MilvusClientWrapper")
    def test_search_with_filter(self, mock_wrapper: MagicMock) -> None:
        """Test search with filter expression."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.search.return_value = [[]]
        mock_wrapper.get_instance.return_value = mock_client

        manager = SearchManager()
        request = SearchRequest(
            collection_name="test_collection",
            query_vector=[0.1] * 1536,
            anns_field=FieldName.TEXT_DENSE.value,
            top_k=10,
            filter_expr=f'{FieldName.SOURCE.value} == "test"',
        )

        result = manager.search(request)

        # Verify filter was passed to client
        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["filter_expr"] == f'{FieldName.SOURCE.value} == "test"'

    @patch("apps.milvus_database_controller.managers.search_manager.MilvusClientWrapper")
    def test_search_collection_not_found(self, mock_wrapper: MagicMock) -> None:
        """Test search raises error when collection not found."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_wrapper.get_instance.return_value = mock_client

        manager = SearchManager()
        request = SearchRequest(
            collection_name="non_existent",
            query_vector=[0.1] * 1536,
            anns_field=FieldName.TEXT_DENSE.value,
        )

        with pytest.raises(CollectionNotFoundError):
            manager.search(request)

    @patch("apps.milvus_database_controller.managers.search_manager.MilvusClientWrapper")
    def test_search_failure(self, mock_wrapper: MagicMock) -> None:
        """Test search raises error on failure."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.search.side_effect = Exception("Search failed")
        mock_wrapper.get_instance.return_value = mock_client

        manager = SearchManager()
        request = SearchRequest(
            collection_name="test_collection",
            query_vector=[0.1] * 1536,
            anns_field=FieldName.TEXT_DENSE.value,
        )

        with pytest.raises(SearchError) as exc_info:
            manager.search(request)

        assert "Search failed" in exc_info.value.reason

    @patch("apps.milvus_database_controller.managers.search_manager.MilvusClientWrapper")
    def test_search_custom_output_fields(self, mock_wrapper: MagicMock) -> None:
        """Test search with custom output fields."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.search.return_value = [[]]
        mock_wrapper.get_instance.return_value = mock_client

        manager = SearchManager()
        request = SearchRequest(
            collection_name="test_collection",
            query_vector=[0.1] * 1536,
            anns_field=FieldName.TEXT_DENSE.value,
            output_fields=["pk", "text"],
        )

        manager.search(request)

        call_kwargs = mock_client.search.call_args[1]
        assert "pk" in call_kwargs["output_fields"]
        assert "text" in call_kwargs["output_fields"]


@pytest.mark.unit
class TestHybridSearch:
    """Test hybrid search across multiple vector fields."""

    @patch("apps.milvus_database_controller.managers.search_manager.MilvusClientWrapper")
    def test_hybrid_search_rrf(self, mock_wrapper: MagicMock) -> None:
        """Test hybrid search with RRF fusion."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True

        # Mock search results for both fields
        def mock_search(**kwargs):
            field = kwargs["anns_field"]
            if field == FieldName.SUMMARY_DENSE.value:
                return [[
                    {"id": "id1", "distance": 0.1, "text": "text1"},
                    {"id": "id2", "distance": 0.2, "text": "text2"},
                ]]
            else:
                return [[
                    {"id": "id2", "distance": 0.1, "text": "text2"},
                    {"id": "id3", "distance": 0.3, "text": "text3"},
                ]]

        mock_client.search.side_effect = mock_search
        mock_wrapper.get_instance.return_value = mock_client

        manager = SearchManager()
        request = HybridSearchRequest(
            collection_name="test_collection",
            query_text="test query",
            query_vectors={
                FieldName.SUMMARY_DENSE.value: [0.1] * 1536,
                FieldName.TEXT_DENSE.value: [0.2] * 1536,
            },
            top_k=5,
            rerank_method="rrf",
        )

        result = manager.hybrid_search(request)

        assert result.total > 0
        assert result.search_details["method"] == "rrf"
        # Should have called search twice (once per field)
        assert mock_client.search.call_count == 2

    @patch("apps.milvus_database_controller.managers.search_manager.MilvusClientWrapper")
    def test_hybrid_search_weighted(self, mock_wrapper: MagicMock) -> None:
        """Test hybrid search with weighted fusion."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.search.return_value = [[
            {"id": "id1", "distance": 0.1, "text": "text1"},
        ]]
        mock_wrapper.get_instance.return_value = mock_client

        manager = SearchManager()
        request = HybridSearchRequest(
            collection_name="test_collection",
            query_text="test query",
            query_vectors={
                FieldName.SUMMARY_DENSE.value: [0.1] * 1536,
                FieldName.TEXT_DENSE.value: [0.2] * 1536,
            },
            top_k=5,
            rerank_method="weighted",
            weights=[0.6, 0.4],
        )

        result = manager.hybrid_search(request)

        assert result.search_details["method"] == "weighted"

    @patch("apps.milvus_database_controller.managers.search_manager.MilvusClientWrapper")
    def test_hybrid_search_collection_not_found(self, mock_wrapper: MagicMock) -> None:
        """Test hybrid search raises error when collection not found."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = False
        mock_wrapper.get_instance.return_value = mock_client

        manager = SearchManager()
        request = HybridSearchRequest(
            collection_name="non_existent",
            query_text="test query",
            query_vectors={FieldName.TEXT_DENSE.value: [0.1] * 1536},
        )

        with pytest.raises(CollectionNotFoundError):
            manager.hybrid_search(request)


@pytest.mark.unit
class TestRRFFusion:
    """Test Reciprocal Rank Fusion algorithm."""

    def test_rrf_combines_ranks(self) -> None:
        """Test RRF correctly combines ranks from multiple lists."""
        mock_client = MagicMock()
        manager = SearchManager(client=mock_client)

        all_results = {
            "field1": [
                {"id": "a", "distance": 0.1},
                {"id": "b", "distance": 0.2},
                {"id": "c", "distance": 0.3},
            ],
            "field2": [
                {"id": "b", "distance": 0.1},
                {"id": "a", "distance": 0.2},
                {"id": "d", "distance": 0.3},
            ],
        }

        result = manager._reciprocal_rank_fusion(all_results, k=60, top_k=10)

        # 'a' and 'b' appear in both lists, should rank higher
        ids = [item.id for item in result]
        assert "a" in ids
        assert "b" in ids
        # Items in both lists should rank higher
        assert ids.index("a") < ids.index("c") or "c" not in ids
        assert ids.index("b") < ids.index("d") or "d" not in ids

    def test_rrf_respects_top_k(self) -> None:
        """Test RRF respects top_k parameter."""
        mock_client = MagicMock()
        manager = SearchManager(client=mock_client)

        all_results = {
            "field1": [{"id": f"item{i}", "distance": 0.1} for i in range(20)],
        }

        result = manager._reciprocal_rank_fusion(all_results, k=60, top_k=5)

        assert len(result) == 5


@pytest.mark.unit
class TestWeightedFusion:
    """Test weighted fusion algorithm."""

    def test_weighted_fusion_applies_weights(self) -> None:
        """Test weighted fusion correctly applies weights."""
        mock_client = MagicMock()
        manager = SearchManager(client=mock_client)

        all_results = {
            "field1": [
                {"id": "a", "distance": 0.0},  # Perfect match
                {"id": "b", "distance": 1.0},  # Worst match
            ],
            "field2": [
                {"id": "a", "distance": 0.0},
                {"id": "b", "distance": 0.0},  # Good match in field2
            ],
        }

        # Give more weight to field1
        result = manager._weighted_fusion(all_results, weights=[0.8, 0.2], top_k=10)

        # 'a' should rank higher due to better field1 performance and weight
        assert result[0].id == "a"

    def test_weighted_fusion_equal_weights(self) -> None:
        """Test weighted fusion with equal weights."""
        mock_client = MagicMock()
        manager = SearchManager(client=mock_client)

        all_results = {
            "field1": [{"id": "a", "distance": 0.5}],
            "field2": [{"id": "b", "distance": 0.5}],
        }

        # Equal weights (default)
        result = manager._weighted_fusion(all_results, weights=None, top_k=10)

        # Both should have equal scores
        assert len(result) == 2


@pytest.mark.unit
class TestBM25Search:
    """Test BM25 sparse vector search."""

    @patch("apps.milvus_database_controller.managers.search_manager.MilvusClientWrapper")
    def test_bm25_search_placeholder(self, mock_wrapper: MagicMock) -> None:
        """Test BM25 search returns placeholder (requires embedding service)."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_wrapper.get_instance.return_value = mock_client

        manager = SearchManager()
        request = BM25SearchRequest(
            collection_name="test_collection",
            query_text="test query",
        )

        # BM25 search is not fully implemented yet
        result = manager.bm25_search(request)

        # Should return empty results for now
        assert result.total == 0
        assert len(result.items) == 0


@pytest.mark.unit
class TestSearchHelpers:
    """Test search helper methods."""

    @patch("apps.milvus_database_controller.managers.search_manager.MilvusClientWrapper")
    def test_search_by_document(self, mock_wrapper: MagicMock) -> None:
        """Test search within a specific document."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.search.return_value = [[
            {"id": "id1", "distance": 0.1, "text": "text1"},
        ]]
        mock_wrapper.get_instance.return_value = mock_client

        manager = SearchManager()
        result = manager.search_by_document(
            collection_name="test_collection",
            document_id="doc-001",
            query_vector=[0.1] * 1536,
        )

        # Verify filter was applied
        call_kwargs = mock_client.search.call_args[1]
        assert "doc-001" in call_kwargs["filter_expr"]

    @patch("apps.milvus_database_controller.managers.search_manager.MilvusClientWrapper")
    def test_search_by_source(self, mock_wrapper: MagicMock) -> None:
        """Test search within a specific source type."""
        mock_client = MagicMock()
        mock_client.has_collection.return_value = True
        mock_client.search.return_value = [[]]
        mock_wrapper.get_instance.return_value = mock_client

        manager = SearchManager()
        result = manager.search_by_source(
            collection_name="test_collection",
            source_type="upload",
            query_vector=[0.1] * 1536,
        )

        # Verify filter was applied
        call_kwargs = mock_client.search.call_args[1]
        assert "upload" in call_kwargs["filter_expr"]


@pytest.mark.integration
class TestSearchManagerIntegration:
    """Integration tests for SearchManager (requires running Milvus)."""

    def test_single_vector_search(
        self,
        search_manager: SearchManager,
        vector_manager: "VectorManager",
        index_manager: "IndexManager",
        test_collection: str,
        sample_vector_records: list[dict],
    ) -> None:
        """Test single vector search with real Milvus."""
        import time

        from apps.milvus_database_controller.dto import InsertVectorsRequest
        from apps.milvus_database_controller.managers.index_manager import IndexManager
        from apps.milvus_database_controller.managers.vector_manager import VectorManager

        # Insert test data
        request = InsertVectorsRequest(
            collection_name=test_collection,
            data=sample_vector_records,
        )
        insert_result = vector_manager.insert_vectors(request)
        assert insert_result.inserted_count > 0

        # Wait for Milvus eventual consistency
        time.sleep(0.5)

        # Load collection
        index_manager.load_collection(test_collection)

        # Perform search
        import random
        query_vector = [random.random() for _ in range(1536)]

        search_request = SearchRequest(
            collection_name=test_collection,
            query_vector=query_vector,
            anns_field=FieldName.TEXT_DENSE.value,
            top_k=5,
        )

        result = search_manager.search(search_request)

        assert result.total > 0
        assert len(result.items) <= 5
        assert result.query_time_ms > 0

    def test_hybrid_search_integration(
        self,
        search_manager: SearchManager,
        vector_manager: "VectorManager",
        index_manager: "IndexManager",
        test_collection: str,
        sample_vector_records: list[dict],
    ) -> None:
        """Test hybrid search with real Milvus."""
        import time

        from apps.milvus_database_controller.dto import InsertVectorsRequest
        from apps.milvus_database_controller.managers.index_manager import IndexManager
        from apps.milvus_database_controller.managers.vector_manager import VectorManager

        # Insert test data
        request = InsertVectorsRequest(
            collection_name=test_collection,
            data=sample_vector_records,
        )
        vector_manager.insert_vectors(request)

        # Wait for Milvus eventual consistency
        time.sleep(0.5)

        # Load collection
        index_manager.load_collection(test_collection)

        # Perform hybrid search
        import random
        query_vector = [random.random() for _ in range(1536)]

        hybrid_request = HybridSearchRequest(
            collection_name=test_collection,
            query_text="test query",
            query_vectors={
                FieldName.SUMMARY_DENSE.value: query_vector,
                FieldName.TEXT_DENSE.value: query_vector,
            },
            top_k=5,
        )

        result = search_manager.hybrid_search(hybrid_request)

        assert result.total > 0  # Should find results after consistency delay
        assert result.search_details["method"] == "rrf"
