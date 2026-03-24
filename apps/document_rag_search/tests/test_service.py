"""
Unit tests for SearchService.

This module tests the SearchService facade class, which coordinates
multiple retrievers and applies RRF fusion.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from apps.document_rag_search.constants import RetrieverName
from apps.document_rag_search.dto import (
    AdvancedSearchRequest,
    HybridSearchRequest,
    RankedResult,
    RetrieverResult,
    SearchQuery,
    SearchResponse,
    SearchSuggestionsRequest,
)
from apps.document_rag_search.exceptions import (
    EmptyQueryError,
    InvalidDateRangeError,
    NoResultsError,
    QueryTooLongError,
    QueryTooShortError,
    SearchServiceError,
)
from apps.document_rag_search.services import SearchService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def search_service(mock_embedding_service):
    """Create a SearchService with mocked dependencies.

    Args:
        mock_embedding_service: Mock embedding service fixture.

    Returns:
        SearchService: Service instance with mocked dependencies.
    """
    with patch(
        "apps.document_rag_search.services.search_service.EmbeddingService"
    ) as mock_embedding_class:
        mock_embedding_class.return_value = mock_embedding_service
        service = SearchService()
        return service


@pytest.fixture
def sample_hybrid_request():
    """Create a sample HybridSearchRequest.

    Returns:
        HybridSearchRequest: Sample request for testing.
    """
    return HybridSearchRequest(
        query="What is machine learning?",
        top_k=10,
        use_vector=True,
        use_keyword=True,
        use_graph=False,
        filters={},
        rrf_k=60,
    )


@pytest.fixture
def sample_advanced_request():
    """Create a sample AdvancedSearchRequest.

    Returns:
        AdvancedSearchRequest: Sample request for testing.
    """
    return AdvancedSearchRequest(
        query="What is machine learning?",
        top_k=10,
        use_vector=True,
        use_keyword=True,
        use_graph=False,
        user_id=None,
        document_ids=None,
        expand_context=False,
        context_window=1,
    )


@pytest.fixture
def mock_vector_result():
    """Create a mock vector retriever result.

    Returns:
        RetrieverResult: Mocked vector search result.
    """
    chunk_id = str(uuid4())
    doc_id = str(uuid4())

    return RetrieverResult(
        retriever_name=RetrieverName.VECTOR.value,
        items=[
            {
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "text": "Machine learning is a subset of AI.",
                "score": 0.92,
                "source": "ml_guide.pdf",
                "metadata": {"chunk_index": 0},
            }
        ],
        query_time_ms=50.0,
        total=1,
    )


@pytest.fixture
def mock_keyword_result():
    """Create a mock keyword retriever result.

    Returns:
        RetrieverResult: Mocked keyword search result.
    """
    chunk_id = str(uuid4())
    doc_id = str(uuid4())

    return RetrieverResult(
        retriever_name=RetrieverName.KEYWORD.value,
        items=[
            {
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "text": "Machine learning algorithms learn from data.",
                "score": 0.85,
                "source": "ml_intro.pdf",
                "metadata": {"chunk_index": 1},
            }
        ],
        query_time_ms=30.0,
        total=1,
    )


@pytest.fixture
def mock_graph_result():
    """Create a mock graph retriever result.

    Returns:
        RetrieverResult: Mocked graph search result.
    """
    chunk_id = str(uuid4())
    doc_id = str(uuid4())

    return RetrieverResult(
        retriever_name=RetrieverName.GRAPH.value,
        items=[
            {
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "text": "Deep learning is a type of machine learning.",
                "score": 0.75,
                "source": "dl_paper.pdf",
                "metadata": {"chunk_index": 2},
            }
        ],
        query_time_ms=80.0,
        total=1,
    )


# =============================================================================
# Test SearchService Initialization
# =============================================================================


class TestSearchServiceInit:
    """Tests for SearchService initialization."""

    def test_init_default_config(self, mock_embedding_service):
        """Test initialization with default configuration."""
        with patch(
            "apps.document_rag_search.services.search_service.EmbeddingService"
        ) as mock_embedding_class:
            mock_embedding_class.return_value = mock_embedding_service

            service = SearchService()

            assert service is not None
            assert service._embedding_service is not None

    def test_init_custom_config(self, mock_embedding_service):
        """Test initialization with custom configuration."""
        from apps.document_rag_search.dto import SearchConfig

        custom_config = SearchConfig(
            default_top_k=20,
            default_rrf_k=100,
        )

        with patch(
            "apps.document_rag_search.services.search_service.EmbeddingService"
        ) as mock_embedding_class:
            mock_embedding_class.return_value = mock_embedding_service

            service = SearchService(config=custom_config)

            assert service._config.default_top_k == 20
            assert service._config.default_rrf_k == 100


# =============================================================================
# Test Query Validation
# =============================================================================


class TestQueryValidation:
    """Tests for query validation."""

    def test_validate_empty_query_raises_error(self, search_service):
        """Test that empty query raises EmptyQueryError."""
        with pytest.raises(EmptyQueryError):
            search_service._validate_query("")

    def test_validate_whitespace_query_raises_error(self, search_service):
        """Test that whitespace-only query raises EmptyQueryError."""
        with pytest.raises(EmptyQueryError):
            search_service._validate_query("   ")

    def test_validate_too_short_query_raises_error(self, search_service):
        """Test that too short query raises QueryTooShortError."""
        with pytest.raises(QueryTooShortError):
            search_service._validate_query("x")

    def test_validate_too_long_query_raises_error(self, search_service):
        """Test that too long query raises QueryTooLongError."""
        long_query = "a" * 600
        with pytest.raises(QueryTooLongError):
            search_service._validate_query(long_query)

    def test_validate_valid_query_passes(self, search_service):
        """Test that valid query passes validation."""
        # Should not raise any exception
        search_service._validate_query("What is machine learning?")


# =============================================================================
# Test Filter Validation
# =============================================================================


class TestFilterValidation:
    """Tests for filter validation."""

    def test_validate_invalid_date_range_raises_error(self, search_service):
        """Test that invalid date range raises InvalidDateRangeError."""
        from datetime import datetime, timedelta

        today = datetime.now()
        yesterday = today - timedelta(days=1)

        request = AdvancedSearchRequest(
            query="test",
            date_from=today,
            date_to=yesterday,
        )

        with pytest.raises(InvalidDateRangeError):
            search_service._validate_filters(request)

    def test_validate_valid_date_range_passes(self, search_service):
        """Test that valid date range passes validation."""
        from datetime import datetime, timedelta

        today = datetime.now()
        tomorrow = today + timedelta(days=1)

        request = AdvancedSearchRequest(
            query="test",
            date_from=today,
            date_to=tomorrow,
        )

        # Should not raise any exception
        search_service._validate_filters(request)

    def test_validate_no_dates_passes(self, search_service):
        """Test that no date filter passes validation."""
        request = AdvancedSearchRequest(query="test")

        # Should not raise any exception
        search_service._validate_filters(request)


# =============================================================================
# Test Simple Search
# =============================================================================


class TestSimpleSearch:
    """Tests for simple search functionality."""

    def test_simple_search_returns_response(
        self,
        search_service,
        mock_vector_result,
    ):
        """Test that simple search returns a valid response."""
        with patch.object(
            search_service,
            "_retrieve_with_vector",
            return_value=mock_vector_result,
        ):
            response = search_service.search(
                query="What is machine learning?",
                top_k=10,
            )

            assert isinstance(response, SearchResponse)
            assert response.total >= 0
            assert response.query_time_ms >= 0

    def test_simple_search_empty_query_raises_error(self, search_service):
        """Test that simple search with empty query raises error."""
        with pytest.raises(EmptyQueryError):
            search_service.search(query="", top_k=10)


# =============================================================================
# Test Hybrid Search
# =============================================================================


class TestHybridSearch:
    """Tests for hybrid search functionality."""

    def test_hybrid_search_vector_only(
        self,
        search_service,
        mock_vector_result,
    ):
        """Test hybrid search with vector retriever only."""
        request = HybridSearchRequest(
            query="What is machine learning?",
            use_vector=True,
            use_keyword=False,
            use_graph=False,
            top_k=10,
        )

        with patch.object(
            search_service,
            "_retrieve_with_vector",
            return_value=mock_vector_result,
        ):
            response = search_service.hybrid_search(request)

            assert isinstance(response, SearchResponse)
            assert response.total == 1
            assert RetrieverName.VECTOR.value in response.retrievers_used

    def test_hybrid_search_keyword_only(
        self,
        search_service,
        mock_keyword_result,
    ):
        """Test hybrid search with keyword retriever only."""
        request = HybridSearchRequest(
            query="What is machine learning?",
            use_vector=False,
            use_keyword=True,
            use_graph=False,
            top_k=10,
        )

        with patch.object(
            search_service,
            "_retrieve_with_keyword",
            return_value=mock_keyword_result,
        ):
            response = search_service.hybrid_search(request)

            assert isinstance(response, SearchResponse)
            assert response.total == 1
            assert RetrieverName.KEYWORD.value in response.retrievers_used

    def test_hybrid_search_all_retrievers(
        self,
        search_service,
        mock_vector_result,
        mock_keyword_result,
        mock_graph_result,
    ):
        """Test hybrid search with all retrievers."""
        request = HybridSearchRequest(
            query="What is machine learning?",
            use_vector=True,
            use_keyword=True,
            use_graph=True,
            top_k=10,
        )

        with patch.object(
            search_service,
            "_retrieve_with_vector",
            return_value=mock_vector_result,
        ), patch.object(
            search_service,
            "_retrieve_with_keyword",
            return_value=mock_keyword_result,
        ), patch.object(
            search_service,
            "_retrieve_with_graph",
            return_value=mock_graph_result,
        ):
            response = search_service.hybrid_search(request)

            assert isinstance(response, SearchResponse)
            assert len(response.retrievers_used) == 3

    def test_hybrid_search_no_results_returns_empty(
        self,
        search_service,
    ):
        """Test hybrid search when no retrievers return results."""
        request = HybridSearchRequest(
            query="What is machine learning?",
            use_vector=True,
            use_keyword=True,
            use_graph=False,
            top_k=10,
        )

        with patch.object(
            search_service,
            "_retrieve_with_vector",
            return_value=None,
        ), patch.object(
            search_service,
            "_retrieve_with_keyword",
            return_value=None,
        ):
            response = search_service.hybrid_search(request)

            assert isinstance(response, SearchResponse)
            assert response.total == 0
            assert len(response.results) == 0

    def test_hybrid_search_with_user_filter(
        self,
        search_service,
        mock_vector_result,
    ):
        """Test hybrid search with user filter."""
        user_id = str(uuid4())
        request = HybridSearchRequest(
            query="What is machine learning?",
            use_vector=True,
            use_keyword=False,
            use_graph=False,
            filters={"user_id": user_id},
            top_k=10,
        )

        with patch.object(
            search_service,
            "_retrieve_with_vector",
            return_value=mock_vector_result,
        ) as mock_retrieve:
            search_service.hybrid_search(request)

            # Verify that user_id was passed to search query
            call_args = mock_retrieve.call_args
            assert call_args[0][0].user_id == user_id


# =============================================================================
# Test Advanced Search
# =============================================================================


class TestAdvancedSearch:
    """Tests for advanced search functionality."""

    def test_advanced_search_basic(
        self,
        search_service,
        mock_vector_result,
        mock_keyword_result,
    ):
        """Test advanced search with basic parameters."""
        request = AdvancedSearchRequest(
            query="What is machine learning?",
            use_vector=True,
            use_keyword=True,
            use_graph=False,
            top_k=10,
        )

        with patch.object(
            search_service,
            "_retrieve_with_vector",
            return_value=mock_vector_result,
        ), patch.object(
            search_service,
            "_retrieve_with_keyword",
            return_value=mock_keyword_result,
        ):
            response = search_service.advanced_search(request)

            assert isinstance(response, SearchResponse)
            assert response.total >= 0

    def test_advanced_search_with_user_filter(
        self,
        search_service,
        mock_vector_result,
    ):
        """Test advanced search with user filter."""
        user_id = str(uuid4())
        request = AdvancedSearchRequest(
            query="What is machine learning?",
            user_id=user_id,
            use_vector=True,
            use_keyword=False,
            use_graph=False,
            top_k=10,
        )

        with patch.object(
            search_service,
            "_retrieve_with_vector",
            return_value=mock_vector_result,
        ):
            response = search_service.advanced_search(request)

            assert isinstance(response, SearchResponse)


# =============================================================================
# Test Search Suggestions
# =============================================================================


class TestSearchSuggestions:
    """Tests for search suggestions functionality."""

    def test_get_search_suggestions_returns_response(
        self,
        search_service,
    ):
        """Test that get_search_suggestions returns a valid response."""
        request = SearchSuggestionsRequest(
            prefix="mach",
            limit=5,
        )

        # Create a mock that supports the full chain:
        # objects.filter().distinct().order_by()[:n].values_list()
        mock_queryset = MagicMock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.distinct.return_value = mock_queryset
        mock_queryset.order_by.return_value = mock_queryset

        # After slicing, we need a mock that has values_list
        mock_sliced = MagicMock()
        mock_sliced.values_list.return_value = []
        mock_queryset.__getitem__.return_value = mock_sliced

        with patch(
            "apps.documents_parser.models.DocumentChunk.objects",
            mock_queryset,
        ):
            response = search_service.get_search_suggestions(request)

            assert response.total >= 0
            assert isinstance(response.suggestions, list)

    def test_get_search_suggestions_with_results(
        self,
        search_service,
    ):
        """Test search suggestions with mock results."""
        request = SearchSuggestionsRequest(
            prefix="mach",
            limit=5,
        )

        # Create a mock that supports the full chain
        mock_queryset = MagicMock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.distinct.return_value = mock_queryset
        mock_queryset.order_by.return_value = mock_queryset

        # After slicing, we need a mock that has values_list returning content
        mock_sliced = MagicMock()
        mock_sliced.values_list.return_value = [
            "machine learning is a subset of AI",
            "machine algorithms process data",
        ]
        mock_queryset.__getitem__.return_value = mock_sliced

        with patch(
            "apps.documents_parser.models.DocumentChunk.objects",
            mock_queryset,
        ):
            response = search_service.get_search_suggestions(request)

            assert isinstance(response.suggestions, list)


# =============================================================================
# Test Health Check
# =============================================================================


class TestHealthCheck:
    """Tests for health check functionality."""

    def test_health_check_all_healthy(self, search_service):
        """Test health check when all retrievers are healthy."""
        with patch.object(
            search_service.vector_retriever,
            "health_check",
            return_value=True,
        ), patch.object(
            search_service.keyword_retriever,
            "health_check",
            return_value=True,
        ), patch.object(
            search_service.graph_retriever,
            "health_check",
            return_value=True,
        ):
            health = search_service.health_check()

            assert health["vector"] is True
            assert health["keyword"] is True
            assert health["graph"] is True
            assert health["overall"] is True

    def test_health_check_partial_failure(self, search_service):
        """Test health check when some retrievers fail."""
        with patch.object(
            search_service.vector_retriever,
            "health_check",
            return_value=True,
        ), patch.object(
            search_service.keyword_retriever,
            "health_check",
            return_value=False,
        ), patch.object(
            search_service.graph_retriever,
            "health_check",
            side_effect=Exception("Connection error"),
        ):
            health = search_service.health_check()

            assert health["vector"] is True
            assert health["keyword"] is False
            assert health["graph"] is False
            assert health["overall"] is True  # At least one healthy


# =============================================================================
# Test RRF Fusion Integration
# =============================================================================


class TestRRFFusionIntegration:
    """Tests for RRF fusion integration in SearchService."""

    def test_apply_rrf_fusion_basic(
        self,
        search_service,
        mock_vector_result,
        mock_keyword_result,
    ):
        """Test RRF fusion with two retrievers."""
        retriever_results = {
            RetrieverName.VECTOR.value: mock_vector_result,
            RetrieverName.KEYWORD.value: mock_keyword_result,
        }

        ranked_results = search_service._apply_rrf_fusion(
            retriever_results=retriever_results,
            top_k=10,
        )

        assert isinstance(ranked_results, list)
        assert all(isinstance(r, RankedResult) for r in ranked_results)
        # Results should be sorted by score descending
        if len(ranked_results) > 1:
            assert ranked_results[0].score >= ranked_results[-1].score

    def test_apply_rrf_fusion_with_custom_weights(
        self,
        search_service,
        mock_vector_result,
        mock_keyword_result,
    ):
        """Test RRF fusion with custom weights."""
        retriever_results = {
            RetrieverName.VECTOR.value: mock_vector_result,
            RetrieverName.KEYWORD.value: mock_keyword_result,
        }

        custom_weights = {
            RetrieverName.VECTOR.value: 0.8,
            RetrieverName.KEYWORD.value: 0.2,
        }

        ranked_results = search_service._apply_rrf_fusion(
            retriever_results=retriever_results,
            top_k=10,
            weights=custom_weights,
        )

        assert isinstance(ranked_results, list)


# =============================================================================
# Test Helper Methods
# =============================================================================


class TestHelperMethods:
    """Tests for helper methods."""

    def test_convert_to_search_items(
        self,
        search_service,
    ):
        """Test conversion of RankedResult to SearchResultItem."""
        ranked_results = [
            RankedResult(
                chunk_id=str(uuid4()),
                document_id=str(uuid4()),
                text="Sample text",
                score=0.95,
                source="test.pdf",
                metadata={"chunk_index": 0},
                retriever_scores={"vector": 0.92},
            )
        ]

        search_items = search_service._convert_to_search_items(ranked_results)

        assert len(search_items) == 1
        assert search_items[0].chunk_id == ranked_results[0].chunk_id
        assert search_items[0].score == ranked_results[0].score

    def test_create_empty_response(
        self,
        search_service,
    ):
        """Test creation of empty search response."""
        response = search_service._create_empty_response(
            query_time_ms=10.0,
            retrievers_used=["vector"],
        )

        assert response.total == 0
        assert len(response.results) == 0
        assert response.query_time_ms == 10.0
        assert response.retrievers_used == ["vector"]


# =============================================================================
# Test Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    def test_hybrid_search_handles_retriever_exception(
        self,
        search_service,
    ):
        """Test that hybrid search handles retriever exceptions gracefully."""
        request = HybridSearchRequest(
            query="What is machine learning?",
            use_vector=True,
            use_keyword=False,
            use_graph=False,
            top_k=10,
        )

        with patch.object(
            search_service,
            "_retrieve_with_vector",
            return_value=None,  # Simulate retriever failure
        ):
            response = search_service.hybrid_search(request)

            # Should return empty response, not raise exception
            assert response.total == 0


# =============================================================================
# Test Retriever Exception Handling
# =============================================================================


class TestRetrieverExceptionHandling:
    """Tests for retriever exception handling."""

    def test_retrieve_with_vector_exception(self, search_service):
        """Test _retrieve_with_vector handles exceptions."""
        with patch.object(
            search_service.vector_retriever,
            "retrieve",
            side_effect=Exception("Vector error"),
        ):
            result = search_service._retrieve_with_vector(
                query=SearchQuery(text="test"),
                top_k=10,
            )
            assert result is None

    def test_retrieve_with_keyword_exception(self, search_service):
        """Test _retrieve_with_keyword handles exceptions."""
        with patch.object(
            search_service.keyword_retriever,
            "retrieve",
            side_effect=Exception("Keyword error"),
        ):
            result = search_service._retrieve_with_keyword(
                query=SearchQuery(text="test"),
                top_k=10,
            )
            assert result is None

    def test_retrieve_with_graph_exception(self, search_service):
        """Test _retrieve_with_graph handles exceptions."""
        with patch.object(
            search_service.graph_retriever,
            "retrieve",
            side_effect=Exception("Graph error"),
        ):
            result = search_service._retrieve_with_graph(
                query=SearchQuery(text="test"),
                top_k=10,
            )
            assert result is None
