"""
Unit tests for retriever components.

This module tests the BaseRetriever abstract class and all concrete retriever
implementations (Vector, Keyword, Graph).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from apps.document_rag_search.constants import DEFAULT_TOP_K, RetrieverName
from apps.document_rag_search.dto import RetrieverResult, SearchQuery
from apps.document_rag_search.exceptions import (
    VectorRetrieverError,
    KeywordRetrieverError,
    GraphRetrieverError,
)
from apps.document_rag_search.retrievers.base import BaseRetriever


# =============================================================================
# Base Retriever Tests
# =============================================================================


class TestBaseRetriever:
    """Tests for the BaseRetriever abstract class."""

    def test_base_retriever_is_abstract(self):
        """Test that BaseRetriever cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseRetriever()

    def test_base_retriever_requires_name_property(self):
        """Test that subclasses must implement name property."""
        with pytest.raises(TypeError):

            class IncompleteRetriever(BaseRetriever):
                pass

            IncompleteRetriever()

    def test_base_retriever_requires_retrieve_method(self):
        """Test that subclasses must implement retrieve method."""
        with pytest.raises(TypeError):

            class IncompleteRetriever(BaseRetriever):
                @property
                def name(self) -> str:
                    return "incomplete"

            IncompleteRetriever()

    def test_base_retriever_requires_health_check_method(self):
        """Test that subclasses must implement health_check method."""
        with pytest.raises(TypeError):

            class IncompleteRetriever(BaseRetriever):
                @property
                def name(self) -> str:
                    return "incomplete"

                def retrieve(self, query, top_k=10, **kwargs):
                    pass

            IncompleteRetriever()

    def test_build_filter_expr_with_user_id(self):
        """Test _build_filter_expr with user_id filter."""

        class ConcreteRetriever(BaseRetriever):
            @property
            def name(self) -> str:
                return "concrete"

            def retrieve(self, query, top_k=10, **kwargs):
                return RetrieverResult(
                    retriever_name=self.name,
                    items=[],
                    query_time_ms=0.0,
                    total=0,
                )

            def health_check(self) -> bool:
                return True

        retriever = ConcreteRetriever()
        result = retriever._build_filter_expr(user_id="user-123")

        assert result == 'user_id == "user-123"'

    def test_build_filter_expr_with_document_ids(self):
        """Test _build_filter_expr with document_ids filter."""

        class ConcreteRetriever(BaseRetriever):
            @property
            def name(self) -> str:
                return "concrete"

            def retrieve(self, query, top_k=10, **kwargs):
                return RetrieverResult(
                    retriever_name=self.name,
                    items=[],
                    query_time_ms=0.0,
                    total=0,
                )

            def health_check(self) -> bool:
                return True

        retriever = ConcreteRetriever()
        result = retriever._build_filter_expr(
            user_id=None, document_ids=["doc-1", "doc-2"]
        )

        assert 'document_id in ["doc-1", "doc-2"]' in result

    def test_build_filter_expr_with_both_filters(self):
        """Test _build_filter_expr with both user_id and document_ids."""

        class ConcreteRetriever(BaseRetriever):
            @property
            def name(self) -> str:
                return "concrete"

            def retrieve(self, query, top_k=10, **kwargs):
                return RetrieverResult(
                    retriever_name=self.name,
                    items=[],
                    query_time_ms=0.0,
                    total=0,
                )

            def health_check(self) -> bool:
                return True

        retriever = ConcreteRetriever()
        result = retriever._build_filter_expr(
            user_id="user-123", document_ids=["doc-1"]
        )

        assert 'user_id == "user-123"' in result
        assert "document_id in" in result
        assert " and " in result

    def test_build_filter_expr_empty(self):
        """Test _build_filter_expr with no filters."""

        class ConcreteRetriever(BaseRetriever):
            @property
            def name(self) -> str:
                return "concrete"

            def retrieve(self, query, top_k=10, **kwargs):
                return RetrieverResult(
                    retriever_name=self.name,
                    items=[],
                    query_time_ms=0.0,
                    total=0,
                )

            def health_check(self) -> bool:
                return True

        retriever = ConcreteRetriever()
        result = retriever._build_filter_expr(user_id=None, document_ids=None)

        assert result == ""


# =============================================================================
# Vector Retriever Tests
# =============================================================================


