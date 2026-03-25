"""
Serializers for chat_agent application.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.chat_agent.constants import AgentType


class ConversationSerializer(serializers.Serializer):
    """Serializer for Conversation model."""

    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(max_length=255, required=False, default="")
    agent_type = serializers.ChoiceField(
        choices=[(t.value, t.name) for t in AgentType],
        default=AgentType.TEXT_RAG.value,
    )
    is_active = serializers.BooleanField(default=True)
    message_count = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class ConversationCreateSerializer(serializers.Serializer):
    """Serializer for creating a new conversation."""

    title = serializers.CharField(max_length=255, required=False, default="")
    agent_type = serializers.ChoiceField(
        choices=[(t.value, t.name) for t in AgentType],
        default=AgentType.TEXT_RAG.value,
    )


class MessageSerializer(serializers.Serializer):
    """Serializer for Message model."""

    id = serializers.UUIDField(read_only=True)
    role = serializers.CharField()
    content = serializers.CharField()
    sources = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    token_count = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class SendMessageSerializer(serializers.Serializer):
    """Serializer for sending a message (HTTP fallback)."""

    content = serializers.CharField(max_length=4000)


class MessageResponseSerializer(serializers.Serializer):
    """Serializer for message response with sources."""

    id = serializers.UUIDField(read_only=True)
    role = serializers.CharField()
    content = serializers.CharField()
    sources = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )
    token_count = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class ChatResponseSerializer(serializers.Serializer):
    """Serializer for chat response."""

    message_id = serializers.UUIDField()
    content = serializers.CharField()
    sources = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )
    token_count = serializers.IntegerField()
