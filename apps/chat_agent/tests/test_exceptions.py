"""
Tests for Exception classes.
"""

from __future__ import annotations

import pytest

from apps.chat_agent.exceptions import (
    AgentError,
    ChatAgentError,
    ContextAssemblyError,
    ConversationNotFoundError,
    LLMError,
    RateLimitError,
    TimeoutError,
    UnauthorizedAccessError,
)


class TestExceptions:
    """Tests for custom exception classes."""

    def test_chat_agent_error(self):
        """Test ChatAgentError base exception."""
        error = ChatAgentError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"

    def test_chat_agent_error_default_message(self):
        """Test ChatAgentError with default message."""
        error = ChatAgentError()
        assert str(error) == "Chat agent error"

    def test_conversation_not_found_error(self):
        """Test ConversationNotFoundError."""
        error = ConversationNotFoundError("conv-123")
        assert "conv-123" in str(error)
        assert "not found" in str(error).lower()

    def test_unauthorized_access_error(self):
        """Test UnauthorizedAccessError."""
        error = UnauthorizedAccessError()
        assert "Unauthorized" in str(error)

    def test_agent_error(self):
        """Test AgentError."""
        error = AgentError("text_rag", "Connection failed")
        assert "text_rag" in str(error)
        assert "Connection failed" in str(error)

    def test_llm_error(self):
        """Test LLMError."""
        error = LLMError("API timeout")
        assert "LLM error" in str(error)
        assert "API timeout" in str(error)

    def test_context_assembly_error(self):
        """Test ContextAssemblyError."""
        error = ContextAssemblyError("No documents found")
        assert "Context assembly error" in str(error)
        assert "No documents found" in str(error)

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError("messages")
        assert "Rate limit" in str(error)
        assert "messages" in str(error)

    def test_timeout_error(self):
        """Test TimeoutError."""
        error = TimeoutError("generation")
        assert "Timeout" in str(error)
        assert "generation" in str(error)

    def test_exception_inheritance(self):
        """Test all exceptions inherit from ChatAgentError."""
        exceptions = [
            ConversationNotFoundError("conv-1"),
            UnauthorizedAccessError(),
            AgentError("text_rag", "error"),
            LLMError("error"),
            ContextAssemblyError("error"),
            RateLimitError(),
            TimeoutError(),
        ]

        for exc in exceptions:
            assert isinstance(exc, ChatAgentError)
            assert isinstance(exc, Exception)
