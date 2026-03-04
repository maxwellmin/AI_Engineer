"""
Mock Entity Extractor Implementation.

This module provides a deterministic mock entity extractor for development
and testing purposes. It generates consistent fake entities based on text hash.
"""

from __future__ import annotations

import hashlib
import logging

from typing import TYPE_CHECKING

from apps.document_pipeline_manager.constants import EntityType
from apps.document_pipeline_manager.dto import ExtractedEntity, ExtractionResult
from apps.document_pipeline_manager.extractors.base import BaseEntityExtractor

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class MockEntityExtractor(BaseEntityExtractor):
    """
    Mock entity extractor for development and testing.

    Generates deterministic fake entities based on text content hash.
    This allows for consistent testing without requiring actual NER models.
    """

    def __init__(
        self,
        min_entities: int = 1,
        max_entities: int = 3,
        base_confidence: float = 0.85,
    ) -> None:
        """
        Initialize the mock extractor.

        Args:
            min_entities: Minimum number of entities to generate per text.
            max_entities: Maximum number of entities to generate per text.
            base_confidence: Base confidence score for generated entities.
        """
        self.min_entities = min_entities
        self.max_entities = max_entities
        self.base_confidence = base_confidence

    def extract(self, text: str) -> ExtractionResult:
        """
        Generate mock entities from text.

        Uses a hash of the text to deterministically generate entities,
        ensuring consistent results for the same input.

        Args:
            text: The text content to "extract" entities from.

        Returns:
            ExtractionResult with mock entities.
        """
        if not text or not text.strip():
            return ExtractionResult(
                entities=[],
                relationships=[],
                total_mentions=0,
            )

        # Generate hash for deterministic results
        text_hash = hashlib.sha256(text.encode()).hexdigest()

        # Determine number of entities based on text length and hash
        entity_count = self._calculate_entity_count(text, text_hash)

        # Generate entities
        entities = []
        entity_types = list(EntityType)

        for i in range(entity_count):
            entity_hash = hashlib.sha256(f"{text_hash}_{i}".encode()).hexdigest()

            # Select entity type based on index
            entity_type = entity_types[i % len(entity_types)]

            # Generate entity name from hash
            entity_name = self._generate_entity_name(entity_type, entity_hash)

            # Calculate confidence with some variation
            confidence = self._calculate_confidence(entity_hash)

            entities.append(
                ExtractedEntity(
                    name=entity_name,
                    entity_type=entity_type.value,
                    description=f"Mock {entity_type.value} entity extracted from text",
                    confidence=confidence,
                    mentions=[],
                )
            )

        logger.debug(f"MockEntityExtractor: Generated {len(entities)} entities")

        return ExtractionResult(
            entities=entities,
            relationships=[],  # No relationships in mock
            total_mentions=len(entities),
        )

    def extract_from_chunks(self, chunks: list[dict]) -> ExtractionResult:
        """
        Extract entities from multiple text chunks.

        Extracts entities from each chunk and deduplicates by name.

        Args:
            chunks: List of chunk dictionaries with 'text' and optionally 'id' keys.

        Returns:
            ExtractionResult with deduplicated entities.
        """
        if not chunks:
            return ExtractionResult(
                entities=[],
                relationships=[],
                total_mentions=0,
            )

        all_entities: dict[str, ExtractedEntity] = {}
        total_mentions = 0

        for chunk in chunks:
            text = chunk.get("text", "")
            chunk_id = str(chunk.get("id", ""))

            if not text:
                continue

            result = self.extract(text)

            for entity in result.entities:
                # Add chunk ID to mentions
                mentions = list(entity.mentions)
                if chunk_id and chunk_id not in mentions:
                    mentions.append(chunk_id)

                # Create updated entity with mention
                updated_entity = ExtractedEntity(
                    name=entity.name,
                    entity_type=entity.entity_type,
                    description=entity.description,
                    confidence=entity.confidence,
                    mentions=mentions,
                )

                # Deduplicate by name, keeping highest confidence
                if entity.name not in all_entities:
                    all_entities[entity.name] = updated_entity
                elif entity.confidence > all_entities[entity.name].confidence:
                    # Merge mentions
                    existing_mentions = list(all_entities[entity.name].mentions)
                    merged_mentions = list(set(existing_mentions + mentions))
                    all_entities[entity.name] = ExtractedEntity(
                        name=entity.name,
                        entity_type=entity.entity_type,
                        description=entity.description,
                        confidence=entity.confidence,
                        mentions=merged_mentions,
                    )

            total_mentions += len(result.entities)

        logger.debug(
            f"MockEntityExtractor: Generated {len(all_entities)} unique entities "
            f"from {len(chunks)} chunks"
        )

        return ExtractionResult(
            entities=list(all_entities.values()),
            relationships=[],  # No relationships in mock
            total_mentions=total_mentions,
        )

    def _calculate_entity_count(self, text: str, text_hash: str) -> int:
        """
        Calculate the number of entities to generate based on text properties.

        Args:
            text: The input text.
            text_hash: Hash of the text for deterministic calculation.

        Returns:
            Number of entities to generate.
        """
        # Base count on hash
        hash_value = int(text_hash[0], 16)

        # Scale based on text length
        text_length = len(text)
        if text_length < 100:
            count = hash_value % 2 + 1  # 1-2 entities for short text
        elif text_length < 500:
            count = hash_value % 3 + 1  # 1-3 entities for medium text
        else:
            count = hash_value % 4 + 2  # 2-5 entities for long text

        return min(max(count, self.min_entities), self.max_entities)

    def _generate_entity_name(self, entity_type: EntityType, entity_hash: str) -> str:
        """
        Generate a mock entity name based on type and hash.

        Args:
            entity_type: The type of entity.
            entity_hash: Hash for generating the name.

        Returns:
            A mock entity name.
        """
        # Use hash to generate a unique suffix
        suffix = entity_hash[:8].upper()

        # Prefix based on entity type
        prefixes = {
            EntityType.PERSON: "Person",
            EntityType.ORGANIZATION: "Org",
            EntityType.LOCATION: "Location",
            EntityType.DATE: "Date",
            EntityType.CONCEPT: "Concept",
            EntityType.EVENT: "Event",
            EntityType.PRODUCT: "Product",
            EntityType.UNKNOWN: "Entity",
        }

        prefix = prefixes.get(entity_type, "Entity")

        return f"{prefix}_{suffix}"

    def _calculate_confidence(self, entity_hash: str) -> float:
        """
        Calculate a confidence score with variation.

        Args:
            entity_hash: Hash for generating variation.

        Returns:
            Confidence score between base_confidence and 1.0.
        """
        # Use hash to add variation to confidence
        variation = int(entity_hash[0], 16) % 15 / 100  # 0.00 to 0.14
        confidence = self.base_confidence + variation

        return min(confidence, 1.0)

    def get_supported_entity_types(self) -> list[str]:
        """
        Get the list of entity types this extractor can identify.

        Returns:
            List of supported entity type names.
        """
        return [e.value for e in EntityType]
