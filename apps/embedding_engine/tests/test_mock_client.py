"""
Tests for MockEmbeddingClient.

This module tests the MockEmbeddingClient class for generating
deterministic embeddings without API access.
"""

from __future__ import annotations

import pytest

from apps.embedding_engine.clients.mock_client import MockEmbeddingClient
from apps.embedding_engine.constants import DEFAULT_DIMENSION
from apps.embedding_engine.exceptions import EmbeddingEmptyInputError


@pytest.mark.unit
class TestMockEmbeddingClientInit:
    """Tests for MockEmbeddingClient initialization."""

    def test_init_default_values(self) -> None:
        """Test initialization with default values."""
        client = MockEmbeddingClient()

        assert client.dimension == DEFAULT_DIMENSION
        assert client.model == "mock"

    def test_init_custom_dimension(self) -> None:
        """Test initialization with custom dimension."""
        client = MockEmbeddingClient(dimension=512)

        assert client.dimension == 512

    def test_init_custom_model(self) -> None:
        """Test initialization with custom model name."""
        client = MockEmbeddingClient(model="test-mock")

        assert client.model == "test-mock"

    def test_init_with_seed(self) -> None:
        """Test initialization with seed for reproducibility."""
        client = MockEmbeddingClient(seed=42)

        assert client.dimension == DEFAULT_DIMENSION


@pytest.mark.unit
class TestMockEmbeddingClientEmbedSingle:
    """Tests for MockEmbeddingClient.embed_single method."""

    def test_embed_single_returns_correct_dimension(self) -> None:
        """Test that embed_single returns correct dimension."""
        client = MockEmbeddingClient(dimension=1536)
        result = client.embed_single("Hello world")

        assert len(result.embedding) == 1536
        assert result.dimension == 1536

    def test_embed_single_returns_model_name(self) -> None:
        """Test that embed_single returns correct model name."""
        client = MockEmbeddingClient(model="test-model")
        result = client.embed_single("Hello world")

        assert result.model == "test-model"

    def test_embed_single_is_deterministic(self) -> None:
        """Test that same text produces same embedding."""
        client = MockEmbeddingClient()
        text = "This is a test"

        result1 = client.embed_single(text)
        result2 = client.embed_single(text)

        assert result1.embedding == result2.embedding

    def test_embed_single_different_texts_different_embeddings(self) -> None:
        """Test that different texts produce different embeddings."""
        client = MockEmbeddingClient()

        result1 = client.embed_single("Hello world")
        result2 = client.embed_single("Goodbye world")

        assert result1.embedding != result2.embedding

    def test_embed_single_empty_text_raises_error(self) -> None:
        """Test that empty text raises EmbeddingEmptyInputError."""
        client = MockEmbeddingClient()

        with pytest.raises(EmbeddingEmptyInputError):
            client.embed_single("")

    def test_embed_single_whitespace_only_raises_error(self) -> None:
        """Test that whitespace-only text raises EmbeddingEmptyInputError."""
        client = MockEmbeddingClient()

        with pytest.raises(EmbeddingEmptyInputError):
            client.embed_single("   ")

    def test_embed_single_vector_is_normalized(self) -> None:
        """Test that embedding vector is normalized."""
        import math

        client = MockEmbeddingClient()
        result = client.embed_single("Hello world")

        # Calculate norm
        norm = math.sqrt(sum(x * x for x in result.embedding))

        # Should be approximately 1.0
        assert abs(norm - 1.0) < 0.0001

    def test_embed_single_returns_tokens_used(self) -> None:
        """Test that embed_single returns estimated tokens."""
        client = MockEmbeddingClient()
        result = client.embed_single("Hello world")

        # Tokens should be positive
        assert result.tokens_used > 0


@pytest.mark.unit
class TestMockEmbeddingClientEmbed:
    """Tests for MockEmbeddingClient.embed method."""

    def test_embed_returns_correct_number_of_embeddings(self) -> None:
        """Test that embed returns correct number of embeddings."""
        client = MockEmbeddingClient()
        texts = ["Hello", "World", "Test"]
        result = client.embed(texts)

        assert len(result.embeddings) == 3

    def test_embed_returns_correct_dimension(self) -> None:
        """Test that embed returns correct dimension."""
        client = MockEmbeddingClient(dimension=1536)
        texts = ["Hello", "World"]
        result = client.embed(texts)

        assert result.dimension == 1536
        for embedding in result.embeddings:
            assert len(embedding) == 1536

    def test_embed_is_deterministic(self) -> None:
        """Test that same texts produce same embeddings."""
        client = MockEmbeddingClient()
        texts = ["Hello", "World"]

        result1 = client.embed(texts)
        result2 = client.embed(texts)

        assert result1.embeddings == result2.embeddings

    def test_embed_empty_list_raises_error(self) -> None:
        """Test that empty list raises EmbeddingEmptyInputError."""
        client = MockEmbeddingClient()

        with pytest.raises(EmbeddingEmptyInputError):
            client.embed([])

    def test_embed_filters_empty_strings(self) -> None:
        """Test that empty strings are filtered."""
        client = MockEmbeddingClient()
        texts = ["Hello", "", "World", "   "]
        result = client.embed(texts)

        # Should only embed non-empty texts
        assert len(result.embeddings) == 2

    def test_embed_all_empty_raises_error(self) -> None:
        """Test that all empty strings raises EmbeddingEmptyInputError."""
        client = MockEmbeddingClient()

        with pytest.raises(EmbeddingEmptyInputError):
            client.embed(["", "   ", "\t"])

    def test_embed_returns_total_tokens(self) -> None:
        """Test that embed returns total tokens."""
        client = MockEmbeddingClient()
        texts = ["Hello", "World"]
        result = client.embed(texts)

        assert result.total_tokens > 0

    def test_embed_returns_success_count(self) -> None:
        """Test that embed returns success count."""
        client = MockEmbeddingClient()
        texts = ["Hello", "World"]
        result = client.embed(texts)

        assert result.success_count == 2


@pytest.mark.unit
class TestMockEmbeddingClientHealthCheck:
    """Tests for MockEmbeddingClient.health_check method."""

    def test_health_check_returns_true(self) -> None:
        """Test that health_check returns True."""
        client = MockEmbeddingClient()
        result = client.health_check()

        assert result is True


@pytest.mark.unit
class TestMockEmbeddingClientProperties:
    """Tests for MockEmbeddingClient properties."""

    def test_dimension_property(self) -> None:
        """Test dimension property."""
        client = MockEmbeddingClient(dimension=512)

        assert client.dimension == 512

    def test_model_property(self) -> None:
        """Test model property."""
        client = MockEmbeddingClient(model="custom-mock")

        assert client.model == "custom-mock"


@pytest.mark.unit
class TestMockEmbeddingClientDeterminism:
    """Tests for embedding determinism across instances."""

    def test_determinism_across_instances(self) -> None:
        """Test that different instances produce same embeddings."""
        client1 = MockEmbeddingClient()
        client2 = MockEmbeddingClient()
        text = "Same text"

        result1 = client1.embed_single(text)
        result2 = client2.embed_single(text)

        assert result1.embedding == result2.embedding

    def test_determinism_with_seed(self) -> None:
        """Test determinism with explicit seed."""
        client1 = MockEmbeddingClient(seed=42)
        client2 = MockEmbeddingClient(seed=42)
        text = "Test text"

        result1 = client1.embed_single(text)
        result2 = client2.embed_single(text)

        assert result1.embedding == result2.embedding
