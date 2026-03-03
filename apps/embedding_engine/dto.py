"""
Data Transfer Objects (DTOs) for embedding engine.

This module defines all dataclasses used for request and response objects
in the embedding engine API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# =============================================================================
# Request DTOs
# =============================================================================


@dataclass(frozen=True)
class EmbedTextRequest:
    """Request to embed a single text.

    Attributes:
        text: Text content to embed.
        model: Embedding model name.
        task_type: Task type (document or query).
    """

    text: str
    model: str = "text-embedding-v1"
    task_type: str = "retrieval.document"


@dataclass(frozen=True)
class EmbedTextsRequest:
    """Request to embed multiple texts.

    Attributes:
        texts: List of text contents to embed.
        model: Embedding model name.
        task_type: Task type (document or query).
        batch_size: Number of texts per API call.
    """

    texts: list[str]
    model: str = "text-embedding-v1"
    task_type: str = "retrieval.document"
    batch_size: int = 20


@dataclass(frozen=True)
class EmbedForStorageRequest:
    """Request to embed document chunks for Milvus storage.

    Attributes:
        chunks: List of chunk dictionaries with 'text' and 'summary' fields.
        model: Embedding model name.
    """

    chunks: list[dict[str, Any]]  # Each chunk: {text, summary, chunk_id, ...}
    model: str = "text-embedding-v1"


# =============================================================================
# Response DTOs
# =============================================================================


@dataclass(frozen=True)
class EmbeddingResult:
    """Result of a single embedding operation.

    Attributes:
        embedding: Dense vector (shape: dimension,).
        dimension: Vector dimension.
        model: Model used for embedding.
        tokens_used: Number of tokens consumed.
    """

    embedding: list[float]
    dimension: int
    model: str
    tokens_used: int


@dataclass(frozen=True)
class BatchEmbeddingResult:
    """Result of a batch embedding operation.

    Attributes:
        embeddings: List of dense vectors.
        dimension: Vector dimension.
        model: Model used for embedding.
        total_tokens: Total tokens consumed.
        success_count: Number of successful embeddings.
        failed_count: Number of failed embeddings.
    """

    embeddings: list[list[float]]
    dimension: int
    model: str
    total_tokens: int
    success_count: int
    failed_count: int = 0


@dataclass(frozen=True)
class StorageEmbeddingResult:
    """Result of embedding document chunks for storage.

    Attributes:
        chunks: List of chunks with added 'summary_dense' and 'text_dense' fields.
        total_tokens: Total tokens consumed.
        success_count: Number of successfully embedded chunks.
        failed_count: Number of failed chunks.
    """

    chunks: list[dict[str, Any]]
    total_tokens: int
    success_count: int
    failed_count: int = 0


# =============================================================================
# Health Check DTOs
# =============================================================================


@dataclass(frozen=True)
class HealthCheckResult:
    """Result of embedding service health check.

    Attributes:
        healthy: Whether the service is healthy.
        provider: Provider type (qwen or mock).
        model: Model name.
        dimension: Embedding dimension.
        latency_ms: Response latency in milliseconds.
        error: Error message if unhealthy.
    """

    healthy: bool
    provider: str
    model: str
    dimension: int
    latency_ms: float = 0.0
    error: str | None = None


# =============================================================================
# Model Info DTOs
# =============================================================================


@dataclass(frozen=True)
class ModelInfo:
    """Information about an embedding model.

    Attributes:
        name: Model name.
        dimension: Vector dimension.
        max_tokens: Maximum input tokens.
        description: Model description.
    """

    name: str
    dimension: int
    max_tokens: int = 8192
    description: str = ""


# =============================================================================
# Helper Functions
# =============================================================================


def create_embedding_result(
    embedding: list[float],
    model: str,
    tokens_used: int,
    dimension: int | None = None,
) -> EmbeddingResult:
    """Create an EmbeddingResult with computed dimension.

    Args:
        embedding: Dense vector.
        model: Model used for embedding.
        tokens_used: Number of tokens consumed.
        dimension: Vector dimension (computed from embedding if not provided).

    Returns:
        EmbeddingResult instance.
    """
    return EmbeddingResult(
        embedding=embedding,
        dimension=dimension if dimension is not None else len(embedding),
        model=model,
        tokens_used=tokens_used,
    )


def create_batch_embedding_result(
    embeddings: list[list[float]],
    model: str,
    total_tokens: int,
    failed_count: int = 0,
    dimension: int | None = None,
) -> BatchEmbeddingResult:
    """Create a BatchEmbeddingResult with computed dimension.

    Args:
        embeddings: List of dense vectors.
        model: Model used for embedding.
        total_tokens: Total tokens consumed.
        failed_count: Number of failed embeddings.
        dimension: Vector dimension (computed from first embedding if not provided).

    Returns:
        BatchEmbeddingResult instance.
    """
    computed_dimension = dimension
    if computed_dimension is None and embeddings:
        computed_dimension = len(embeddings[0])
    elif computed_dimension is None:
        computed_dimension = 0

    return BatchEmbeddingResult(
        embeddings=embeddings,
        dimension=computed_dimension,
        model=model,
        total_tokens=total_tokens,
        success_count=len(embeddings),
        failed_count=failed_count,
    )
