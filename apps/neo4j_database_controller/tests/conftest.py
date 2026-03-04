"""
Pytest fixtures for Neo4j database controller tests.

This module provides fixtures for testing Neo4j operations:
- Neo4j client instance
- Sample nodes (Document, Chunk, Entity, Concept, User)
- Sample relationships
- Cleanup utilities
"""

import os
import uuid
from typing import TYPE_CHECKING, Any, Generator

import pytest

if TYPE_CHECKING:
    from neo4j import Driver

# Skip all tests in this module if Neo4j is not available
# This allows tests to be run in CI environments without Neo4j
pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_NEO4J_TESTS", "false").lower() == "true",
    reason="Neo4j tests are disabled",
)


# =============================================================================
# Client Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def neo4j_driver() -> Generator["Driver", None, None]:
    """Create a Neo4j driver for the test session.

    Yields:
        Neo4j Driver instance.
    """
    from neo4j import GraphDatabase

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "password")

    driver = GraphDatabase.driver(uri, auth=(user, password))

    yield driver

    driver.close()


@pytest.fixture
def neo4j_client(neo4j_driver: "Driver") -> Generator[Any, None, None]:
    """Create a Neo4jClient instance for testing.

    Yields:
        Neo4jClient instance.
    """
    from apps.neo4j_database_controller.client import Neo4jClient

    # Reset singleton for testing
    Neo4jClient._instance = None

    client = Neo4jClient.get_instance()

    yield client

    # Cleanup: delete all test nodes
    try:
        client.execute_write(
            "MATCH (n) WHERE n.id STARTS WITH 'test-' DETACH DELETE n"
        )
    except Exception:
        pass

    # Reset singleton after test
    Neo4jClient._instance = None


@pytest.fixture
def clean_database(neo4j_client: Any) -> None:
    """Clean the database before and after a test.

    This fixture ensures a clean state for each test.
    """
    # Clean before test
    neo4j_client.execute_write(
        "MATCH (n) WHERE n.id STARTS WITH 'test-' DETACH DELETE n"
    )

    yield

    # Clean after test
    neo4j_client.execute_write(
        "MATCH (n) WHERE n.id STARTS WITH 'test-' DETACH DELETE n"
    )


# =============================================================================
# Node Fixtures
# =============================================================================


@pytest.fixture
def test_document_id() -> str:
    """Generate a test document ID."""
    return f"test-doc-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_chunk_id() -> str:
    """Generate a test chunk ID."""
    return f"test-chunk-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_entity_id() -> str:
    """Generate a test entity ID."""
    return f"test-entity-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_concept_id() -> str:
    """Generate a test concept ID."""
    return f"test-concept-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_user_id() -> str:
    """Generate a test user ID."""
    return f"test-user-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def sample_document(test_document_id: str) -> dict[str, Any]:
    """Create sample document properties."""
    return {
        "id": test_document_id,
        "title": "Test Document",
        "source": "test.pdf",
        "doc_type": "pdf",
        "status": "active",
    }


@pytest.fixture
def sample_chunk(test_chunk_id: str, test_document_id: str) -> dict[str, Any]:
    """Create sample chunk properties."""
    return {
        "id": test_chunk_id,
        "text": "This is a test chunk with some text content.",
        "chunk_index": 0,
        "page_number": 1,
        "document_id": test_document_id,
    }


@pytest.fixture
def sample_entity(test_entity_id: str) -> dict[str, Any]:
    """Create sample entity properties."""
    return {
        "id": test_entity_id,
        "name": "Python",
        "entity_type": "technology",
        "description": "A programming language",
        "confidence": 0.95,
    }


@pytest.fixture
def sample_concept(test_concept_id: str) -> dict[str, Any]:
    """Create sample concept properties."""
    return {
        "id": test_concept_id,
        "name": "Programming",
        "description": "The process of creating software",
        "category": "Computer Science",
    }


@pytest.fixture
def sample_user(test_user_id: str) -> dict[str, Any]:
    """Create sample user properties."""
    return {
        "id": test_user_id,
        "username": "testuser",
        "email": "test@example.com",
    }


# =============================================================================
# Manager Fixtures
# =============================================================================


@pytest.fixture
def node_manager(neo4j_client: Any) -> Any:
    """Create a NodeManager instance for testing."""
    from apps.neo4j_database_controller.managers import NodeManager

    return NodeManager(neo4j_client)