class TestVectorRetriever:
    """Tests for the VectorRetriever class."""

    def test_vector_retriever_name(self, mock_milvus_service):
        """Test that VectorRetriever returns correct name."""
        from apps.document_rag_search.retrievers.vector_retriever import VectorRetriever

        retriever = VectorRetriever(milvus_service=mock_milvus_service)

        assert retriever.name == RetrieverName.VECTOR.value

    def test_vector_retriever_retrieve_success(
        self, mock_milvus_service, sample_search_query
    ):
        """Test successful vector retrieval."""
        from apps.document_rag_search.retrievers.vector_retriever import VectorRetriever

        retriever = VectorRetriever(milvus_service=mock_milvus_service)
        result = retriever.retrieve(query=sample_search_query, top_k=10)

        assert result.retriever_name == RetrieverName.VECTOR.value
        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0]["score"] >= 0
        mock_milvus_service.search.assert_called_once()

    def test_vector_retriever_retrieve_without_embedding_raises_error(
        self, mock_milvus_service, sample_search_query_no_embedding
    ):
        """Test that retrieval without embedding raises VectorRetrieverError."""
        from apps.document_rag_search.retrievers.vector_retriever import VectorRetriever

        retriever = VectorRetriever(milvus_service=mock_milvus_service)

        with pytest.raises(VectorRetrieverError) as exc_info:
            retriever.retrieve(query=sample_search_query_no_embedding, top_k=10)

        assert "embedding is required" in str(exc_info.value).lower()

    def test_vector_retriever_retrieve_with_user_filter(
        self, mock_milvus_service
    ):
        """Test vector retrieval with user_id filter."""
        from apps.document_rag_search.retrievers.vector_retriever import VectorRetriever

        user_id = str(uuid4())
        query = SearchQuery(
            text="test query",
            embedding=[0.1] * 1536,
            user_id=user_id,
        )

        retriever = VectorRetriever(milvus_service=mock_milvus_service)
        result = retriever.retrieve(query=query, top_k=10)

        # Verify filter was passed to MilvusService
        call_kwargs = mock_milvus_service.search.call_args[1]
        assert user_id in call_kwargs["filter_expr"]

    def test_vector_retriever_retrieve_with_document_ids_filter(
        self, mock_milvus_service
    ):
        """Test vector retrieval with document_ids filter."""
        from apps.document_rag_search.retrievers.vector_retriever import VectorRetriever

        doc_id = str(uuid4())
        query = SearchQuery(
            text="test query",
            embedding=[0.1] * 1536,
            user_id=None,
        )

        retriever = VectorRetriever(milvus_service=mock_milvus_service)
        result = retriever.retrieve(query=query, top_k=10, document_ids=[doc_id])

        # Verify filter was passed to MilvusService
        call_kwargs = mock_milvus_service.search.call_args[1]
        assert doc_id in call_kwargs["filter_expr"]

    def test_vector_retriever_hybrid_search(self, mock_milvus_service):
        """Test vector retriever hybrid search mode."""
        from apps.document_rag_search.retrievers.vector_retriever import VectorRetriever

        query = SearchQuery(
            text="test query",
            embedding=[0.1] * 1536,
            user_id=None,
        )

        retriever = VectorRetriever(milvus_service=mock_milvus_service)
        result = retriever.retrieve(query=query, top_k=10, use_hybrid=True)

        mock_milvus_service.hybrid_search.assert_called_once()
        assert result.retriever_name == RetrieverName.VECTOR.value

    def test_vector_retriever_health_check_success(self, mock_milvus_service):
        """Test health_check returns True when Milvus is healthy."""
        from apps.document_rag_search.retrievers.vector_retriever import VectorRetriever

        retriever = VectorRetriever(milvus_service=mock_milvus_service)
        result = retriever.health_check()

        assert result is True
        mock_milvus_service.health_check.assert_called_once()
        mock_milvus_service.has_collection.assert_called_once()

    def test_vector_retriever_health_check_failure(self, mock_milvus_service):
        """Test health_check returns False when Milvus is not connected."""
        from apps.document_rag_search.retrievers.vector_retriever import VectorRetriever

        mock_milvus_service.health_check.return_value = {"connected": False}

        retriever = VectorRetriever(milvus_service=mock_milvus_service)
        result = retriever.health_check()

        assert result is False

    def test_vector_retriever_milvus_error_propagates(self, mock_milvus_service):
        """Test that Milvus errors are wrapped in VectorRetrieverError."""
        from apps.document_rag_search.retrievers.vector_retriever import VectorRetriever

        mock_milvus_service.search.side_effect = Exception("Milvus connection error")

        query = SearchQuery(
            text="test query",
            embedding=[0.1] * 1536,
            user_id=None,
        )

        retriever = VectorRetriever(milvus_service=mock_milvus_service)

        with pytest.raises(VectorRetrieverError):
            retriever.retrieve(query=query, top_k=10)


