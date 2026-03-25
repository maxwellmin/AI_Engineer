"""
Data models for chat_agent application.

This module defines the Conversation and Message models for persistent storage
of chat conversations.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from apps.chat_agent.constants import AgentType, MessageRole


class Conversation(models.Model):
    """
    Conversation session model.

    A conversation represents a chat session between a user and the RAG agent.
    It contains metadata about the conversation and links to all messages.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
        help_text="User who owns this conversation",
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Title of the conversation (auto-generated or user-defined)",
    )

    # Configuration
    agent_type = models.CharField(
        max_length=20,
        choices=[(t.value, t.name.replace("_", " ").title()) for t in AgentType],
        default=AgentType.TEXT_RAG.value,
        help_text="Type of RAG agent to use",
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this conversation is active",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conversations"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "-updated_at"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"Conversation {self.id} ({self.agent_type})"

    @property
    def message_count(self) -> int:
        """Return the number of messages in this conversation."""
        return self.messages.count()


class Message(models.Model):
    """
    Message in a conversation.

    A message represents a single turn in the conversation, either from
    the user or the assistant. It stores the content, metadata, and
    references to RAG context.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        help_text="Conversation this message belongs to",
    )

    role = models.CharField(
        max_length=10,
        choices=[(r.value, r.name.title()) for r in MessageRole],
        help_text="Role of the message sender",
    )
    content = models.TextField(
        help_text="Content of the message",
    )

    # RAG context (for assistant messages)
    sources = models.JSONField(
        default=list,
        blank=True,
        help_text="List of source chunk IDs used for this response",
    )
    retrieval_scores = models.JSONField(
        default=dict,
        blank=True,
        help_text="Retrieval scores for each source",
    )

    # Metadata
    token_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of tokens in this message",
    )
    model_used = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="LLM model used for generating this message",
    )

    # Milvus reference (for conversation history vector search)
    embedding_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="ID of the message embedding in Milvus",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self) -> str:
        return f"Message {self.id} ({self.role})"

    def to_llm_format(self) -> dict[str, str]:
        """Convert message to LLM API format."""
        return {
            "role": self.role,
            "content": self.content,
        }
