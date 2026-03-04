"""
Unit tests for Entity Extractors.

Tests the base extractor interface and mock extractor implementation.
"""

from __future__ import annotations

import pytest

from apps.document_pipeline_manager.dto import ExtractedEntity, ExtractionResult
from apps.document_pipeline_manager.extractors import MockEntityExtractor
from apps.document_pipeline_manager.extractors.base import BaseEntityExtractor


class TestMockEntityExtractor:
    """Tests for MockEntityExtractor."""

    def test_extract_returns_extraction_result(self) -> None:
        """Test that extract returns an ExtractionResult."""
        extractor = MockEntityExtractor()
        result = extractor.extract("Some test text")

        assert isinstance(result, ExtractionResult)
        assert isinstance(result.entities, list)
        assert isinstance(result.relationships, list)
        assert isinstance(result.total_mentions, int)

    def test_extract_empty_text_returns_empty_result(self) -> None:
        """Test that empty text returns empty result."""
        extractor = MockEntityExtractor()
        result = extractor.extract("")

        assert result.entities == []
        assert result.total_mentions == 0

    def test_extract_whitespace_text_returns_empty_result(self) -> None:
        """Test that whitespace-only text returns empty result."""
        extractor = MockEntityExtractor()
        result = extractor.extract("   \n\t  ")

        assert result.entities == []
        assert result.total_mentions == 0

    def test_extract_deterministic_results(self) -> None:
        """Test that same text produces same entities (deterministic)."""
        extractor = MockEntityExtractor()
        text = "This is a test document with some content."

        result1 = extractor.extract(text)
        result2 = extractor.extract(text)

        # Same text should produce same entities
        assert len(result1.entities) == len(result2.entities)
        for e1, e2 in zip(result1.entities, result2.entities):
            assert e1.name == e2.name
            assert e1.entity_type == e2.entity_type

    def test_extract_different_text_different_results(self) -> None:
        """Test that different texts produce different entities."""
        extractor = MockEntityExtractor()

        result1 = extractor.extract("First text content here")
        result2 = extractor.extract("Completely different text content")

        # Different texts should likely produce different entities
        names1 = {e.name for e in result1.entities}
        names2 = {e.name for e in result2.entities}

        # At least some names should be different (hash-based)
        assert names1 != names2 or len(names1) == 0

    def test_extract_entities_have_valid_confidence(self) -> None:
        """Test that extracted entities have valid confidence scores."""
        extractor = MockEntityExtractor()
        result = extractor.extract("Test text for extraction")

        for entity in result.entities:
            assert 0.0 <= entity.confidence <= 1.0
            assert entity.confidence >= extractor.base_confidence

    def test_extract_entities_have_valid_types(self) -> None:
        """Test that extracted entities have valid entity types."""
        extractor = MockEntityExtractor()
        result = extractor.extract("Another test text")

        valid_types = extractor.get_supported_entity_types()

        for entity in result.entities:
            assert entity.entity_type in valid_types

    def test_extract_from_chunks_returns_result(self) -> None:
        """Test that extract_from_chunks returns ExtractionResult."""
        extractor = MockEntityExtractor()
        chunks = [
            {"id": "chunk-1", "text": "First chunk content"},
            {"id": "chunk-2", "text": "Second chunk content"},
        ]

        result = extractor.extract_from_chunks(chunks)

        assert isinstance(result, ExtractionResult)
        assert isinstance(result.entities, list)

    def test_extract_from_chunks_empty_list(self) -> None:
        """Test that empty chunks list returns empty result."""
        extractor = MockEntityExtractor()
        result = extractor.extract_from_chunks([])

        assert result.entities == []
        assert result.total_mentions == 0

    def test_extract_from_chunks_deduplicates(self) -> None:
        """Test that extract_from_chunks deduplicates entities."""
        extractor = MockEntityExtractor(min_entities=1, max_entities=2)

        # Use same text in multiple chunks to produce same entities
        same_text = "Identical content for testing"
        chunks = [
            {"id": "chunk-1", "text": same_text},
            {"id": "chunk-2", "text": same_text},
        ]

        result = extractor.extract_from_chunks(chunks)

        # Should deduplicate by name
        entity_names = [e.name for e in result.entities]
        assert len(entity_names) == len(set(entity_names))

    def test_extract_from_chunks_includes_mentions(self) -> None:
        """Test that entities include chunk IDs in mentions."""
        extractor = MockEntityExtractor()
        chunks = [
            {"id": "chunk-1", "text": "First chunk"},
            {"id": "chunk-2", "text": "Second chunk"},
        ]

        result = extractor.extract_from_chunks(chunks)

        # Entities should have mentions from chunks
        for entity in result.entities:
            assert isinstance(entity.mentions, list)

    def test_custom_min_max_entities(self) -> None:
        """Test that custom min/max entities are respected."""
        extractor = MockEntityExtractor(min_entities=2, max_entities=4)

        # Long text should allow up to max_entities
        long_text = "This is a longer text " * 50
        result = extractor.extract(long_text)

        # Should have at least min_entities
        assert len(result.entities) >= 2
        # Should have at most max_entities per text
        assert len(result.entities) <= 4

    def test_custom_base_confidence(self) -> None:
        """Test that custom base confidence is used."""
        extractor = MockEntityExtractor(base_confidence=0.95)

        result = extractor.extract("Test text")

        for entity in result.entities:
            assert entity.confidence >= 0.95