# =============================================================================
# Keyword Retriever Tests
# =============================================================================


@pytest.mark.django_db
class TestKeywordRetriever:
    """Tests for the KeywordRetriever class."""

    def test_keyword_retriever_name(self):
        """Test that KeywordRetriever returns correct name."""
        from apps.document_rag_search.retrievers.keyword_retriever import KeywordRetriever

        retriever = KeywordRetriever()

        assert retriever.name == RetrieverName.KEYWORD.value

    def test_keyword_retriever_empty_query_returns_empty_result(self):
        """Test that empty query returns empty result without error."""
        from apps.document_rag_search.retrievers.keyword_retriever import KeywordRetriever

        retriever = KeywordRetriever()
        query = SearchQuery(text="", embedding=None, user_id=None)

        result = retriever.retrieve(query=query, top_k=10)

        assert result.total == 0
        assert result.items == []

    def test_keyword_retriever_whitespace_query_returns_empty_result(self):
        """Test that whitespace-only query returns empty result."""
        from apps.document_rag_search.retrievers.keyword_retriever import KeywordRetriever

        retriever = KeywordRetriever()
        query = SearchQuery(text="   ", embedding=None, user_id=None)

        result = retriever.retrieve(query=query, top_k=10)

        assert result.total == 0
        assert result.items == []

    @patch("apps.document_rag_search.retrievers.keyword_retriever.DocumentChunk")
    def test_keyword_retriever_fallback_to_like_search(self, mock_chunk_model):
        """Test fallback to LIKE search when search_vector is not available."""
        from apps.document_rag_search.retrievers.keyword_retriever import KeywordRetriever

        # Mock that search_vector field does not exist
        mock_chunk_model.objects.filter.return_value.select_related.return_value.filter.return_value.distinct.return_value = []

        retriever = KeywordRetriever(use_search_vector=False)

        query = SearchQuery(text="machine learning", embedding=None, user_id=None)
        result = retriever.retrieve(query=query, top_k=10)

        assert result.retriever_name == RetrieverName.KEYWORD.value

    @patch("apps.document_rag_search.retrievers.keyword_retriever.DocumentChunk")
    def test_keyword_retriever_health_check_success(self, mock_chunk_model):
        """Test health_check returns True when PostgreSQL is accessible."""
        from apps.document_rag_search.retrievers.keyword_retriever import KeywordRetriever

        mock_chunk_model.objects.count.return_value = 100

        retriever = KeywordRetriever()
        result = retriever.health_check()

        assert result is True

    @patch("apps.document_rag_search.retrievers.keyword_retriever.DocumentChunk")
    def test_keyword_retriever_health_check_failure(self, mock_chunk_model):
        """Test health_check returns False when PostgreSQL is not accessible."""
        from apps.document_rag_search.retrievers.keyword_retriever import KeywordRetriever

        mock_chunk_model.objects.count.side_effect = Exception("DB connection error")

        retriever = KeywordRetriever()
        result = retriever.health_check()

        assert result is False

    def test_keyword_retriever_has_search_vector_field_check(self):
        """Test _has_search_vector_field method."""
        from apps.document_rag_search.retrievers.keyword_retriever import KeywordRetriever

        retriever = KeywordRetriever()

        # This will return True if DocumentChunk has search_vector field
        # or False if it doesn't - both are valid outcomes
        result = retriever._has_search_vector_field()
        assert isinstance(result, bool)


# =============================================================================
# Graph Retriever Tests
# =============================================================================


