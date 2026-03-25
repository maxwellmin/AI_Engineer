"""
LLM service for streaming generation with Qwen API.

This service handles LLM operations including:
- Streaming text generation
- Prompt building
- Token counting
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from django.conf import settings

from apps.chat_agent.constants import DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE
from apps.chat_agent.exceptions import LLMError

logger = logging.getLogger(__name__)

# Default system prompt for RAG assistant
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant specialized in answering questions based on the provided context.

Instructions:
1. Answer the user's question based primarily on the provided context
2. If the context doesn't contain enough information, say so honestly
3. Cite relevant sources when possible using [Document X] notation
4. Be concise and accurate
5. If the user's question is unclear, ask for clarification

You have access to conversation history and relevant documents from the knowledge base."""


class LLMService:
    """Service for LLM operations.

    This service provides methods for:
    - Streaming text generation via Qwen API
    - Building prompts for RAG
    - Token estimation

    Example:
        >>> service = LLMService()
        >>> async for chunk in service.stream_generate(messages):
        ...     print(chunk, end="", flush=True)
    """

    def __init__(self) -> None:
        """Initialize the LLM service."""
        self._config = getattr(settings, "QWEN_CONFIG", {})
        self._chat_config = getattr(settings, "CHAT_AGENT_CONFIG", {}).get(
            "llm", {}
        )
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Get or create OpenAI client (lazy initialization).

        Qwen API is OpenAI-compatible.
        """
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(
                    api_key=self._config.get("api_key", ""),
                    base_url=self._config.get("base_url", ""),
                )
            except ImportError:
                raise LLMError("OpenAI package not installed")
        return self._client

    @property
    def model(self) -> str:
        """Get the model name."""
        return self._chat_config.get("model") or self._config.get(
            "chat_model", "qwen-2-7b"
        )

    @property
    def default_temperature(self) -> float:
        """Get default temperature."""
        return self._chat_config.get("temperature", DEFAULT_TEMPERATURE)

    @property
    def default_max_tokens(self) -> int:
        """Get default max tokens."""
        return self._chat_config.get("max_tokens", DEFAULT_MAX_TOKENS)

    # =========================================================================
    # Main Methods
    # =========================================================================

    async def stream_generate(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream generate response from LLM.

        This method calls the Qwen API with streaming enabled and yields
        token chunks for real-time display.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model name (optional override).
            temperature: Temperature (optional override).
            max_tokens: Maximum tokens (optional override).

        Yields:
            Token chunks as they are generated.

        Raises:
            LLMError: If API call fails.

        Example:
            >>> messages = [
            ...     {"role": "system", "content": "You are helpful."},
            ...     {"role": "user", "content": "Hello!"},
            ... ]
            >>> async for chunk in service.stream_generate(messages):
            ...     print(chunk, end="")
        """
        model = model or self.model
        temperature = temperature if temperature is not None else self.default_temperature
        max_tokens = max_tokens or self.default_max_tokens

        logger.debug(
            f"Starting streaming generation with model={model}, "
            f"temperature={temperature}, max_tokens={max_tokens}"
        )

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except asyncio.TimeoutError:
            raise LLMError("Request timeout")
        except Exception as e:
            logger.exception(f"LLM streaming failed: {e}")
            raise LLMError(str(e))

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate response from LLM (non-streaming).

        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model name (optional override).
            temperature: Temperature (optional override).
            max_tokens: Maximum tokens (optional override).

        Returns:
            Complete response text.

        Raises:
            LLMError: If API call fails.
        """
        model = model or self.model
        temperature = temperature if temperature is not None else self.default_temperature
        max_tokens = max_tokens or self.default_max_tokens

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            logger.exception(f"LLM generation failed: {e}")
            raise LLMError(str(e))

    # =========================================================================
    # Prompt Building
    # =========================================================================

    def build_prompt(
        self,
        system_prompt: str | None = None,
        context: str = "",
        history: list[dict[str, str]] | None = None,
        query: str = "",
    ) -> list[dict[str, str]]:
        """Build message list for LLM API.

        Args:
            system_prompt: System prompt (uses default if not provided).
            context: Assembled context from RAG retrieval.
            history: Conversation history messages.
            query: Current user query.

        Returns:
            List of message dicts for the API.

        Example:
            >>> messages = service.build_prompt(
            ...     context="Retrieved context...",
            ...     query="What is ML?",
            ... )
        """
        messages: list[dict[str, str]] = []

        # System message
        system_content = system_prompt or DEFAULT_SYSTEM_PROMPT

        if context:
            system_content += f"\n\n=== Context ===\n{context}"

        messages.append({"role": "system", "content": system_content})

        # History messages
        if history:
            messages.extend(history)

        # Current query
        if query:
            messages.append({"role": "user", "content": query})

        return messages

    def build_rag_prompt(
        self,
        query: str,
        context: str,
        history: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
    ) -> list[dict[str, str]]:
        """Build prompt specifically for RAG.

        This is a convenience method that wraps build_prompt.

        Args:
            query: User query.
            context: Retrieved context.
            history: Conversation history.
            system_prompt: Custom system prompt.

        Returns:
            List of message dicts.
        """
        return self.build_prompt(
            system_prompt=system_prompt,
            context=context,
            history=history,
            query=query,
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        This is a rough estimation using character count.
        For accurate counting, use a tokenizer like tiktoken.

        Args:
            text: Text to estimate.

        Returns:
            Estimated token count.
        """
        # Rough estimation: ~4 characters per token for English/Chinese mixed
        return len(text) // 4

    async def health_check(self) -> dict[str, Any]:
        """Check LLM service health.

        Returns:
            Dictionary with health status.
        """
        try:
            # Try a minimal generation
            response = await self.generate(
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10,
            )
            return {
                "status": "healthy",
                "model": self.model,
                "response_length": len(response),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "model": self.model,
                "error": str(e),
            }