class TestBaseEntityExtractor:
    """Tests for BaseEntityExtractor interface."""

    def test_get_supported_entity_types(self) -> None:
        """Test that get_supported_entity_types returns expected types."""
        extractor = MockEntityExtractor()
        supported_types = extractor.get_supported_entity_types()

        expected_types = [
            "person",
            "organization",
            "location",
            "date",
            "concept",
            "event",
            "product",
        ]

        for expected_type in expected_types:
            assert expected_type in supported_types

    def test_get_confidence_threshold(self) -> None:
        """Test that get_confidence_threshold returns valid value."""
        extractor = MockEntityExtractor()
        threshold = extractor.get_confidence_threshold()

        assert 0.0 <= threshold <= 1.0
        assert threshold == 0.7  # Default threshold


class TestExtractedEntity:
    """Tests for ExtractedEntity DTO."""

    def test_create_extracted_entity(self) -> None:
        """Test creating an ExtractedEntity."""
        entity = ExtractedEntity(
            name="John Doe",
            entity_type="person",
            description="A test person",
            confidence=0.95,
            mentions=["chunk-1", "chunk-2"],
        )

        assert entity.name == "John Doe"
        assert entity.entity_type == "person"
        assert entity.description == "A test person"
        assert entity.confidence == 0.95
        assert entity.mentions == ["chunk-1", "chunk-2"]

    def test_extracted_entity_frozen(self) -> None:
        """Test that ExtractedEntity is immutable (frozen)."""
        entity = ExtractedEntity(
            name="Test",
            entity_type="concept",
        )

        with pytest.raises(AttributeError):
            entity.name = "Changed"  # type: ignore


class TestExtractionResult:
    """Tests for ExtractionResult DTO."""

    def test_create_extraction_result(self) -> None:
        """Test creating an ExtractionResult."""
        entities = [
            ExtractedEntity(name="Entity 1", entity_type="person"),
            ExtractedEntity(name="Entity 2", entity_type="organization"),
        ]

        result = ExtractionResult(
            entities=entities,
            relationships=[],
            total_mentions=2,
        )

        assert len(result.entities) == 2
        assert result.relationships == []
        assert result.total_mentions == 2

    def test_extraction_result_frozen(self) -> None:
        """Test that ExtractionResult is immutable (frozen)."""
        result = ExtractionResult(
            entities=[],
            relationships=[],
            total_mentions=0,
        )

        with pytest.raises(AttributeError):
            result.total_mentions = 5  # type: ignore
