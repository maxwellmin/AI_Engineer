"""
Entity Extraction Service.

This module provides a service layer for entity extraction and
knowledge graph integration, coordinating extractors and Neo4j storage.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

from apps.document_pipeline_manager.dto import ExtractionResult
from apps.document_pipeline_manager.extractors import MockEntityExtractor
from apps.neo4j_database_controller.services import Neo4jService

if TYPE_CHECKING:
    from apps.document_pipeline_manager.dto import ExtractedEntity
    from apps.document_pipeline_manager.extractors.base import BaseEntityExtractor

logger = logging.getLogger(__name__)


class EntityService:
    """
    Service for entity extraction and knowledge graph integration.

    Coordinates entity extraction from text and storage in Neo4j.
    Provides a unified interface for the pipeline to use.
    """

    def __init__(
        self,
        extractor: BaseEntityExtractor | None = None,
        neo4j_service: Neo4jService | None = None,
    ) -> None:
        """
        Initialize the entity service.

        Args:
            extractor: Entity extractor to use. Defaults to MockEntityExtractor.
            neo4j_service: Neo4j service for graph operations.
        """
        self._extractor = extractor or MockEntityExtractor()
        self._neo4j_service = neo4j_service

    @property
    def neo4j_service(self) -> Neo4jService:
        """Get or create Neo4j service instance."""
        if self._neo4j_service is None:
            self._neo4j_service = Neo4jService()
        return self._neo4j_service

    def extract_entities(self, text: str) -> ExtractionResult:
        """
        Extract entities from text.

        Args:
            text: Text content to extract entities from.

        Returns:
            ExtractionResult with extracted entities.
        """
        return self._extractor.extract(text)

    def extract_entities_from_chunks(
        self,
        chunks: list[dict],
    ) -> ExtractionResult:
        """
        Extract entities from multiple chunks.

        Args:
            chunks: List of chunk dictionaries with 'text' and 'id' keys.

        Returns:
            ExtractionResult with deduplicated entities.
        """
        return self._extractor.extract_from_chunks(chunks)

    def store_entity(
        self,
        entity: ExtractedEntity,
        merge: bool = True,
    ) -> dict[str, Any]:
        """
        Store an entity in Neo4j.

        Args:
            entity: ExtractedEntity to store.
            merge: If True, merge with existing entity (upsert).

        Returns:
            Dict with entity_id and success status.
        """
        # Generate entity ID based on name to enable deduplication
        entity_id = self._generate_entity_id(entity.name, entity.entity_type)

        try:
            result = self.neo4j_service.create_entity(
                entity_id=entity_id,
                name=entity.name,
                entity_type=entity.entity_type,
                description=entity.description,
                confidence=entity.confidence,
            )

            logger.debug(
                f"Stored entity '{entity.name}' (type: {entity.entity_type}) "
                f"in Neo4j with ID: {result.node_id}"
            )

            return {
                "entity_id": entity_id,
                "neo4j_id": result.node_id,
                "success": True,
            }

        except Exception as e:
            logger.exception(f"Failed to store entity '{entity.name}' in Neo4j")
            return {
                "entity_id": entity_id,
                "error": str(e),
                "success": False,
            }

    def store_entities(
        self,
        entities: list[ExtractedEntity],
    ) -> list[dict[str, Any]]:
        """
        Store multiple entities in Neo4j.

        Args:
            entities: List of ExtractedEntity objects to store.

        Returns:
            List of storage results.
        """
        results = []
        for entity in entities:
            result = self.store_entity(entity)
            results.append(result)
        return results

    def link_chunk_to_entity(
        self,
        chunk_id: str,
        entity: ExtractedEntity,
    ) -> dict[str, Any]:
        """
        Create a MENTIONS relationship from chunk to entity.

        Args:
            chunk_id: ID of the chunk mentioning the entity.
            entity: The mentioned entity.

        Returns:
            Dict with relationship creation result.
        """
        entity_id = self._generate_entity_id(entity.name, entity.entity_type)

        try:
            result = self.neo4j_service.link_chunk_to_entity(
                chunk_id=chunk_id,
                entity_id=entity_id,
                confidence=entity.confidence,
            )

            logger.debug(
                f"Created MENTIONS relationship: Chunk[{chunk_id}] -> Entity[{entity.name}]"
            )

            return {
                "chunk_id": chunk_id,
                "entity_id": entity_id,
                "success": True,
            }

        except Exception as e:
            logger.exception(
                f"Failed to link chunk {chunk_id} to entity {entity.name}"
            )
            return {
                "chunk_id": chunk_id,
                "entity_id": entity_id,
                "error": str(e),
                "success": False,
            }

    def process_extraction_result(
        self,
        extraction_result: ExtractionResult,
        chunk_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Process extraction result and store in Neo4j.

        Stores entities and creates MENTIONS relationships.

        Args:
            extraction_result: ExtractionResult from entity extraction.
            chunk_ids: Optional list of chunk IDs that mention these entities.

        Returns:
            Dict with processing summary.
        """
        # Store entities
        entity_results = self.store_entities(extraction_result.entities)

        # Create MENTIONS relationships if chunk IDs provided
        mention_results = []
        if chunk_ids:
            for entity in extraction_result.entities:
                for chunk_id in chunk_ids:
                    if chunk_id in entity.mentions or not entity.mentions:
                        result = self.link_chunk_to_entity(chunk_id, entity)
                        mention_results.append(result)

        successful_entities = sum(1 for r in entity_results if r.get("success"))
        successful_mentions = sum(1 for r in mention_results if r.get("success"))

        return {
            "entities_stored": successful_entities,
            "entities_failed": len(entity_results) - successful_entities,
            "mentions_created": successful_mentions,
            "mentions_failed": len(mention_results) - successful_mentions,
            "total_entities": len(extraction_result.entities),
        }

    def extract_and_store(
        self,
        text: str,
        chunk_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Extract entities from text and store in Neo4j.

        Convenience method that combines extraction and storage.

        Args:
            text: Text content to process.
            chunk_id: Optional chunk ID for MENTIONS relationship.

        Returns:
            Dict with extraction and storage results.
        """
        # Extract entities
        extraction_result = self.extract_entities(text)

        # Store and link
        chunk_ids = [chunk_id] if chunk_id else None
        storage_result = self.process_extraction_result(
            extraction_result,
            chunk_ids=chunk_ids,
        )

        return {
            "extraction": {
                "entity_count": len(extraction_result.entities),
                "total_mentions": extraction_result.total_mentions,
            },
            "storage": storage_result,
        }

    def extract_and_store_from_chunks(
        self,
        chunks: list[dict],
    ) -> dict[str, Any]:
        """
        Extract entities from chunks and store in Neo4j.

        Args:
            chunks: List of chunk dictionaries with 'text' and 'id' keys.

        Returns:
            Dict with extraction and storage results.
        """
        # Extract entities from all chunks
        extraction_result = self.extract_entities_from_chunks(chunks)

        # Get chunk IDs
        chunk_ids = [str(chunk.get("id", "")) for chunk in chunks if chunk.get("id")]

        # Store and link
        storage_result = self.process_extraction_result(
            extraction_result,
            chunk_ids=chunk_ids,
        )

        return {
            "extraction": {
                "entity_count": len(extraction_result.entities),
                "total_mentions": extraction_result.total_mentions,
            },
            "storage": storage_result,
        }

    def _generate_entity_id(self, name: str, entity_type: str) -> str:
        """
        Generate a deterministic entity ID based on name and type.

        This ensures that the same entity extracted from different texts
        will have the same ID, enabling proper deduplication.

        Args:
            name: Entity name.
            entity_type: Entity type.

        Returns:
            Deterministic entity ID.
        """
        # Create a unique key from name and type
        unique_key = f"{entity_type}:{name}".lower()

        # Generate UUID from the key (deterministic)
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_key))
