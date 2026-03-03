# Phase 8: Embedding Engine Implementation Plan

## Overview

Implement embedding engine module for melon RAG project, providing text vectorization functionality for dense embeddings (via Qwen API) and supporting the multi-vector schema (summary_dense + text_dense) used in Milvus database controller.

## Status: Ready for Implementation

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Phase 2: Basic Setup | ✅ Completed | Django project structure ready |
| Phase 3: User Management Module | ✅ Completed | Authentication available |
| Phase 6: Milvus Database Controller | ✅ Completed | Vector storage ready, multi-vector schema defined |
| Phase 4: Document Parser | ✅ Completed | Text chunking ready |
| Phase 5: Object Storage Controller | ✅ Completed | File storage ready |

**Key Integration Points:**
- `MilvusService` expects vectors with `summary_dense` and `text_dense` fields
- BM25 sparse embedding handled by Milvus built-in function (no implementation needed)
- Vector dimension must match Milvus schema: 1536 (Qwen text-embedding-v1)

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Dense Embedding Provider | Qwen API (text-embedding-v1) | Project standard, 1536 dimensions, matches Milvus schema |
| Sparse Embedding Strategy | Milvus Built-in BM25 | Already implemented in Phase 6, no additional work needed |
| Embedding Interface | Service Layer Pattern | Matches MilvusService architecture, clean API for other modules |
| HTTP Client | httpx | Modern async-capable HTTP client |
| Retry Logic | tenacity | Industry standard for retry with exponential backoff |
| Error Handling | Custom Exception Hierarchy | Matches MilvusController pattern |
| Mock Mode | Supported | Enable development without API access |
| API Endpoints | Minimal (health + single embed) | Primary use via service layer, not HTTP API |

---

## Architecture Design

### Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    External Modules                          │
│  (documents_parser, milvus_database_controller, rag_process) │
└─────────────────────────┬───────────────────────────────────┘
                          │ Service Layer Import
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    EmbeddingService (Facade)                 │
│  - High-level API for all embedding operations              │
│  - Batch processing support                                  │
│  - Dimension validation                                      │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
┌──────────────────────┐      ┌──────────────────────┐
│   QwenEmbedding      │      │   MockEmbedding      │
│     Client           │      │     Client           │
│  (dashscope API)     │      │  (deterministic)     │
└──────────┬───────────┘      └──────────┬───────────┘
           │                              │
           ▼                              ▼
┌──────────────────────┐      ┌──────────────────────┐
│    Qwen API          │      │   numpy random       │
│  (dashscope)         │      │   (seeded by hash)   │
└──────────────────────┘      └──────────────────────┘
```

### Embedding Types

| Type | Field Name | Provider | Dimension | Usage |
|------|------------|----------|-----------|-------|
| Dense (Summary) | `summary_dense` | Qwen API | 1536 | Question/summary semantic search |
| Dense (Text) | `text_dense` | Qwen API | 1536 | Full text semantic search |
| Sparse (BM25) | `text_sparse` | Milvus Built-in | Variable | Keyword matching (Phase 6) |

> **Note**: BM25 sparse embedding is handled by Milvus Function in Phase 6. No implementation needed in embedding_engine.

---

## File Structure (Aligned with MilvusController Pattern)

```
apps/embedding_engine/
├── __init__.py                 # App config
├── apps.py                     # Django AppConfig
├── constants.py                # Model names, dimensions, defaults (Enum + constants)
├── exceptions.py               # Custom exceptions (hierarchy matching MilvusController)
├── dto.py                      # Data Transfer Objects (frozen dataclasses)
├── models.py                   # Empty (no DB models needed)
├── serializers.py              # DRF serializers for API
├── urls.py                     # URL routing
│
├── clients/
│   ├── __init__.py
│   ├── base.py                 # BaseEmbeddingClient (ABC)
│   ├── qwen_client.py          # QwenEmbeddingClient (httpx + tenacity)
│   └── mock_client.py          # MockEmbeddingClient (deterministic)
│
├── services/
│   ├── __init__.py
│   └── embedding_service.py    # EmbeddingService facade
│
├── views/
│   ├── __init__.py
│   └── embedding_views.py      # Health + embed endpoints (minimal API)
│
└── tests/
    ├── __init__.py
    ├── conftest.py             # Pytest fixtures (matching MilvusController pattern)
    ├── test_qwen_client.py     # Client unit tests
    ├── test_mock_client.py     # Mock client tests
    ├── test_embedding_service.py # Service tests
    └── test_api_views.py       # API integration tests
