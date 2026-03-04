"""
Neo4j client module.

This module provides the Neo4jClient singleton for database connections.
"""

from apps.neo4j_database_controller.client.neo4j_client import (
    Neo4jClient,
    parse_node,
    parse_relationship,
)

__all__ = [
    "Neo4jClient",
    "parse_node",
    "parse_relationship",
]
