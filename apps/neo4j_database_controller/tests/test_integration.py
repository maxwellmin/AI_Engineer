"""
Integration tests for Neo4j database controller.

End-to-end tests that validate the complete workflow.
"""

import pytest

from apps.neo4j_database_controller.constants import NodeLabel, RelType
from apps.neo4j_database_controller.services import Neo4jService


@pytest.mark.integration
class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    def test_document_processing_workflow(
        self,
        neo4j_service,
        clean_database,
    ):
        """Test complete document processing workflow."""
        doc_id = "test-workflow-doc-1"

        # 1. Create document
        doc_result = neo4j_service.create_document(
            document_id=doc_id,
            title="Introduction to Python",
            source="python_intro.pdf",
            doc_type="pdf",
        )
        assert doc_result.created is True

        # 2. Add chunks
        chunks = []
        for i in range(3):
            chunk_id = f"{doc_id}-chunk-{i}"
            chunk_result, _ = neo4j_service.add_chunk_to_document(
                document_id=doc_id,
                chunk_id=chunk_id,
                text=f"Chunk {i} content about Python.",
                chunk_index=i,
            )
            chunks.append(chunk_result)

        assert len(chunks) == 3

        # 3. Create entities
        entity_id = "test-workflow-entity-python"
        entity_result = neo4j_service.create_entity(
            entity_id=entity_id,
            name="Python",
            entity_type="technology",
            description="Programming language",
        )
        assert entity_result.created is True

        # 4. Link chunks to entities
        for i in range(3):
            chunk_id = f"{doc_id}-chunk-{i}"
            neo4j_service.link_chunk_to_entity(
                chunk_id=chunk_id,
                entity_id=entity_id,
                confidence=0.9 - i * 0.1,
            )

        # 5. Create concept
        concept_id = "test-workflow-concept-programming"
        concept_result = neo4j_service.create_concept(
            concept_id=concept_id,
            name="Programming",
            category="Computer Science",
        )
        assert concept_result.created is True

        # 6. Link document to concept
        neo4j_service.link_document_to_concept(
            document_id=doc_id,
            concept_id=concept_id,
            confidence=0.95,
        )

        # 7. Retrieve entity context
        context = neo4j_service.get_entity_context(entity_id)
        assert context is not None
        assert len(context.mentioned_in) == 3

        # 8. Retrieve document graph
        graph = neo4j_service.get_document_graph(doc_id)
        assert graph is not None
        assert len(graph.chunks) == 3
        assert len(graph.entities) >= 1
        assert len(graph.concepts) >= 1

    def test_entity_relationship_discovery(
        self,
        neo4j_service,
        clean_database,
    ):
        """Test entity relationship discovery workflow."""
        # Create entities
        python_id = "test-disc-entity-python"
        django_id = "test-disc-entity-django"
        flask_id = "test-disc-entity-flask"

        neo4j_service.create_entity(
            entity_id=python_id,
            name="Python",
            entity_type="technology",
        )
        neo4j_service.create_entity(
            entity_id=django_id,
            name="Django",
            entity_type="technology",
        )
        neo4j_service.create_entity(
            entity_id=flask_id,
            name="Flask",
            entity_type="technology",
        )

        # Create relationships between entities
        from apps.neo4j_database_controller.dto import CreateRelationshipRequest

        neo4j_service.create_relationship(
            CreateRelationshipRequest(
                rel_type=RelType.RELATED_TO.value,
                from_node_id=django_id,
                from_node_label=NodeLabel.ENTITY.value,
                to_node_id=python_id,
                to_node_label=NodeLabel.ENTITY.value,
                properties={"relation_type": "framework_for"},
            )
        )
        neo4j_service.create_relationship(
            CreateRelationshipRequest(
                rel_type=RelType.RELATED_TO.value,
                from_node_id=flask_id,
                from_node_label=NodeLabel.ENTITY.value,
                to_node_id=python_id,
                to_node_label=NodeLabel.ENTITY.value,
                properties={"relation_type": "framework_for"},
            )
        )

        # Find related entities
        related = neo4j_service.find_related_entities(entity_id=python_id)

        assert len(related) >= 2
        related_names = [e.properties.get("name") for e in related]
        assert "Django" in related_names or "Flask" in related_names


