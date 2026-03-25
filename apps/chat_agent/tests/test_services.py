"""
Tests for ConversationService.
"""

from __future__ import annotations

import uuid

import pytest

from apps.chat_agent.constants import AgentType
from apps.chat_agent.exceptions import (
    ConversationNotFoundError,
    UnauthorizedAccessError,
)
from apps.chat_agent.services import ConversationService


@pytest.mark.django_db
class TestConversationService:
    """Tests for ConversationService."""

    def test_create_conversation(self, test_user):
        """Test creating a conversation."""
        service = ConversationService()

        conversation = service.create_conversation(
            user_id=test_user.id,
            agent_type=AgentType.TEXT_RAG.value,
            title="Test Conversation",
        )

        assert conversation.id is not None
        assert str(conversation.user_id) == str(test_user.id)
        assert conversation.agent_type == AgentType.TEXT_RAG.value
        assert conversation.title == "Test Conversation"

    def test_get_conversation(self, test_user, test_conversation):
        """Test getting a conversation."""
        service = ConversationService()

        result = service.get_conversation(
            conversation_id=test_conversation.id,
            user_id=test_user.id,
        )

        assert result.id == test_conversation.id

    def test_get_conversation_not_found(self, test_user):
        """Test getting a non-existent conversation."""
        service = ConversationService()

        with pytest.raises(ConversationNotFoundError):
            service.get_conversation(
                conversation_id=uuid.uuid4(),
                user_id=test_user.id,
            )

    def test_get_conversation_unauthorized(self, test_conversation, test_user2):
        """Test getting a conversation owned by another user."""
        service = ConversationService()

        with pytest.raises(UnauthorizedAccessError):
            service.get_conversation(
                conversation_id=test_conversation.id,
                user_id=test_user2.id,
            )

    def test_list_conversations(self, test_user, test_conversation):
        """Test listing conversations."""
        service = ConversationService()

        conversations = service.list_conversations(user_id=test_user.id)

        assert len(conversations) == 1
        assert conversations[0].id == test_conversation.id

    def test_update_conversation(self, test_user, test_conversation):
        """Test updating a conversation."""
        service = ConversationService()

        result = service.update_conversation(
            conversation_id=test_conversation.id,
            user_id=test_user.id,
            title="Updated Title",
            is_active=False,
        )

        assert result.title == "Updated Title"
        assert result.is_active is False

    def test_delete_conversation(self, test_user, test_conversation):
        """Test deleting a conversation."""
        service = ConversationService()

        result = service.delete_conversation(
            conversation_id=test_conversation.id,
            user_id=test_user.id,
        )

        assert result is True
        with pytest.raises(ConversationNotFoundError):
            service.get_conversation(
                conversation_id=test_conversation.id,
                user_id=test_user.id,
            )


@pytest.mark.django_db
class TestMessageService:
    """Tests for message operations in ConversationService."""

    def test_add_message(self, test_conversation):
        """Test adding a message."""
        service = ConversationService()

        message = service.add_message(
            conversation_id=test_conversation.id,
            role="user",
            content="Hello world",
        )

        assert message.id is not None
        assert message.role == "user"
        assert message.content == "Hello world"

    def test_add_message_with_sources(self, test_conversation):
        """Test adding a message with sources."""
        service = ConversationService()

        message = service.add_message(
            conversation_id=test_conversation.id,
            role="assistant",
            content="Response",
            sources=["chunk_1", "chunk_2"],
            retrieval_scores={"vector": 0.9},
            token_count=10,
            model_used="qwen-2-7b",
        )

        assert message.sources == ["chunk_1", "chunk_2"]
        assert message.retrieval_scores == {"vector": 0.9}
        assert message.token_count == 10
        assert message.model_used == "qwen-2-7b"

    def test_get_history(self, test_conversation_with_messages):
        """Test getting conversation history."""
        conversation, messages = test_conversation_with_messages
        service = ConversationService()

        history = service.get_history(
            conversation_id=conversation.id,
            limit=5,
        )

        # Should return 5 messages (most recent)
        assert len(history) == 5

    def test_count_conversations(self, test_user, test_conversation):
        """Test counting conversations."""
        service = ConversationService()

        count = service.count_conversations(user_id=test_user.id)
        assert count == 1

        count_active = service.count_conversations(
            user_id=test_user.id,
            is_active=True,
        )
        assert count_active == 1

    def test_count_messages(self, test_conversation_with_messages):
        """Test counting messages."""
        conversation, messages = test_conversation_with_messages
        service = ConversationService()

        count = service.count_messages(conversation_id=conversation.id)
        assert count == 10  # 5 user + 5 assistant
