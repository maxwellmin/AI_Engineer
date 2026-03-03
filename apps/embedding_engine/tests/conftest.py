"""
Pytest fixtures for embedding engine tests.

This module provides fixtures for testing the embedding engine module,
following the MilvusController test pattern.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apps.embedding_engine.clients.mock_client import MockEmbeddingClient
from apps.embedding_engine.clients.qwen_client import QwenEmbeddingClient
from apps.embedding_engine.dto import BatchEmbeddingResult, EmbeddingResult
from apps.embedding_engine.services.embedding_service import EmbeddingService


# =============================================================================
# API Response Fixtures
# =============================================================================


@pytest.fixture
def mock_embedding_response() -> dict:
    """Mock API response for embedding.

    Returns:
        Dictionary mimicking Qwen API response.
    """
    import random

    return {
        "object": "list",
        "data": [
            {
                "object": "embedding",
                "index": i,
                "embedding": [random.random() for _ in range(1536)],
            }
            for i in range(3)
        ],
        "model": "text-embedding-v1",
        "usage": {"prompt_tokens": 30, "total_tokens": 30},
    }


@pytest.fixture
def mock_single_embedding_response() -> dict:
    """Mock API response for single text embedding.

    Returns:
        Dictionary mimicking Qwen API response for single text.
    """
    import random

    return {
        "object": "list",
        "data": [
            {
                "object": "embedding",
                "index": 0,
                "embedding": [random.random() for _ in range(1536)],
            }
        ],
        "model": "text-embedding-v1",
        "usage": {"prompt_tokens": 10, "total_tokens": 10},
    }


# =============================================================================
# Client Fixtures
# =============================================================================


@pytest.fixture
def mock_client() -> MockEmbeddingClient:
    """Real mock client for deterministic testing.

    Returns:
        MockEmbeddingClient instance.
    """
    return MockEmbeddingClient(dimension=1536)


@pytest.fixture
def mock_qwen_client(mock_embedding_response: dict) -> MagicMock:
    """Mock Qwen client for testing.

    Args:
        mock_embedding_response: Mock API response fixture.

    Returns:
        Mocked QwenEmbeddingClient.
    """
    client = MagicMock(spec=QwenEmbeddingClient)
    client.embed.return_value = BatchEmbeddingResult(
        embeddings=[
            mock_embedding_response["data"][i]["embedding"]
            for i in range(len(mock_embedding_response["data"]))
        ],
        dimension=1536,
        model="text-embedding-v1",
        total_tokens=30,
        success_count=3,
    )
    client.embed_single.return_value = EmbeddingResult(
        embedding=mock_embedding_response["data"][0]["embedding"],
        dimension=1536,
        model="text-embedding-v1",
        tokens_used=10,
    )
    client.dimension = 1536
    client.model = "text-embedding-v1"
    client.health_check.return_value = True
    return client


# =============================================================================
# Service Fixtures
# =============================================================================


@pytest.fixture
def embedding_service_with_mock(mock_client: MockEmbeddingClient) -> EmbeddingService:
    """Embedding service with mock client.

    Args:
        mock_client: MockEmbeddingClient fixture.

    Yields:
        EmbeddingService configured with mock client.
    """
    with patch(
        "apps.embedding_engine.services.embedding_service.get_embedding_client",
        return_value=mock_client,
    ):
        yield EmbeddingService(config={"use_mock": True, "dimension": 1536})


@pytest.fixture
def embedding_service_with_mock_qwen(
    mock_qwen_client: MagicMock,
) -> EmbeddingService:
    """Embedding service with mocked Qwen client.

    Args:
        mock_qwen_client: Mocked QwenEmbeddingClient fixture.

    Yields:
        EmbeddingService configured with mocked Qwen client.
    """
    with patch(
        "apps.embedding_engine.services.embedding_service.get_embedding_client",
        return_value=mock_qwen_client,
    ):
        yield EmbeddingService(config={"use_mock": False, "dimension": 1536})


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def sample_texts() -> list[str]:
    """Sample texts for embedding tests.

    Returns:
        List of sample text strings.
    """
    return [
        "This is a test document for embedding.",
        "Another sample text for batch processing.",
        "Machine learning is a subset of artificial intelligence.",
    ]


@pytest.fixture
def sample_chunks() -> list[dict]:
    """Sample document chunks for storage embedding tests.

    Returns:
        List of sample chunk dictionaries.
    """
    return [
        {
            "text": "This is the first document chunk with some content.",
            "summary": "First document summary",
            "chunk_id": 0,
            "lt_doc_id": "doc_001",
        },
        {
            "text": "This is the second document chunk with more content.",
            "summary": "Second document summary",
            "chunk_id": 1,
            "lt_doc_id": "doc_001",
        },
    ]


@pytest.fixture
def sample_query() -> str:
    """Sample query for search tests.

    Returns:
        Sample query string.
    """
    return "What is machine learning?"


# =============================================================================
# Configuration Fixtures
# =============================================================================


@pytest.fixture
def mock_config() -> dict:
    """Mock embedding configuration.

    Returns:
        Dictionary with mock configuration.
    """
    return {
        "use_mock": True,
        "api_key": "test-api-key",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "text-embedding-v1",
        "dimension": 1536,
        "max_batch_size": 20,
        "retry": {
            "max_attempts": 3,
            "backoff_factor": 2.0,
        },
        "timeout": {
            "connect": 10.0,
            "read": 60.0,
        },
    }


# =============================================================================
# User Fixtures (for API tests)
# =============================================================================


@pytest.fixture
@pytest.mark.django_db
def api_user():
    """Create a test user for API authentication.

    Yields:
        Test user instance.
    """
    from apps.accounts.models import User

    user = User.objects.create_user(
        email="test@example.com",
        password="testpassword123",
        username="testuser",
    )
    yield user
    user.delete()


@pytest.fixture
def api_client():
    """Create an API client for testing.

    Returns:
        APIClient instance.
    """
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def authenticated_client(api_client, api_user):
    """Create an authenticated API client.

    Args:
        api_client: APIClient fixture.
        api_user: Test user fixture.

    Returns:
        Authenticated APIClient instance.
    """
    api_client.force_authenticate(user=api_user)
    return api_client
