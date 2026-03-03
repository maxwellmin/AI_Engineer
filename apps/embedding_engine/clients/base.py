"""
Base embedding client interface.

This module defines the abstract base class for all embedding clients,
providing a consistent interface for different embedding providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from apps.embedding_engine.dto import BatchEmbeddingResult, EmbeddingResult


class BaseEmbeddingClient(ABC):
    """Abstract base class for embedding clients.

    This class defines the interface that all embedding client implementations
    must follow, enabling easy substitution between different providers.

    Example:
        >>> class MyEmbeddingClient(BaseEmbeddingClient):
        ...     def embed(self, texts, model=None, **kwargs):
        ...         # Implementation here
        ...         pass
    """

    @abstractmethod
    def embed(
        self,
        texts: list[str],
        model: str | None = None,
        **kwargs: Any,
    ) -> BatchEmbeddingResult:
        """Embed a list of texts.

        Args:
            texts: List of text strings to embed.
            model: Optional model override.
            **kwargs: Additional provider-specific parameters.
                - task_type: Task type for embedding (document or query)

        Returns:
            BatchEmbeddingResult with embeddings.

        Raises:
            EmbeddingEmptyInputError: If texts list is empty.
            EmbeddingInputTooLongError: If text exceeds token limit.
            EmbeddingAPIError: If API request fails.
        """
        ...

    @abstractmethod
    def embed_single(
        self,
        text: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResult:
        """Embed a single text.

        Args:
            text: Text string to embed.
            model: Optional model override.
            **kwargs: Additional provider-specific parameters.
                - task_type: Task type for embedding (document or query)

        Returns:
            EmbeddingResult with embedding.

        Raises:
            EmbeddingEmptyInputError: If text is empty.
            EmbeddingInputTooLongError: If text exceeds token limit.
            EmbeddingAPIError: If API request fails.
        """
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension.

        Returns:
            Dimension of the embedding vectors.
        """
        ...

    @property
    @abstractmethod
    def model(self) -> str:
        """Return the default model name.

        Returns:
            Name of the default embedding model.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the embedding service is healthy.

        Returns:
            True if service is healthy, False otherwise.
        """
        ...