```

---

## Constants Design (Aligned with MilvusController Pattern)

```python
# constants.py
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
    """Task types for embedding (Qwen API specific)."""

    DOCUMENT = "retrieval.document"  # For documents to be stored
    QUERY = "retrieval.query"  # For search queries


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
VALID_DIMENSIONS = [EmbeddingDimension.QWEN_V1, EmbeddingDimension.QWEN_V3]
```

---

## Exception Design (Aligned with MilvusController Pattern)

```python
# exceptions.py
from __future__ import annotations


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
```

---

## DTO Design (Aligned with MilvusController Pattern)

```python
# dto.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# =============================================================================
# Request DTOs
# =============================================================================


@dataclass(frozen=True)
class EmbedTextRequest:
    """Request to embed a single text.

    Attributes:
        text: Text content to embed.
        model: Embedding model name.
        task_type: Task type (document or query).
    """

    text: str
    model: str = "text-embedding-v1"
    task_type: str = "retrieval.document"


@dataclass(frozen=True)
class EmbedTextsRequest:
    """Request to embed multiple texts.

    Attributes:
        texts: List of text contents to embed.
        model: Embedding model name.
        task_type: Task type (document or query).
        batch_size: Number of texts per API call.
    """

    texts: list[str]
    model: str = "text-embedding-v1"
    task_type: str = "retrieval.document"
    batch_size: int = 20


@dataclass(frozen=True)
class EmbedForStorageRequest:
    """Request to embed document chunks for Milvus storage.

    Attributes:
        chunks: List of chunk dictionaries with 'text' and 'summary' fields.
        model: Embedding model name.
    """

    chunks: list[dict[str, Any]]  # Each chunk: {text, summary, chunk_id, ...}
    model: str = "text-embedding-v1"


# =============================================================================
# Response DTOs
# =============================================================================


@dataclass(frozen=True)
class EmbeddingResult:
    """Result of a single embedding operation.

    Attributes:
        embedding: Dense vector (shape: dimension,).
        dimension: Vector dimension.
        model: Model used for embedding.
        tokens_used: Number of tokens consumed.
    """

    embedding: list[float]
    dimension: int
    model: str
    tokens_used: int


@dataclass(frozen=True)
class BatchEmbeddingResult:
    """Result of a batch embedding operation.

    Attributes:
        embeddings: List of dense vectors.
        dimension: Vector dimension.
        model: Model used for embedding.
        total_tokens: Total tokens consumed.
        success_count: Number of successful embeddings.
        failed_count: Number of failed embeddings.
    """

    embeddings: list[list[float]]
    dimension: int
    model: str
    total_tokens: int
    success_count: int
    failed_count: int = 0


@dataclass(frozen=True)
class StorageEmbeddingResult:
    """Result of embedding document chunks for storage.

    Attributes:
        chunks: List of chunks with added 'summary_dense' and 'text_dense' fields.
        total_tokens: Total tokens consumed.
        success_count: Number of successfully embedded chunks.
        failed_count: Number of failed chunks.
    """

    chunks: list[dict[str, Any]]
    total_tokens: int
    success_count: int
    failed_count: int = 0
```

---

## Client Interface Design

```python
# clients/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from apps.embedding_engine.dto import BatchEmbeddingResult, EmbeddingResult


