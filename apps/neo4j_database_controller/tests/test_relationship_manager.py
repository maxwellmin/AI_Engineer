"""
Tests for RelationshipManager.

Unit and integration tests for relationship CRUD operations.
"""

import pytest

from apps.neo4j_database_controller.constants import NodeLabel, RelType
from apps.neo4j_database_controller.exceptions import (
    InvalidRelationshipTypeError,
    NodeNotFoundError,
    RelationshipNotFoundError,
)


@pytest.mark.integration
class TestRelationshipManagerCreate:
    """Tests for RelationshipManager create operations."""

    def test_create_contains_relationship(
        self,
        node_manager,
        relationship_manager,
        clean_database,
        sample_document,
        sample_chunk,
    ):
        """Test creating a CONTAINS relationship."""
        # Create nodes first
        node_manager.create_node(NodeLabel.DOCUMENT.value, sample_document)
        node_manager.create_node(NodeLabel.CHUNK.value, sample_chunk)

        result = relationship_manager.create_relationship(
            rel_type=RelType.CONTAINS.value,
            from_node_id=sample_document["id"],
            from_node_label=NodeLabel.DOCUMENT.value,
            to_node_id=sample_chunk["id"],
            to_node_label=NodeLabel.CHUNK.value,
            properties={"order": 0},
        )

        assert result.created is True
        assert result.relationship.rel_type == RelType.CONTAINS.value
        assert result.relationship.from_node_id == sample_document["id"]
        assert result.relationship.to_node_id == sample_chunk["id"]

    def test_create_mentions_relationship(
        self,
        node_manager,
        relationship_manager,
        clean_database,
        sample_chunk,
        sample_entity,
    ):
        """Test creating a MENTIONS relationship."""
        node_manager.create_node(NodeLabel.CHUNK.value, sample_chunk)
        node_manager.create_node(NodeLabel.ENTITY.value, sample_entity)

        result = relationship_manager.create_relationship(
            rel_type=RelType.MENTIONS.value,
            from_node_id=sample_chunk["id"],
            from_node_label=NodeLabel.CHUNK.value,
            to_node_id=sample_entity["id"],
            to_node_label=NodeLabel.ENTITY.value,
            properties={"confidence": 0.9, "count": 1},
        )

        assert result.created is True
        assert result.relationship.rel_type == RelType.MENTIONS.value

    def test_create_relationship_invalid_type(
        self,
        node_manager,
        relationship_manager,
        clean_database,
        sample_document,
        sample_chunk,
    ):
        """Test creating a relationship with an invalid type."""
        node_manager.create_node(NodeLabel.DOCUMENT.value, sample_document)
        node_manager.create_node(NodeLabel.CHUNK.value, sample_chunk)

        with pytest.raises(InvalidRelationshipTypeError):
            relationship_manager.create_relationship(
                rel_type="INVALID_TYPE",
                from_node_id=sample_document["id"],
                from_node_label=NodeLabel.DOCUMENT.value,
                to_node_id=sample_chunk["id"],
                to_node_label=NodeLabel.CHUNK.value,
            )

    def test_create_relationship_node_not_found(
        self,
        relationship_manager,
        clean_database,
        sample_document,
        sample_chunk,
    ):
        """Test creating a relationship when a node doesn't exist."""
        with pytest.raises(NodeNotFoundError):
            relationship_manager.create_relationship(
                rel_type=RelType.CONTAINS.value,
                from_node_id=sample_document["id"],
                from_node_label=NodeLabel.DOCUMENT.value,
                to_node_id=sample_chunk["id"],
                to_node_label=NodeLabel.CHUNK.value,
            )

    def test_create_relationships_batch(
        self,
        node_manager,
        relationship_manager,
        clean_database,
        sample_document,
    ):
        """Test batch creating relationships."""
        from apps.neo4j_database_controller.dto import CreateRelationshipRequest

        # Create document and multiple chunks
        node_manager.create_node(NodeLabel.DOCUMENT.value, sample_document)

        relationships = []
        for i in range(3):
            chunk_id = f"{sample_document['id']}-chunk-{i}"
            node_manager.create_node(
                NodeLabel.CHUNK.value,
                {"id": chunk_id, "text": f"Chunk {i}", "document_id": sample_document["id"]},
            )
            relationships.append(
                CreateRelationshipRequest(
                    rel_type=RelType.CONTAINS.value,
                    from_node_id=sample_document["id"],
                    from_node_label=NodeLabel.DOCUMENT.value,
                    to_node_id=chunk_id,
                    to_node_label=NodeLabel.CHUNK.value,
                    properties={"order": i},
                )
            )

        result = relationship_manager.create_relationships_batch(relationships)

        assert result.created_count == 3
        assert result.failed_count == 0

    def test_create_contains_relationship_convenience(
        self,
        node_manager,
        relationship_manager,
        clean_database,
        sample_document,
        sample_chunk,
    ):
        """Test the create_contains_relationship convenience method."""
        node_manager.create_node(NodeLabel.DOCUMENT.value, sample_document)
        node_manager.create_node(NodeLabel.CHUNK.value, sample_chunk)

        result = relationship_manager.create_contains_relationship(
            document_id=sample_document["id"],
            chunk_id=sample_chunk["id"],
            order=0,
        )

        assert result.created is True

    def test_create_mentions_relationship_convenience(
        self,
        node_manager,
        relationship_manager,
        clean_database,
        sample_chunk,
        sample_entity,
    ):
        """Test the create_mentions_relationship convenience method."""
        node_manager.create_node(NodeLabel.CHUNK.value, sample_chunk)
        node_manager.create_node(NodeLabel.ENTITY.value, sample_entity)

        result = relationship_manager.create_mentions_relationship(
            chunk_id=sample_chunk["id"],
            entity_id=sample_entity["id"],
            confidence=0.95,
            count=2,
        )

        assert result.created is True


