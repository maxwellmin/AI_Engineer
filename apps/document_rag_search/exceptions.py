"""
Custom exceptions for document RAG search module.

This module defines all custom exception classes used throughout the
document RAG search module for proper error handling and propagation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# =============================================================================
# Base Exception
# =============================================================================


class SearchError(Exception):
    """Base exception for all search-related errors.

    All exceptions in the search module inherit from this base class,
    allowing for consistent error handling across the application.

    Attributes:
        message: Human-readable error message.
    """

    def __init__(self, message: str = "An error occurred in search operation") -> None:
        self.message = message
        super().__init__(self.message)


# =============================================================================
# Query Exceptions
# =============================================================================


class InvalidQueryError(SearchError):
    """Invalid search query.

    Raised when the search query does not meet validation requirements.

    Attributes:
        reason: Detailed reason for the validation failure.
    """

    def __init__(self, reason: str = "") -> None:
        self.reason = reason
        message = f"Invalid query: {reason}" if reason else "Invalid query"
        super().__init__(message)


class EmptyQueryError(InvalidQueryError):
    """Empty search query.

    Raised when the search query is empty or contains only whitespace.
    """

    def __init__(self) -> None:
        super().__init__("Query cannot be empty")


class QueryTooLongError(InvalidQueryError):
    """Query exceeds maximum length.

    Raised when the search query exceeds the configured maximum length.

    Attributes:
        length: Actual length of the query.
        max_length: Maximum allowed length.
    """

    def __init__(self, length: int, max_length: int) -> None:
        self.length = length
        self.max_length = max_length
        super().__init__(f"Query too long: {length} chars (max: {max_length})")


class QueryTooShortError(InvalidQueryError):
    """Query is too short.

    Raised when the search query is shorter than the minimum required length.

    Attributes:
        length: Actual length of the query.
        min_length: Minimum required length.
    """

    def __init__(self, length: int, min_length: int) -> None:
        self.length = length
        self.min_length = min_length
        super().__init__(f"Query too short: {length} chars (min: {min_length})")


# =============================================================================
# Retriever Exceptions
# =============================================================================


class RetrieverError(SearchError):
    """Error during retrieval operation.

    Base exception for all retriever-related errors.

    Attributes:
        retriever_name: Name of the retriever that encountered the error.
        reason: Detailed reason for the error.
    """

    def __init__(self, retriever_name: str, reason: str = "") -> None:
        self.retriever_name = retriever_name
        self.reason = reason
        message = f"Retriever '{retriever_name}' failed: {reason}" if reason else f"Retriever '{retriever_name}' failed"
        super().__init__(message)


class VectorRetrieverError(RetrieverError):
    """Vector retriever error.

    Raised when the Milvus vector search operation fails.
    """

    def __init__(self, reason: str = "") -> None:
        super().__init__("vector", reason)


class KeywordRetrieverError(RetrieverError):
    """Keyword retriever error.

    Raised when the PostgreSQL full-text search operation fails.
    """

    def __init__(self, reason: str = "") -> None:
        super().__init__("keyword", reason)


class GraphRetrieverError(RetrieverError):
    """Graph retriever error.

    Raised when the Neo4j graph traversal operation fails.
    """

    def __init__(self, reason: str = "") -> None:
        super().__init__("graph", reason)


class RetrieverUnavailableError(RetrieverError):
    """Retriever is unavailable.

    Raised when a retriever cannot be initialized or is temporarily unavailable.
    """

    def __init__(self, retriever_name: str, reason: str = "") -> None:
        self.retriever_name = retriever_name
        super().__init__(retriever_name, f"unavailable: {reason}" if reason else "unavailable")


class RetrieverTimeoutError(RetrieverError):
    """Retriever operation timed out.

    Raised when a retriever operation exceeds the configured timeout.

    Attributes:
        timeout_seconds: The timeout duration in seconds.
    """

    def __init__(self, retriever_name: str, timeout_seconds: int = 10) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(retriever_name, f"operation timed out after {timeout_seconds}s")


# =============================================================================
# Fusion Exceptions
# =============================================================================


class FusionError(SearchError):
    """Error during result fusion.

    Raised when the RRF fusion or ranking operation fails.

    Attributes:
        reason: Detailed reason for the fusion failure.
    """

    def __init__(self, reason: str = "") -> None:
        self.reason = reason
        message = f"Fusion failed: {reason}" if reason else "Fusion failed"
        super().__init__(message)


class NoResultsError(SearchError):
    """No results found from any retriever.

    Raised when all retrievers return empty results and no fusion can be performed.
    """

    def __init__(self) -> None:
        super().__init__("No results found from any retriever")


class FusionConfigError(FusionError):
    """Invalid fusion configuration.

    Raised when the fusion configuration is invalid or incomplete.

    Attributes:
        config_key: The configuration key that is invalid.
    """

    def __init__(self, config_key: str, reason: str = "") -> None:
        self.config_key = config_key
        message = f"Invalid fusion config '{config_key}': {reason}" if reason else f"Invalid fusion config '{config_key}'"
        super().__init__(message)


# =============================================================================
# Filter Exceptions
# =============================================================================


class FilterError(SearchError):
    """Error in search filter.

    Base exception for filter-related errors.

    Attributes:
        filter_name: Name of the filter that caused the error.
        reason: Detailed reason for the error.
    """

    def __init__(self, filter_name: str, reason: str = "") -> None:
        self.filter_name = filter_name
        self.reason = reason
        message = f"Filter '{filter_name}' error: {reason}" if reason else f"Filter '{filter_name}' error"
        super().__init__(message)


class InvalidFilterValueError(FilterError):
    """Invalid filter value.

    Raised when a filter value does not meet validation requirements.
    """

    def __init__(self, filter_name: str, value: str, reason: str = "") -> None:
        self.value = value
        full_reason = f"invalid value '{value}': {reason}" if reason else f"invalid value '{value}'"
        super().__init__(filter_name, full_reason)


class InvalidDateRangeError(FilterError):
    """Invalid date range filter.

    Raised when date_from is after date_to in a date range filter.

    Attributes:
        date_from: The start date of the range.
        date_to: The end date of the range.
    """

    def __init__(self, date_from: str, date_to: str) -> None:
        self.date_from = date_from
        self.date_to = date_to
        super().__init__("date_range", f"date_from ({date_from}) must be before date_to ({date_to})")


# =============================================================================
# Service Exceptions
# =============================================================================


class SearchServiceError(SearchError):
    """Search service error.

    Raised when the search service encounters an unexpected error.
    """

    def __init__(self, operation: str, reason: str = "") -> None:
        self.operation = operation
        self.reason = reason
        message = f"Search service error during {operation}: {reason}" if reason else f"Search service error during {operation}"
        super().__init__(message)


class SearchConfigError(SearchError):
    """Search configuration error.

    Raised when the search configuration is missing or invalid.

    Attributes:
        config_key: The configuration key that is missing or invalid.
    """

    def __init__(self, config_key: str, reason: str = "") -> None:
        self.config_key = config_key
        message = f"Missing or invalid search config '{config_key}': {reason}" if reason else f"Missing or invalid search config '{config_key}'"
        super().__init__(message)
