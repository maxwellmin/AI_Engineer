"""
Graph Step Runner for Document Pipeline.

This module implements the graph step that creates Document and Chunk
nodes in Neo4j knowledge graph.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.document_pipeline_manager.constants import PipelineStepName, PipelineStepOrder
from apps.document_pipeline_manager.dto import StepResult
from apps.document_pipeline_manager.exceptions import GraphError
from apps.document_pipeline_manager.runners.base import BaseStepRunner
from apps.documents_parser.models import Document, DocumentChunk
from apps.neo4j_database_controller.constants import NodeLabel, RelType
from apps.neo4j_database_controller.services import Neo4jService

logger = logging.getLogger(__name__)


class GraphStepRunner(BaseStepRunner):
    """
    Graph step runner that creates knowledge graph nodes.

    This step:
    1. Creates a Document node in Neo4j
    2. Creates Chunk nodes for each document chunk
    3. Creates CONTAINS relationships between Document and Chunks
    """

    step_name = PipelineStepName.GRAPH.value
    step_order = PipelineStepOrder.GRAPH

    def __init__(
        self,
        batch_size: int = 100,
    ) -> None:
        """
        Initialize the graph step runner.

        Args:
            batch_size: Number of chunks to create per batch.
        """
        self._batch_size = batch_size
        self._neo4j_service: Neo4jService | None = None

    @property
    def neo4j_service(self) -> Neo4jService:
        """Get or create Neo4jService instance."""
        if self._neo4j_service is None:
            self._neo4j_service = Neo4jService()
        return self._neo4j_service

    def execute(self, document_id: str, **kwargs) -> StepResult:
        """
        Execute the graph step.

        Args:
            document_id: UUID of the document to add to graph.

        Returns:
            StepResult with graph creation outcome and statistics.
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

            # Create document node
            doc_result = self._create_document_node(document)

            if not doc_result.get("success"):
                error_msg = f"Failed to create document node: {doc_result.get('error')}"
                self._log_failure(document_id, error_msg)
                return self._create_failure_result(error_msg)

            # Create chunk nodes
            chunk_results = self._create_chunk_nodes(chunks)

            # Create CONTAINS relationships
            relationship_results = self._create_contains_relationships(
                document_id, chunks
            )

            duration_ms = self._calculate_duration_ms(start_time)
            self._log_complete(document_id, duration_ms)

            # Prepare output data
            successful_chunks = sum(1 for r in chunk_results if r.get("success"))
            successful_relationships = sum(
                1 for r in relationship_results if r.get("success")
            )

            output_data = {
                "document_created": doc_result.get("success", False),
                "chunk_count": len(chunks),
                "chunks_created": successful_chunks,
                "relationships_created": successful_relationships,
            }

            logger.debug(
                f"[Pipeline] Created graph for document {document_id}: "
                f"{output_data['chunks_created']} chunks, "
                f"{output_data['relationships_created']} relationships"
            )

            return self._create_success_result(output_data, duration_ms)

        except Exception as e:
            error_msg = f"Graph error: {str(e)}"
            self._log_failure(document_id, error_msg)
            logger.exception(f"[Pipeline] Graph step failed for document {document_id}")
            return self._create_failure_result(
                error_msg, self._calculate_duration_ms(start_time)
            )

    def _create_document_node(self, document: Document) -> dict[str, Any]:
        """
        Create a Document node in Neo4j.

        Args:
            document: Document model instance.

        Returns:
            Dictionary with creation result.
        """
        try:
            result = self.neo4j_service.create_document(
                document_id=str(document.id),
                title=document.title or document.original_name,
                source=document.file_path,
                doc_type=document.file_type,
                status=document.status,
                extra_properties={
                    "original_name": document.original_name,
                    "file_size": document.file_size,
                    "file_hash": document.file_hash,
                },
            )

            logger.debug(f"Created document node: {document.id}")
            return {"success": True, "node_id": result.node.id}

        except Exception as e:
            logger.error(f"Failed to create document node: {e}")
            return {"success": False, "error": str(e)}

    def _create_chunk_nodes(
        self,
        chunks: list[DocumentChunk],
    ) -> list[dict[str, Any]]:
        """
        Create Chunk nodes in Neo4j.

        Args:
            chunks: List of DocumentChunk instances.

        Returns:
            List of creation results.
        """
        results = []

        for chunk in chunks:
            try:
                result = self.neo4j_service.create_chunk(
                    chunk_id=str(chunk.id),
                    document_id=str(chunk.document_id),
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    char_count=chunk.char_count,
                    token_count=chunk.token_count,
                    page_number=chunk.page_number,
                    content_hash=chunk.content_hash,
                )

                results.append({"success": True, "chunk_id": str(chunk.id)})

            except Exception as e:
                logger.error(f"Failed to create chunk node {chunk.id}: {e}")
                results.append({"success": False, "chunk_id": str(chunk.id), "error": str(e)})

        logger.debug(f"Created {sum(1 for r in results if r.get('success'))} chunk nodes")
        return results

    def _create_contains_relationships(
        self,
        document_id: str,
        chunks: list[DocumentChunk],
    ) -> list[dict[str, Any]]:
        """
        Create CONTAINS relationships between Document and Chunks.

        Args:
            document_id: UUID of the document.
            chunks: List of DocumentChunk instances.

        Returns:
            List of relationship creation results.
        """
        results = []

        for chunk in chunks:
            try:
                result = self.neo4j_service.link_document_to_chunk(
                    document_id=document_id,
                    chunk_id=str(chunk.id),
                )

                results.append({"success": True, "chunk_id": str(chunk.id)})

            except Exception as e:
                logger.error(f"Failed to create relationship for chunk {chunk.id}: {e}")
                results.append({"success": False, "chunk_id": str(chunk.id), "error": str(e)})

        logger.debug(
            f"Created {sum(1 for r in results if r.get('success'))} CONTAINS relationships"
        )
        return results