@pytest.mark.integration
class TestRelationshipManagerRead:
    """Tests for RelationshipManager read operations."""

    def test_get_relationship_by_id(
        self,
        sample_knowledge_graph,
        relationship_manager,
    ):
        """Test getting a relationship by ID."""
        rel_id = sample_knowledge_graph["contains_rel"].id

        rel = relationship_manager.get_relationship_by_id(rel_id)

        assert rel is not None
        assert rel.id == rel_id
        assert rel.rel_type == RelType.CONTAINS.value

    def test_get_relationship_by_id_not_found(self, relationship_manager):
        """Test getting a relationship that doesn't exist."""
        rel = relationship_manager.get_relationship_by_id(999999)

        assert rel is None

    def test_get_relationship_by_id_or_raise(
        self,
        sample_knowledge_graph,
        relationship_manager,
    ):
        """Test getting a relationship by ID or raising an error."""
        rel_id = sample_knowledge_graph["contains_rel"].id

        rel = relationship_manager.get_relationship_by_id_or_raise(rel_id)

        assert rel.id == rel_id

    def test_get_relationship_by_id_or_raise_not_found(
        self, relationship_manager
    ):
        """Test that get_relationship_by_id_or_raise raises for nonexistent."""
        with pytest.raises(RelationshipNotFoundError):
            relationship_manager.get_relationship_by_id_or_raise(999999)

    def test_get_relationships(
        self,
        sample_knowledge_graph,
        relationship_manager,
    ):
        """Test getting relationships for a node."""
        doc_id = sample_knowledge_graph["document"].id

        rels = relationship_manager.get_relationships(
            node_id=doc_id,
            node_label=NodeLabel.DOCUMENT.value,
            direction="OUTGOING",
        )

        assert len(rels) >= 1
        assert any(r.rel_type == RelType.CONTAINS.value for r in rels)

    def test_get_outgoing_relationships(
        self,
        sample_knowledge_graph,
        relationship_manager,
    ):
        """Test getting outgoing relationships."""
        doc_id = sample_knowledge_graph["document"].id

        rels = relationship_manager.get_outgoing_relationships(
            node_id=doc_id,
            node_label=NodeLabel.DOCUMENT.value,
        )

        assert len(rels) >= 1

    def test_get_incoming_relationships(
        self,
        sample_knowledge_graph,
        relationship_manager,
    ):
        """Test getting incoming relationships."""
        chunk_id = sample_knowledge_graph["chunk"].id

        rels = relationship_manager.get_incoming_relationships(
            node_id=chunk_id,
            node_label=NodeLabel.CHUNK.value,
        )

        # Chunk should have CONTAINS incoming from Document
        assert len(rels) >= 1

    def test_count_relationships(
        self,
        sample_knowledge_graph,
        relationship_manager,
    ):
        """Test counting relationships."""
        doc_id = sample_knowledge_graph["document"].id

        count = relationship_manager.count_relationships(
            node_id=doc_id,
            node_label=NodeLabel.DOCUMENT.value,
            direction="OUTGOING",
        )

        assert count >= 2  # CONTAINS and ABOUT

    def test_relationship_exists(
        self,
        sample_knowledge_graph,
        relationship_manager,
    ):
        """Test checking if a relationship exists."""
        doc_id = sample_knowledge_graph["document"].id
        chunk_id = sample_knowledge_graph["chunk"].id

        exists = relationship_manager.relationship_exists(
            rel_type=RelType.CONTAINS.value,
            from_node_id=doc_id,
            to_node_id=chunk_id,
        )

        assert exists is True


