"""
Custom exceptions for Milvus database controller.

This module defines all custom exception classes used throughout the
Milvus database controller module for proper error handling and propagation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# =============================================================================
# Base Exception
# =============================================================================


class MilvusError(Exception):
    """Base exception for all Milvus-related errors."""

    def __init__(self, message: str = "An error occurred in Milvus operation") -> None:
        self.message = message
        super().__init__(self.message)


# =============================================================================
# Connection Exceptions
# =============================================================================


class MilvusConnectionError(MilvusError):
    """Failed to establish connection to Milvus server."""

    def __init__(self, reason: str = "Unknown reason") -> None:
        self.reason = reason
        message = f"Failed to connect to Milvus server: {reason}"
        super().__init__(message)


class MilvusConnectionTimeoutError(MilvusConnectionError):
    """Connection to Milvus server timed out."""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        message = f"Connection to Milvus server timed out after {timeout} seconds"
        super().__init__(message)


# =============================================================================
# Collection Exceptions
# =============================================================================


class CollectionError(MilvusError):
    """Base exception for collection-related errors."""

    def __init__(self, collection_name: str, message: str) -> None:
        self.collection_name = collection_name
        super().__init__(message)


class CollectionNotFoundError(CollectionError):
    """Collection does not exist."""

    def __init__(self, collection_name: str) -> None:
        message = f"Collection '{collection_name}' not found"
        super().__init__(collection_name, message)


class CollectionAlreadyExistsError(CollectionError):
    """Collection already exists."""

    def __init__(self, collection_name: str) -> None:
        message = f"Collection '{collection_name}' already exists"
        super().__init__(collection_name, message)


class CollectionCreationError(CollectionError):
    """Failed to create collection."""

    def __init__(self, collection_name: str, reason: str = "Unknown reason") -> None:
        self.reason = reason
        message = f"Failed to create collection '{collection_name}': {reason}"
        super().__init__(collection_name, message)


class CollectionLoadError(CollectionError):
    """Failed to load collection into memory."""

    def __init__(self, collection_name: str, reason: str = "Unknown reason") -> None:
        self.reason = reason
        message = f"Failed to load collection '{collection_name}': {reason}"
        super().__init__(collection_name, message)


class CollectionReleaseError(CollectionError):
    """Failed to release collection from memory."""

    def __init__(self, collection_name: str, reason: str = "Unknown reason") -> None:
        self.reason = reason
        message = f"Failed to release collection '{collection_name}': {reason}"
        super().__init__(collection_name, message)


# =============================================================================
# Index Exceptions
# =============================================================================


class IndexError(MilvusError):
    """Base exception for index-related errors."""

    def __init__(self, index_name: str, message: str) -> None:
        self.index_name = index_name
        super().__init__(message)


class IndexCreationError(IndexError):
    """Failed to create index."""

    def __init__(self, index_name: str, reason: str = "Unknown reason") -> None:
        self.reason = reason
        message = f"Failed to create index '{index_name}': {reason}"
        super().__init__(index_name, message)


class IndexNotFoundError(IndexError):
    """Index does not exist."""

    def __init__(self, index_name: str, collection_name: str) -> None:
        self.collection_name = collection_name
        message = f"Index '{index_name}' not found in collection '{collection_name}'"
        super().__init__(index_name, message)


# =============================================================================
# Vector Exceptions
# =============================================================================


class VectorError(MilvusError):
    """Base exception for vector-related errors."""

    pass


class VectorInsertError(VectorError):
    """Failed to insert vectors."""

    def __init__(self, reason: str = "Unknown reason", count: int = 0) -> None:
        self.reason = reason
        self.count = count
        message = f"Failed to insert {count} vectors: {reason}"
        super().__init__(message)


class VectorUpsertError(VectorError):
    """Failed to upsert vectors."""

    def __init__(self, reason: str = "Unknown reason", count: int = 0) -> None:
        self.reason = reason
        self.count = count
        message = f"Failed to upsert {count} vectors: {reason}"
        super().__init__(message)


class VectorDeleteError(VectorError):
    """Failed to delete vectors."""

    def __init__(self, reason: str = "Unknown reason", count: int = 0) -> None:
        self.reason = reason
        self.count = count
        message = f"Failed to delete {count} vectors: {reason}"
        super().__init__(message)


class InvalidVectorDimensionError(VectorError):
    """Vector dimension mismatch."""

    def __init__(self, expected: int, actual: int, field_name: str = "") -> None:
        self.expected = expected
        self.actual = actual
        self.field_name = field_name
        field_info = f" for field '{field_name}'" if field_name else ""
        message = f"Invalid vector dimension{field_info}: expected {expected}, got {actual}"
        super().__init__(message)


class InvalidVectorDataError(VectorError):
    """Invalid vector data format."""

    def __init__(self, reason: str = "Invalid vector data format") -> None:
        self.reason = reason
        message = f"Invalid vector data: {reason}"
        super().__init__(message)


# =============================================================================
# Search Exceptions
# =============================================================================


class SearchError(MilvusError):
    """Failed to perform search operation."""

    def __init__(self, reason: str = "Unknown reason", collection_name: str = "") -> None:
        self.reason = reason
        self.collection_name = collection_name
        collection_info = f" in collection '{collection_name}'" if collection_name else ""
        message = f"Search operation failed{collection_info}: {reason}"
        super().__init__(message)


class HybridSearchError(SearchError):
    """Failed to perform hybrid search."""

    def __init__(self, reason: str = "Unknown reason", collection_name: str = "") -> None:
        message = f"Hybrid search failed: {reason}"
        super().__init__(reason, collection_name)


class InvalidFilterError(SearchError):
    """Invalid filter expression."""

    def __init__(self, filter_expr: str, reason: str = "Invalid syntax") -> None:
        self.filter_expr = filter_expr
        message = f"Invalid filter expression '{filter_expr}': {reason}"
        super().__init__(message)


class InvalidSearchParameterError(SearchError):
    """Invalid search parameter."""

    def __init__(self, param_name: str, param_value: str, reason: str = "") -> None:
        self.param_name = param_name
        self.param_value = param_value
        reason_info = f": {reason}" if reason else ""
        message = f"Invalid search parameter '{param_name}' with value '{param_value}'{reason_info}"
        super().__init__(message)


# =============================================================================
# Query Exceptions
# =============================================================================


class QueryError(MilvusError):
    """Failed to perform query operation."""

    def __init__(self, reason: str = "Unknown reason", collection_name: str = "") -> None:
        self.reason = reason
        self.collection_name = collection_name
        collection_info = f" in collection '{collection_name}'" if collection_name else ""
        message = f"Query operation failed{collection_info}: {reason}"
        super().__init__(message)


# =============================================================================
# Configuration Exceptions
# =============================================================================


class ConfigurationError(MilvusError):
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
