"""
Extract Step Runner for Document Pipeline.

This module implements the extract step that extracts entities from
document chunks and stores them in Neo4j knowledge graph.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.document_pipeline_manager.constants import PipelineStepName, PipelineStepOrder
from apps.document_pipeline_manager.dto import StepResult
from apps.document_pipeline_manager.exceptions import ExtractionError
from apps.document_pipeline_manager.runners.base import BaseStepRunner
from apps.documents_parser.models import Document, DocumentChunk

# Lazy import to avoid circular dependency
# from apps.document_pipeline_manager.services.entity_service import EntityService

logger = logging.getLogger(__name__)


class ExtractStepRunner(BaseStepRunner):
    """
    Extract step runner that extracts entities from document chunks.

    This step:
    1. Retrieves all chunks for the document
    2. Extracts entities using EntityService (Mock for MVP)
    3. Creates Entity nodes in Neo4j
    4. Creates MENTIONS relationships between Chunks and Entities
    """

    step_name = PipelineStepName.EXTRACT.value
    step_order = PipelineStepOrder.EXTRACT

    def __init__(
        self,
        enable_extraction: bool = True,
    ) -> None:
        """
        Initialize the extract step runner.

        Args:
            enable_extraction: Whether to enable entity extraction.
                               Set to False to skip this step.
        """
        self._enable_extraction = enable_extraction
        self._entity_service: EntityService | None = None

    @property
    def entity_service(self):
        """Get or create EntityService instance (lazy import to avoid circular dependency)."""
        if self._entity_service is None:
            from apps.document_pipeline_manager.services.entity_service import EntityService
            self._entity_service = EntityService()
        return self._entity_service

    def execute(self, document_id: str, **kwargs) -> StepResult:
        """
        Execute the extract step.

        Args:
            document_id: UUID of the document to extract entities from.

        Returns:
            StepResult with extraction outcome and statistics.
        """
        start_time = self._get_start_time()
        self._log_start(document_id)

        # Check if extraction is enabled
        if not self._enable_extraction:
            logger.info(f"[Pipeline] Entity extraction disabled, skipping for {document_id}")
            duration_ms = self._calculate_duration_ms(start_time)
            return self._create_success_result(
                {"skipped": True, "reason": "extraction_disabled"},
                duration_ms,
            )

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
                # No chunks is not an error, just no entities to extract
                duration_ms = self._calculate_duration_ms(start_time)
                self._log_complete(document_id, duration_ms)
                return self._create_success_result(
                    {"entities_extracted": 0, "chunks_processed": 0},
                    duration_ms,
                )

            # Extract and store entities
            extraction_result = self._extract_and_store_entities(document, chunks)

            duration_ms = self._calculate_duration_ms(start_time)
            self._log_complete(document_id, duration_ms)

            # Prepare output data
            output_data = {
                "entities_extracted": extraction_result.get("entities_stored", 0),
                "entities_failed": extraction_result.get("entities_failed", 0),
                "mentions_created": extraction_result.get("mentions_created", 0),
                "chunks_processed": len(chunks),
            }

            logger.debug(
                f"[Pipeline] Extracted entities for document {document_id}: "
                f"{output_data['entities_extracted']} entities, "
                f"{output_data['mentions_created']} mentions"
            )

            return self._create_success_result(output_data, duration_ms)

        except Exception as e:
            error_msg = f"Extraction error: {str(e)}"
            self._log_failure(document_id, error_msg)
            logger.exception(f"[Pipeline] Extract step failed for document {document_id}")
            return self._create_failure_result(
                error_msg, self._calculate_duration_ms(start_time)
            )

    def _extract_and_store_entities(
        self,
        document: Document,
        chunks: list[DocumentChunk],
    ) -> dict[str, Any]:
        """
        Extract entities from chunks and store in Neo4j.

        Args:
            document: Document model instance.
            chunks: List of DocumentChunk instances.

        Returns:
            Dictionary with extraction and storage results.
        """
        # Prepare chunks for extraction
        chunk_data = [
            {
                "id": str(chunk.id),
                "text": chunk.content,
                "chunk_index": chunk.chunk_index,
            }
            for chunk in chunks
        ]

        # Extract entities from all chunks
        try:
            result = self.entity_service.extract_and_store_from_chunks(chunk_data)
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            raise ExtractionError(str(e))

        return result.get("storage", {})

    def _update_document_status(
        self,
        document: Document,
    ) -> None:
        """
        Update document status to DONE after successful extraction.

        Args:
            document: Document model instance.
        """
        document.status = Document.Status.DONE
        document.save(update_fields=["status", "updated_at"])
        logger.debug(f"Updated document {document.id} status to DONE")
