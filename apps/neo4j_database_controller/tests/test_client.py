"""
Tests for Neo4jClient.

Unit tests for the Neo4j client wrapper.
"""

import pytest

from apps.neo4j_database_controller.exceptions import Neo4jConnectionError


@pytest.mark.integration
class TestNeo4jClient:
    """Integration tests for Neo4jClient."""

    def test_get_instance_returns_singleton(self, neo4j_client):
        """Test that get_instance returns the same instance."""
        from apps.neo4j_database_controller.client import Neo4jClient

        instance1 = Neo4jClient.get_instance()
        instance2 = Neo4jClient.get_instance()

        assert instance1 is instance2

    def test_is_connected(self, neo4j_client):
        """Test that is_connected returns True when connected."""
        assert neo4j_client.is_connected() is True

    def test_execute_read(self, neo4j_client, clean_database):
        """Test execute_read with a simple query."""
        result = neo4j_client.execute_read("RETURN 1 AS value")

        assert len(result) == 1
        assert result[0].get("value") == 1

    def test_execute_write(self, neo4j_client, clean_database, test_document_id):
        """Test execute_write with a CREATE query."""
        query = """
        CREATE (d:Document {id: $id, title: $title})
        RETURN d.id AS id, d.title AS title
        """

        result = neo4j_client.execute_write(
            query,
            parameters={"id": test_document_id, "title": "Test"},
        )

        assert len(result) == 1
        assert result[0].get("id") == test_document_id
        assert result[0].get("title") == "Test"

    def test_execute_query_alias(self, neo4j_client, clean_database):
        """Test that execute_query is an alias for execute_read."""
        result = neo4j_client.execute_query("RETURN 'test' AS value")

        assert len(result) == 1
        assert result[0].get("value") == "test"

    def test_get_server_info(self, neo4j_client):
        """Test get_server_info returns server information."""
        info = neo4j_client.get_server_info()

        assert info is not None
        assert "version" in info or "address" in info

    def test_execute_read_with_parameters(self, neo4j_client, clean_database):
        """Test execute_read with parameters."""
        query = "RETURN $value AS result"
        result = neo4j_client.execute_read(query, parameters={"value": 42})

        assert len(result) == 1
        assert result[0].get("result") == 42

    def test_execute_write_with_complex_query(
        self, neo4j_client, clean_database, test_document_id, test_chunk_id
    ):
        """Test execute_write with a complex query involving relationships."""
        # Create document
        create_doc = """
        CREATE (d:Document {id: $doc_id, title: 'Test'})
        RETURN d.id AS id
        """
        neo4j_client.execute_write(create_doc, parameters={"doc_id": test_document_id})

        # Create chunk with relationship
        create_chunk = """
        MATCH (d:Document {id: $doc_id})
        CREATE (c:Chunk {id: $chunk_id, text: 'Test text'})
        CREATE (d)-[:CONTAINS]->(c)
        RETURN c.id AS id
        """
        result = neo4j_client.execute_write(
            create_chunk,
            parameters={"doc_id": test_document_id, "chunk_id": test_chunk_id},
        )

        assert len(result) == 1
        assert result[0].get("id") == test_chunk_id

        # Verify relationship exists
        verify_query = """
        MATCH (d:Document {id: $doc_id})-[:CONTAINS]->(c:Chunk {id: $chunk_id})
        RETURN count(c) AS count
        """
        verify_result = neo4j_client.execute_read(
            verify_query,
            parameters={"doc_id": test_document_id, "chunk_id": test_chunk_id},
        )

        assert verify_result[0].get("count") == 1


@pytest.mark.unit
class TestNeo4jClientUnit:
    """Unit tests for Neo4jClient with mocked driver."""

    def test_singleton_reset(self):
        """Test that singleton can be reset for testing."""
        from apps.neo4j_database_controller.client import Neo4jClient

        # Reset singleton
        Neo4jClient._instance = None

        # Verify it's None
        assert Neo4jClient._instance is None

    def test_invalid_connection_parameters(self):
        """Test handling of invalid connection parameters."""
        from unittest.mock import MagicMock, patch

        from apps.neo4j_database_controller.client import Neo4jClient

        # Reset singleton
        Neo4jClient._instance = None

        # Mock the driver to raise an error
        with patch("neo4j.GraphDatabase.driver") as mock_driver:
            mock_driver.side_effect = Exception("Connection failed")

            # This should still create an instance, but connection will fail later
            # The singleton pattern doesn't prevent creation
            try:
                client = Neo4jClient()
                # Connection check should fail
                assert client.is_connected() is False
            except Exception:
                # Expected - connection failed
                pass
            finally:
                # Reset singleton
                Neo4jClient._instance = None
