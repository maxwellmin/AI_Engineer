"""
Tests for Conversation and Message models.
"""

from __future__ import annotations

import pytest

from apps.chat_agent.constants import AgentType, MessageRole
from apps.chat_agent.models import Conversation, Message


@pytest.mark.django_db
class TestConversationModel:
    """Tests for Conversation model."""

    def test_create_conversation(self, test_user):
        """Test creating a conversation."""
        conversation = Conversation.objects.create(
            user=test_user,
            agent_type=AgentType.TEXT_RAG.value,
            title="Test",
        )

        assert conversation.id is not None
        assert str(conversation.user_id) == str(test_user.id)
        assert conversation.agent_type == AgentType.TEXT_RAG.value
        assert conversation.title == "Test"
        assert conversation.is_active is True
        assert conversation.created_at is not None
        assert conversation.updated_at is not None

    def test_conversation_str(self, test_conversation):
        """Test conversation string representation."""
        assert "Conversation" in str(test_conversation)
        assert test_conversation.agent_type in str(test_conversation)

    def test_message_count_property(self, test_conversation_with_messages):
        """Test message_count property."""
        conversation, messages = test_conversation_with_messages
        assert conversation.message_count == 10  # 5 user + 5 assistant

    def test_conversation_ordering(self, test_user):
        """Test conversations are ordered by updated_at descending."""
        import time

        conv1 = Conversation.objects.create(
            user=test_user,
            title="First",
        )
        time.sleep(0.01)  # Ensure different timestamps
        conv2 = Conversation.objects.create(
            user=test_user,
            title="Second",
        )

        conversations = list(Conversation.objects.all())
        assert conversations[0].id == conv2.id
        assert conversations[1].id == conv1.id

    def test_agent_type_choices(self, test_user):
        """Test all agent types can be created."""
        for agent_type in [AgentType.TEXT_RAG, AgentType.GRAPH_RAG]:
            conversation = Conversation.objects.create(
                user=test_user,
                agent_type=agent_type.value,
            )
            assert conversation.agent_type == agent_type.value


@pytest.mark.django_db
class TestMessageModel:
    """Tests for Message model."""

    def test_create_message(self, test_conversation):
        """Test creating a message."""
        message = Message.objects.create(
            conversation=test_conversation,
            role=MessageRole.USER.value,
            content="Test message",
        )

        assert message.id is not None
        assert str(message.conversation_id) == str(test_conversation.id)
        assert message.role == MessageRole.USER.value
        assert message.content == "Test message"
        assert message.sources == []
        assert message.retrieval_scores == {}
        assert message.created_at is not None

    def test_message_str(self, test_message):
        """Test message string representation."""
        assert "Message" in str(test_message)
        assert test_message.role in str(test_message)

    def test_to_llm_format(self, test_message):
        """Test to_llm_format method."""
        llm_format = test_message.to_llm_format()

        assert llm_format["role"] == test_message.role
        assert llm_format["content"] == test_message.content

    def test_message_with_sources(self, test_assistant_message):
        """Test message with sources."""
        assert test_assistant_message.sources == ["chunk_1", "chunk_2"]
        assert test_assistant_message.retrieval_scores == {
            "vector": 0.85,
            "keyword": 0.72,
        }

    def test_message_ordering(self, test_conversation):
        """Test messages are ordered by created_at."""
        msg1 = Message.objects.create(
            conversation=test_conversation,
            role="user",
            content="First",
        )
        msg2 = Message.objects.create(
            conversation=test_conversation,
            role="assistant",
            content="Second",
        )

        messages = list(Message.objects.filter(conversation=test_conversation))
        assert messages[0].id == msg1.id
        assert messages[1].id == msg2.id

    def test_role_choices(self, test_conversation):
        """Test all message roles can be created."""
        for role in [MessageRole.USER, MessageRole.ASSISTANT, MessageRole.SYSTEM]:
            message = Message.objects.create(
                conversation=test_conversation,
                role=role.value,
                content=f"Test {role.value}",
            )
            assert message.role == role.value

    def test_cascade_delete(self, test_user):
        """Test messages are deleted when conversation is deleted."""
        conversation = Conversation.objects.create(
            user=test_user,
        )
        message = Message.objects.create(
            conversation=conversation,
            role="user",
            content="Test",
        )

        conversation_id = conversation.id
        message_id = message.id

        conversation.delete()

        assert not Conversation.objects.filter(id=conversation_id).exists()
        assert not Message.objects.filter(id=message_id).exists()