class BaseEmbeddingClient(ABC):
    """Abstract base class for embedding clients."""

    @abstractmethod
    def embed(
        self,
        texts: list[str],
        model: str | None = None,
        **kwargs: Any,
    ) -> BatchEmbeddingResult:
        """Embed a list of texts.

        Args:
            texts: List of text strings to embed.
            model: Optional model override.
            **kwargs: Additional provider-specific parameters.

        Returns:
            BatchEmbeddingResult with embeddings.
        """
        ...

    @abstractmethod
    def embed_single(
        self,
        text: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResult:
        """Embed a single text.

        Args:
            text: Text string to embed.
            model: Optional model override.
            **kwargs: Additional provider-specific parameters.

        Returns:
            EmbeddingResult with embedding.
        """
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        ...

    @property
    @abstractmethod
    def model(self) -> str:
        """Return the default model name."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the embedding service is healthy."""
        ...
```

---

## EmbeddingService Interface Design

```python
# services/embedding_service.py
from __future__ import annotations

from typing import Any

from apps.embedding_engine.dto import (
    BatchEmbeddingResult,
    EmbedForStorageRequest,
    EmbedTextRequest,
    EmbedTextsRequest,
    EmbeddingResult,
    StorageEmbeddingResult,
)


class EmbeddingService:
    """High-level facade service for embedding operations.

    This service provides a unified interface for all embedding operations,
    coordinating between different embedding providers (Qwen, Mock).

    Example:
        >>> service = EmbeddingService()
        >>> # Embed single text
        >>> result = service.embed_text("Hello world")
        >>> # Embed for Milvus storage
        >>> result = service.embed_for_storage(chunks)
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize with optional config override.

        Args:
            config: Optional configuration override.
        """
        ...

    # =========================================================================
    # Core Embedding Methods
    # =========================================================================

    def embed_text(
        self,
        text: str,
        task_type: str = "retrieval.document",
    ) -> EmbeddingResult:
        """Embed a single text.

        Args:
            text: Text to embed.
            task_type: Task type (document or query).

        Returns:
            EmbeddingResult with embedding vector.
        """
        ...

    def embed_texts(
        self,
        texts: list[str],
        task_type: str = "retrieval.document",
        batch_size: int = 20,
    ) -> BatchEmbeddingResult:
        """Embed multiple texts in batch.

        Args:
            texts: List of texts to embed.
            task_type: Task type (document or query).
            batch_size: Number of texts per API call.

        Returns:
            BatchEmbeddingResult with all embeddings.
        """
        ...

    def embed_query(self, query: str) -> EmbeddingResult:
        """Embed a search query (optimized for retrieval).

        Args:
            query: Query text.

        Returns:
            EmbeddingResult with query embedding.
        """
        ...

    # =========================================================================
    # Storage-Oriented Methods
    # =========================================================================

    def embed_for_storage(
        self,
        request: EmbedForStorageRequest,
    ) -> StorageEmbeddingResult:
        """Embed document chunks for Milvus storage.

        This method generates both summary_dense and text_dense embeddings
        for each chunk, matching the Milvus multi-vector schema.

        Args:
            request: EmbedForStorageRequest with chunks.

        Returns:
            StorageEmbeddingResult with chunks containing embeddings.
        """
        ...

    # =========================================================================
    # Utility Methods
    # =========================================================================

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        ...

    def health_check(self) -> dict[str, Any]:
        """Check embedding service health.

        Returns:
            Dictionary with health status.
        """
        ...

    def get_supported_models(self) -> list[str]:
        """Return list of supported embedding models."""
        ...
```

---

## Configuration Design

### Settings (base.py) - Add after QWEN_CONFIG

```python
# =============================================================================
# Embedding Configuration
# =============================================================================

USE_MOCK_EMBEDDING = os.environ.get("USE_MOCK_EMBEDDING", "false").lower() == "true"

EMBEDDING_CONFIG = {
    # Provider settings
    "use_mock": USE_MOCK_EMBEDDING,
    # Qwen API settings (reuse from QWEN_CONFIG)
    "api_key": QWEN_API_KEY,
    "base_url": QWEN_BASE_URL,
    "model": QWEN_EMBEDDING_MODEL,
    # Embedding settings
    "dimension": QWEN_CONFIG["embedding_dimension"],  # 1536
    "max_batch_size": 20,
    "max_tokens_per_request": 8000,
    # Retry settings
    "retry": {
        "max_attempts": 3,
        "backoff_factor": 2.0,
        "max_backoff": 60.0,
    },
    # Timeout settings
    "timeout": {
        "connect": 10.0,
        "read": 60.0,
    },
    # Cache settings (optional)
    "cache": {
        "enabled": False,  # Disable by default, enable in production
        "ttl": 3600,  # 1 hour
        "max_size": 1000,
    },
}
```

### Environment Variables (.env.local)

```bash
# Embedding Configuration
USE_MOCK_EMBEDDING=false  # Set to true for development without API

# Qwen API (already exists, reused for embedding)
QWEN_API_KEY=your-api-key-here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_EMBEDDING_MODEL=text-embedding-v1
```

---

## Integration with Other Modules

### documents_parser Integration

```python
# In documents_parser, after chunking:
from apps.embedding_engine.services import EmbeddingService
from apps.embedding_engine.dto import EmbedForStorageRequest

embedding_service = EmbeddingService()


def process_document_chunks(document_id: str, chunks: list[dict]) -> list[dict]:
    """Process and embed document chunks."""
    request = EmbedForStorageRequest(chunks=chunks)
    result = embedding_service.embed_for_storage(request)

    # result.chunks now contains summary_dense and text_dense
    return result.chunks
```

### milvus_database_controller Integration

```python
# In milvus_database_controller, for hybrid search:
from apps.embedding_engine.services import EmbeddingService

embedding_service = EmbeddingService()


def prepare_query_vectors(query: str) -> dict[str, list[float]]:
    """Prepare query vectors for hybrid search."""
    result = embedding_service.embed_query(query)

    # For hybrid search, use same embedding for both fields
    return {
        "summary_dense": result.embedding,
        "text_dense": result.embedding,
    }
```

### rag_processing Integration

```python
# In rag_processing, for query embedding:
from apps.embedding_engine.services import EmbeddingService

embedding_service = EmbeddingService()


def embed_search_query(query: str) -> list[float]:
    """Embed a search query for vector search."""
    result = embedding_service.embed_query(query)
    return result.embedding
```

---

## API Endpoints (Minimal)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/embedding/health/` | GET | Health check (authenticated) |
| `/api/v1/embedding/embed/` | POST | Single text embedding (authenticated, optional) |

> **Note**: Primary usage is via service layer import, not HTTP API. API endpoints are provided for testing and monitoring only.

---

## Submodule Breakdown

### Submodule 8.1: Infrastructure Setup ✅ COMPLETED

**Goal**: Establish foundation for embedding operations

| # | Task | Description | Acceptance Criteria | Status |
|---|------|-------------|---------------------|--------|
| 1.1 | Update constants.py | Create constants with Enum + value pattern | All constants defined, matches MilvusController pattern | ✅ Done |
| 1.2 | Create exceptions.py | Create exception hierarchy | All exception types defined, inherit from EmbeddingError | ✅ Done |
| 1.3 | Create dto.py | Create frozen dataclass DTOs | All request/response DTOs defined, frozen=True | ✅ Done |
| 1.4 | Update settings | Add EMBEDDING_CONFIG to base.py | Configuration added, uses QWEN_CONFIG values | ✅ Done |
| 1.5 | Update environment | Add USE_MOCK_EMBEDDING to .env.local | Environment variable documented | ✅ Done |

**Dependencies**: None

### Submodule 8.2: Embedding Clients ✅ COMPLETED

**Goal**: Implement embedding client interfaces

| # | Task | Description | Acceptance Criteria | Status |
|---|------|-------------|---------------------|--------|
| 2.1 | Create base.py | Abstract BaseEmbeddingClient | Interface defined with all abstract methods | ✅ Done |
| 2.2 | Create qwen_client.py | QwenEmbeddingClient with httpx | embed() and embed_single() implemented, retry with tenacity | ✅ Done |
| 2.3 | Implement error handling | Handle API errors, rate limits, timeouts | All error types properly raised | ✅ Done |
| 2.4 | Create mock_client.py | MockEmbeddingClient | Deterministic embeddings, matches dimension | ✅ Done |
| 2.5 | Create client factory | get_embedding_client() function | Returns correct client based on config | ✅ Done |

**Dependencies**: Submodule 8.1

### Submodule 8.3: Embedding Service Layer ✅ COMPLETED

**Goal**: Provide unified service interface

| # | Task | Description | Acceptance Criteria | Status |
|---|------|-------------|---------------------|--------|
| 3.1 | Create embedding_service.py | EmbeddingService facade class | All methods implemented | ✅ Done |
| 3.2 | Implement embed_text | Single text embedding | Validates input, returns EmbeddingResult | ✅ Done |
| 3.3 | Implement embed_texts | Batch text embedding | Handles batching, returns BatchEmbeddingResult | ✅ Done |
| 3.4 | Implement embed_query | Query embedding helper | Uses task_type="retrieval.query" | ✅ Done |
| 3.5 | Implement embed_for_storage | Chunk embedding for Milvus | Generates summary_dense and text_dense | ✅ Done |
| 3.6 | Implement health_check | Service health check | Returns status dict | ✅ Done |

**Dependencies**: Submodule 8.2

### Submodule 8.4: API Endpoints (Minimal) ✅ COMPLETED

**Goal**: Provide minimal HTTP API for testing

| # | Task | Description | Acceptance Criteria | Status |
|---|------|-------------|---------------------|--------|
| 4.1 | Create serializers.py | DRF serializers | HealthCheckSerializer, EmbedSerializer | ✅ Done |
| 4.2 | Create embedding_views.py | Health + embed endpoints | IsAuthenticated, drf_yasg docs | ✅ Done |
| 4.3 | Create urls.py | URL routing | Endpoints registered | ✅ Done |

**Dependencies**: Submodule 8.3

### Submodule 8.5: Testing ✅ COMPLETED

**Goal**: Comprehensive test coverage (80%+)

| # | Task | Description | Acceptance Criteria | Status |
|---|------|-------------|---------------------|--------|
| 5.1 | Create conftest.py | Pytest fixtures | Fixtures match MilvusController pattern | ✅ Done |
| 5.2 | Write test_mock_client.py | Mock client tests | 100% coverage of MockEmbeddingClient | ✅ Done |
| 5.3 | Write test_qwen_client.py | Qwen client tests with mocks | All methods tested, error scenarios covered | ✅ Done |
| 5.4 | Write test_embedding_service.py | Service layer tests | All public methods tested | ✅ Done |
| 5.5 | Write test_api_views.py | API endpoint tests | Auth required, responses correct | ✅ Done |
| 5.6 | Verify coverage | Run pytest --cov | 80%+ coverage achieved | ✅ Done (79.71%) |

**Dependencies**: Submodule 8.4

---

## Test Strategy

### Test Categories

| Category | Marker | Description |
|----------|--------|-------------|
| Unit Tests | `@pytest.mark.unit` | Mock API responses, test logic |
| Integration Tests | `@pytest.mark.integration` | Real API calls (requires API key) |

### Test Fixtures (Aligned with MilvusController)

```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock, patch

from apps.embedding_engine.clients.qwen_client import QwenEmbeddingClient
from apps.embedding_engine.clients.mock_client import MockEmbeddingClient
from apps.embedding_engine.services.embedding_service import EmbeddingService


@pytest.fixture
def mock_embedding_response():
    """Mock API response for embedding."""
    import random

    return {
        "object": "list",
        "data": [
            {
                "object": "embedding",
                "index": i,
                "embedding": [random.random() for _ in range(1536)],
            }
            for i in range(3)
        ],
        "model": "text-embedding-v1",
        "usage": {"prompt_tokens": 30, "total_tokens": 30},
    }


@pytest.fixture
def mock_qwen_client(mock_embedding_response):
    """Mock Qwen client for testing."""
    client = MagicMock(spec=QwenEmbeddingClient)
    client.embed.return_value = mock_embedding_response
    client.dimension = 1536
    client.model = "text-embedding-v1"
    return client


@pytest.fixture
def mock_client():
    """Real mock client for deterministic testing."""
    return MockEmbeddingClient(dimension=1536)


@pytest.fixture
def embedding_service_with_mock(mock_client):
    """Embedding service with mock client."""
    with patch(
        "apps.embedding_engine.services.embedding_service.get_embedding_client",
        return_value=mock_client,
    ):
        yield EmbeddingService(config={"use_mock": True})


@pytest.fixture
def sample_texts():
    """Sample texts for embedding tests."""
    return [
        "This is a test document for embedding.",
        "Another sample text for batch processing.",
        "Machine learning is a subset of artificial intelligence.",
    ]
```

### Test Commands

```bash
# Run all embedding engine tests
pytest apps/embedding_engine/tests/ -v

# Run with coverage
pytest apps/embedding_engine/tests/ --cov=apps/embedding_engine --cov-report=term-missing

# Run only unit tests (mock)
pytest apps/embedding_engine/tests/ -v -m "not integration"

# Run integration tests (requires API key)
pytest apps/embedding_engine/tests/ -v -m integration

# Run with Django settings
DJANGO_SETTINGS_MODULE=config.settings.local pytest apps/embedding_engine/tests/ -v
```

---

## Dependencies

```toml
# pyproject.toml - Already present or add:
[tool.poetry.dependencies]
httpx = "^0.27"          # HTTP client for API calls (may already exist)
tenacity = "^8.2"        # Retry logic (may already exist)
numpy = "^1.26"          # Vector operations (may already exist)

# No additional dependencies needed if above already present
```

---

## Acceptance Criteria

- [ ] QwenEmbeddingClient with retry and error handling
- [ ] MockEmbeddingClient for development/testing (deterministic)
- [ ] EmbeddingService with clean API matching MilvusService pattern
- [ ] Single text embedding support (embed_text, embed_query)
- [ ] Batch text embedding support (embed_texts)
- [ ] Storage embedding support (embed_for_storage with summary_dense, text_dense)
- [ ] Rate limit handling with tenacity retry
- [ ] Timeout handling with httpx
- [ ] All constants use Enum pattern
- [ ] All exceptions inherit from EmbeddingError
- [ ] All DTOs are frozen dataclasses
- [ ] API endpoints use IsAuthenticated permission
- [ ] API documented with drf_yasg
- [ ] Test coverage >= 80%
- [ ] conftest.py matches MilvusController pattern

---

## Risks & Considerations

| Risk | Mitigation |
|------|------------|
| API Rate Limits | Implement retry with exponential backoff (tenacity) |
| Token Limits | Validate input length, chunk large texts |
| Cost Management | Consider caching for repeated queries (optional) |
| Latency | Batch processing for efficiency |
| Mock Mode | Deterministic embeddings for reproducible tests |
| Dimension Consistency | Validate 1536 dimensions to match Milvus schema |

---

## Execution Order

Recommended execution order:

```
Phase 8.1 (Infrastructure)
    │
    ├── 1.1 constants.py
    ├── 1.2 exceptions.py
    ├── 1.3 dto.py
    ├── 1.4 Update settings
    └── 1.5 Update environment
    │
    ▼
Phase 8.2 (Clients)
    │
    ├── 2.1 base.py (interface)
    ├── 2.2 qwen_client.py
    ├── 2.3 error handling
    ├── 2.4 mock_client.py
    └── 2.5 client factory
    │
    ▼
Phase 8.3 (Service)
    │
    ├── 3.1 embedding_service.py (skeleton)
    ├── 3.2 embed_text
    ├── 3.3 embed_texts
    ├── 3.4 embed_query
    ├── 3.5 embed_for_storage
    └── 3.6 health_check
    │
    ▼
Phase 8.4 (API)
    │
    ├── 4.1 serializers.py
    ├── 4.2 embedding_views.py
    └── 4.3 urls.py
    │
    ▼
Phase 8.5 (Testing)
    │
    ├── 5.1 conftest.py
    ├── 5.2 test_mock_client.py
    ├── 5.3 test_qwen_client.py
    ├── 5.4 test_embedding_service.py
    ├── 5.5 test_api_views.py
    └── 5.6 Verify coverage
```

---

## Files to Create/Modify

### New Files

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `apps/embedding_engine/constants.py` | Model names, dimensions, defaults | 80 |
| `apps/embedding_engine/exceptions.py` | Custom exceptions | 100 |
| `apps/embedding_engine/dto.py` | Data transfer objects | 120 |
| `apps/embedding_engine/serializers.py` | DRF serializers | 60 |
| `apps/embedding_engine/urls.py` | URL routing | 20 |
| `apps/embedding_engine/clients/__init__.py` | Clients module init | 15 |
| `apps/embedding_engine/clients/base.py` | Base client interface | 50 |
| `apps/embedding_engine/clients/qwen_client.py` | Qwen API client | 150 |
| `apps/embedding_engine/clients/mock_client.py` | Mock client | 80 |
| `apps/embedding_engine/services/__init__.py` | Services module init | 10 |
| `apps/embedding_engine/services/embedding_service.py` | Facade service | 200 |
| `apps/embedding_engine/views/__init__.py` | Views module init | 10 |
| `apps/embedding_engine/views/embedding_views.py` | API endpoints | 80 |
| `apps/embedding_engine/tests/__init__.py` | Tests module init | 5 |
| `apps/embedding_engine/tests/conftest.py` | Test fixtures | 100 |
| `apps/embedding_engine/tests/test_mock_client.py` | Mock client tests | 80 |
| `apps/embedding_engine/tests/test_qwen_client.py` | Qwen client tests | 150 |
| `apps/embedding_engine/tests/test_embedding_service.py` | Service tests | 200 |
| `apps/embedding_engine/tests/test_api_views.py` | API tests | 100 |

### Modified Files

| File | Changes |
|------|---------|
| `config/settings/base.py` | Add EMBEDDING_CONFIG |
| `env/.env.local` | Add USE_MOCK_EMBEDDING variable |
| `apps/embedding_engine/__init__.py` | Update with default config |

---

## Summary

Phase 8 implements the embedding engine module following the established patterns from Phase 6 (Milvus Database Controller):

1. **Architecture Alignment**: Follows the same layer architecture (Client → Service → API)
2. **Code Style Consistency**: Uses Enum for constants, frozen dataclasses for DTOs, exception hierarchy
3. **Integration Ready**: Generates embeddings matching Milvus multi-vector schema
4. **Testing Strategy**: Matches MilvusController test patterns with conftest.py and pytest markers

**Total Estimated Time**: ~25-30 hours

---

*Updated: 2026-02-27*
*Plan for Phase 8: Embedding Engine*
*Aligned with Phase 6: Milvus Database Controller patterns*
