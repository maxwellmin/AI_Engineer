"""
Mock embedding client implementation.

This module provides the MockEmbeddingClient for generating deterministic
embeddings without requiring an API key, useful for development and testing.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import numpy as np

from apps.embedding_engine.constants import DEFAULT_DIMENSION, DEFAULT_MODEL
from apps.embedding_engine.dto import BatchEmbeddingResult, EmbeddingResult
from apps.embedding_engine.exceptions import EmbeddingEmptyInputError

logger = logging.getLogger(__name__)


class MockEmbeddingClient:
    """Mock client for generating deterministic embeddings.

    This client generates consistent, deterministic embeddings based on text
    content hash, useful for development and testing without API access.

    The embeddings are not semantically meaningful but are:
    - Deterministic: Same text always produces same embedding
    - Dimension-correct: Matches expected embedding dimension
    - Normalized: Vectors are unit-normalized for cosine similarity

    Attributes:
        dimension: Embedding dimension.
        model: Model name (always "mock").

    Example:
        >>> client = MockEmbeddingClient(dimension=1536)
        >>> result = client.embed_single("Hello world")
        >>> print(len(result.embedding))
        1536
    """

    def __init__(
        self,
        dimension: int | None = None,
        model: str | None = None,
        seed: int | None = None,
    ) -> None:
        """Initialize the mock embedding client.

        Args:
            dimension: Embedding dimension. Defaults to 1536.
            model: Model name for identification.
            seed: Optional random seed for reproducibility.
        """
        self._dimension = dimension or DEFAULT_DIMENSION
        self._model = model or "mock"
        self._seed = seed
        self._rng = np.random.default_rng(seed)

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._dimension

    @property
    def model(self) -> str:
        """Return the model name."""
        return self._model

    def _hash_text(self, text: str) -> int:
        """Generate a deterministic hash from text.

        Args:
            text: Text to hash.

        Returns:
            Integer hash value.
        """
        # Use SHA-256 for consistent hashing
        hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()
        # Convert first 8 bytes to integer
        return int.from_bytes(hash_bytes[:8], byteorder="big")

    def _generate_embedding(self, text: str) -> list[float]:
        """Generate a deterministic embedding for text.

        Args:
            text: Text to embed.

        Returns:
            List of floats representing the embedding vector.
        """
        # Generate seed from text hash
        text_seed = self._hash_text(text)

        # Create a new RNG with text-specific seed for determinism
        rng = np.random.default_rng(text_seed)

        # Generate random vector
        vector = rng.standard_normal(self._dimension)

        # Normalize to unit length (for cosine similarity)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector.tolist()

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Simple estimation: ~4 characters per token on average.

        Args:
            text: Text to estimate.

        Returns:
            Estimated token count.
        """
        return max(1, len(text) // 4)

    def embed(
        self,
        texts: list[str],
        model: str | None = None,
        **kwargs: Any,
    ) -> BatchEmbeddingResult:
        """Embed a list of texts.

        Args:
            texts: List of text strings to embed.
            model: Optional model override (ignored in mock).
            **kwargs: Additional parameters (ignored in mock).

        Returns:
            BatchEmbeddingResult with deterministic embeddings.

        Raises:
            EmbeddingEmptyInputError: If texts list is empty.
        """
        if not texts:
            raise EmbeddingEmptyInputError()

        # Filter empty strings
        non_empty_texts = [t for t in texts if t.strip()]
        if not non_empty_texts:
            raise EmbeddingEmptyInputError()

        # Generate embeddings
        embeddings = [self._generate_embedding(text) for text in non_empty_texts]

        # Estimate total tokens
        total_tokens = sum(self._estimate_tokens(text) for text in non_empty_texts)

        return BatchEmbeddingResult(
            embeddings=embeddings,
            dimension=self._dimension,
            model=self._model,
            total_tokens=total_tokens,
            success_count=len(embeddings),
        )

    def embed_single(
        self,
        text: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResult:
        """Embed a single text.

        Args:
            text: Text string to embed.
            model: Optional model override (ignored in mock).
            **kwargs: Additional parameters (ignored in mock).

        Returns:
            EmbeddingResult with deterministic embedding.

        Raises:
            EmbeddingEmptyInputError: If text is empty.
        """
        if not text or not text.strip():
            raise EmbeddingEmptyInputError()

        # Generate embedding
        embedding = self._generate_embedding(text)

        # Estimate tokens
        tokens_used = self._estimate_tokens(text)

        return EmbeddingResult(
            embedding=embedding,
            dimension=self._dimension,
            model=self._model,
            tokens_used=tokens_used,
        )

    def health_check(self) -> bool:
        """Check if the embedding service is healthy.

        Mock client is always healthy.

        Returns:
            Always True for mock client.
        """
        return True