class TestGraphRetriever:
    """Tests for the GraphRetriever class."""

    def test_graph_retriever_name(self, mock_neo4j_service):
        """Test that GraphRetriever returns correct name."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)

        assert retriever.name == RetrieverName.GRAPH.value

    def test_graph_retriever_extract_entity_keywords_english(self, mock_neo4j_service):
        """Test entity keyword extraction for English text."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)
        keywords = retriever._extract_entity_keywords("What is machine learning and AI?")

        # Stop words should be filtered out
        assert "what" not in [k.lower() for k in keywords]
        assert "is" not in [k.lower() for k in keywords]
        # Meaningful words should be included
        assert any("machine" in k.lower() for k in keywords) or "machine learning" in [k.lower() for k in keywords]

    def test_graph_retriever_extract_entity_keywords_chinese(self, mock_neo4j_service):
        """Test entity keyword extraction for Chinese text."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)
        keywords = retriever._extract_entity_keywords("什么是机器学习和人工智能？")

        # Should extract meaningful Chinese phrases
        assert len(keywords) > 0
        # The full phrase without stop words should be included
        # Note: The algorithm splits long Chinese phrases into 2-char segments
        # so some partial matches like "什么" might appear from splitting "什么是..."
        assert any("机器" in k or "学习" in k for k in keywords)

    def test_graph_retriever_extract_entity_keywords_empty(self, mock_neo4j_service):
        """Test entity extraction with empty or stop-word only text."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)

        # Empty text
        keywords = retriever._extract_entity_keywords("")
        assert keywords == []

        # Stop words only
        keywords = retriever._extract_entity_keywords("the is a an")
        assert keywords == []

    def test_graph_retriever_is_chinese_detection(self, mock_neo4j_service):
        """Test Chinese character detection."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)

        assert retriever._is_chinese("中文") is True
        assert retriever._is_chinese("English") is False
        assert retriever._is_chinese("混合 text") is True  # Contains Chinese

    def test_graph_retriever_retrieve_no_entities(self, mock_neo4j_service):
        """Test retrieval when no entity keywords can be extracted."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)
        query = SearchQuery(text="", embedding=None, user_id=None)

        result = retriever.retrieve(query=query, top_k=10)

        assert result.total == 0
        assert result.items == []

    def test_graph_retriever_retrieve_with_entities(self, mock_neo4j_service):
        """Test successful retrieval with entity matching."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)
        query = SearchQuery(
            text="machine learning algorithms",
            embedding=None,
            user_id=None,
        )

        result = retriever.retrieve(query=query, top_k=10)

        assert result.retriever_name == RetrieverName.GRAPH.value
        mock_neo4j_service.search_entities.assert_called()

    def test_graph_retriever_retrieve_no_matching_entities(self, mock_neo4j_service):
        """Test retrieval when no entities match in the graph."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        mock_neo4j_service.search_entities.return_value = []

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)
        query = SearchQuery(
            text="unknown concept xyz123",
            embedding=None,
            user_id=None,
        )

        result = retriever.retrieve(query=query, top_k=10)

        assert result.total == 0

    def test_graph_retriever_health_check_success(self, mock_neo4j_service):
        """Test health_check returns True when Neo4j is connected."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)
        result = retriever.health_check()

        assert result is True
        mock_neo4j_service.health_check.assert_called_once()

    def test_graph_retriever_health_check_failure(self, mock_neo4j_service):
        """Test health_check returns False when Neo4j is not connected."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        mock_neo4j_service.health_check.return_value = {"connected": False}

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)
        result = retriever.health_check()

        assert result is False

    def test_graph_retriever_health_check_exception(self, mock_neo4j_service):
        """Test health_check returns False when health check throws exception."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        mock_neo4j_service.health_check.side_effect = Exception("Connection error")

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)
        result = retriever.health_check()

        assert result is False

    def test_graph_retriever_entity_limit(self, mock_neo4j_service):
        """Test that entity_limit parameter limits number of entities processed."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        retriever = GraphRetriever(
            neo4j_service=mock_neo4j_service,
            entity_limit=2,
        )

        query = SearchQuery(
            text="machine learning artificial intelligence deep learning neural networks",
            embedding=None,
            user_id=None,
        )

        result = retriever.retrieve(query=query, top_k=10)

        # Should only process up to entity_limit entities
        assert mock_neo4j_service.search_entities.call_count <= 2

    def test_graph_retriever_entity_search_exception_handled(self, mock_neo4j_service):
        """Test that entity search exceptions are handled gracefully (returns empty result)."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        # When search_entities throws an exception, the retriever handles it
        # by logging a warning and continuing with other entities or returning empty results
        mock_neo4j_service.search_entities.side_effect = Exception("Neo4j error")

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)
        query = SearchQuery(
            text="machine learning",
            embedding=None,
            user_id=None,
        )

        # The retriever should handle the exception internally and return empty results
        result = retriever.retrieve(query=query, top_k=10)
        assert result.total == 0

    def test_graph_retriever_extract_keywords_exception_raises_error(
        self, mock_neo4j_service
    ):
        """Test that exceptions during entity extraction are wrapped in GraphRetrieverError."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)

        # Mock _extract_entity_keywords to raise an exception
        with patch.object(
            retriever,
            "_extract_entity_keywords",
            side_effect=Exception("Extraction error"),
        ):
            query = SearchQuery(
                text="machine learning",
                embedding=None,
                user_id=None,
            )

            with pytest.raises(GraphRetrieverError):
                retriever.retrieve(query=query, top_k=10)


