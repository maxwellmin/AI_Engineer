"""
Embed Step Runner for Document Pipeline.

This module implements the embed step that generates embeddings
for document chunks using the embedding_engine module.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from django.db import transaction

from apps.document_pipeline_manager.constants import PipelineStepName, PipelineStepOrder
from apps.document_pipeline_manager.dto import StepResult
from apps.document_pipeline_manager.exceptions import EmbedError
from apps.document_pipeline_manager.runners.base import BaseStepRunner
from apps.documents_parser.models import Document, DocumentChunk
from apps.embedding_engine.dto import EmbedForStorageRequest
from apps.embedding_engine.services import EmbeddingService

logger = logging.getLogger(__name__)


class EmbedStepRunner(BaseStepRunner):
    """
    Embed step runner that generates embeddings for document chunks.

    This step:
    1. Retrieves all chunks for the document
    2. Generates embeddings using EmbeddingService
    3. Updates chunks with embedding vectors (stored temporarily)
    """

    step_name = PipelineStepName.EMBED.value
    step_order = PipelineStepOrder.EMBED

    # Maximum text length for summary
    MAX_SUMMARY_LENGTH = 200

    def __init__(
        self,
        batch_size: int = 20,
        dimension: int = 1536,
    ) -> None:
        """
        Initialize the embed step runner.

        Args:
            batch_size: Number of chunks to embed per batch.
            dimension: Embedding dimension (default 1536 for OpenAI/Qwen).
        """
        self._batch_size = batch_size
        self._dimension = dimension
        self._embedding_service: EmbeddingService | None = None

    @property
    def embedding_service(self) -> EmbeddingService:
        """Get or create EmbeddingService instance."""
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    def execute(self, document_id: str, **kwargs) -> StepResult:
        """
        Execute the embed step.

        Args:
            document_id: UUID of the document to embed.

        Returns:
            StepResult with embedding outcome and statistics.
        """
        start_time = self._get_start_time()
        self._log_start(document_id)

        try:
            # Get document
            try:
                document = Document.objects.get(id=document_id)
            except Document.DoesNotExist:
                error_msg = f"Document '{document_id}' not found"
                self._log_failure(document_id, error_msg)
                return self._create_failure_result(error_msg)

            # Get chunks
            chunks = list(document.chunks.all().order_by("chunk_index"))

            if not chunks:
                error_msg = f"No chunks found for document '{document_id}'"
                self._log_failure(document_id, error_msg)
                return self._create_failure_result(error_msg)

            # Prepare chunks for embedding
            chunk_data = self._prepare_chunks_for_embedding(chunks)

            # Generate embeddings
            embed_result = self._generate_embeddings(chunk_data)

            # Update chunks with embeddings
            updated_count = self._update_chunks_with_embeddings(
                chunks, embed_result.get("chunks", [])
            )

            duration_ms = self._calculate_duration_ms(start_time)
            self._log_complete(document_id, duration_ms)

            # Prepare output data
            output_data = {
                "chunk_count": len(chunks),
                "embedded_count": updated_count,
                "total_tokens": embed_result.get("total_tokens", 0),
                "dimension": self._dimension,
                "batch_size": self._batch_size,
            }

            logger.debug(
                f"[Pipeline] Embedded document {document_id}: "
                f"{output_data['embedded_count']} chunks, {output_data['total_tokens']} tokens"
            )

            return self._create_success_result(output_data, duration_ms)

        except Exception as e:
            error_msg = f"Embed error: {str(e)}"
            self._log_failure(document_id, error_msg)
            logger.exception(f"[Pipeline] Embed step failed for document {document_id}")
            return self._create_failure_result(
                error_msg, self._calculate_duration_ms(start_time)
            )

    def _prepare_chunks_for_embedding(
        self,
        chunks: list[DocumentChunk],
    ) -> list[dict[str, Any]]:
        """
        Prepare chunk data for embedding.

        Args:
            chunks: List of DocumentChunk instances.

        Returns:
            List of dictionaries with text and summary for each chunk.
        """
        chunk_data = []
        for chunk in chunks:
            # Use first MAX_SUMMARY_LENGTH characters as summary
            summary = chunk.content[: self.MAX_SUMMARY_LENGTH] if chunk.content else ""

            chunk_data.append({
                "chunk_id": str(chunk.id),
                "chunk_index": chunk.chunk_index,
                "text": chunk.content,
                "summary": summary,
            })

        return chunk_data

    def _generate_embeddings(
        self,
        chunk_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Generate embeddings for chunks using EmbeddingService.

        Args:
            chunk_data: List of chunk dictionaries with text and summary.

        Returns:
            Dictionary with embedded chunks and token count.
        """
        try:
            # Create embedding request
            request = EmbedForStorageRequest(chunks=chunk_data)

            # Generate embeddings
            result = self.embedding_service.embed_for_storage(request)

            return {
                "chunks": result.chunks,
                "total_tokens": result.total_tokens,
                "success_count": result.success_count,
                "failed_count": result.failed_count,
            }

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise EmbedError(str(e))

    def _update_chunks_with_embeddings(
        self,
        chunks: list[DocumentChunk],
        embedded_chunks: list[dict[str, Any]],
    ) -> int:
        """
        Update chunks with their embeddings.

        Note: Embeddings are stored in a temporary location and will be
        sent to Milvus in the vectorize step. The chunk's vector_id field
        will be set after Milvus insertion.

        For now, we store embeddings in a simple cache that the vectorize
        step can access.

        Args:
            chunks: Original DocumentChunk instances.
            embedded_chunks: Chunks with embeddings from EmbeddingService.

        Returns:
            Number of chunks updated.
        """
        updated_count = 0

        # Create mapping of chunk_id to embeddings
        embedding_map = {}
        for embedded_chunk in embedded_chunks:
            chunk_id = embedded_chunk.get("chunk_id")
            if chunk_id:
                embedding_map[chunk_id] = {
                    "text_dense": embedded_chunk.get("text_dense", []),
                    "summary_dense": embedded_chunk.get("summary_dense", []),
                }

        # Store embeddings temporarily (they'll be used by vectorize step)
        # We store them in a module-level cache for simplicity
        # In production, use Redis or similar
        _chunk_embeddings_cache.update(embedding_map)

        updated_count = len(embedding_map)
        logger.debug(f"Cached embeddings for {updated_count} chunks")

        return updated_count


# Temporary cache for chunk embeddings
# In production, use Redis or similar
_chunk_embeddings_cache: dict[str, dict[str, list[float]]] = {}


def get_cached_embedding(chunk_id: str) -> dict[str, list[float]] | None:
    """
    Get cached embedding for a chunk.

    Args:
        chunk_id: UUID of the chunk.

    Returns:
        Dictionary with text_dense and summary_dense, or None if not found.
    """
    return _chunk_embeddings_cache.get(chunk_id)


def clear_cached_embeddings(chunk_ids: list[str] | None = None) -> None:
    """
    Clear cached embeddings.

    Args:
        chunk_ids: Optional list of chunk IDs to clear.
                   If None, clears all.
    """
    global _chunk_embeddings_cache

    if chunk_ids:
        for chunk_id in chunk_ids:
            _chunk_embeddings_cache.pop(chunk_id, None)
    else:
        _chunk_embeddings_cache.clear()
