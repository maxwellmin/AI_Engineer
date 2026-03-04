"""
Services module for Neo4j database controller.

This module contains:
- Neo4jService: High-level facade service for all Neo4j operations
- EntityExtractorInterface: Abstract interface for entity extraction
"""

from apps.neo4j_database_controller.services.neo4j_service import (
    EntityExtractorInterface,
    MockEntityExtractor,
    Neo4jService,
    get_neo4j_service,
)

__all__ = [
    "Neo4jService",
    "EntityExtractorInterface",
    "MockEntityExtractor",
    "get_neo4j_service",
]
