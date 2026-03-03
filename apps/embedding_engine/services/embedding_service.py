"""
Embedding service implementation.

This module provides the EmbeddingService facade class for all embedding operations,
coordinating between different embedding providers (Qwen, Mock).
"""

from __future__ import annotations

import logging
import time
from typing import Any

from django.conf import settings

from apps.embedding_engine.clients import get_embedding_client
from apps.embedding_engine.clients.base import BaseEmbeddingClient
from apps.embedding_engine.constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_DIMENSION,
    DEFAULT_MODEL,
    TaskType,
)
from apps.embedding_engine.dto import (
    BatchEmbeddingResult,
    EmbedForStorageRequest,
    EmbeddingResult,
    HealthCheckResult,
    StorageEmbeddingResult,
)
from apps.embedding_engine.exceptions import (
    EmbeddingDimensionError,
    EmbeddingEmptyInputError,
    EmbeddingProcessingError,
)

logger = logging.getLogger(__name__)


class EmbeddingService:
    """High-level facade service for embedding operations.

    This service provides a unified interface for all embedding operations,
    coordinating between different embedding providers (Qwen, Mock).

    The service handles:
    - Single text embedding (embed_text, embed_query)
    - Batch text embedding (embed_texts)
    - Storage-oriented embedding for Milvus (embed_for_storage)
    - Health checking (health_check)

    Example:
        >>> service = EmbeddingService()
        >>> # Embed single text
        >>> result = service.embed_text("Hello world")
        >>> print(result.embedding[:5])
        [0.123, -0.456, 0.789, ...]
        >>> # Embed for Milvus storage
        >>> chunks = [{"text": "doc text", "summary": "summary"}]
        >>> result = service.embed_for_storage(
        ...     EmbedForStorageRequest(chunks=chunks)
        ... )
        >>> print(result.chunks[0]["text_dense"][:5])
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the embedding service.

        Args:
            config: Optional configuration override. If not provided,
                uses EMBEDDING_CONFIG from Django settings.
        """
        self._config = config or getattr(settings, "EMBEDDING_CONFIG", {})
        self._client: BaseEmbeddingClient | None = None

    @property
    def _embedding_client(self) -> BaseEmbeddingClient:
        """Get or create the embedding client (lazy initialization).

        Returns:
            BaseEmbeddingClient instance.
        """
        if self._client is None:
            self._client = get_embedding_client(self._config)
        return self._client

    @property
    def dimension(self) -> int:
        """Return the embedding dimension.

        Returns:
            Embedding dimension (default: 1536).
        """
        return self._config.get("dimension", DEFAULT_DIMENSION)

    # =========================================================================
    # Core Embedding Methods
    # =========================================================================

    def embed_text(
        self,
        text: str,
        task_type: str = TaskType.DOCUMENT.value,
    ) -> EmbeddingResult:
        """Embed a single text.

        Args:
            text: Text to embed.
            task_type: Task type (document or query).
                - "retrieval.document": For documents to be stored
                - "retrieval.query": For search queries

        Returns:
            EmbeddingResult with embedding vector.

        Raises:
            EmbeddingEmptyInputError: If text is empty.
            EmbeddingAPIError: If API request fails.

        Example:
            >>> service = EmbeddingService()
            >>> result = service.embed_text("Hello world")
            >>> print(len(result.embedding))
            1536
        """
        if not text or not text.strip():
            raise EmbeddingEmptyInputError()

        return self._embedding_client.embed_single(
            text=text,
            task_type=task_type,
        )

    def embed_texts(
        self,
        texts: list[str],
        task_type: str = TaskType.DOCUMENT.value,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> BatchEmbeddingResult:
        """Embed multiple texts in batch.

        This method processes texts in batches to optimize API usage
        and handle large numbers of texts efficiently.

        Args:
            texts: List of texts to embed.
            task_type: Task type (document or query).
            batch_size: Number of texts per API call.

        Returns:
            BatchEmbeddingResult with all embeddings.

        Raises:
            EmbeddingEmptyInputError: If texts list is empty.
            EmbeddingAPIError: If API request fails.

        Example:
            >>> service = EmbeddingService()
            >>> texts = ["Hello", "World", "Test"]
            >>> result = service.embed_texts(texts)
            >>> print(len(result.embeddings))
            3
        """
        if not texts:
            raise EmbeddingEmptyInputError()

        # Filter empty strings
        non_empty_texts = [t for t in texts if t and t.strip()]
        if not non_empty_texts:
            raise EmbeddingEmptyInputError()

        # Process in batches if needed
        max_batch_size = self._config.get("max_batch_size", DEFAULT_BATCH_SIZE)
        effective_batch_size = min(batch_size, max_batch_size)

        if len(non_empty_texts) <= effective_batch_size:
            # Single batch
            return self._embedding_client.embed(
                texts=non_empty_texts,
                task_type=task_type,
            )

        # Multiple batches
        all_embeddings: list[list[float]] = []
        total_tokens = 0
        success_count = 0
        failed_count = 0

        for i in range(0, len(non_empty_texts), effective_batch_size):
            batch = non_empty_texts[i : i + effective_batch_size]
            try:
                batch_result = self._embedding_client.embed(
                    texts=batch,
                    task_type=task_type,
                )
                all_embeddings.extend(batch_result.embeddings)
                total_tokens += batch_result.total_tokens
                success_count += batch_result.success_count
                failed_count += batch_result.failed_count
            except Exception as e:
                logger.error(f"Batch embedding failed at index {i}: {e}")
                failed_count += len(batch)
                raise EmbeddingProcessingError(
                    reason=str(e),
                    batch_index=i // effective_batch_size,
                )

        return BatchEmbeddingResult(
            embeddings=all_embeddings,
            dimension=self.dimension,
            model=self._embedding_client.model,
            total_tokens=total_tokens,
            success_count=success_count,
            failed_count=failed_count,
        )

    def embed_query(self, query: str) -> EmbeddingResult:
        """Embed a search query (optimized for retrieval).

        This method is specifically designed for embedding search queries,
        using the "retrieval.query" task type for optimal retrieval performance.

        Args:
            query: Query text to embed.

        Returns:
            EmbeddingResult with query embedding.

        Raises:
            EmbeddingEmptyInputError: If query is empty.
            EmbeddingAPIError: If API request fails.

        Example:
            >>> service = EmbeddingService()
            >>> result = service.embed_query("What is machine learning?")
            >>> print(len(result.embedding))
            1536
        """
        return self.embed_text(
            text=query,
            task_type=TaskType.QUERY.value,
        )

    # =========================================================================
    # Storage-Oriented Methods
    # =========================================================================

    def embed_for_storage(
        self,
        request: EmbedForStorageRequest,
    ) -> StorageEmbeddingResult:
        """Embed document chunks for Milvus storage.

        This method generates both summary_dense and text_dense embeddings
        for each chunk, matching the Milvus multi-vector schema.

        The input chunks should have the following structure:
        ```python
        [
            {
                "text": "Full text content",
                "summary": "Summary or question",
                "chunk_id": 0,
                ...
            },
            ...
        ]
        ```

        The output chunks will have additional fields:
        - summary_dense: Embedding of the summary/question
        - text_dense: Embedding of the full text

        Args:
            request: EmbedForStorageRequest with chunks.

        Returns:
            StorageEmbeddingResult with chunks containing embeddings.

        Raises:
            EmbeddingEmptyInputError: If chunks list is empty.
            EmbeddingProcessingError: If embedding fails.

        Example:
            >>> service = EmbeddingService()
            >>> chunks = [
            ...     {"text": "Document content", "summary": "Summary"}
            ... ]
            >>> result = service.embed_for_storage(
            ...     EmbedForStorageRequest(chunks=chunks)
            ... )
            >>> print(result.chunks[0]["text_dense"][:5])
        """
        if not request.chunks:
            raise EmbeddingEmptyInputError()

        chunks_with_embeddings: list[dict[str, Any]] = []
        total_tokens = 0
        success_count = 0
        failed_count = 0

        # Extract texts and summaries for batch embedding
        texts = []
        summaries = []
        for chunk in request.chunks:
            text = chunk.get("text", "")
            summary = chunk.get("summary", text[:200] if text else "")  # Fallback to text prefix
            texts.append(text if text else "")
            summaries.append(summary if summary else "")

        # Batch embed texts
        text_embeddings: list[list[float]] = []
        summary_embeddings: list[list[float]] = []

        try:
            # Embed all texts
            if any(texts):
                text_result = self.embed_texts(
                    texts=texts,
                    task_type=TaskType.DOCUMENT.value,
                )
                text_embeddings = text_result.embeddings
                total_tokens += text_result.total_tokens

            # Embed all summaries
            if any(summaries):
                summary_result = self.embed_texts(
                    texts=summaries,
                    task_type=TaskType.DOCUMENT.value,
                )
                summary_embeddings = summary_result.embeddings
                total_tokens += summary_result.total_tokens

            # Combine embeddings with chunks
            for i, chunk in enumerate(request.chunks):
                chunk_copy = dict(chunk)

                # Add embeddings
                chunk_copy["text_dense"] = (
                    text_embeddings[i] if i < len(text_embeddings) else []
                )
                chunk_copy["summary_dense"] = (
                    summary_embeddings[i] if i < len(summary_embeddings) else []
                )

                # Validate dimensions
                if chunk_copy["text_dense"] and len(chunk_copy["text_dense"]) != self.dimension:
                    raise EmbeddingDimensionError(
                        expected=self.dimension,
                        actual=len(chunk_copy["text_dense"]),
                    )

                chunks_with_embeddings.append(chunk_copy)
                success_count += 1

        except Exception as e:
            logger.error(f"Storage embedding failed: {e}")
            failed_count = len(request.chunks)
            raise EmbeddingProcessingError(reason=str(e))

        return StorageEmbeddingResult(
            chunks=chunks_with_embeddings,
            total_tokens=total_tokens,
            success_count=success_count,
            failed_count=failed_count,
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def health_check(self) -> dict[str, Any]:
        """Check embedding service health.

        Returns:
            Dictionary with health status containing:
            - healthy: Whether the service is healthy
            - provider: Provider type (qwen or mock)
            - model: Model name
            - dimension: Embedding dimension
            - latency_ms: Response latency in milliseconds
            - error: Error message if unhealthy

        Example:
            >>> service = EmbeddingService()
            >>> result = service.health_check()
            >>> print(result["healthy"])
            True
        """
        start_time = time.time()
        provider = "mock" if self._config.get("use_mock") else "qwen"

        try:
            is_healthy = self._embedding_client.health_check()
            latency_ms = (time.time() - start_time) * 1000

            return HealthCheckResult(
                healthy=is_healthy,
                provider=provider,
                model=self._embedding_client.model,
                dimension=self._embedding_client.dimension,
                latency_ms=latency_ms,
            ).__dict__

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Health check failed: {e}")

            return HealthCheckResult(
                healthy=False,
                provider=provider,
                model=self._config.get("model", DEFAULT_MODEL),
                dimension=self.dimension,
                latency_ms=latency_ms,
                error=str(e),
            ).__dict__

    def get_supported_models(self) -> list[str]:
        """Return list of supported embedding models.

        Returns:
            List of supported model names.

        Example:
            >>> service = EmbeddingService()
            >>> print(service.get_supported_models())
            ['text-embedding-v1', 'text-embedding-v3']
        """
        from apps.embedding_engine.constants import EmbeddingModel

        return [model.value for model in EmbeddingModel]
