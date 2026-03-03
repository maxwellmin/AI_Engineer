"""
Embedding clients module.

This module provides client implementations for different embedding providers
and a factory function to create the appropriate client based on configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings

from apps.embedding_engine.clients.base import BaseEmbeddingClient
from apps.embedding_engine.clients.mock_client import MockEmbeddingClient
from apps.embedding_engine.clients.qwen_client import QwenEmbeddingClient
from apps.embedding_engine.exceptions import MissingAPIKeyError

if TYPE_CHECKING:
    pass

__all__ = [
    "BaseEmbeddingClient",
    "MockEmbeddingClient",
    "QwenEmbeddingClient",
    "get_embedding_client",
]


def get_embedding_client(config: dict | None = None) -> BaseEmbeddingClient:
    """Get an embedding client based on configuration.

    This factory function returns the appropriate embedding client
    based on the configuration settings.

    Args:
        config: Optional configuration override. If not provided,
            uses EMBEDDING_CONFIG from Django settings.

    Returns:
        BaseEmbeddingClient instance (QwenEmbeddingClient or MockEmbeddingClient).

    Raises:
        MissingAPIKeyError: If Qwen client is selected but API key is missing.

    Example:
        >>> # Get default client from settings
        >>> client = get_embedding_client()
        >>> result = client.embed_single("Hello world")

        >>> # Get mock client for testing
        >>> client = get_embedding_client({"use_mock": True})
        >>> result = client.embed_single("Hello world")
    """
    # Use provided config or get from Django settings
    if config is None:
        config = getattr(settings, "EMBEDDING_CONFIG", {})

    # Check if mock mode is enabled
    use_mock = config.get("use_mock", False)

    if use_mock:
        return MockEmbeddingClient(
            dimension=config.get("dimension"),
            model=config.get("model"),
        )

    # Use Qwen client
    api_key = config.get("api_key")
    if not api_key:
        raise MissingAPIKeyError()

    return QwenEmbeddingClient(
        api_key=api_key,
        base_url=config.get("base_url"),
        model=config.get("model"),
        dimension=config.get("dimension"),
        timeout=config.get("timeout", {}).get("read"),
        max_retries=config.get("retry", {}).get("max_attempts"),
        backoff_factor=config.get("retry", {}).get("backoff_factor"),
    )
