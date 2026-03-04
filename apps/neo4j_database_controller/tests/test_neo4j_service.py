"""
Tests for Neo4jService.

Integration tests for the high-level Neo4j service.
"""

import pytest

from apps.neo4j_database_controller.constants import NodeLabel, RelType
from apps.neo4j_database_controller.exceptions import NodeNotFoundError


@pytest.mark.integration
class TestNeo4jServiceDocument:
    """Tests for Neo4jService document operations."""

    def test_create_document(self, neo4j_service, clean_database, test_document_id):
        """Test creating a document."""
        result = neo4j_service.create_document(
            document_id=test_document_id,
            title="Test Document",
            source="test.pdf",
            doc_type="pdf",
        )

        assert result.created is True
        assert result.node.id == test_document_id

    def test_get_document(self, neo4j_service, clean_database, test_document_id):
        """Test getting a document."""
        neo4j_service.create_document(
            document_id=test_document_id,
            title="Test Document",
            source="test.pdf",
        )

        doc = neo4j_service.get_document(test_document_id)

        assert doc is not None
        assert doc.id == test_document_id

    def test_delete_document(self, neo4j_service, clean_database, test_document_id):
        """Test deleting a document."""
        neo4j_service.create_document(
            document_id=test_document_id,
            title="Test Document",
            source="test.pdf",
        )

        result = neo4j_service.delete_document(test_document_id)

        assert result.deleted is True

        # Verify document is gone
        doc = neo4j_service.get_document(test_document_id)
        assert doc is None

    def test_add_chunk_to_document(
        self, neo4j_service, clean_database, test_document_id, test_chunk_id
    ):
        """Test adding a chunk to a document."""
        neo4j_service.create_document(
            document_id=test_document_id,
            title="Test Document",
            source="test.pdf",
        )

        chunk_result, rel_result = neo4j_service.add_chunk_to_document(
            document_id=test_document_id,
            chunk_id=test_chunk_id,
            text="Test chunk content",
            chunk_index=0,
        )

        assert chunk_result.created is True
        assert rel_result.created is True

    def test_get_document_chunks(
        self, neo4j_service, clean_database, test_document_id, test_chunk_id
    ):
        """Test getting document chunks."""
        neo4j_service.create_document(
            document_id=test_document_id,
            title="Test Document",
            source="test.pdf",
        )
        neo4j_service.add_chunk_to_document(
            document_id=test_document_id,
            chunk_id=test_chunk_id,
            text="Test chunk",
            chunk_index=0,
        )

        chunks = neo4j_service.get_document_chunks(test_document_id)

        assert len(chunks) >= 1


@pytest.mark.integration
class TestNeo4jServiceEntity:
    """Tests for Neo4jService entity operations."""

    def test_create_entity(self, neo4j_service, clean_database, test_entity_id):
        """Test creating an entity."""
        result = neo4j_service.create_entity(
            entity_id=test_entity_id,
            name="Python",
            entity_type="technology",
            description="A programming language",
        )

        assert result.created is True
        assert result.node.properties["name"] == "Python"

    def test_get_entity(self, neo4j_service, clean_database, test_entity_id):
        """Test getting an entity."""
        neo4j_service.create_entity(
            entity_id=test_entity_id,
            name="Python",
            entity_type="technology",
        )

        entity = neo4j_service.get_entity(test_entity_id)

        assert entity is not None
        assert entity.properties["name"] == "Python"

    def test_find_entity_by_name(self, neo4j_service, clean_database, test_entity_id):
        """Test finding an entity by name."""
        neo4j_service.create_entity(
            entity_id=test_entity_id,
            name="UniqueEntityName123",
            entity_type="test",
        )

        entity = neo4j_service.find_entity_by_name("UniqueEntityName123")

        assert entity is not None
        assert entity.properties["name"] == "UniqueEntityName123"

    def test_link_chunk_to_entity(
        self,
        neo4j_service,
        clean_database,
        test_document_id,
        test_chunk_id,
        test_entity_id,
    ):
        """Test linking a chunk to an entity."""
        neo4j_service.create_document(
            document_id=test_document_id,
            title="Test",
            source="test.pdf",
        )
        neo4j_service.add_chunk_to_document(
            document_id=test_document_id,
            chunk_id=test_chunk_id,
            text="Test chunk",
        )
        neo4j_service.create_entity(
            entity_id=test_entity_id,
            name="TestEntity",
            entity_type="test",
        )

        result = neo4j_service.link_chunk_to_entity(
            chunk_id=test_chunk_id,
            entity_id=test_entity_id,
            confidence=0.9,
        )

        assert result.created is True


