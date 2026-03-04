"""
Chunk Step Runner for Document Pipeline.

This module implements the chunk step that splits document text
into smaller chunks for embedding and vector storage.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from django.db import transaction

from apps.document_pipeline_manager.constants import PipelineStepName, PipelineStepOrder
from apps.document_pipeline_manager.dto import StepResult
from apps.document_pipeline_manager.exceptions import ChunkError
from apps.document_pipeline_manager.runners.base import BaseStepRunner
from apps.documents_parser.models import Document, DocumentChunk
from apps.documents_parser.services.chunking.splitter import (
    ChunkingConfig,
    TextSplitter,
)
from apps.documents_parser.services.hash import calculate_content_hash

logger = logging.getLogger(__name__)


class ChunkStepRunner(BaseStepRunner):
    """
    Chunk step runner that splits document text into chunks.

    This step:
    1. Retrieves the document and checks its status
    2. Reads the parsed text content
    3. Splits text into chunks using TextSplitter
    4. Creates DocumentChunk records with content hashes
    """

    step_name = PipelineStepName.CHUNK.value
    step_order = PipelineStepOrder.CHUNK

    # Default chunking configuration
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_CHUNK_OVERLAP = 200

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        """
        Initialize the chunk step runner.

        Args:
            chunk_size: Maximum size of each chunk in characters.
            chunk_overlap: Number of characters to overlap between chunks.
        """
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def execute(self, document_id: str, **kwargs) -> StepResult:
        """
        Execute the chunk step.

        Args:
            document_id: UUID of the document to chunk.

        Returns:
            StepResult with chunking outcome and statistics.
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

            # Check document status
            if document.status == Document.Status.UPLOADED:
                error_msg = f"Document '{document_id}' has not been parsed yet"
                self._log_failure(document_id, error_msg)
                return self._create_failure_result(error_msg)

            # Get parsed content
            # Note: In a real implementation, we would store parsed content
            # For now, we'll read from the file again (this should be optimized)
            parsed_content = self._get_parsed_content(document)

            if not parsed_content:
                error_msg = f"No content found for document '{document_id}'"
                self._log_failure(document_id, error_msg)
                return self._create_failure_result(error_msg)

            # Initialize text splitter
            config = ChunkingConfig(
                chunk_size=self._chunk_size,
                chunk_overlap=self._chunk_overlap,
            )
            splitter = TextSplitter(config)

            # Split content into chunks
            chunk_results = splitter.split(content=parsed_content)

            # Create DocumentChunk records
            chunks_created = self._create_chunks(document, chunk_results)

            duration_ms = self._calculate_duration_ms(start_time)
            self._log_complete(document_id, duration_ms)

            # Prepare output data
            total_chars = sum(c.char_count for c in chunk_results)
            total_tokens = sum(c.token_count for c in chunk_results)

            output_data = {
                "chunk_count": len(chunks_created),
                "total_chars": total_chars,
                "total_tokens": total_tokens,
                "avg_chunk_size": total_chars // len(chunks_created) if chunks_created else 0,
                "chunk_size_config": self._chunk_size,
                "chunk_overlap_config": self._chunk_overlap,
            }

            logger.debug(
                f"[Pipeline] Chunked document {document_id}: "
                f"{output_data['chunk_count']} chunks, {output_data['total_tokens']} tokens"
            )

            return self._create_success_result(output_data, duration_ms)

        except Exception as e:
            error_msg = f"Chunk error: {str(e)}"
            self._log_failure(document_id, error_msg)
            logger.exception(f"[Pipeline] Chunk step failed for document {document_id}")
            return self._create_failure_result(
                error_msg, self._calculate_duration_ms(start_time)
            )

    def _get_parsed_content(self, document: Document) -> str:
        """
        Get parsed content for the document.

        This method reads the document content. In a production system,
        the parsed content should be cached/stored after the parse step.

        Args:
            document: Document model instance.

        Returns:
            Parsed text content.
        """
        # For now, re-parse to get content
        # TODO: Store parsed content after parse step to avoid re-parsing
        from apps.documents_parser.services.parsers.factory import ParserFactory
        from pathlib import Path

        if not ParserFactory.is_supported(file_type=document.file_type):
            return ""

        parser = ParserFactory.get_parser(file_type=document.file_type)
        file_path = Path(document.file_path)

        try:
            parsed_doc = parser.parse(file_path=file_path)
            return parsed_doc.content
        except Exception as e:
            logger.warning(f"Failed to get parsed content: {e}")
            return ""

    def _create_chunks(
        self,
        document: Document,
        chunk_results: list,
    ) -> list[DocumentChunk]:
        """
        Create DocumentChunk records from split results.

        Args:
            document: Document model instance.
            chunk_results: List of ChunkResult from TextSplitter.

        Returns:
            List of created DocumentChunk instances.
        """
        # Delete existing chunks (for re-processing)
        document.chunks.all().delete()

        chunks = []
        with transaction.atomic():
            for chunk_result in chunk_results:
                # Generate content hash
                content_hash = calculate_content_hash(content=chunk_result.content)

                chunk = DocumentChunk(
                    document=document,
                    chunk_index=chunk_result.index,
                    content=chunk_result.content,
                    content_hash=content_hash,
                    char_count=chunk_result.char_count,
                    token_count=chunk_result.token_count,
                    page_number=chunk_result.page_number,
                )
                chunk.save()
                chunks.append(chunk)

        logger.debug(f"Created {len(chunks)} chunks for document {document.id}")
        return chunks