@pytest.mark.integration
class TestRAGWorkflow:
    """Tests for RAG-specific workflows."""

    def test_retrieve_context_for_query(
        self,
        neo4j_service,
        clean_database,
    ):
        """Test retrieving context for a RAG query."""
        # Setup knowledge graph
        doc_id = "test-rag-doc"
        neo4j_service.create_document(
            document_id=doc_id,
            title="Machine Learning Guide",
            source="ml_guide.pdf",
        )

        # Add chunks
        chunk_data = [
            ("test-rag-chunk-1", "Machine learning is a subset of AI."),
            ("test-rag-chunk-2", "Neural networks are used in deep learning."),
            ("test-rag-chunk-3", "Python is popular for ML development."),
        ]

        for chunk_id, text in chunk_data:
            neo4j_service.add_chunk_to_document(
                document_id=doc_id,
                chunk_id=chunk_id,
                text=text,
                chunk_index=int(chunk_id[-1]) - 1,
            )

        # Create entities
        ml_entity_id = "test-rag-entity-ml"
        ai_entity_id = "test-rag-entity-ai"
        neo4j_service.create_entity(
            entity_id=ml_entity_id,
            name="Machine Learning",
            entity_type="concept",
        )
        neo4j_service.create_entity(
            entity_id=ai_entity_id,
            name="Artificial Intelligence",
            entity_type="concept",
        )

        # Link entities
        neo4j_service.link_chunk_to_entity(
            chunk_id="test-rag-chunk-1",
            entity_id=ml_entity_id,
        )
        neo4j_service.link_chunk_to_entity(
            chunk_id="test-rag-chunk-1",
            entity_id=ai_entity_id,
        )

        # Retrieve context
        context = neo4j_service.get_entity_context(ml_entity_id)

        assert context is not None
        assert len(context.mentioned_in) >= 1

        # Get chunks by entity names
        chunks = neo4j_service.get_chunks_by_entities(
            entity_names=["Machine Learning", "Artificial Intelligence"]
        )

        assert len(chunks) >= 1


@pytest.mark.integration
class TestBatchOperations:
    """Tests for batch operations."""

    def test_batch_node_creation(
        self,
        neo4j_service,
        clean_database,
    ):
        """Test creating nodes in batch."""
        nodes = [
            {"id": f"test-batch-entity-{i}", "name": f"Entity {i}", "entity_type": "test"}
            for i in range(10)
        ]

        result = neo4j_service.create_nodes_batch(
            label=NodeLabel.ENTITY.value,
            nodes=nodes,
        )

        assert result.created_count == 10
        assert result.failed_count == 0

    def test_batch_relationship_creation(
        self,
        node_manager,
        neo4j_service,
        clean_database,
    ):
        """Test creating relationships in batch."""
        from apps.neo4j_database_controller.dto import CreateRelationshipRequest

        # Create entities
        entities = []
        for i in range(5):
            entity_id = f"test-batch-rel-entity-{i}"
            node_manager.create_node(
                NodeLabel.ENTITY.value,
                {"id": entity_id, "name": f"Entity {i}"},
            )
            entities.append(entity_id)

        # Create relationships
        relationships = []
        for i in range(4):
            relationships.append(
                CreateRelationshipRequest(
                    rel_type=RelType.RELATED_TO.value,
                    from_node_id=entities[i],
                    from_node_label=NodeLabel.ENTITY.value,
                    to_node_id=entities[i + 1],
                    to_node_label=NodeLabel.ENTITY.value,
                )
            )

        from apps.neo4j_database_controller.managers import RelationshipManager

        rel_manager = RelationshipManager()
        result = rel_manager.create_relationships_batch(relationships)

        assert result.created_count == 4
