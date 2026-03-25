"""
Pytest fixtures for chat_agent tests.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from apps.chat_agent.constants import AgentType
from apps.chat_agent.models import Conversation, Message

User = get_user_model()


# =============================================================================
# User Fixtures
# =============================================================================


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User.objects.create_user(
        email="test@example.com",
        username="testuser",
        password="testpassword123",
    )
    return user


@pytest.fixture
def test_user2(db):
    """Create a second test user for authorization tests."""
    user = User.objects.create_user(
        email="test2@example.com",
        username="testuser2",
        password="testpassword123",
    )
    return user


# =============================================================================
# Conversation Fixtures
# =============================================================================


@pytest.fixture
def test_conversation(db, test_user):
    """Create a test conversation."""
    conversation = Conversation.objects.create(
        user=test_user,
        agent_type=AgentType.TEXT_RAG.value,
        title="Test Conversation",
    )
    return conversation


@pytest.fixture
def test_graph_conversation(db, test_user):
    """Create a test graph RAG conversation."""
    conversation = Conversation.objects.create(
        user=test_user,
        agent_type=AgentType.GRAPH_RAG.value,
        title="Test Graph Conversation",
    )
    return conversation


# =============================================================================
# Message Fixtures
# =============================================================================


@pytest.fixture
def test_message(db, test_conversation):
    """Create a test user message."""
    message = Message.objects.create(
        conversation=test_conversation,
        role="user",
        content="Hello, this is a test message.",
    )
    return message


@pytest.fixture
def test_assistant_message(db, test_conversation):
    """Create a test assistant message."""
    message = Message.objects.create(
        conversation=test_conversation,
        role="assistant",
        content="Hello! How can I help you today?",
        sources=["chunk_1", "chunk_2"],
        retrieval_scores={"vector": 0.85, "keyword": 0.72},
        token_count=10,
        model_used="qwen-2-7b",
    )
    return message


@pytest.fixture
def test_conversation_with_messages(db, test_conversation):
    """Create a conversation with multiple messages."""
    messages = []
    for i in range(5):
        # User message
        user_msg = Message.objects.create(
            conversation=test_conversation,
            role="user",
            content=f"User message {i}",
        )
        messages.append(user_msg)

        # Assistant message
        assistant_msg = Message.objects.create(
            conversation=test_conversation,
            role="assistant",
            content=f"Assistant response {i}",
            token_count=5,
        )
        messages.append(assistant_msg)

    return test_conversation, messages


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_embedding_service():
    """Create a mock EmbeddingService."""
    mock = MagicMock()
    mock.embed_query.return_value = MagicMock(
        embedding=[0.1] * 1536,
        model="text-embedding-v1",
    )
    mock.dimension = 1536
    return mock


@pytest.fixture
def mock_milvus_service():
    """Create a mock MilvusService."""
    mock = MagicMock()
    mock.has_collection.return_value = True
    mock.insert_vectors.return_value = MagicMock(
        inserted_count=1,
        inserted_ids=[str(uuid.uuid4())],
    )
    mock.search.return_value = MagicMock(
        items=[],
        total=0,
    )
    mock.delete_vectors_by_filter.return_value = MagicMock(count=0)
    return mock


@pytest.fixture
def mock_search_service():
    """Create a mock SearchService."""
    from apps.document_rag_search.dto import SearchResponse

    mock = MagicMock()
    mock.hybrid_search.return_value = SearchResponse(
        results=[],
        total=0,
        query_time_ms=100.0,
        retrievers_used=["vector"],
    )
    return mock


@pytest.fixture
def mock_llm_service():
    """Create a mock LLMService."""
    mock = MagicMock()
    mock.model = "qwen-2-7b"
    mock.build_rag_prompt.return_value = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Test query"},
    ]
    mock.estimate_tokens.return_value = 10

    # Create async generator for stream_generate
    async def mock_stream(messages):
        for chunk in ["Hello", " ", "world", "!"]:
            yield chunk

    mock.stream_generate = mock_stream
    return mock


@pytest.fixture
def mock_conversation_service(test_conversation, test_message):
    """Create a mock ConversationService."""
    mock = MagicMock()
    mock.get_conversation.return_value = test_conversation
    mock.create_conversation.return_value = test_conversation
    mock.add_message.return_value = test_message
    mock.get_history.return_value = []
    return mock


@pytest.fixture
def mock_context_service():
    """Create a mock ContextService."""
    from apps.chat_agent.agents.state import ContextResult

    mock = MagicMock()
    mock.assemble_context.return_value = ContextResult(
        context="Test context",
        sources=[],
        retrieval_scores={},
        history=[],
    )
    return mock


# =============================================================================
# API Client Fixtures
# =============================================================================


@pytest.fixture
def api_client():
    """Create an API client."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def authenticated_client(api_client, test_user):
    """Create an authenticated API client."""
    api_client.force_authenticate(user=test_user)
    return api_client
