"""
Custom exceptions for embedding engine.

This module defines all custom exception classes used throughout the
embedding engine module for proper error handling and propagation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# =============================================================================
# Base Exception
# =============================================================================


class EmbeddingError(Exception):
    """Base exception for all embedding-related errors."""

    def __init__(self, message: str = "An error occurred in embedding operation") -> None:
        self.message = message
        super().__init__(self.message)


# =============================================================================
# Connection Exceptions
# =============================================================================


class EmbeddingConnectionError(EmbeddingError):
    """Failed to connect to embedding API."""

    def __init__(self, reason: str = "Unknown reason") -> None:
        self.reason = reason
        message = f"Failed to connect to embedding API: {reason}"
        super().__init__(message)


class EmbeddingTimeoutError(EmbeddingError):
    """Embedding request timed out."""

    def __init__(self, timeout: float = 60.0) -> None:
        self.timeout = timeout
        message = f"Embedding request timed out after {timeout} seconds"
        super().__init__(message)


# =============================================================================
# API Exceptions
# =============================================================================


class EmbeddingAPIError(EmbeddingError):
    """Error from embedding API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class EmbeddingRateLimitError(EmbeddingAPIError):
    """Rate limit exceeded."""

    def __init__(self, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        message = (
            f"Rate limit exceeded. Retry after {retry_after}s"
            if retry_after
            else "Rate limit exceeded"
        )
        super().__init__(message, status_code=429)


class EmbeddingInvalidResponseError(EmbeddingAPIError):
    """Invalid response from embedding API."""

    def __init__(self, reason: str = "Invalid response format") -> None:
        self.reason = reason
        message = f"Invalid response from embedding API: {reason}"
        super().__init__(message)


class EmbeddingServiceUnavailableError(EmbeddingAPIError):
    """Embedding service is temporarily unavailable."""

    def __init__(self, reason: str = "Service unavailable") -> None:
        self.reason = reason
        message = f"Embedding service unavailable: {reason}"
        super().__init__(message, status_code=503)


# =============================================================================
# Input Validation Exceptions
# =============================================================================


class EmbeddingInvalidInputError(EmbeddingError):
    """Invalid input for embedding."""

    def __init__(self, message: str, input_text: str | None = None) -> None:
        self.input_text = input_text
        super().__init__(message)


class EmbeddingEmptyInputError(EmbeddingInvalidInputError):
    """Empty input text for embedding."""

    def __init__(self) -> None:
        super().__init__("Input text cannot be empty")


class EmbeddingInputTooLongError(EmbeddingInvalidInputError):
    """Input text exceeds maximum token limit."""

    def __init__(self, token_count: int, max_tokens: int) -> None:
        self.token_count = token_count
        self.max_tokens = max_tokens
        message = f"Input text too long: {token_count} tokens (max: {max_tokens})"
        super().__init__(message)


class EmbeddingBatchSizeError(EmbeddingInvalidInputError):
    """Batch size exceeds maximum allowed."""

    def __init__(self, batch_size: int, max_batch_size: int) -> None:
        self.batch_size = batch_size
        self.max_batch_size = max_batch_size
        message = f"Batch size {batch_size} exceeds maximum {max_batch_size}"
        super().__init__(message)


# =============================================================================
# Dimension Exceptions
# =============================================================================


class EmbeddingDimensionError(EmbeddingError):
    """Embedding dimension mismatch."""

    def __init__(self, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        message = f"Embedding dimension mismatch: expected {expected}, got {actual}"
        super().__init__(message)


# =============================================================================
# Configuration Exceptions
# =============================================================================


class EmbeddingConfigError(EmbeddingError):
    """Configuration error for embedding."""

    def __init__(self, config_key: str, reason: str = "") -> None:
        self.config_key = config_key
        self.reason = reason
        reason_info = f": {reason}" if reason else ""
        message = f"Invalid configuration for '{config_key}'{reason_info}"
        super().__init__(message)


class MissingAPIKeyError(EmbeddingConfigError):
    """Required API key is missing."""

    def __init__(self) -> None:
        super().__init__("QWEN_API_KEY", "API key is required for Qwen embedding")


class UnsupportedModelError(EmbeddingConfigError):
    """Unsupported embedding model."""

    def __init__(self, model: str) -> None:
        self.model = model
        super().__init__("model", f"Unsupported embedding model: {model}")


# =============================================================================
# Processing Exceptions
# =============================================================================


class EmbeddingProcessingError(EmbeddingError):
    """Error during embedding processing."""

    def __init__(self, reason: str = "Unknown reason", batch_index: int | None = None) -> None:
        self.reason = reason
        self.batch_index = batch_index
        batch_info = f" at batch index {batch_index}" if batch_index is not None else ""
        message = f"Embedding processing error{batch_info}: {reason}"
        super().__init__(message)


class EmbeddingPartialFailureError(EmbeddingProcessingError):
    """Partial failure in batch embedding."""

    def __init__(
        self,
        success_count: int,
        failed_count: int,
        failed_indices: list[int] | None = None,
    ) -> None:
        self.success_count = success_count
        self.failed_count = failed_count
        self.failed_indices = failed_indices or []
        message = (
            f"Partial batch failure: {success_count} succeeded, {failed_count} failed. "
            f"Failed indices: {failed_indices}"
        )
        super().__init__(message)
