"""
Tests for NodeManager.

Unit and integration tests for node CRUD operations.
"""

import pytest

from apps.neo4j_database_controller.constants import NodeLabel
from apps.neo4j_database_controller.exceptions import (
    InvalidNodeLabelError,
    NodeNotFoundError,
)


@pytest.mark.integration
class TestNodeManagerCreate:
    """Tests for NodeManager create operations."""

    def test_create_document_node(
        self, node_manager, clean_database, sample_document
    ):
        """Test creating a Document node."""
        result = node_manager.create_node(
            NodeLabel.DOCUMENT.value, sample_document
        )

        assert result.created is True
        assert result.node.id == sample_document["id"]
        assert result.node.label == NodeLabel.DOCUMENT.value
        assert result.node.properties["title"] == sample_document["title"]
        assert "created_at" in result.node.properties

    def test_create_chunk_node(self, node_manager, clean_database, sample_chunk):
        """Test creating a Chunk node."""
        result = node_manager.create_node(NodeLabel.CHUNK.value, sample_chunk)

        assert result.created is True
        assert result.node.id == sample_chunk["id"]
        assert result.node.properties["text"] == sample_chunk["text"]

    def test_create_entity_node(self, node_manager, clean_database, sample_entity):
        """Test creating an Entity node."""
        result = node_manager.create_node(NodeLabel.ENTITY.value, sample_entity)

        assert result.created is True
        assert result.node.id == sample_entity["id"]
        assert result.node.properties["name"] == sample_entity["name"]

    def test_create_concept_node(
        self, node_manager, clean_database, sample_concept
    ):
        """Test creating a Concept node."""
        result = node_manager.create_node(NodeLabel.CONCEPT.value, sample_concept)

        assert result.created is True
        assert result.node.id == sample_concept["id"]
        assert result.node.properties["name"] == sample_concept["name"]

    def test_create_user_node(self, node_manager, clean_database, sample_user):
        """Test creating a User node."""
        result = node_manager.create_node(NodeLabel.USER.value, sample_user)

        assert result.created is True
        assert result.node.id == sample_user["id"]
        assert result.node.properties["username"] == sample_user["username"]

    def test_create_node_with_merge(
        self, node_manager, clean_database, sample_document
    ):
        """Test creating a node with merge option (upsert)."""
        # First create
        result1 = node_manager.create_node(
            NodeLabel.DOCUMENT.value, sample_document
        )
        assert result1.created is True

        # Merge (should update existing)
        updated_props = sample_document.copy()
        updated_props["title"] = "Updated Title"

        result2 = node_manager.create_node(
            NodeLabel.DOCUMENT.value, updated_props, merge=True
        )

        assert result2.created is True

        # Verify title was updated
        node = node_manager.get_node_by_label_and_id(
            NodeLabel.DOCUMENT.value, sample_document["id"]
        )
        assert node.properties["title"] == "Updated Title"

    def test_create_node_invalid_label(self, node_manager, clean_database):
        """Test creating a node with an invalid label."""
        with pytest.raises(InvalidNodeLabelError):
            node_manager.create_node("InvalidLabel", {"id": "test-1"})

    def test_create_nodes_batch(self, node_manager, clean_database):
        """Test batch creating nodes."""
        nodes = [
            {"id": f"test-entity-{i}", "name": f"Entity {i}", "entity_type": "test"}
            for i in range(5)
        ]

        result = node_manager.create_nodes_batch(NodeLabel.ENTITY.value, nodes)

        assert result.created_count == 5
        assert result.failed_count == 0
        assert len(result.nodes) == 5

    def test_create_document_node_convenience(
        self, node_manager, clean_database, test_document_id
    ):
        """Test the create_document_node convenience method."""
        result = node_manager.create_document_node(
            id=test_document_id,
            title="Test Doc",
            source="test.pdf",
        )

        assert result.created is True
        assert result.node.id == test_document_id

    def test_create_entity_node_convenience(
        self, node_manager, clean_database, test_entity_id
    ):
        """Test the create_entity_node convenience method."""
        result = node_manager.create_entity_node(
            id=test_entity_id,
            name="Python",
            entity_type="technology",
        )

        assert result.created is True
        assert result.node.properties["name"] == "Python"