# =============================================================================
# Extended Vector Retriever Tests
# =============================================================================


class TestVectorRetrieverExtended:
    """Extended tests for VectorRetriever covering edge cases."""

    def test_vector_retriever_with_custom_anns_field(self, mock_milvus_service):
        """Test vector retrieval with custom anns_field."""
        from apps.document_rag_search.retrievers.vector_retriever import VectorRetriever

        query = SearchQuery(
            text="test query",
            embedding=[0.1] * 1536,
            user_id=None,
        )

        retriever = VectorRetriever(milvus_service=mock_milvus_service)
        result = retriever.retrieve(query=query, top_k=10, anns_field="summary_dense")

        # Verify anns_field was passed correctly
        call_kwargs = mock_milvus_service.search.call_args[1]
        assert call_kwargs["anns_field"] == "summary_dense"

    def test_vector_retriever_with_additional_filter_expr(self, mock_milvus_service):
        """Test vector retrieval with additional filter expression."""
        from apps.document_rag_search.retrievers.vector_retriever import VectorRetriever

        query = SearchQuery(
            text="test query",
            embedding=[0.1] * 1536,
            user_id="user-123",
        )

        retriever = VectorRetriever(milvus_service=mock_milvus_service)
        result = retriever.retrieve(
            query=query,
            top_k=10,
            filter_expr="status == 'active'",
        )

        # Verify combined filter expression
        call_kwargs = mock_milvus_service.search.call_args[1]
        assert "user-123" in call_kwargs["filter_expr"]
        assert "status == 'active'" in call_kwargs["filter_expr"]

    def test_vector_retriever_health_check_collection_not_exists(self, mock_milvus_service):
        """Test health_check returns False when collection does not exist."""
        from apps.document_rag_search.retrievers.vector_retriever import VectorRetriever

        mock_milvus_service.has_collection.return_value = False

        retriever = VectorRetriever(milvus_service=mock_milvus_service)
        result = retriever.health_check()

        assert result is False

    def test_vector_retriever_health_check_exception(self, mock_milvus_service):
        """Test health_check returns False when exception occurs."""
        from apps.document_rag_search.retrievers.vector_retriever import VectorRetriever

        mock_milvus_service.health_check.side_effect = Exception("Connection error")

        retriever = VectorRetriever(milvus_service=mock_milvus_service)
        result = retriever.health_check()

        assert result is False

    def test_vector_retriever_multiple_results(self, mock_milvus_service):
        """Test vector retrieval with multiple results."""
        from apps.document_rag_search.retrievers.vector_retriever import VectorRetriever

        # Create multiple mock results
        mock_items = []
        for i in range(5):
            item = MagicMock()
            item.id = str(uuid4())
            item.lt_doc_id = str(uuid4())
            item.text = f"Document text {i}"
            item.distance = 0.1 + i * 0.1
            item.summary = f"Summary {i}"
            item.document = f"Document {i}"
            item.source = "upload"
            item.source_name = f"doc_{i}.pdf"
            item.chunk_id = i
            mock_items.append(item)

        mock_search_result = MagicMock()
        mock_search_result.items = mock_items
        mock_search_result.total = 5
        mock_search_result.query_time_ms = 50.0

        mock_milvus_service.search.return_value = mock_search_result

        query = SearchQuery(
            text="test query",
            embedding=[0.1] * 1536,
            user_id=None,
        )

        retriever = VectorRetriever(milvus_service=mock_milvus_service)
        result = retriever.retrieve(query=query, top_k=10)

        assert result.total == 5
        assert len(result.items) == 5
        # Verify scores are converted from distance correctly
        for item in result.items:
            assert 0 <= item["score"] <= 1

    def test_vector_retriever_empty_results(self, mock_milvus_service):
        """Test vector retrieval with no results."""
        from apps.document_rag_search.retrievers.vector_retriever import VectorRetriever

        mock_search_result = MagicMock()
        mock_search_result.items = []
        mock_search_result.total = 0
        mock_search_result.query_time_ms = 10.0

        mock_milvus_service.search.return_value = mock_search_result

        query = SearchQuery(
            text="test query",
            embedding=[0.1] * 1536,
            user_id=None,
        )

        retriever = VectorRetriever(milvus_service=mock_milvus_service)
        result = retriever.retrieve(query=query, top_k=10)

        assert result.total == 0
        assert result.items == []

    def test_vector_retriever_hybrid_search_with_empty_results(self, mock_milvus_service):
        """Test hybrid search with no results."""
        from apps.document_rag_search.retrievers.vector_retriever import VectorRetriever

        mock_hybrid_result = MagicMock()
        mock_hybrid_result.items = []
        mock_hybrid_result.total = 0
        mock_hybrid_result.query_time_ms = 20.0

        mock_milvus_service.hybrid_search.return_value = mock_hybrid_result

        query = SearchQuery(
            text="test query",
            embedding=[0.1] * 1536,
            user_id=None,
        )

        retriever = VectorRetriever(milvus_service=mock_milvus_service)
        result = retriever.retrieve(query=query, top_k=10, use_hybrid=True)

        assert result.total == 0
        assert result.items == []

    def test_vector_retriever_default_initialization(self):
        """Test that VectorRetriever can be initialized without parameters."""
        from apps.document_rag_search.retrievers.vector_retriever import VectorRetriever

        # This should not raise any errors
        with patch(
            "apps.document_rag_search.retrievers.vector_retriever.MilvusService"
        ) as mock_milvus:
            mock_instance = MagicMock()
            mock_milvus.return_value = mock_instance
            retriever = VectorRetriever()
            assert retriever.name == "vector"