@pytest.mark.integration
class TestRelationshipManagerUpdate:
    """Tests for RelationshipManager update operations."""

    def test_update_relationship(
        self,
        sample_knowledge_graph,
        relationship_manager,
    ):
        """Test updating a relationship."""
        rel_id = sample_knowledge_graph["contains_rel"].id

        updated = relationship_manager.update_relationship(
            rel_id=rel_id,
            properties={"order": 99, "updated": True},
        )

        assert updated.properties["order"] == 99
        assert updated.properties["updated"] is True

    def test_update_relationship_not_found(self, relationship_manager):
        """Test updating a nonexistent relationship."""
        with pytest.raises(RelationshipNotFoundError):
            relationship_manager.update_relationship(
                rel_id=999999,
                properties={"test": "value"},
            )


@pytest.mark.integration
class TestRelationshipManagerDelete:
    """Tests for RelationshipManager delete operations."""

    def test_delete_relationship(
        self,
        node_manager,
        relationship_manager,
        clean_database,
        sample_document,
        sample_chunk,
    ):
        """Test deleting a relationship."""
        # Create nodes and relationship
        node_manager.create_node(NodeLabel.DOCUMENT.value, sample_document)
        node_manager.create_node(NodeLabel.CHUNK.value, sample_chunk)
        result = relationship_manager.create_relationship(
            rel_type=RelType.CONTAINS.value,
            from_node_id=sample_document["id"],
            from_node_label=NodeLabel.DOCUMENT.value,
            to_node_id=sample_chunk["id"],
            to_node_label=NodeLabel.CHUNK.value,
        )

        rel_id = result.relationship.id

        # Delete relationship
        delete_result = relationship_manager.delete_relationship(rel_id)

        assert delete_result.deleted is True

        # Verify relationship is gone
        rel = relationship_manager.get_relationship_by_id(rel_id)
        assert rel is None

    def test_delete_relationship_not_found(self, relationship_manager):
        """Test deleting a nonexistent relationship."""
        with pytest.raises(RelationshipNotFoundError):
            relationship_manager.delete_relationship(999999)

    def test_delete_relationships_by_filter(
        self,
        sample_knowledge_graph,
        relationship_manager,
    ):
        """Test deleting relationships by filter."""
        doc_id = sample_knowledge_graph["document"].id

        # Delete all outgoing relationships from document
        result = relationship_manager.delete_relationships_by_filter(
            node_id=doc_id,
            node_label=NodeLabel.DOCUMENT.value,
            direction="OUTGOING",
        )

        assert result.deleted_count >= 2  # CONTAINS and ABOUT
