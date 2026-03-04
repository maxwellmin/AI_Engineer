"""
Custom exceptions for Neo4j database controller.

This module defines all custom exception classes used throughout the
Neo4j database controller module for proper error handling and propagation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# =============================================================================
# Base Exception
# =============================================================================


class Neo4jError(Exception):
    """Base exception for all Neo4j-related errors."""

    def __init__(self, message: str = "An error occurred in Neo4j operation") -> None:
        self.message = message
        super().__init__(self.message)


# =============================================================================
# Connection Exceptions
# =============================================================================


class Neo4jConnectionError(Neo4jError):
    """Failed to establish connection to Neo4j server."""

    def __init__(self, reason: str = "Unknown reason") -> None:
        self.reason = reason
        message = f"Failed to connect to Neo4j server: {reason}"
        super().__init__(message)


class Neo4jConnectionTimeoutError(Neo4jConnectionError):
    """Connection to Neo4j server timed out."""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        message = f"Connection to Neo4j server timed out after {timeout} seconds"
        super().__init__(message)


class Neo4jAuthError(Neo4jConnectionError):
    """Authentication failed with Neo4j server."""

    def __init__(self, reason: str = "Invalid credentials") -> None:
        message = f"Neo4j authentication failed: {reason}"
        super().__init__(message)


# =============================================================================
# Node Exceptions
# =============================================================================


class NodeError(Neo4jError):
    """Base exception for node-related errors."""

    def __init__(self, node_id: str, label: str, message: str) -> None:
        self.node_id = node_id
        self.label = label
        super().__init__(message)


class NodeNotFoundError(NodeError):
    """Node does not exist."""

    def __init__(self, node_id: str, label: str = "") -> None:
        label_info = f" (label: {label})" if label else ""
        message = f"Node '{node_id}'{label_info} not found"
        super().__init__(node_id, label, message)


class NodeAlreadyExistsError(NodeError):
    """Node already exists."""

    def __init__(self, node_id: str, label: str) -> None:
        message = f"Node '{node_id}' (label: {label}) already exists"
        super().__init__(node_id, label, message)


class NodeCreationError(NodeError):
    """Failed to create node."""

    def __init__(self, label: str, reason: str = "Unknown reason") -> None:
        self.reason = reason
        message = f"Failed to create node with label '{label}': {reason}"
        super().__init__("", label, message)


class NodeDeletionError(NodeError):
    """Failed to delete node."""

    def __init__(self, node_id: str, label: str, reason: str = "Unknown reason") -> None:
        self.reason = reason
        message = f"Failed to delete node '{node_id}' (label: {label}): {reason}"
        super().__init__(node_id, label, message)


# =============================================================================
# Relationship Exceptions
# =============================================================================


class RelationshipError(Neo4jError):
    """Base exception for relationship-related errors."""

    def __init__(self, rel_id: int | str, message: str) -> None:
        self.rel_id = rel_id
        super().__init__(message)


class RelationshipNotFoundError(RelationshipError):
    """Relationship does not exist."""

    def __init__(self, rel_id: int) -> None:
        message = f"Relationship {rel_id} not found"
        super().__init__(rel_id, message)


class RelationshipCreationError(RelationshipError):
    """Failed to create relationship."""

    def __init__(
        self,
        rel_type: str,
        from_node_id: str,
        to_node_id: str,
        reason: str = "Unknown reason",
    ) -> None:
        self.rel_type = rel_type
        self.from_node_id = from_node_id
        self.to_node_id = to_node_id
        self.reason = reason
        message = (
            f"Failed to create relationship '{rel_type}' from '{from_node_id}' "
            f"to '{to_node_id}': {reason}"
        )
        super().__init__("", message)


class RelationshipDeletionError(RelationshipError):
    """Failed to delete relationship."""

    def __init__(self, rel_id: int, reason: str = "Unknown reason") -> None:
        self.reason = reason
        message = f"Failed to delete relationship {rel_id}: {reason}"
        super().__init__(rel_id, message)


# =============================================================================
# Query Exceptions
# =============================================================================


class QueryError(Neo4jError):
    """Failed to execute Cypher query."""

    def __init__(self, query: str = "", reason: str = "Unknown reason") -> None:
        self.query = query
        self.reason = reason
        # Truncate query in message for readability
        query_preview = query[:100] + "..." if len(query) > 100 else query
        message = f"Query failed: {reason}. Query: {query_preview}"
        super().__init__(message)


class PathNotFoundError(QueryError):
    """No path found between nodes."""

    def __init__(self, from_node_id: str, to_node_id: str) -> None:
        self.from_node_id = from_node_id
        self.to_node_id = to_node_id
        message = f"No path found from '{from_node_id}' to '{to_node_id}'"
        super().__init__("", message)


class InvalidQueryParameterError(QueryError):
    """Invalid query parameter."""

    def __init__(self, param_name: str, param_value: str, reason: str = "") -> None:
        self.param_name = param_name
        self.param_value = param_value
        reason_info = f": {reason}" if reason else ""
        message = f"Invalid query parameter '{param_name}' with value '{param_value}'{reason_info}"
        super().__init__("", message)


# =============================================================================
# Constraint Exceptions
# =============================================================================


class ConstraintViolationError(Neo4jError):
    """Constraint violation error."""

    def __init__(self, constraint: str, reason: str = "") -> None:
        self.constraint = constraint
        self.reason = reason
        reason_info = f": {reason}" if reason else ""
        message = f"Constraint violation '{constraint}'{reason_info}"
        super().__init__(message)


class UniqueConstraintViolationError(ConstraintViolationError):
    """Unique constraint violation."""

    def __init__(self, label: str, property_name: str, value: str) -> None:
        self.label = label
        self.property_name = property_name
        self.value = value
        constraint = f"{label}.{property_name}"
        reason = f"Value '{value}' already exists"
        super().__init__(constraint, reason)


# =============================================================================
# Validation Exceptions
# =============================================================================


class ValidationError(Neo4jError):
    """Base exception for validation errors."""

    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(message)


class InvalidNodeLabelError(ValidationError):
    """Invalid node label."""

    def __init__(self, label: str) -> None:
        self.label = label
        from apps.neo4j_database_controller.constants import VALID_NODE_LABELS

        message = f"Invalid node label '{label}'. Valid labels: {VALID_NODE_LABELS}"
        super().__init__(message)


class InvalidRelationshipTypeError(ValidationError):
    """Invalid relationship type."""

    def __init__(self, rel_type: str) -> None:
        self.rel_type = rel_type
        from apps.neo4j_database_controller.constants import VALID_REL_TYPES

        message = f"Invalid relationship type '{rel_type}'. Valid types: {VALID_REL_TYPES}"
        super().__init__(message)


class InvalidEntityTypeError(ValidationError):
    """Invalid entity type."""

    def __init__(self, entity_type: str) -> None:
        self.entity_type = entity_type
        from apps.neo4j_database_controller.constants import VALID_ENTITY_TYPES

        message = f"Invalid entity type '{entity_type}'. Valid types: {VALID_ENTITY_TYPES}"
        super().__init__(message)


class InvalidDirectionError(ValidationError):
    """Invalid relationship direction."""

    def __init__(self, direction: str) -> None:
        self.direction = direction
        from apps.neo4j_database_controller.constants import Direction

        valid_directions = [d.value for d in Direction]
        message = f"Invalid direction '{direction}'. Valid directions: {valid_directions}"
        super().__init__(message)


# =============================================================================
# Transaction Exceptions
# =============================================================================


class TransactionError(Neo4jError):
    """Transaction-related error."""

    def __init__(self, reason: str = "Unknown reason") -> None:
        self.reason = reason
        message = f"Transaction failed: {reason}"
        super().__init__(message)


class TransactionTimeoutError(TransactionError):
    """Transaction timed out."""

    def __init__(self, timeout: int = 60) -> None:
        self.timeout = timeout
        message = f"Transaction timed out after {timeout} seconds"
        super().__init__(message)


# =============================================================================
# Configuration Exceptions
# =============================================================================


class ConfigurationError(Neo4jError):
    """Invalid configuration."""

    def __init__(self, config_key: str, reason: str = "") -> None:
        self.config_key = config_key
        self.reason = reason
        reason_info = f": {reason}" if reason else ""
        message = f"Invalid configuration for '{config_key}'{reason_info}"
        super().__init__(message)


class MissingConfigurationError(ConfigurationError):
    """Required configuration is missing."""

    def __init__(self, config_key: str) -> None:
        message = f"Required configuration '{config_key}' is missing"
        super().__init__(config_key, message)