@pytest.mark.integration
class TestNeo4jServiceConcept:
    """Tests for Neo4jService concept operations."""

    def test_create_concept(self, neo4j_service, clean_database, test_concept_id):
        """Test creating a concept."""
        result = neo4j_service.create_concept(
            concept_id=test_concept_id,
            name="Programming",
            description="The act of writing code",
            category="Computer Science",
        )

        assert result.created is True
        assert result.node.properties["name"] == "Programming"

    def test_link_document_to_concept(
        self,
        neo4j_service,
        clean_database,
        test_document_id,
        test_concept_id,
    ):
        """Test linking a document to a concept."""
        neo4j_service.create_document(
            document_id=test_document_id,
            title="Test",
            source="test.pdf",
        )
        neo4j_service.create_concept(
            concept_id=test_concept_id,
            name="TestConcept",
        )

        result = neo4j_service.link_document_to_concept(
            document_id=test_document_id,
            concept_id=test_concept_id,
            confidence=0.85,
        )

        assert result.created is True


@pytest.mark.integration
class TestNeo4jServiceKGRetrieval:
    """Tests for Neo4jService knowledge graph retrieval."""

    def test_get_entity_context(
        self,
        neo4j_service,
        clean_database,
        test_document_id,
        test_chunk_id,
        test_entity_id,
    ):
        """Test getting entity context for RAG."""
        # Setup: create document, chunk, entity
        neo4j_service.create_document(
            document_id=test_document_id,
            title="Test",
            source="test.pdf",
        )
        neo4j_service.add_chunk_to_document(
            document_id=test_document_id,
            chunk_id=test_chunk_id,
            text="Python is a programming language.",
        )
        neo4j_service.create_entity(
            entity_id=test_entity_id,
            name="Python",
            entity_type="technology",
        )
        neo4j_service.link_chunk_to_entity(
            chunk_id=test_chunk_id,
            entity_id=test_entity_id,
        )

        context = neo4j_service.get_entity_context(test_entity_id)

        assert context is not None
        assert context.entity.id == test_entity_id
        assert len(context.mentioned_in) >= 1

    def test_get_document_graph(
        self,
        neo4j_service,
        clean_database,
        test_document_id,
        test_chunk_id,
        test_entity_id,
        test_concept_id,
    ):
        """Test getting document subgraph."""
        # Setup
        neo4j_service.create_document(
            document_id=test_document_id,
            title="Test",
            source="test.pdf",
        )
        neo4j_service.add_chunk_to_document(
            document_id=test_document_id,
            chunk_id=test_chunk_id,
            text="Test content",
        )
        neo4j_service.create_entity(
            entity_id=test_entity_id,
            name="TestEntity",
            entity_type="test",
        )
        neo4j_service.create_concept(
            concept_id=test_concept_id,
            name="TestConcept",
        )
        neo4j_service.link_chunk_to_entity(test_chunk_id, test_entity_id)
        neo4j_service.link_document_to_concept(test_document_id, test_concept_id)

        graph = neo4j_service.get_document_graph(test_document_id)

        assert graph is not None
        assert graph.document.id == test_document_id
        assert len(graph.chunks) >= 1
        assert len(graph.entities) >= 1
        assert len(graph.concepts) >= 1

    def test_search_entities(self, neo4j_service, clean_database, test_entity_id):
        """Test searching entities."""
        neo4j_service.create_entity(
            entity_id=test_entity_id,
            name="SearchTestEntity123",
            entity_type="test",
        )

        entities = neo4j_service.search_entities(name="SearchTestEntity123")

        assert len(entities) >= 1
        assert any(e.properties.get("name") == "SearchTestEntity123" for e in entities)

    def test_get_chunks_by_entities(
        self,
        neo4j_service,
        clean_database,
        test_document_id,
        test_chunk_id,
        test_entity_id,
    ):
        """Test getting chunks by entity names."""
        neo4j_service.create_document(
            document_id=test_document_id,
            title="Test",
            source="test.pdf",
        )
        neo4j_service.add_chunk_to_document(
            document_id=test_document_id,
            chunk_id=test_chunk_id,
            text="Python is great for data science.",
        )
        neo4j_service.create_entity(
            entity_id=test_entity_id,
            name="PythonDataScienceEntity",
            entity_type="technology",
        )
        neo4j_service.link_chunk_to_entity(
            chunk_id=test_chunk_id,
            entity_id=test_entity_id,
        )

        chunks = neo4j_service.get_chunks_by_entities(
            entity_names=["PythonDataScienceEntity"]
        )

        assert len(chunks) >= 1


@pytest.mark.integration
class TestNeo4jServiceHealth:
    """Tests for Neo4jService health operations."""

    def test_health_check(self, neo4j_service):
        """Test health check."""
        health = neo4j_service.health_check()

        assert health["status"] == "healthy"
        assert health["connected"] is True

    def test_get_graph_stats(self, neo4j_service, sample_knowledge_graph):
        """Test getting graph statistics."""
        stats = neo4j_service.get_graph_stats()

        assert "total_nodes" in stats
        assert "total_relationships" in stats

    def test_initialize_schema(self, neo4j_service):
        """Test schema initialization."""
        result = neo4j_service.initialize_schema()

        assert "constraints_created" in result
        assert "indexes_created" in result
