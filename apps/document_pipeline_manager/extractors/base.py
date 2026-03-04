"""
Base Entity Extractor Interface.

This module defines the abstract base class for entity extractors,
providing a common interface for all extraction implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.document_pipeline_manager.dto import ExtractionResult


class BaseEntityExtractor(ABC):
    """
    Abstract base class for entity extractors.

    Defines the interface for extracting entities from text content.
    Implementations can use different extraction strategies (LLM, NER, etc.).
    """

    @abstractmethod
    def extract(self, text: str) -> ExtractionResult:
        """
        Extract entities from a single text.

        Args:
            text: The text content to extract entities from.

        Returns:
            ExtractionResult containing extracted entities and relationships.
        """
        ...

    @abstractmethod
    def extract_from_chunks(self, chunks: list[dict]) -> ExtractionResult:
        """
        Extract entities from multiple text chunks.

        Args:
            chunks: List of chunk dictionaries, each containing at least:
                - text: The chunk text content
                - id: The chunk identifier

        Returns:
            ExtractionResult containing deduplicated entities and relationships.
        """
        ...

    def get_supported_entity_types(self) -> list[str]:
        """
        Get the list of entity types this extractor can identify.

        Returns:
            List of supported entity type names.
        """
        return ["person", "organization", "location", "date", "concept", "event", "product"]

    def get_confidence_threshold(self) -> float:
        """
        Get the minimum confidence threshold for entities.

        Returns:
            Confidence threshold value (0.0 to 1.0).
        """
        return 0.7
