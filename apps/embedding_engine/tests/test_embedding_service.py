"""
Tests for EmbeddingService.

This module tests the EmbeddingService facade class for embedding operations.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apps.embedding_engine.clients.mock_client import MockEmbeddingClient
from apps.embedding_engine.constants import TaskType
from apps.embedding_engine.dto import (
    BatchEmbeddingResult,
    EmbedForStorageRequest,
    EmbeddingResult,
)
from apps.embedding_engine.exceptions import EmbeddingEmptyInputError
from apps.embedding_engine.services.embedding_service import EmbeddingService


@pytest.mark.unit
class TestEmbeddingServiceInit:
    """Tests for EmbeddingService initialization."""

    def test_init_default_config(self) -> None:
        """Test initialization with default config."""
        service = EmbeddingService()
        # Client should be lazy-loaded, not created yet
        assert service._client is None

    def test_init_custom_config(self) -> None:
        """Test initialization with custom config."""
        config = {"use_mock": True, "dimension": 512}
        service = EmbeddingService(config=config)
        assert service._config == config

    def test_dimension_property(self) -> None:
        """Test dimension property."""
        service = EmbeddingService(config={"dimension": 512})
        assert service.dimension == 512


@pytest.mark.unit
class TestEmbeddingServiceEmbedText:
    """Tests for EmbeddingService.embed_text method."""

    def test_embed_text_success(self) -> None:
        """Test successful text embedding."""
        mock_client = MockEmbeddingClient(dimension=1536)
        with patch(
            "apps.embedding_engine.services.embedding_service.get_embedding_client",
            return_value=mock_client,
        ):
            service = EmbeddingService(config={"use_mock": True})
            result = service.embed_text("Hello world")

            assert len(result.embedding) == 1536
            assert result.dimension == 1536

    def test_embed_text_empty_raises_error(self) -> None:
        """Test that empty text raises error."""
        service = EmbeddingService(config={"use_mock": True})
        with pytest.raises(EmbeddingEmptyInputError):
            service.embed_text("")

    def test_embed_text_with_task_type(self) -> None:
        """Test embed_text with task_type."""
        mock_client = MockEmbeddingClient(dimension=1536)
        with patch(
            "apps.embedding_engine.services.embedding_service.get_embedding_client",
            return_value=mock_client,
        ):
            service = EmbeddingService(config={"use_mock": True})
            result = service.embed_text("Hello", task_type=TaskType.QUERY.value)

            assert len(result.embedding) == 1536


@pytest.mark.unit
class TestEmbeddingServiceEmbedTexts:
    """Tests for EmbeddingService.embed_texts method."""

    def test_embed_texts_success(self) -> None:
        """Test successful batch embedding."""
        mock_client = MockEmbeddingClient(dimension=1536)
        with patch(
            "apps.embedding_engine.services.embedding_service.get_embedding_client",
            return_value=mock_client,
        ):
            service = EmbeddingService(config={"use_mock": True})
            texts = ["Hello", "World"]
            result = service.embed_texts(texts)

            assert len(result.embeddings) == 2
            assert result.success_count == 2

    def test_embed_texts_empty_list_raises_error(self) -> None:
        """Test that empty list raises error."""
        service = EmbeddingService(config={"use_mock": True})
        with pytest.raises(EmbeddingEmptyInputError):
            service.embed_texts([])

    def test_embed_texts_filters_empty_strings(self) -> None:
        """Test that empty strings are filtered."""
        mock_client = MockEmbeddingClient(dimension=1536)
        with patch(
            "apps.embedding_engine.services.embedding_service.get_embedding_client",
            return_value=mock_client,
        ):
            service = EmbeddingService(config={"use_mock": True})
            result = service.embed_texts(["Hello", ""])

            # Empty strings should be filtered
            assert len(result.embeddings) == 1


@pytest.mark.unit
class TestEmbeddingServiceEmbedQuery:
    """Tests for EmbeddingService.embed_query method."""

    def test_embed_query_uses_query_task_type(self) -> None:
        """Test that embed_query uses query task type."""
        mock_client = MockEmbeddingClient(dimension=1536)
        with patch(
            "apps.embedding_engine.services.embedding_service.get_embedding_client",
            return_value=mock_client,
        ):
            service = EmbeddingService(config={"use_mock": True})
            result = service.embed_query("What is AI?")

            assert len(result.embedding) == 1536

    def test_embed_query_empty_raises_error(self) -> None:
        """Test that empty query raises error."""
        service = EmbeddingService(config={"use_mock": True})
        with pytest.raises(EmbeddingEmptyInputError):
            service.embed_query("")


@pytest.mark.unit
class TestEmbeddingServiceEmbedForStorage:
    """Tests for EmbeddingService.embed_for_storage method."""

    def test_embed_for_storage_success(self) -> None:
        """Test successful storage embedding."""
        mock_client = MockEmbeddingClient(dimension=1536)
        with patch(
            "apps.embedding_engine.services.embedding_service.get_embedding_client",
            return_value=mock_client,
        ):
            service = EmbeddingService(config={"use_mock": True})
            chunks = [{"text": "Hello world", "summary": "Greeting"}]
            request = EmbedForStorageRequest(chunks=chunks)
            result = service.embed_for_storage(request)

            assert len(result.chunks) == 1
            assert "text_dense" in result.chunks[0]
            assert "summary_dense" in result.chunks[0]
            assert len(result.chunks[0]["text_dense"]) == 1536
            assert len(result.chunks[0]["summary_dense"]) == 1536

    def test_embed_for_storage_empty_chunks_raises_error(self) -> None:
        """Test that empty chunks raises error."""
        service = EmbeddingService(config={"use_mock": True})
        request = EmbedForStorageRequest(chunks=[])
        with pytest.raises(EmbeddingEmptyInputError):
            service.embed_for_storage(request)


@pytest.mark.unit
class TestEmbeddingServiceHealthCheck:
    """Tests for EmbeddingService.health_check method."""

    def test_health_check_healthy(self) -> None:
        """Test healthy health check."""
        mock_client = MockEmbeddingClient(dimension=1536)
        with patch(
            "apps.embedding_engine.services.embedding_service.get_embedding_client",
            return_value=mock_client,
        ):
            service = EmbeddingService(config={"use_mock": True})
            result = service.health_check()

            assert result["healthy"] is True
            assert result["provider"] == "mock"
            assert result["dimension"] == 1536
            assert result["latency_ms"] >= 0

    def test_health_check_unhealthy(self) -> None:
        """Test unhealthy health check."""
        with patch(
            "apps.embedding_engine.services.embedding_service.get_embedding_client",
            side_effect=Exception("Connection failed"),
        ):
            service = EmbeddingService(config={"use_mock": False})
            result = service.health_check()

            assert result["healthy"] is False
            assert "error" in result


@pytest.mark.unit
class TestEmbeddingServiceGetSupportedModels:
    """Tests for EmbeddingService.get_supported_models method."""

    def test_get_supported_models(self) -> None:
        """Test getting supported models."""
        service = EmbeddingService(config={"use_mock": True})
        models = service.get_supported_models()

        assert "text-embedding-v1" in models
        assert "text-embedding-v3" in models
