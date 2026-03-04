"""
Vectorize Step Runner for Document Pipeline.

This module implements the vectorize step that stores document chunk
embeddings in Milvus vector database.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction

from apps.document_pipeline_manager.constants import PipelineStepName, PipelineStepOrder
from apps.document_pipeline_manager.dto import StepResult
from apps.document_pipeline_manager.exceptions import VectorizeError
from apps.document_pipeline_manager.runners.base import BaseStepRunner
from apps.document_pipeline_manager.runners.embed_step import (
    clear_cached_embeddings,
    get_cached_embedding,
)
from apps.documents_parser.models import Document, DocumentChunk
from apps.milvus_database_controller.constants import COLLECTION_DOCUMENTS
from apps.milvus_database_controller.dto import VectorRecord
from apps.milvus_database_controller.services import MilvusService

logger = logging.getLogger(__name__)


class VectorizeStepRunner(BaseStepRunner):
    """
    Vectorize step runner that stores embeddings in Milvus.

    This step:
    1. Retrieves chunks with their embeddings
    2. Prepares vector records for Milvus
    3. Inserts vectors into Milvus collection
    4. Updates chunks with Milvus primary keys
    """

    step_name = PipelineStepName.VECTORIZE.value
    step_order = PipelineStepOrder.VECTORIZE

    # Default collection name
    DEFAULT_COLLECTION = COLLECTION_DOCUMENTS

    # Maximum text length for Milvus VARCHAR fields
    MAX_TEXT_LENGTH = 65535

    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION,
        batch_size: int = 100,
    ) -> None:
        """
        Initialize the vectorize step runner.

        Args:
            collection_name: Milvus collection name.
            batch_size: Number of vectors to insert per batch.
        """
        self._collection_name = collection_name
        self._batch_size = batch_size
        self._milvus_service: MilvusService | None = None

    @property
    def milvus_service(self) -> MilvusService:
        """Get or create MilvusService instance."""
        if self._milvus_service is None:
            self._milvus_service = MilvusService()
        return self._milvus_service

    def execute(self, document_id: str, **kwargs) -> StepResult:
        """
        Execute the vectorize step.

        Args:
            document_id: UUID of the document to vectorize.

        Returns:
            StepResult with vectorization outcome and statistics.
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

            # Ensure collection exists
            self._ensure_collection_exists()

            # Prepare vector records
            vector_records = self._prepare_vector_records(document, chunks)

            if not vector_records:
                error_msg = f"No valid embeddings found for document '{document_id}'"
                self._log_failure(document_id, error_msg)
                return self._create_failure_result(error_msg)

            # Insert into Milvus
            insert_result = self.milvus_service.insert_vectors_batch(
                collection_name=self._collection_name,
                data=vector_records,
                batch_size=self._batch_size,
            )

            # Update chunks with Milvus PKs
            updated_count = self._update_chunk_vector_ids(
                chunks, insert_result.inserted_ids
            )

            # Clear cached embeddings
            clear_cached_embeddings([str(chunk.id) for chunk in chunks])

            duration_ms = self._calculate_duration_ms(start_time)
            self._log_complete(document_id, duration_ms)

            # Prepare output data
            output_data = {
                "chunk_count": len(chunks),
                "vectorized_count": insert_result.inserted_count,
                "collection_name": self._collection_name,
                "batch_size": self._batch_size,
            }

            logger.debug(
                f"[Pipeline] Vectorized document {document_id}: "
                f"{output_data['vectorized_count']} vectors in '{self._collection_name}'"
            )

            return self._create_success_result(output_data, duration_ms)

        except Exception as e:
            error_msg = f"Vectorize error: {str(e)}"
            self._log_failure(document_id, error_msg)
            logger.exception(f"[Pipeline] Vectorize step failed for document {document_id}")
            return self._create_failure_result(
                error_msg, self._calculate_duration_ms(start_time)
            )

    def _ensure_collection_exists(self) -> None:
        """
        Ensure the Milvus collection exists.

        Creates the collection if it doesn't exist.
        """
        if not self.milvus_service.has_collection(self._collection_name):
            logger.info(f"Creating Milvus collection: {self._collection_name}")
            self.milvus_service.create_collection(
                collection_name=self._collection_name,
                create_indexes=True,
            )

    def _prepare_vector_records(
        self,
        document: Document,
        chunks: list[DocumentChunk],
    ) -> list[dict[str, Any]]:
        """
        Prepare vector records for Milvus insertion.

        Args:
            document: Document model instance.
            chunks: List of DocumentChunk instances.

        Returns:
            List of dictionaries ready for Milvus insertion.
        """
        records = []

        for chunk in chunks:
            # Get cached embedding
            embedding = get_cached_embedding(str(chunk.id))

            if not embedding:
                logger.warning(f"No embedding found for chunk {chunk.id}")
                continue

            text_dense = embedding.get("text_dense", [])
            summary_dense = embedding.get("summary_dense", [])

            if not text_dense or not summary_dense:
                logger.warning(f"Incomplete embedding for chunk {chunk.id}")
                continue

            # Truncate text if too long
            text = chunk.content[: self.MAX_TEXT_LENGTH] if chunk.content else ""
            summary = text[:200] if text else ""  # Use first 200 chars as summary

            # Create vector record
            record = VectorRecord(
                pk=str(chunk.id),  # Use chunk ID as primary key
                text=text,
                summary=summary,
                document=document.title or document.original_name,
                source="upload",
                source_name=document.original_name,
                lt_doc_id=str(document.id),
                chunk_id=chunk.chunk_index,
                summary_dense=summary_dense,
                text_dense=text_dense,
            )

            records.append(record.to_dict())

        logger.debug(f"Prepared {len(records)} vector records")
        return records

    def _update_chunk_vector_ids(
        self,
        chunks: list[DocumentChunk],
        inserted_ids: list[str],
    ) -> int:
        """
        Update chunks with Milvus primary keys.

        Args:
            chunks: List of DocumentChunk instances.
            inserted_ids: List of inserted primary keys from Milvus.

        Returns:
            Number of chunks updated.
        """
        updated_count = 0

        # Create mapping of chunk ID to Milvus PK
        # The inserted_ids should correspond to the chunks in order
        with transaction.atomic():
            for i, chunk in enumerate(chunks):
                if i < len(inserted_ids):
                    chunk.vector_id = inserted_ids[i]
                    chunk.save(update_fields=["vector_id"])
                    updated_count += 1

        logger.debug(f"Updated {updated_count} chunks with vector IDs")
        return updated_count