@pytest.fixture
def relationship_manager(neo4j_client: Any) -> Any:
    """Create a RelationshipManager instance for testing."""
    from apps.neo4j_database_controller.managers import RelationshipManager

    return RelationshipManager(neo4j_client)


@pytest.fixture
def query_manager(neo4j_client: Any) -> Any:
    """Create a QueryManager instance for testing."""
    from apps.neo4j_database_controller.managers import QueryManager

    return QueryManager(neo4j_client)


@pytest.fixture
def neo4j_service(neo4j_client: Any) -> Any:
    """Create a Neo4jService instance for testing."""
    from apps.neo4j_database_controller.services import Neo4jService

    return Neo4jService(neo4j_client)


# =============================================================================
# Sample Graph Fixtures
# =============================================================================


@pytest.fixture
def sample_knowledge_graph(
    node_manager: Any,
    relationship_manager: Any,
    sample_document: dict[str, Any],
    sample_chunk: dict[str, Any],
    sample_entity: dict[str, Any],
    sample_concept: dict[str, Any],
) -> dict[str, Any]:
    """Create a sample knowledge graph for testing.

    Creates:
    - Document node
    - Chunk node
    - Entity node
    - Concept node
    - CONTAINS relationship (Document -> Chunk)
    - MENTIONS relationship (Chunk -> Entity)
    - ABOUT relationship (Document -> Concept)
    """
    # Create nodes
    doc_result = node_manager.create_node("Document", sample_document)
    chunk_result = node_manager.create_node("Chunk", sample_chunk)
    entity_result = node_manager.create_node("Entity", sample_entity)
    concept_result = node_manager.create_node("Concept", sample_concept)

    # Create relationships
    contains_result = relationship_manager.create_relationship(
        rel_type="CONTAINS",
        from_node_id=sample_document["id"],
        from_node_label="Document",
        to_node_id=sample_chunk["id"],
        to_node_label="Chunk",
        properties={"order": 0},
    )

    mentions_result = relationship_manager.create_relationship(
        rel_type="MENTIONS",
        from_node_id=sample_chunk["id"],
        from_node_label="Chunk",
        to_node_id=sample_entity["id"],
        to_node_label="Entity",
        properties={"confidence": 0.9, "count": 1},
    )

    about_result = relationship_manager.create_relationship(
        rel_type="ABOUT",
        from_node_id=sample_document["id"],
        from_node_label="Document",
        to_node_id=sample_concept["id"],
        to_node_label="Concept",
        properties={"confidence": 0.85},
    )

    return {
        "document": doc_result.node,
        "chunk": chunk_result.node,
        "entity": entity_result.node,
        "concept": concept_result.node,
        "contains_rel": contains_result.relationship,
        "mentions_rel": mentions_result.relationship,
        "about_rel": about_result.relationship,
    }


# =============================================================================
# Helper Functions
# =============================================================================


def create_test_document(
    node_manager: Any,
    document_id: str,
    title: str = "Test Document",
    source: str = "test.pdf",
) -> Any:
    """Helper to create a test document."""
    return node_manager.create_node(
        "Document",
        {
            "id": document_id,
            "title": title,
            "source": source,
            "doc_type": "pdf",
            "status": "active",
        },
    )


def create_test_chunk(
    node_manager: Any,
    chunk_id: str,
    document_id: str,
    text: str = "Test chunk content",
    chunk_index: int = 0,
) -> Any:
    """Helper to create a test chunk."""
    return node_manager.create_node(
        "Chunk",
        {
            "id": chunk_id,
            "text": text,
            "chunk_index": chunk_index,
            "document_id": document_id,
        },
    )


def create_test_entity(
    node_manager: Any,
    entity_id: str,
    name: str = "Test Entity",
    entity_type: str = "person",
) -> Any:
    """Helper to create a test entity."""
    return node_manager.create_node(
        "Entity",
        {
            "id": entity_id,
            "name": name,
            "entity_type": entity_type,
            "confidence": 0.9,
        },
    )


def create_test_concept(
    node_manager: Any,
    concept_id: str,
    name: str = "Test Concept",
) -> Any:
    """Helper to create a test concept."""
    return node_manager.create_node(
        "Concept",
        {
            "id": concept_id,
            "name": name,
            "category": "general",
        },
    )


# =============================================================================
# Markers
# =============================================================================


def pytest_configure(config: Any) -> None:
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires Neo4j)"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (mocked Neo4j)"
    )
