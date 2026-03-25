"""
Tests for Context Service.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apps.chat_agent.services.context_service import ContextService, ContextResult


@pytest.mark.django_db
class TestContextService:
    """Tests for ContextService."""

    def test_service_initialization(self):
        """Test service can be initialized."""
        service = ContextService()
        assert service is not None

    def test_lazy_service_initialization(self):
        """Test services are lazily initialized."""
        service = ContextService()

        # Services should not be initialized yet
        assert service._search_service is None
        assert service._conversation_service is None
        assert service._embedding_service is None

    def test_assemble_context_basic(self):
        """Test assembling context with minimal inputs."""
        service = ContextService()

        # Mock the services
        mock_search_service = MagicMock()
        mock_search_service.hybrid_search.return_value = MagicMock(
            results=[],
            total=0,
            query_time_ms=100.0,
            retrievers_used=["vector"],
        )

        mock_conversation_service = MagicMock()
        mock_conversation_service.get_history.return_value = []

        service._search_service = mock_search_service
        service._conversation_service = mock_conversation_service

        result = service.assemble_context(
            query="What is AI?",
            conversation_id="test-conv-id",
        )

        assert isinstance(result, dict)
        assert "context" in result
        assert "sources" in result
        assert "history" in result

    def test_assemble_context_with_mocked_services(self):
        """Test context assembly with fully mocked services."""
        service = ContextService()

        # Create mock search response
        mock_search_result = MagicMock()
        mock_search_result.results = [
            MagicMock(
                chunk_id="chunk-1",
                document_id="doc-1",
                text="AI is artificial intelligence",
                score=0.9,
                source="vector",
                metadata={},
                retriever_scores={"vector": 0.9},
            )
        ]
        mock_search_result.total = 1
        mock_search_result.query_time_ms = 100.0
        mock_search_result.retrievers_used = ["vector"]

        mock_search_service = MagicMock()
        mock_search_service.hybrid_search.return_value = mock_search_result

        mock_conversation_service = MagicMock()
        mock_conversation_service.get_history.return_value = []

        service._search_service = mock_search_service
        service._conversation_service = mock_conversation_service

        result = service.assemble_context(
            query="What is AI?",
            conversation_id="test-conv-id",
            user_id="user-1",
            top_k=5,
        )

        # Verify the result structure
        assert "context" in result
        assert "sources" in result
        assert len(result["sources"]) == 1
        assert result["sources"][0]["chunk_id"] == "chunk-1"

    def test_extract_sources(self):
        """Test _extract_sources method."""
        service = ContextService()

        # Create mock search results
        mock_result = MagicMock()
        mock_result.results = [
            MagicMock(
                chunk_id="chunk-1",
                document_id="doc-1",
                text="Text 1",
                score=0.9,
                source="vector",
            ),
            MagicMock(
                chunk_id="chunk-2",
                document_id="doc-2",
                text="Text 2",
                score=0.8,
                source="keyword",
            ),
        ]

        sources = service._extract_sources(mock_result)

        assert len(sources) == 2
        assert sources[0]["chunk_id"] == "chunk-1"
        assert sources[1]["chunk_id"] == "chunk-2"

    def test_extract_scores(self):
        """Test _extract_scores method."""
        service = ContextService()

        mock_result = MagicMock()
        mock_result.retrievers_used = ["vector", "keyword"]
        mock_result.query_time_ms = 150.0
        mock_result.total = 5

        scores = service._extract_scores(mock_result)

        assert scores["retrievers_used"] == ["vector", "keyword"]
        assert scores["query_time_ms"] == 150.0
        assert scores["total_results"] == 5

    def test_format_context_window(self):
        """Test _format_context_window method."""
        service = ContextService()

        # Mock search results
        mock_search = MagicMock()
        mock_search.results = [
            MagicMock(
                text="Document text 1",
                score=0.9,
            ),
        ]

        # Mock history messages
        mock_history = [
            MagicMock(role="user", content="Hello"),
            MagicMock(role="assistant", content="Hi there!"),
        ]

        context = service._format_context_window(
            search_results=mock_search,
            history_messages=mock_history,
            max_tokens=1000,
        )

        assert isinstance(context, str)
        assert len(context) > 0

    def test_context_result_typed_dict(self):
        """Test ContextResult TypedDict."""
        result: ContextResult = {
            "context": "Test context",
            "sources": [{"chunk_id": "1"}],
            "retrieval_scores": {"vector": 0.9},
            "history": [],
        }

        assert result["context"] == "Test context"
        assert len(result["sources"]) == 1