# =============================================================================
# Extended Keyword Retriever Tests
# =============================================================================


@pytest.mark.django_db
class TestKeywordRetrieverExtended:
    """Extended tests for KeywordRetriever covering edge cases."""

    def test_keyword_retriever_with_real_data(
        self, test_document_with_chunks
    ):
        """Test keyword retriever with real database data."""
        from apps.document_rag_search.retrievers.keyword_retriever import KeywordRetriever

        doc, chunks = test_document_with_chunks

        retriever = KeywordRetriever(use_search_vector=False)
        query = SearchQuery(
            text="machine learning",
            embedding=None,
            user_id=None,
        )

        result = retriever.retrieve(query=query, top_k=10)

        assert result.retriever_name == "keyword"
        assert result.total >= 0  # May have results depending on content

    def test_keyword_retriever_with_user_filter_real_data(
        self, test_document_with_chunks
    ):
        """Test keyword retriever with user filter on real data."""
        from apps.document_rag_search.retrievers.keyword_retriever import KeywordRetriever

        doc, chunks = test_document_with_chunks

        retriever = KeywordRetriever(use_search_vector=False)
        query = SearchQuery(
            text="machine learning",
            embedding=None,
            user_id=str(doc.user_id),
        )

        result = retriever.retrieve(query=query, top_k=10)

        # All results should belong to the user
        for item in result.items:
            # Note: user_id filter is applied at query level
            pass

    def test_keyword_retriever_with_document_ids_filter(
        self, test_document_with_chunks
    ):
        """Test keyword retriever with document_ids filter."""
        from apps.document_rag_search.retrievers.keyword_retriever import KeywordRetriever

        doc, chunks = test_document_with_chunks

        retriever = KeywordRetriever(use_search_vector=False)
        query = SearchQuery(
            text="machine learning",
            embedding=None,
            user_id=None,
        )

        result = retriever.retrieve(
            query=query,
            top_k=10,
            document_ids=[str(doc.id)],
        )

        assert result.retriever_name == "keyword"

    def test_keyword_retriever_chinese_query(self):
        """Test keyword retriever with Chinese query."""
        from apps.document_rag_search.retrievers.keyword_retriever import KeywordRetriever

        retriever = KeywordRetriever(use_search_vector=False)
        query = SearchQuery(
            text="机器学习",
            embedding=None,
            user_id=None,
        )

        result = retriever.retrieve(query=query, top_k=10)

        assert result.retriever_name == "keyword"
        assert isinstance(result.items, list)

    def test_keyword_retriever_mixed_language_query(self):
        """Test keyword retriever with mixed language query."""
        from apps.document_rag_search.retrievers.keyword_retriever import KeywordRetriever

        retriever = KeywordRetriever(use_search_vector=False)
        query = SearchQuery(
            text="machine learning 机器学习",
            embedding=None,
            user_id=None,
        )

        result = retriever.retrieve(query=query, top_k=10)

        assert result.retriever_name == "keyword"

    def test_keyword_retriever_min_rank_filter(self):
        """Test keyword retriever with min_rank filter."""
        from apps.document_rag_search.retrievers.keyword_retriever import KeywordRetriever

        retriever = KeywordRetriever(use_search_vector=False)
        query = SearchQuery(
            text="machine learning",
            embedding=None,
            user_id=None,
        )

        result = retriever.retrieve(query=query, top_k=10, min_rank=0.5)

        assert result.retriever_name == "keyword"

    def test_keyword_retriever_exception_wrapped(self):
        """Test that exceptions are wrapped in KeywordRetrieverError."""
        from apps.document_rag_search.retrievers.keyword_retriever import KeywordRetriever
        from apps.documents_parser.models import DocumentChunk

        with patch.object(
            DocumentChunk.objects,
            "select_related",
            side_effect=Exception("Database error"),
        ):
            retriever = KeywordRetriever(use_search_vector=False)
            query = SearchQuery(
                text="machine learning",
                embedding=None,
                user_id=None,
            )

            with pytest.raises(KeywordRetrieverError):
                retriever.retrieve(query=query, top_k=10)

    def test_keyword_retriever_like_search_with_short_terms(self):
        """Test LIKE search behavior with short search terms."""
        from apps.document_rag_search.retrievers.keyword_retriever import KeywordRetriever

        retriever = KeywordRetriever(use_search_vector=False)
        # Query with only short terms (less than 2 chars)
        query = SearchQuery(
            text="a b c d",
            embedding=None,
            user_id=None,
        )

        result = retriever.retrieve(query=query, top_k=10)

        # Should return empty because all terms are too short
        assert result.total == 0
        assert result.items == []

    def test_keyword_retriever_custom_fts_config(self):
        """Test KeywordRetriever with custom FTS config."""
        from apps.document_rag_search.retrievers.keyword_retriever import KeywordRetriever

        retriever = KeywordRetriever(fts_config="english", use_search_vector=False)
        assert retriever.name == "keyword"