@pytest.mark.integration
class TestNodeManagerRead:
    """Tests for NodeManager read operations."""

    def test_get_node_by_id(self, node_manager, clean_database, sample_document):
        """Test getting a node by ID."""
        node_manager.create_node(NodeLabel.DOCUMENT.value, sample_document)

        node = node_manager.get_node_by_label_and_id(
            NodeLabel.DOCUMENT.value, sample_document["id"]
        )

        assert node is not None
        assert node.id == sample_document["id"]
        assert node.properties["title"] == sample_document["title"]

    def test_get_node_by_id_not_found(self, node_manager, clean_database):
        """Test getting a node that doesn't exist."""
        node = node_manager.get_node_by_label_and_id(
            NodeLabel.DOCUMENT.value, "nonexistent-id"
        )

        assert node is None

    def test_get_node_by_id_or_raise(self, node_manager, clean_database, sample_document):
        """Test getting a node by ID or raising an error."""
        node_manager.create_node(NodeLabel.DOCUMENT.value, sample_document)

        node = node_manager.get_node_by_label_and_id_or_raise(
            NodeLabel.DOCUMENT.value, sample_document["id"]
        )

        assert node.id == sample_document["id"]

    def test_get_node_by_id_or_raise_not_found(self, node_manager, clean_database):
        """Test that get_node_by_id_or_raise raises for nonexistent node."""
        with pytest.raises(NodeNotFoundError):
            node_manager.get_node_by_label_and_id_or_raise(
                NodeLabel.DOCUMENT.value, "nonexistent-id"
            )

    def test_get_nodes_by_label(self, node_manager, clean_database):
        """Test getting nodes by label."""
        # Create multiple entities
        for i in range(3):
            node_manager.create_node(
                NodeLabel.ENTITY.value,
                {"id": f"test-entity-{i}", "name": f"Entity {i}", "entity_type": "test"},
            )

        nodes = node_manager.get_nodes_by_label(NodeLabel.ENTITY.value)

        assert len(nodes) >= 3

    def test_get_nodes_by_label_with_filters(self, node_manager, clean_database):
        """Test getting nodes by label with filters."""
        # Create entities with different types
        node_manager.create_node(
            NodeLabel.ENTITY.value,
            {"id": "test-entity-person", "name": "John", "entity_type": "person"},
        )
        node_manager.create_node(
            NodeLabel.ENTITY.value,
            {"id": "test-entity-tech", "name": "Python", "entity_type": "technology"},
        )

        nodes = node_manager.get_nodes_by_label(
            NodeLabel.ENTITY.value,
            filters={"entity_type": "person"},
        )

        assert len(nodes) >= 1
        assert all(n.properties.get("entity_type") == "person" for n in nodes)

    def test_count_nodes(self, node_manager, clean_database):
        """Test counting nodes."""
        # Create some entities
        for i in range(3):
            node_manager.create_node(
                NodeLabel.ENTITY.value,
                {"id": f"test-count-entity-{i}", "name": f"Entity {i}"},
            )

        count = node_manager.count_nodes(NodeLabel.ENTITY.value)

        assert count >= 3

    def test_node_exists(self, node_manager, clean_database, sample_document):
        """Test checking if a node exists."""
        node_manager.create_node(NodeLabel.DOCUMENT.value, sample_document)

        exists = node_manager.node_exists(
            sample_document["id"], NodeLabel.DOCUMENT.value
        )

        assert exists is True

    def test_node_not_exists(self, node_manager, clean_database):
        """Test checking if a nonexistent node exists."""
        exists = node_manager.node_exists("nonexistent-id", NodeLabel.DOCUMENT.value)

        assert exists is False


@pytest.mark.integration
class TestNodeManagerUpdate:
    """Tests for NodeManager update operations."""

    def test_update_node(self, node_manager, clean_database, sample_document):
        """Test updating a node."""
        node_manager.create_node(NodeLabel.DOCUMENT.value, sample_document)

        updated = node_manager.update_node(
            sample_document["id"],
            NodeLabel.DOCUMENT.value,
            {"title": "Updated Title", "status": "archived"},
        )

        assert updated.properties["title"] == "Updated Title"
        assert updated.properties["status"] == "archived"
        assert "updated_at" in updated.properties

    def test_update_node_not_found(self, node_manager, clean_database):
        """Test updating a nonexistent node."""
        with pytest.raises(NodeNotFoundError):
            node_manager.update_node(
                "nonexistent-id",
                NodeLabel.DOCUMENT.value,
                {"title": "New Title"},
            )

    def test_update_node_replace_mode(
        self, node_manager, clean_database, sample_document
    ):
        """Test updating a node in replace mode."""
        node_manager.create_node(NodeLabel.DOCUMENT.value, sample_document)

        # Replace all properties except id
        updated = node_manager.update_node(
            sample_document["id"],
            NodeLabel.DOCUMENT.value,
            {"title": "New Title", "new_prop": "value"},
            merge=False,
        )

        assert updated.properties["title"] == "New Title"
        assert updated.properties["new_prop"] == "value"
        # Original source should be gone
        assert "source" not in updated.properties or updated.properties.get("source") is None


@pytest.mark.integration
class TestNodeManagerDelete:
    """Tests for NodeManager delete operations."""

    def test_delete_node(self, node_manager, clean_database, sample_document):
        """Test deleting a node."""
        node_manager.create_node(NodeLabel.DOCUMENT.value, sample_document)

        result = node_manager.delete_node(
            sample_document["id"], NodeLabel.DOCUMENT.value
        )

        assert result.deleted is True
        assert result.deleted_count == 1

        # Verify node is gone
        exists = node_manager.node_exists(
            sample_document["id"], NodeLabel.DOCUMENT.value
        )
        assert exists is False

    def test_delete_node_not_found(self, node_manager, clean_database):
        """Test deleting a nonexistent node."""
        with pytest.raises(NodeNotFoundError):
            node_manager.delete_node("nonexistent-id", NodeLabel.DOCUMENT.value)

    def test_delete_nodes_by_filter(self, node_manager, clean_database):
        """Test deleting nodes by filter."""
        # Create multiple entities
        for i in range(3):
            node_manager.create_node(
                NodeLabel.ENTITY.value,
                {
                    "id": f"test-delete-entity-{i}",
                    "name": f"Entity {i}",
                    "entity_type": "to_delete",
                },
            )

        result = node_manager.delete_nodes_by_filter(
            NodeLabel.ENTITY.value,
            filters={"entity_type": "to_delete"},
        )

        assert result.deleted_count >= 3
