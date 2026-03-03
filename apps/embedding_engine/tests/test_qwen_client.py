"""
Tests for QwenEmbeddingClient.

This module tests the QwenEmbeddingClient class for generating
embeddings via the Qwen API using mocked HTTP responses.
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from apps.embedding_engine.clients.qwen_client import QwenEmbeddingClient
from apps.embedding_engine.constants import DEFAULT_DIMENSION
from apps.embedding_engine.dto import BatchEmbeddingResult, EmbeddingResult
from apps.embedding_engine.exceptions import (
    EmbeddingAPIError,
    EmbeddingEmptyInputError,
    EmbeddingRateLimitError,
    MissingAPIKeyError,
)


@pytest.mark.unit
class TestQwenEmbeddingClientInit:
    """Tests for QwenEmbeddingClient initialization."""

    def test_init_requires_api_key(self) -> None:
        """Test that initialization requires API key."""
        with pytest.raises(MissingAPIKeyError):
            QwenEmbeddingClient(api_key=None)

    def test_init_with_api_key(self) -> None:
        """Test initialization with API key."""
        with patch("apps.embedding_engine.clients.qwen_client.httpx.Client"):
            client = QwenEmbeddingClient(api_key="test-api-key")
            assert client.model == "text-embedding-v1"
            assert client.dimension == DEFAULT_DIMENSION

    def test_init_with_custom_values(self) -> None:
        """Test initialization with custom values."""
        with patch("apps.embedding_engine.clients.qwen_client.httpx.Client"):
            client = QwenEmbeddingClient(
                api_key="test-api-key",
                model="custom-model",
                dimension=512,
            )
            assert client.model == "custom-model"
            assert client.dimension == 512


@pytest.mark.unit
class TestQwenEmbeddingClientEmbedSingle:
    """Tests for QwenEmbeddingClient.embed_single method."""

    def _create_mock_response(self, status_code: int, json_data: dict | None = None) -> Mock:
        """Create a mock HTTP response."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = status_code
        mock_response.headers = {}
        if json_data:
            mock_response.json.return_value = json_data
        return mock_response

    def test_embed_single_success(self) -> None:
        """Test successful single text embedding."""
        response_data = {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "index": 0,
                    "embedding": [0.1] * 1536,
                }
            ],
            "model": "text-embedding-v1",
            "usage": {"prompt_tokens": 10, "total_tokens": 10},
        }
        mock_response = self._create_mock_response(200, response_data)

        with patch("apps.embedding_engine.clients.qwen_client.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = QwenEmbeddingClient(api_key="test-api-key")
            result = client.embed_single("Hello world")

            assert isinstance(result, EmbeddingResult)
            assert len(result.embedding) == 1536
            assert result.dimension == 1536
            assert result.model == "text-embedding-v1"
            assert result.tokens_used == 10

    def test_embed_single_empty_text_raises_error(self) -> None:
        """Test that empty text raises EmbeddingEmptyInputError."""
        with patch("apps.embedding_engine.clients.qwen_client.httpx.Client"):
            client = QwenEmbeddingClient(api_key="test-api-key")
            with pytest.raises(EmbeddingEmptyInputError):
                client.embed_single("")

    def test_embed_single_whitespace_raises_error(self) -> None:
        """Test that whitespace-only text raises error."""
        with patch("apps.embedding_engine.clients.qwen_client.httpx.Client"):
            client = QwenEmbeddingClient(api_key="test-api-key")
            with pytest.raises(EmbeddingEmptyInputError):
                client.embed_single("   ")

    def test_embed_single_rate_limit_error(self) -> None:
        """Test that rate limit response raises EmbeddingRateLimitError."""
        mock_response = self._create_mock_response(429)

        with patch("apps.embedding_engine.clients.qwen_client.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = QwenEmbeddingClient(api_key="test-api-key")
            with pytest.raises(EmbeddingRateLimitError):
                client.embed_single("Hello world")

    def test_embed_single_unauthorized_error(self) -> None:
        """Test that 401 response raises EmbeddingAPIError."""
        mock_response = self._create_mock_response(401)

        with patch("apps.embedding_engine.clients.qwen_client.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = QwenEmbeddingClient(api_key="test-api-key")
            with pytest.raises(EmbeddingAPIError) as exc_info:
                client.embed_single("Hello world")
            assert exc_info.value.status_code == 401

    def test_embed_single_server_error(self) -> None:
        """Test that 500 response raises EmbeddingAPIError."""
        mock_response = self._create_mock_response(500)

        with patch("apps.embedding_engine.clients.qwen_client.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = QwenEmbeddingClient(api_key="test-api-key")
            with pytest.raises(EmbeddingAPIError) as exc_info:
                client.embed_single("Hello world")
            assert exc_info.value.status_code == 500


@pytest.mark.unit
class TestQwenEmbeddingClientEmbed:
    """Tests for QwenEmbeddingClient.embed method."""

    def _create_mock_response(self, status_code: int, json_data: dict | None = None) -> Mock:
        """Create a mock HTTP response."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = status_code
        mock_response.headers = {}
        if json_data:
            mock_response.json.return_value = json_data
        return mock_response

    def test_embed_success(self) -> None:
        """Test successful batch embedding."""
        response_data = {
            "object": "list",
            "data": [
                {"object": "embedding", "index": 0, "embedding": [0.1] * 1536},
                {"object": "embedding", "index": 1, "embedding": [0.2] * 1536},
                {"object": "embedding", "index": 2, "embedding": [0.3] * 1536},
            ],
            "model": "text-embedding-v1",
            "usage": {"prompt_tokens": 30, "total_tokens": 30},
        }
        mock_response = self._create_mock_response(200, response_data)

        with patch("apps.embedding_engine.clients.qwen_client.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = QwenEmbeddingClient(api_key="test-api-key")
            texts = ["Hello", "World", "Test"]
            result = client.embed(texts)

            assert isinstance(result, BatchEmbeddingResult)
            assert len(result.embeddings) == 3
            assert result.success_count == 3
            assert result.total_tokens == 30

    def test_embed_empty_list_raises_error(self) -> None:
        """Test that empty list raises EmbeddingEmptyInputError."""
        with patch("apps.embedding_engine.clients.qwen_client.httpx.Client"):
            client = QwenEmbeddingClient(api_key="test-api-key")
            with pytest.raises(EmbeddingEmptyInputError):
                client.embed([])


@pytest.mark.unit
class TestQwenEmbeddingClientHealthCheck:
    """Tests for QwenEmbeddingClient.health_check method."""

    def _create_mock_response(self, status_code: int, json_data: dict | None = None) -> Mock:
        """Create a mock HTTP response."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = status_code
        mock_response.headers = {}
        if json_data:
            mock_response.json.return_value = json_data
        return mock_response

    def test_health_check_success(self) -> None:
        """Test successful health check."""
        response_data = {
            "object": "list",
            "data": [{"object": "embedding", "index": 0, "embedding": [0.1] * 1536}],
            "model": "text-embedding-v1",
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        }
        mock_response = self._create_mock_response(200, response_data)

        with patch("apps.embedding_engine.clients.qwen_client.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = QwenEmbeddingClient(api_key="test-api-key")
            result = client.health_check()
            assert result is True

    def test_health_check_failure(self) -> None:
        """Test health check failure."""
        mock_response = self._create_mock_response(500)

        with patch("apps.embedding_engine.clients.qwen_client.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            client = QwenEmbeddingClient(api_key="test-api-key")
            result = client.health_check()
            assert result is False


@pytest.mark.unit
class TestQwenEmbeddingClientContextManager:
    """Tests for QwenEmbeddingClient context manager."""

    def test_context_manager_closes_client(self) -> None:
        """Test that context manager closes client."""
        with patch("apps.embedding_engine.clients.qwen_client.httpx.Client") as mock_client_class:
            mock_http_client = MagicMock()
            mock_client_class.return_value = mock_http_client

            with QwenEmbeddingClient(api_key="test-api-key") as client:
                assert client is not None
                assert client.model == "text-embedding-v1"

            mock_http_client.close.assert_called_once()


@pytest.mark.unit
class TestQwenEmbeddingClientProperties:
    """Tests for QwenEmbeddingClient properties."""

    def test_dimension_property(self) -> None:
        """Test dimension property."""
        with patch("apps.embedding_engine.clients.qwen_client.httpx.Client"):
            client = QwenEmbeddingClient(api_key="test-api-key", dimension=512)
            assert client.dimension == 512

    def test_model_property(self) -> None:
        """Test model property."""
        with patch("apps.embedding_engine.clients.qwen_client.httpx.Client"):
            client = QwenEmbeddingClient(api_key="test-api-key", model="custom-model")
            assert client.model == "custom-model"