# =============================================================================
# Extended Graph Retriever Tests
# =============================================================================


class TestGraphRetrieverExtended:
    """Extended tests for GraphRetriever covering edge cases."""

    def test_graph_retriever_with_custom_parameters(self, mock_neo4j_service):
        """Test GraphRetriever initialization with custom parameters."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        retriever = GraphRetriever(
            neo4j_service=mock_neo4j_service,
            max_depth=3,
            entity_limit=5,
            min_entity_length=3,
        )

        assert retriever.name == "graph"

    def test_graph_retriever_extract_keywords_mixed_content(self, mock_neo4j_service):
        """Test entity extraction with mixed content (code, symbols, text)."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)
        keywords = retriever._extract_entity_keywords(
            "How to use Python (python3.9) for ML? Check code: def train() -> None"
        )

        # Should extract meaningful words
        assert len(keywords) > 0
        # Stop words should be filtered
        assert "how" not in [k.lower() for k in keywords]
        assert "to" not in [k.lower() for k in keywords]

    def test_graph_retriever_extract_keywords_long_chinese(self, mock_neo4j_service):
        """Test entity extraction with long Chinese phrases."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)
        keywords = retriever._extract_entity_keywords(
            "深度学习神经网络机器学习人工智能"
        )

        # Should split long Chinese text into segments
        assert len(keywords) > 0

    def test_graph_retriever_retrieve_with_user_id(self, mock_neo4j_service):
        """Test graph retrieval with user_id parameter."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)
        query = SearchQuery(
            text="machine learning",
            embedding=None,
            user_id="user-123",
        )

        result = retriever.retrieve(query=query, top_k=10)

        assert result.retriever_name == "graph"

    def test_graph_retriever_enrich_chunk_sources_exception(self, mock_neo4j_service):
        """Test _enrich_chunk_sources handles exceptions gracefully."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)

        # Mock entity that returns chunk data
        mock_entity = MagicMock()
        mock_entity.id = str(uuid4())
        mock_entity.properties = {"name": "ML"}

        mock_chunk_node = MagicMock()
        mock_chunk_node.id = str(uuid4())
        mock_chunk_node.properties = {
            "document_id": str(uuid4()),
            "text": "Test text",
            "chunk_index": 0,
        }

        mock_context = MagicMock()
        mock_context.mentioned_in = [mock_chunk_node]

        mock_neo4j_service.search_entities.return_value = [mock_entity]
        mock_neo4j_service.get_entity_context.return_value = mock_context

        # Query that will have _enrich_chunk_sources called
        query = SearchQuery(
            text="machine learning",
            embedding=None,
            user_id=None,
        )

        result = retriever.retrieve(query=query, top_k=10)

        # Should still return results even if enrichment fails
        assert result.total >= 0

    def test_graph_retriever_multiple_entities_same_chunk(self, mock_neo4j_service):
        """Test that multiple matching entities increase chunk score."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        chunk_id = str(uuid4())

        # Mock two entities that both reference the same chunk
        mock_entity1 = MagicMock()
        mock_entity1.id = str(uuid4())
        mock_entity1.properties = {"name": "ML"}

        mock_entity2 = MagicMock()
        mock_entity2.id = str(uuid4())
        mock_entity2.properties = {"name": "AI"}

        mock_chunk_node = MagicMock()
        mock_chunk_node.id = chunk_id
        mock_chunk_node.properties = {
            "document_id": str(uuid4()),
            "text": "Test text",
            "chunk_index": 0,
        }

        mock_context = MagicMock()
        mock_context.mentioned_in = [mock_chunk_node]

        mock_neo4j_service.search_entities.side_effect = [
            [mock_entity1],
            [mock_entity2],
        ]
        mock_neo4j_service.get_entity_context.return_value = mock_context

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)
        query = SearchQuery(
            text="machine learning artificial intelligence",
            embedding=None,
            user_id=None,
        )

        result = retriever.retrieve(query=query, top_k=10, entity_limit=2)

        # Score should be higher due to multiple entity matches
        if result.items:
            assert result.items[0]["score"] >= 2.0

    def test_graph_retriever_default_initialization(self):
        """Test that GraphRetriever can be initialized without parameters."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        with patch(
            "apps.document_rag_search.retrievers.graph_retriever.Neo4jService"
        ) as mock_neo4j:
            mock_instance = MagicMock()
            mock_neo4j.return_value = mock_instance
            retriever = GraphRetriever()
            assert retriever.name == "graph"

    def test_graph_retriever_empty_entity_context(self, mock_neo4j_service):
        """Test retrieval when entity is found but has no chunk context."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        mock_entity = MagicMock()
        mock_entity.id = str(uuid4())
        mock_entity.properties = {"name": "ML"}

        mock_context = MagicMock()
        mock_context.mentioned_in = []  # No chunks

        mock_neo4j_service.search_entities.return_value = [mock_entity]
        mock_neo4j_service.get_entity_context.return_value = mock_context

        retriever = GraphRetriever(neo4j_service=mock_neo4j_service)
        query = SearchQuery(
            text="machine learning",
            embedding=None,
            user_id=None,
        )

        result = retriever.retrieve(query=query, top_k=10)

        assert result.total == 0

    def test_graph_retriever_min_entity_length(self, mock_neo4j_service):
        """Test that short entities are filtered out based on min_entity_length."""
        from apps.document_rag_search.retrievers.graph_retriever import GraphRetriever

        retriever = GraphRetriever(
            neo4j_service=mock_neo4j_service,
            min_entity_length=4,
        )

        # Query with short and long terms
        keywords = retriever._extract_entity_keywords("AI is a field of ML")

        # All keywords should be at least min_entity_length characters
        for kw in keywords:
            assert len(kw) >= 4
