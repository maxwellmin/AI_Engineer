"""
Tests for LLM Service.
"""

from __future__ import annotations

import pytest

from apps.chat_agent.services.llm_service import LLMService, DEFAULT_SYSTEM_PROMPT


@pytest.mark.django_db
class TestLLMService:
    """Tests for LLMService."""

    def test_model_property(self):
        """Test model property."""
        service = LLMService()
        # Should return a model name
        assert service.model is not None
        assert isinstance(service.model, str)

    def test_default_temperature(self):
        """Test default temperature property."""
        service = LLMService()
        temp = service.default_temperature
        assert isinstance(temp, float)
        assert 0 <= temp <= 2

    def test_default_max_tokens(self):
        """Test default max tokens property."""
        service = LLMService()
        max_tokens = service.default_max_tokens
        assert isinstance(max_tokens, int)
        assert max_tokens > 0

    def test_build_prompt_basic(self):
        """Test building prompt with basic inputs."""
        service = LLMService()

        messages = service.build_prompt(
            query="What is AI?",
        )

        assert isinstance(messages, list)
        assert len(messages) >= 1
        assert messages[0]["role"] == "system"

    def test_build_prompt_with_context(self):
        """Test building prompt with context."""
        service = LLMService()

        messages = service.build_prompt(
            query="What is AI?",
            context="AI is artificial intelligence...",
        )

        assert isinstance(messages, list)
        assert len(messages) >= 2
        # Context should be in system message
        assert "Context" in messages[0]["content"] or "AI is artificial" in messages[0]["content"]

    def test_build_prompt_with_history(self):
        """Test building prompt with conversation history."""
        service = LLMService()

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        messages = service.build_prompt(
            query="How are you?",
            history=history,
        )

        assert isinstance(messages, list)
        # Should include history messages
        assert len(messages) >= 3

    def test_build_rag_prompt(self):
        """Test building RAG prompt specifically."""
        service = LLMService()

        messages = service.build_rag_prompt(
            query="What is ML?",
            context="ML is machine learning...",
        )

        assert isinstance(messages, list)
        assert len(messages) >= 2

    def test_estimate_tokens(self):
        """Test token estimation."""
        service = LLMService()

        # Empty string
        assert service.estimate_tokens("") == 0

        # Short text
        tokens = service.estimate_tokens("Hello world")
        assert tokens >= 0

        # Long text
        long_text = "This is a long text. " * 100
        tokens = service.estimate_tokens(long_text)
        assert tokens > 0

    def test_default_system_prompt_constant(self):
        """Test default system prompt exists."""
        assert DEFAULT_SYSTEM_PROMPT is not None
        assert len(DEFAULT_SYSTEM_PROMPT) > 0
        assert "assistant" in DEFAULT_SYSTEM_PROMPT.lower()
