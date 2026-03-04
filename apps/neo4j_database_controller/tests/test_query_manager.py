"""
Tests for QueryManager.

Unit and integration tests for graph query operations.
"""

import pytest

from apps.neo4j_database_controller.constants import NodeLabel, RelType


@pytest.mark.integration
class TestQueryManagerPathFinding:
    """Tests for QueryManager path finding operations."""

    def test_find_shortest_path(
        self,
        node_manager,
        relationship_manager,
        query_manager,
        clean_database,
    ):
        """Test finding the shortest path between two nodes."""
        # Create a chain: Entity1 -> Entity2 -> Entity3
        entity1_id = "test-path-entity-1"
        entity2_id = "test-path-entity-2"
        entity3_id = "test-path-entity-3"

        node_manager.create_node(
            NodeLabel.ENTITY.value,
            {"id": entity1_id, "name": "Entity 1"},
        )
        node_manager.create_node(
            NodeLabel.ENTITY.value,
            {"id": entity2_id, "name": "Entity 2"},
        )
        node_manager.create_node(
            NodeLabel.ENTITY.value,
            {"id": entity3_id, "name": "Entity 3"},
        )

        # Create relationships
        relationship_manager.create_relationship(
            RelType.RELATED_TO.value,
            entity1_id,
            NodeLabel.ENTITY.value,
            entity2_id,
            NodeLabel.ENTITY.value,
        )
        relationship_manager.create_relationship(
            RelType.RELATED_TO.value,
            entity2_id,
            NodeLabel.ENTITY.value,
            entity3_id,
            NodeLabel.ENTITY.value,
        )

        # Find shortest path
        path = query_manager.find_shortest_path(
            from_node_id=entity1_id,
            from_node_label=NodeLabel.ENTITY.value,
            to_node_id=entity3_id,
            to_node_label=NodeLabel.ENTITY.value,
        )

        assert path is not None
        assert path.length == 2  # Two hops

    def test_find_shortest_path_not_found(
        self,
        node_manager,
        query_manager,
        clean_database,
    ):
        """Test finding path when no path exists."""
        entity1_id = "test-nopath-entity-1"
        entity2_id = "test-nopath-entity-2"

        node_manager.create_node(
            NodeLabel.ENTITY.value,
            {"id": entity1_id, "name": "Entity 1"},
        )
        node_manager.create_node(
            NodeLabel.ENTITY.value,
            {"id": entity2_id, "name": "Entity 2"},
        )

        path = query_manager.find_shortest_path(
            from_node_id=entity1_id,
            from_node_label=NodeLabel.ENTITY.value,
            to_node_id=entity2_id,
            to_node_label=NodeLabel.ENTITY.value,
        )

        assert path is None

    def test_find_all_paths(
        self,
        node_manager,
        relationship_manager,
        query_manager,
        clean_database,
    ):
        """Test finding all paths between two nodes."""
        entity1_id = "test-allpaths-entity-1"
        entity2_id = "test-allpaths-entity-2"

        node_manager.create_node(
            NodeLabel.ENTITY.value,
            {"id": entity1_id, "name": "Entity 1"},
        )
        node_manager.create_node(
            NodeLabel.ENTITY.value,
            {"id": entity2_id, "name": "Entity 2"},
        )

        # Create a direct relationship
        relationship_manager.create_relationship(
            RelType.RELATED_TO.value,
            entity1_id,
            NodeLabel.ENTITY.value,
            entity2_id,
            NodeLabel.ENTITY.value,
        )

        paths = query_manager.find_all_paths(
            from_node_id=entity1_id,
            from_node_label=NodeLabel.ENTITY.value,
            to_node_id=entity2_id,
            to_node_label=NodeLabel.ENTITY.value,
            max_depth=3,
        )

        assert len(paths) >= 1


@pytest.mark.integration
class TestQueryManagerNeighbors:
    """Tests for QueryManager neighbor operations."""

    def test_get_node_neighbors(
        self,
        sample_knowledge_graph,
        query_manager,
    ):
        """Test getting neighboring nodes."""
        doc_id = sample_knowledge_graph["document"].id

        neighbors = query_manager.get_node_neighbors(
            node_id=doc_id,
            node_label=NodeLabel.DOCUMENT.value,
            direction="OUTGOING",
        )

        assert len(neighbors) >= 1
        # Should include chunk and concept

    def test_get_node_neighbors_with_relationships(
        self,
        sample_knowledge_graph,
        query_manager,
    ):
        """Test getting neighbors with relationship info."""
        doc_id = sample_knowledge_graph["document"].id

        neighbors_with_rels = query_manager.get_node_neighbors_with_relationships(
            node_id=doc_id,
            node_label=NodeLabel.DOCUMENT.value,
            direction="OUTGOING",
        )

        assert len(neighbors_with_rels) >= 1
        # Each item should be a tuple of (NodeInfo, RelationshipInfo)
        for neighbor, rel in neighbors_with_rels:
            assert neighbor.id is not None
            assert rel.rel_type is not None

    def test_get_node_degree(
        self,
        sample_knowledge_graph,
        query_manager,
    ):
        """Test getting node degree."""
        doc_id = sample_knowledge_graph["document"].id

        degree = query_manager.get_node_degree(
            node_id=doc_id,
            node_label=NodeLabel.DOCUMENT.value,
            direction="OUTGOING",
        )

        assert degree >= 2  # CONTAINS and ABOUT


