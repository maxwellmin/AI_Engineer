"""
Graph schema definitions for Neo4j database.

This module defines the graph schema including constraints, indexes,
and provides methods to initialize the database schema.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from apps.neo4j_database_controller.constants import NodeLabel

if TYPE_CHECKING:
    from apps.neo4j_database_controller.client.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


# =============================================================================
# Unique Constraints
# =============================================================================

# Unique constraints ensure data integrity and automatically create indexes
# Each constraint follows the pattern: (label, property)
UNIQUE_CONSTRAINTS: list[tuple[str, str]] = [
    # Document node constraints
    (NodeLabel.DOCUMENT.value, "id"),
    # Chunk node constraints
    (NodeLabel.CHUNK.value, "id"),
    # Entity node constraints
    (NodeLabel.ENTITY.value, "id"),
    # Concept node constraints
    (NodeLabel.CONCEPT.value, "id"),
    # User node constraints
    (NodeLabel.USER.value, "id"),
]


# =============================================================================
# Indexes
# =============================================================================

# Additional indexes for common query patterns
# Each index follows the pattern: (label, property)
INDEXES: list[tuple[str, str]] = [
    # Entity name search (common for autocomplete and search)
    (NodeLabel.ENTITY.value, "name"),
    # Entity type filtering
    (NodeLabel.ENTITY.value, "entity_type"),
    # Concept name search
    (NodeLabel.CONCEPT.value, "name"),
    # Chunk document_id for fast lookups
    (NodeLabel.CHUNK.value, "document_id"),
    # Document status filtering
    (NodeLabel.DOCUMENT.value, "status"),
]


# =============================================================================
# Constraint/Index Creation Queries
# =============================================================================

CONSTRAINT_QUERY_TEMPLATE = """
CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
FOR (n:{label}) REQUIRE n.{property} IS UNIQUE
"""

INDEX_QUERY_TEMPLATE = """
CREATE INDEX {index_name} IF NOT EXISTS
FOR (n:{label}) ON (n.{property})
"""


def generate_constraint_name(label: str, property_name: str) -> str:
    """Generate a constraint name from label and property.

    Args:
        label: Node label.
        property_name: Property name.

    Returns:
        Constraint name in format: label_property_unique
    """
    return f"{label.lower()}_{property_name}_unique"


def generate_index_name(label: str, property_name: str) -> str:
    """Generate an index name from label and property.

    Args:
        label: Node label.
        property_name: Property name.

    Returns:
        Index name in format: label_property_index
    """
    return f"{label.lower()}_{property_name}_index"


class GraphSchemaManager:
    """Manager for Neo4j graph schema operations.

    This class provides methods to:
    - Create unique constraints
    - Create indexes
    - Initialize the full database schema
    - Check existing schema elements

    Example:
        >>> from apps.neo4j_database_controller.client import Neo4jClient
        >>> from apps.neo4j_database_controller.schemas import GraphSchemaManager
        >>> client = Neo4jClient.get_instance()
        >>> schema_manager = GraphSchemaManager(client)
        >>> schema_manager.initialize_schema()
    """

    def __init__(self, client: Neo4jClient | None = None) -> None:
        """Initialize the schema manager.

        Args:
            client: Neo4jClient instance. If None, gets singleton instance.
        """
        if client is None:
            from apps.neo4j_database_controller.client import Neo4jClient

            client = Neo4jClient.get_instance()
        self._client = client

    def create_constraint(self, label: str, property_name: str) -> bool:
        """Create a unique constraint for a node property.

        Args:
            label: Node label.
            property_name: Property name to constrain.

        Returns:
            True if constraint created successfully.

        Raises:
            QueryError: If constraint creation fails.
        """
        constraint_name = generate_constraint_name(label, property_name)
        query = CONSTRAINT_QUERY_TEMPLATE.format(
            constraint_name=constraint_name,
            label=label,
            property=property_name,
        )

        try:
            self._client.execute_write(query)
            logger.info(f"Created constraint '{constraint_name}' for {label}.{property_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create constraint '{constraint_name}': {e}")
            raise

    def create_index(self, label: str, property_name: str) -> bool:
        """Create an index for a node property.

        Args:
            label: Node label.
            property_name: Property name to index.

        Returns:
            True if index created successfully.

        Raises:
            QueryError: If index creation fails.
        """
        index_name = generate_index_name(label, property_name)
        query = INDEX_QUERY_TEMPLATE.format(
            index_name=index_name,
            label=label,
            property=property_name,
        )

        try:
            self._client.execute_write(query)
            logger.info(f"Created index '{index_name}' for {label}.{property_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create index '{index_name}': {e}")
            raise

    def initialize_schema(self) -> dict[str, Any]:
        """Initialize the complete database schema.

        Creates all unique constraints and indexes defined in this module.

        Returns:
            Dictionary with creation results:
            - constraints_created: Number of constraints created
            - indexes_created: Number of indexes created
            - errors: List of any errors encountered
        """
        results = {
            "constraints_created": 0,
            "indexes_created": 0,
            "errors": [],
        }

        logger.info("Initializing Neo4j database schema...")

        # Create unique constraints
        for label, property_name in UNIQUE_CONSTRAINTS:
            try:
                self.create_constraint(label, property_name)
                results["constraints_created"] += 1
            except Exception as e:
                results["errors"].append(f"Constraint {label}.{property_name}: {e}")

        # Create indexes
        for label, property_name in INDEXES:
            try:
                self.create_index(label, property_name)
                results["indexes_created"] += 1
            except Exception as e:
                results["errors"].append(f"Index {label}.{property_name}: {e}")

        logger.info(
            f"Schema initialization complete: "
            f"{results['constraints_created']} constraints, "
            f"{results['indexes_created']} indexes created"
        )

        return results

    def list_constraints(self) -> list[dict[str, Any]]:
        """List all constraints in the database.

        Returns:
            List of constraint information dictionaries.
        """
        query = "SHOW CONSTRAINTS"
        return self._client.execute_query(query)

    def list_indexes(self) -> list[dict[str, Any]]:
        """List all indexes in the database.

        Returns:
            List of index information dictionaries.
        """
        query = "SHOW INDEXES"
        return self._client.execute_query(query)

    def constraint_exists(self, label: str, property_name: str) -> bool:
        """Check if a constraint exists.

        Args:
            label: Node label.
            property_name: Property name.

        Returns:
            True if constraint exists.
        """
        constraints = self.list_constraints()
        constraint_name = generate_constraint_name(label, property_name)
        return any(c.get("name") == constraint_name for c in constraints)

    def index_exists(self, label: str, property_name: str) -> bool:
        """Check if an index exists.

        Args:
            label: Node label.
            property_name: Property name.

        Returns:
            True if index exists.
        """
        indexes = self.list_indexes()
        index_name = generate_index_name(label, property_name)
        return any(i.get("name") == index_name for i in indexes)

    def drop_constraint(self, label: str, property_name: str) -> bool:
        """Drop a constraint.

        Args:
            label: Node label.
            property_name: Property name.

        Returns:
            True if constraint dropped successfully.
        """
        constraint_name = generate_constraint_name(label, property_name)
        query = f"DROP CONSTRAINT {constraint_name} IF EXISTS"

        try:
            self._client.execute_write(query)
            logger.info(f"Dropped constraint '{constraint_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to drop constraint '{constraint_name}': {e}")
            return False

    def drop_index(self, label: str, property_name: str) -> bool:
        """Drop an index.

        Args:
            label: Node label.
            property_name: Property name.

        Returns:
            True if index dropped successfully.
        """
        index_name = generate_index_name(label, property_name)
        query = f"DROP INDEX {index_name} IF EXISTS"

        try:
            self._client.execute_write(query)
            logger.info(f"Dropped index '{index_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to drop index '{index_name}': {e}")
            return False


# =============================================================================
# Convenience Functions
# =============================================================================


def initialize_database_schema() -> dict[str, Any]:
    """Initialize the Neo4j database schema.

    This is a convenience function that creates the Neo4jClient
    and initializes the schema in one call.

    Returns:
        Dictionary with creation results.

    Example:
        >>> from apps.neo4j_database_controller.schemas import initialize_database_schema
        >>> results = initialize_database_schema()
        >>> print(results)
    """
    manager = GraphSchemaManager()
    return manager.initialize_schema()


def get_schema_manager() -> GraphSchemaManager:
    """Get a GraphSchemaManager instance.

    Returns:
        GraphSchemaManager instance.
    """
    return GraphSchemaManager()
