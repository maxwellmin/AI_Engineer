"""
Constants for embedding engine.

This module defines all constant values used across the embedding engine,
including embedding models, dimensions, task types, and configuration defaults.
"""

from __future__ import annotations

from enum import Enum


# =============================================================================
# Embedding Models
# =============================================================================


class EmbeddingModel(str, Enum):
    """Supported embedding models."""

    QWEN_V1 = "text-embedding-v1"
    QWEN_V3 = "text-embedding-v3"


class EmbeddingDimension:
    """Embedding dimensions for each model."""

    QWEN_V1 = 1536
    QWEN_V3 = 1024


# =============================================================================
# Task Types (Qwen-specific)
# =============================================================================


class TaskType(str, Enum):
    """Task types for embedding (Qwen API specific).

    The task_type parameter helps the model generate better embeddings
    for specific use cases:
    - DOCUMENT: For documents to be stored in vector database
    - QUERY: For search queries to match against stored documents
    """

    DOCUMENT = "retrieval.document"
    QUERY = "retrieval.query"


# =============================================================================
# Provider Types
# =============================================================================


class ProviderType(str, Enum):
    """Embedding provider types."""

    QWEN = "qwen"
    MOCK = "mock"


# =============================================================================
# Default Values
# =============================================================================

DEFAULT_MODEL = EmbeddingModel.QWEN_V1.value
DEFAULT_DIMENSION = EmbeddingDimension.QWEN_V1
DEFAULT_BATCH_SIZE = 20
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 2.0
MAX_TOKENS_PER_REQUEST = 8000
DEFAULT_CACHE_TTL = 3600  # 1 hour
DEFAULT_CACHE_MAX_SIZE = 1000

# Valid dimensions for validation
VALID_DIMENSIONS: list[int] = [
    EmbeddingDimension.QWEN_V1,
    EmbeddingDimension.QWEN_V3,
]


# =============================================================================
# API Configuration
# =============================================================================

QWEN_EMBEDDING_API_PATH = "/embeddings"
QWEN_API_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


# =============================================================================
# Error Messages
# =============================================================================

ERROR_EMPTY_INPUT = "Input text cannot be empty"
ERROR_INPUT_TOO_LONG = "Input text too long: {token_count} tokens (max: {max_tokens})"
ERROR_INVALID_DIMENSION = "Invalid embedding dimension: expected {expected}, got {actual}"
ERROR_API_REQUEST_FAILED = "API request failed: {reason}"
ERROR_RATE_LIMIT_EXCEEDED = "Rate limit exceeded. Retry after {retry_after}s"
ERROR_INVALID_RESPONSE = "Invalid response from embedding API: {reason}"
ERROR_MISSING_API_KEY = "API key is required for Qwen embedding"
ERROR_INVALID_CONFIG = "Invalid configuration for '{config_key}': {reason}"
ERROR_UNSUPPORTED_MODEL = "Unsupported embedding model: {model}"