@pytest.mark.integration
class TestQueryManagerEntityContext:
    """Tests for QueryManager entity context operations."""

    def test_get_entity_context(
        self,
        sample_knowledge_graph,
        query_manager,
    ):
        """Test getting entity context for RAG."""
        entity_id = sample_knowledge_graph["entity"].id

        context = query_manager.get_entity_context(
            entity_id=entity_id,
            include_chunks=True,
            include_related_entities=True,
            include_concepts=True,
        )

        assert context is not None
        assert context.entity.id == entity_id
        # Chunk that mentions this entity
        assert len(context.mentioned_in) >= 1

    def test_get_entity_context_not_found(self, query_manager):
        """Test getting context for nonexistent entity."""
        context = query_manager.get_entity_context(entity_id="nonexistent-entity")

        assert context is None


@pytest.mark.integration
class TestQueryManagerDocumentGraph:
    """Tests for QueryManager document graph operations."""

    def test_get_document_graph(
        self,
        sample_knowledge_graph,
        query_manager,
    ):
        """Test getting document subgraph."""
        doc_id = sample_knowledge_graph["document"].id

        graph = query_manager.get_document_graph(
            document_id=doc_id,
            include_chunks=True,
            include_entities=True,
            include_concepts=True,
        )

        assert graph is not None
        assert graph.document.id == doc_id
        assert len(graph.chunks) >= 1
        assert len(graph.entities) >= 1
        assert len(graph.concepts) >= 1

    def test_get_document_graph_not_found(self, query_manager):
        """Test getting graph for nonexistent document."""
        graph = query_manager.get_document_graph(document_id="nonexistent-doc")

        assert graph is None


@pytest.mark.integration
class TestQueryManagerEntitySearch:
    """Tests for QueryManager entity search operations."""

    def test_find_entities_by_name(
        self,
        node_manager,
        query_manager,
        clean_database,
    ):
        """Test finding entities by name."""
        node_manager.create_node(
            NodeLabel.ENTITY.value,
            {"id": "test-search-python", "name": "Python Programming", "entity_type": "technology"},
        )

        entities = query_manager.find_entities_by_name(name="Python")

        assert len(entities) >= 1
        assert any("Python" in e.properties.get("name", "") for e in entities)

    def test_find_entities_by_name_with_type_filter(
        self,
        node_manager,
        query_manager,
        clean_database,
    ):
        """Test finding entities by name with type filter."""
        node_manager.create_node(
            NodeLabel.ENTITY.value,
            {"id": "test-filter-entity-1", "name": "Python", "entity_type": "technology"},
        )
        node_manager.create_node(
            NodeLabel.ENTITY.value,
            {"id": "test-filter-entity-2", "name": "Python Developer", "entity_type": "person"},
        )

        entities = query_manager.find_entities_by_name(
            name="Python",
            entity_type="technology",
        )

        assert len(entities) >= 1
        assert all(e.properties.get("entity_type") == "technology" for e in entities)

    def test_find_related_entities(
        self,
        node_manager,
        relationship_manager,
        query_manager,
        clean_database,
    ):
        """Test finding entities related to another entity."""
        entity1_id = "test-related-entity-1"
        entity2_id = "test-related-entity-2"

        node_manager.create_node(
            NodeLabel.ENTITY.value,
            {"id": entity1_id, "name": "Python"},
        )
        node_manager.create_node(
            NodeLabel.ENTITY.value,
            {"id": entity2_id, "name": "Django"},
        )

        relationship_manager.create_relationship(
            RelType.RELATED_TO.value,
            entity1_id,
            NodeLabel.ENTITY.value,
            entity2_id,
            NodeLabel.ENTITY.value,
        )

        related = query_manager.find_related_entities(entity_id=entity1_id)

        assert len(related) >= 1
        assert any(e.id == entity2_id for e in related)


@pytest.mark.integration
class TestQueryManagerGraphStats:
    """Tests for QueryManager graph statistics operations."""

    def test_get_graph_stats(
        self,
        sample_knowledge_graph,
        query_manager,
    ):
        """Test getting graph statistics."""
        stats = query_manager.get_graph_stats()

        assert "total_nodes" in stats
        assert "total_relationships" in stats
        assert "node_counts_by_label" in stats
        assert "relationship_counts_by_type" in stats

        # Should have at least our sample data
        assert stats["total_nodes"] >= 4  # doc, chunk, entity, concept
        assert stats["total_relationships"] >= 3  # CONTAINS, MENTIONS, ABOUT
