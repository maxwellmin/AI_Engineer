# Phase 6: Milvus Database Controller Implementation Plan

## Overview

Implement Milvus database controller module for melon RAG project, providing vector database operations including collection management, vector CRUD, and search functionality.

## Status: Completed ✅

> **Note**: All submodules (6.1-6.7) completed successfully.

## Dependencies

- Phase 2: Basic Setup ✅
- Phase 3: User Management Module ✅
- Phase 4: Document Parser Module ✅
- Phase 5: Object Storage Controller ✅

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Milvus SDK | pymilvus (MilvusClient) | Official Python SDK, high-level API |
| BM25 Strategy | Milvus Built-in Function | Simpler than self-managed vocabulary |
| Vector Fields | Multi-vector design | summary_dense + text_dense + text_sparse |
| Index Type | HNSW | High performance for vector search |
| Metric Type | COSINE | Consistent with embedding model |

---

## Architecture Design

### Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    External Modules                          │
│  (documents_parser, embedding_engine, rag_processing)       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    MilvusService (Facade)                    │
│  - High-level API for all Milvus operations                 │
│  - Business logic coordination                               │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┬───────────────┐
          ▼               ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Collection   │ │    Index     │ │    Vector    │ │   Search     │
│   Manager    │ │   Manager    │ │   Manager    │ │   Manager    │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │                │
       └────────────────┴────────────────┴────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    MilvusClient (Singleton)                  │
│  - Connection management                                      │
│  - Low-level API wrapper                                     │
└─────────────────────────────────────────────────────────────┘
```

### Collection Schema Design

Based on architecture.md reference:

| Field | Type | Description |
|-------|------|-------------|
| pk | VARCHAR | Primary key (document hash) |
| text | VARCHAR | Full text content (for BM25) |
| summary | VARCHAR | Document summary/abstract |
| document | VARCHAR | Original document content |
| source | VARCHAR | Data source type |
| source_name | VARCHAR | Data source name |
| lt_doc_id | VARCHAR | Link to document ID in PostgreSQL |
| chunk_id | INT64 | Chunk sequence number |
| summary_dense | FLOAT_VECTOR | Summary embedding vector |
| text_dense | FLOAT_VECTOR | Text embedding vector |
| text_sparse | SPARSE_FLOAT_VECTOR | BM25 sparse vector |

---

## Submodule Breakdown

### Submodule 6.1: Infrastructure Setup

**Goal**: Establish foundation for Milvus operations

| # | Task | Description | Status |
|---|------|-------------|--------|
| 1.1 | Add pymilvus dependency | Add pymilvus to pyproject.toml | ✅ Done |
| 1.2 | Create constants | Define collection names, field names, index params | ✅ Done |
| 1.3 | Create exceptions | Custom exception classes for Milvus operations | ✅ Done |
| 1.4 | Create DTOs | Dataclasses for requests and responses | ✅ Done |
| 1.5 | Implement MilvusClient | Singleton client with connection management | ✅ Done |
| 1.6 | Update settings | Add Milvus configuration to settings | ✅ Done |
| 1.7 | Update environment | Add MILVUS_* variables to .env file | ✅ Done |

### Submodule 6.2: Collection Management

**Goal**: Implement collection lifecycle management

| # | Task | Description | Status |
|---|------|-------------|--------|
| 2.1 | Define collection schema | Create schema with multi-vector fields | ✅ Done |
| 2.2 | Implement create_collection | Create collection with BM25 function | ✅ Done |
| 2.3 | Implement has_collection | Check if collection exists | ✅ Done |
| 2.4 | Implement list_collections | List all collections | ✅ Done |
| 2.5 | Implement drop_collection | Delete collection | ✅ Done |
| 2.6 | Implement describe_collection | Get collection details | ✅ Done |

### Submodule 6.3: Index Management

**Goal**: Implement vector index management

| # | Task | Description | Status |
|---|------|-------------|--------|
| 3.1 | Implement create_index | Create HNSW index for dense vectors | ✅ Done |
| 3.2 | Implement create_sparse_index | Create sparse index for BM25 | ✅ Done |
| 3.3 | Implement load_collection | Load collection into memory | ✅ Done |
| 3.4 | Implement release_collection | Release collection from memory | ✅ Done |
| 3.5 | Implement get_index_stats | Get index statistics | ✅ Done |

### Submodule 6.4: Vector CRUD Operations

**Goal**: Implement vector data operations

| # | Task | Description | Status |
|---|------|-------------|--------|
| 4.1 | Implement insert_vectors | Batch insert vectors with metadata | ✅ Done |
| 4.2 | Implement upsert_vectors | Insert or update vectors | ✅ Done |
| 4.3 | Implement delete_vectors | Delete vectors by filter or IDs | ✅ Done |
| 4.4 | Implement get_vector | Retrieve single vector by ID | ✅ Done |
| 4.5 | Implement query_vectors | Query vectors with filter | ✅ Done |

### Submodule 6.5: Search Operations

**Goal**: Implement vector search functionality

| # | Task | Description | Status |
|---|------|-------------|--------|
| 5.1 | Implement vector_search | Single vector field search | ✅ Done |
| 5.2 | Implement hybrid_search | Multi-vector hybrid search with RRF | ✅ Done |
| 5.3 | Implement bm25_search | BM25 sparse vector search | ✅ Done |
| 5.4 | Implement search_with_filter | Search with metadata filter | ✅ Done |

### Submodule 6.6: Service Layer & Testing

**Goal**: Provide unified service interface and comprehensive tests

**Status**: Completed ✅

| # | Task | Description | Status |
|---|------|-------------|--------|
| 6.1 | Implement MilvusService | Facade service coordinating all operations | ✅ Done |
| 6.2 | Create test fixtures | Setup test Milvus instance and sample data | ✅ Done |
| 6.3 | Write client tests | Test MilvusClient connection and basic ops | ✅ Done |
| 6.4 | Write collection tests | Test collection management | ✅ Done |
| 6.5 | Write vector tests | Test vector CRUD operations | ✅ Done |
| 6.6 | Write search tests | Test search functionality | ✅ Done |
| 6.7 | Write integration tests | End-to-end tests with real Milvus | ✅ Done |

### Submodule 6.7: API Views Layer

**Goal**: Expose Milvus functionality through REST API endpoints

**Status**: Completed ✅

**Dependencies**: Submodule 6.6 (MilvusService)

| # | Task | Description | Status |
|---|------|-------------|--------|
| 7.1 | Create serializers | Define request/response serializers for all endpoints | ✅ Done |
| 7.2 | Implement CollectionViews | Collection CRUD endpoints (create, list, info, delete, load, release) | ✅ Done |
| 7.3 | Implement VectorViews | Vector CRUD endpoints (insert, upsert, query, get, delete) | ✅ Done |
| 7.4 | Implement SearchViews | Search endpoints (vector search, hybrid search, document search) | ✅ Done |
| 7.5 | Implement HealthView | Health check and stats endpoints | ✅ Done |
| 7.6 | Create URL routing | URL patterns for all Milvus endpoints | ✅ Done |
| 7.7 | Register with main URL config | Include milvus URLs in main api/urls.py | ✅ Done |
| 7.8 | Write API tests | Test all API endpoints with pytest | ✅ Done |

---

## File Structure

```
apps/milvus_database_controller/
├── __init__.py
├── apps.py                     # Django AppConfig
├── constants.py                # Field names, collection names, defaults
├── exceptions.py               # Custom exceptions
├── dto.py                      # Data Transfer Objects (dataclasses)
│
├── client/
│   ├── __init__.py
│   └── milvus_client.py        # MilvusClient singleton wrapper
│
├── managers/
│   ├── __init__.py
│   ├── collection_manager.py   # Collection operations
│   ├── index_manager.py        # Index operations
│   ├── vector_manager.py       # Vector CRUD operations
│   └── search_manager.py       # Search operations
│
├── services/
│   ├── __init__.py
│   └── milvus_service.py       # High-level facade service
│
├── schemas/
│   ├── __init__.py
│   └── collection_schema.py    # Collection schema definitions
│
├── views/                      # API Views Layer (Submodule 6.7)
│   ├── __init__.py
│   ├── collection_views.py     # Collection management endpoints
│   ├── vector_views.py         # Vector CRUD endpoints
│   ├── search_views.py         # Search endpoints
│   └── health_views.py         # Health check endpoints
│
├── serializers.py              # DRF serializers for API requests/responses
├── urls.py                     # URL routing for Milvus API
│
└── tests/
    ├── __init__.py
    ├── conftest.py             # Pytest fixtures
    ├── test_client.py          # Client tests
    ├── test_collection_manager.py
    ├── test_index_manager.py
    ├── test_vector_manager.py
    ├── test_search_manager.py
    ├── test_milvus_service.py  # Service tests + Integration tests (end-to-end)
    └── test_api_views.py       # API endpoint tests (Submodule 6.7)
```

---

## Interface Design

### DTOs (Data Transfer Objects)

```python
from dataclasses import dataclass
from typing import Optional
import uuid

# =============================================================================
# Request DTOs
# =============================================================================

@dataclass(frozen=True)
class CreateCollectionRequest:
    """Request to create a new collection."""
    collection_name: str
    dimension: int = 1536
    auto_id: bool = False
    enable_dynamic_field: bool = True
    description: str = ""


@dataclass(frozen=True)
class InsertVectorsRequest:
    """Request to insert vectors into collection."""
    collection_name: str
    data: list[dict]  # List of vector records
    # Each record contains: pk, text, summary, document, source,
    # source_name, lt_doc_id, chunk_id, summary_dense, text_dense


@dataclass(frozen=True)
class SearchRequest:
    """Request for vector search."""
    collection_name: str
    query_vector: list[float]
    anns_field: str  # "summary_dense" | "text_dense"
    top_k: int = 10
    filter_expr: str = ""
    output_fields: Optional[list[str]] = None
    search_params: Optional[dict] = None


@dataclass(frozen=True)
class HybridSearchRequest:
    """Request for hybrid search across multiple vector fields."""
    collection_name: str
    query_text: str
    query_vectors: dict[str, list[float]]  # {"summary_dense": [...], "text_dense": [...]}
    top_k: int = 10
    filter_expr: str = ""
    output_fields: Optional[list[str]] = None
    rerank_method: str = "rrf"  # "rrf" | "weighted"
    rrf_k: int = 60
    weights: Optional[list[float]] = None


# =============================================================================
# Response DTOs
# =============================================================================

@dataclass(frozen=True)
class CollectionInfo:
    """Information about a collection."""
    name: str
    description: str
    num_entities: int
    schema: dict
    loaded: bool


@dataclass(frozen=True)
class InsertResult:
    """Result of vector insertion."""
    inserted_count: int
    inserted_ids: list[str]


@dataclass(frozen=True)
class SearchResultItem:
    """Single search result item."""
    id: str
    distance: float
    text: str
    summary: str
    document: str
    source: str
    source_name: str
    lt_doc_id: str
    chunk_id: int


@dataclass(frozen=True)
class SearchResult:
    """Result of vector search."""
    items: list[SearchResultItem]
    total: int
    query_time_ms: float
```

### MilvusService Interface

```python
class MilvusService:
    """High-level facade service for Milvus operations."""

    # Collection Management
    def create_collection(self, request: CreateCollectionRequest) -> bool: ...
    def has_collection(self, collection_name: str) -> bool: ...
    def list_collections(self) -> list[str]: ...
    def drop_collection(self, collection_name: str) -> bool: ...
    def get_collection_info(self, collection_name: str) -> CollectionInfo: ...

    # Index Management
    def create_indexes(self, collection_name: str) -> bool: ...
    def load_collection(self, collection_name: str) -> bool: ...
    def release_collection(self, collection_name: str) -> bool: ...

    # Vector Operations
    def insert_vectors(self, request: InsertVectorsRequest) -> InsertResult: ...
    def upsert_vectors(self, request: InsertVectorsRequest) -> InsertResult: ...
    def delete_vectors(self, collection_name: str, ids: list[str]) -> int: ...
    def delete_vectors_by_filter(self, collection_name: str, filter_expr: str) -> int: ...

    # Search Operations
    def search(self, request: SearchRequest) -> SearchResult: ...
    def hybrid_search(self, request: HybridSearchRequest) -> SearchResult: ...
```

---

## API Endpoints Design (Submodule 6.7)

### URL Structure

```
/api/v1/milvus/
├── health/                           # GET - Health check
├── collections/                      # GET - List collections
│   ├── create/                       # POST - Create collection
│   ├── {name}/                       # GET - Get collection info
│   ├── {name}/stats/                 # GET - Get collection stats
│   ├── {name}/load/                  # POST - Load collection into memory
│   ├── {name}/release/               # POST - Release collection from memory
│   └── {name}/delete/                # DELETE - Drop collection
├── vectors/
│   ├── insert/                       # POST - Insert vectors
│   ├── upsert/                       # POST - Upsert vectors
│   ├── query/                        # POST - Query vectors by filter
│   ├── {pk}/                         # GET - Get single vector by PK
│   └── delete/                       # POST - Delete vectors
└── search/
    ├── vector/                       # POST - Vector similarity search
    ├── hybrid/                       # POST - Hybrid search (multi-vector + BM25)
    └── document/                     # POST - Search within specific document
```

### Endpoint Details

#### Health Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/milvus/health/` | Milvus connection health check | IsAuthenticated |

**Response (200):**
```json
{
    "status": "healthy",
    "connected": true,
    "collections_count": 3
}
```

#### Collection Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/milvus/collections/` | List all collections | IsAuthenticated |
| POST | `/api/v1/milvus/collections/create/` | Create new collection | IsAuthenticated |
| GET | `/api/v1/milvus/collections/{name}/` | Get collection info | IsAuthenticated |
| GET | `/api/v1/milvus/collections/{name}/stats/` | Get collection statistics | IsAuthenticated |
| POST | `/api/v1/milvus/collections/{name}/load/` | Load collection into memory | IsAuthenticated |
| POST | `/api/v1/milvus/collections/{name}/release/` | Release collection from memory | IsAuthenticated |
| DELETE | `/api/v1/milvus/collections/{name}/delete/` | Drop collection | IsAuthenticated |

**Create Collection Request (POST):**
```json
{
    "collection_name": "my_collection",
    "dimension": 1536,
    "description": "My document collection"
}
```

**Collection Info Response (200):**
```json
{
    "name": "documents",
    "description": "Document vectors collection",
    "num_entities": 1000,
    "loaded": true,
    "schema": {
        "fields": ["pk", "text", "summary", "document", "source", ...]
    }
}
```

#### Vector Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/milvus/vectors/insert/` | Insert vectors | IsAuthenticated |
| POST | `/api/v1/milvus/vectors/upsert/` | Upsert vectors | IsAuthenticated |
| POST | `/api/v1/milvus/vectors/query/` | Query vectors by filter | IsAuthenticated |
| GET | `/api/v1/milvus/vectors/{pk}/` | Get single vector | IsAuthenticated |
| POST | `/api/v1/milvus/vectors/delete/` | Delete vectors | IsAuthenticated |

**Insert Vectors Request (POST):**
```json
{
    "collection_name": "documents",
    "data": [
        {
            "pk": "doc-001-chunk-001",
            "text": "This is the text content...",
            "summary": "Summary of the content",
            "document": "Full document content...",
            "source": "upload",
            "source_name": "report.pdf",
            "lt_doc_id": "uuid-of-document",
            "chunk_id": 1,
            "summary_dense": [0.1, 0.2, ...],
            "text_dense": [0.3, 0.4, ...]
        }
    ]
}
```

**Insert Response (200):**
```json
{
    "inserted_count": 1,
    "inserted_ids": ["doc-001-chunk-001"]
}
```

**Query Request (POST):**
```json
{
    "collection_name": "documents",
    "filter_expr": "source == 'upload'",
    "output_fields": ["pk", "text", "source"],
    "limit": 10
}
```

**Delete Vectors Request (POST):**
```json
{
    "collection_name": "documents",
    "ids": ["doc-001-chunk-001", "doc-001-chunk-002"]
}
```

#### Search Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/milvus/search/vector/` | Vector similarity search | IsAuthenticated |
| POST | `/api/v1/milvus/search/hybrid/` | Hybrid search (multi-vector + BM25) | IsAuthenticated |
| POST | `/api/v1/milvus/search/document/` | Search within specific document | IsAuthenticated |

**Vector Search Request (POST):**
```json
{
    "collection_name": "documents",
    "query_vector": [0.1, 0.2, ...],
    "anns_field": "text_dense",
    "top_k": 10,
    "filter_expr": "",
    "output_fields": ["pk", "text", "summary", "lt_doc_id"]
}
```

**Search Response (200):**
```json
{
    "items": [
        {
            "pk": "doc-001-chunk-001",
            "distance": 0.95,
            "text": "This is the matching text...",
            "summary": "Summary of the content",
            "document": "Full document content...",
            "source": "upload",
            "source_name": "report.pdf",
            "lt_doc_id": "uuid-of-document",
            "chunk_id": 1
        }
    ],
    "total": 1,
    "query_time_ms": 15.5
}
```

**Hybrid Search Request (POST):**
```json
{
    "collection_name": "documents",
    "query_text": "What is machine learning?",
    "query_vectors": {
        "summary_dense": [0.1, 0.2, ...],
        "text_dense": [0.3, 0.4, ...]
    },
    "top_k": 10,
    "filter_expr": "",
    "output_fields": ["pk", "text", "summary", "lt_doc_id"],
    "rerank_method": "rrf",
    "rrf_k": 60
}
```

**Document Search Request (POST):**
```json
{
    "collection_name": "documents",
    "document_id": "uuid-of-document",
    "query_vector": [0.1, 0.2, ...],
    "top_k": 5
}
```

### Serializers Design

```python
# apps/milvus_database_controller/serializers.py

from rest_framework import serializers


# =============================================================================
# Collection Serializers
# =============================================================================

class CreateCollectionSerializer(serializers.Serializer):
    """Serializer for collection creation request."""
    collection_name = serializers.CharField(max_length=255)
    dimension = serializers.IntegerField(default=1536, min_value=1)
    description = serializers.CharField(default="", allow_blank=True)


class CollectionInfoSerializer(serializers.Serializer):
    """Serializer for collection info response."""
    name = serializers.CharField()
    description = serializers.CharField()
    num_entities = serializers.IntegerField()
    schema = serializers.DictField()
    loaded = serializers.BooleanField()


class CollectionStatsSerializer(serializers.Serializer):
    """Serializer for collection statistics."""
    collection_name = serializers.CharField()
    row_count = serializers.IntegerField()
    index_info = serializers.ListField()
    loaded = serializers.BooleanField()


# =============================================================================
# Vector Serializers
# =============================================================================

class VectorDataSerializer(serializers.Serializer):
    """Serializer for single vector data."""
    pk = serializers.CharField(max_length=255)
    text = serializers.CharField()
    summary = serializers.CharField(allow_blank=True)
    document = serializers.CharField(allow_blank=True)
    source = serializers.CharField(max_length=100)
    source_name = serializers.CharField(max_length=255)
    lt_doc_id = serializers.CharField(max_length=255)
    chunk_id = serializers.IntegerField()
    summary_dense = serializers.ListField(child=serializers.FloatField())
    text_dense = serializers.ListField(child=serializers.FloatField())


class InsertVectorsSerializer(serializers.Serializer):
    """Serializer for vector insertion request."""
    collection_name = serializers.CharField(max_length=255)
    data = VectorDataSerializer(many=True)


class UpsertVectorsSerializer(InsertVectorsSerializer):
    """Serializer for vector upsert request."""
    pass


class QueryVectorsSerializer(serializers.Serializer):
    """Serializer for vector query request."""
    collection_name = serializers.CharField(max_length=255)
    filter_expr = serializers.CharField()
    output_fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
    )
    limit = serializers.IntegerField(default=100, max_value=1000)
    offset = serializers.IntegerField(default=0, min_value=0)


class DeleteVectorsSerializer(serializers.Serializer):
    """Serializer for vector deletion request."""
    collection_name = serializers.CharField(max_length=255)
    ids = serializers.ListField(child=serializers.CharField())


# =============================================================================
# Search Serializers
# =============================================================================

class VectorSearchSerializer(serializers.Serializer):
    """Serializer for vector search request."""
    collection_name = serializers.CharField(max_length=255)
    query_vector = serializers.ListField(child=serializers.FloatField())
    anns_field = serializers.CharField(default="text_dense")
    top_k = serializers.IntegerField(default=10, max_value=100)
    filter_expr = serializers.CharField(default="", allow_blank=True)
    output_fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
    )


class HybridSearchSerializer(serializers.Serializer):
    """Serializer for hybrid search request."""
    collection_name = serializers.CharField(max_length=255)
    query_text = serializers.CharField()
    query_vectors = serializers.DictField(child=serializers.ListField())
    top_k = serializers.IntegerField(default=10, max_value=100)
    filter_expr = serializers.CharField(default="", allow_blank=True)
    output_fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
    )
    rerank_method = serializers.ChoiceField(choices=["rrf", "weighted"], default="rrf")
    rrf_k = serializers.IntegerField(default=60, min_value=1)
    weights = serializers.ListField(
        child=serializers.FloatField(),
        required=False,
        allow_null=True,
    )


class DocumentSearchSerializer(serializers.Serializer):
    """Serializer for document-specific search."""
    collection_name = serializers.CharField(max_length=255)
    document_id = serializers.CharField()
    query_vector = serializers.ListField(child=serializers.FloatField())
    top_k = serializers.IntegerField(default=5, max_value=50)


# =============================================================================
# Response Serializers
# =============================================================================

class SearchResultItemSerializer(serializers.Serializer):
    """Serializer for single search result item."""
    pk = serializers.CharField()
    distance = serializers.FloatField()
    text = serializers.CharField()
    summary = serializers.CharField()
    document = serializers.CharField()
    source = serializers.CharField()
    source_name = serializers.CharField()
    lt_doc_id = serializers.CharField()
    chunk_id = serializers.IntegerField()


class SearchResultSerializer(serializers.Serializer):
    """Serializer for search result response."""
    items = SearchResultItemSerializer(many=True)
    total = serializers.IntegerField()
    query_time_ms = serializers.FloatField()


class InsertResultSerializer(serializers.Serializer):
    """Serializer for insert result response."""
    inserted_count = serializers.IntegerField()
    inserted_ids = serializers.ListField(child=serializers.CharField())


class DeleteResultSerializer(serializers.Serializer):
    """Serializer for delete result response."""
    deleted_count = serializers.IntegerField()


class HealthCheckSerializer(serializers.Serializer):
    """Serializer for health check response."""
    status = serializers.CharField()
    connected = serializers.BooleanField()
    collections_count = serializers.IntegerField(allow_null=True)
    error = serializers.CharField(allow_null=True)
```

---

## Configuration Design

### Settings (base.py)

```python
# =============================================================================
# Milvus Configuration
# =============================================================================

MILVUS_HOST = os.environ.get("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.environ.get("MILVUS_PORT", "19530"))
MILVUS_URI = os.environ.get("MILVUS_URI", f"http://{MILVUS_HOST}:{MILVUS_PORT}")
MILVUS_TOKEN = os.environ.get("MILVUS_TOKEN", "")

MILVUS_CONFIG = {
    # Connection
    "uri": MILVUS_URI,
    "token": MILVUS_TOKEN,

    # Collection names
    "documents_collection": "documents",
    "chat_history_collection": "chat_history",

    # Vector dimensions
    "dense_dimension": 1536,  # OpenAI/Qwen embedding dimension

    # Index settings
    "dense_index_type": "HNSW",
    "sparse_index_type": "SPARSE_INVERTED_INDEX",
    "metric_type": "COSINE",

    # HNSW parameters
    "hnsw_m": 32,
    "hnsw_ef_construction": 200,

    # BM25 parameters
    "bm25_k1": 1.5,
    "bm25_b": 0.75,

    # Search parameters
    "default_top_k": 10,
    "hnsw_ef": 100,

    # Auto ID
    "auto_id": False,
}
```

### Environment Variables (.env)

```bash
# Milvus Configuration
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_URI=http://localhost:19530
MILVUS_TOKEN=
```

---

## Constants Design

```python
from enum import Enum

# =============================================================================
# Collection Names
# =============================================================================

COLLECTION_DOCUMENTS = "documents"
COLLECTION_CHAT_HISTORY = "chat_history"

# =============================================================================
# Field Names
# =============================================================================

class FieldName:
    """Field names for Milvus collections."""
    PK = "pk"
    TEXT = "text"
    SUMMARY = "summary"
    DOCUMENT = "document"
    SOURCE = "source"
    SOURCE_NAME = "source_name"
    LT_DOC_ID = "lt_doc_id"
    CHUNK_ID = "chunk_id"
    SUMMARY_DENSE = "summary_dense"
    TEXT_DENSE = "text_dense"
    TEXT_SPARSE = "text_sparse"


class IndexName:
    """Index names for vector fields."""
    SUMMARY_DENSE = "summary_dense_index"
    TEXT_DENSE = "text_dense_index"
    TEXT_SPARSE = "text_sparse_index"


class MetricType:
    """Metric types for vector search."""
    COSINE = "COSINE"
    IP = "IP"  # Inner Product
    L2 = "L2"
    BM25 = "BM25"
```

---

## Exception Design

```python
class MilvusError(Exception):
    """Base exception for Milvus operations."""
    pass


class MilvusConnectionError(MilvusError):
    """Failed to connect to Milvus server."""
    pass


class CollectionNotFoundError(MilvusError):
    """Collection does not exist."""
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        super().__init__(f"Collection '{collection_name}' not found")


class CollectionAlreadyExistsError(MilvusError):
    """Collection already exists."""
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        super().__init__(f"Collection '{collection_name}' already exists")


class VectorInsertError(MilvusError):
    """Failed to insert vectors."""
    pass


class SearchError(MilvusError):
    """Failed to perform search."""
    pass


class InvalidVectorDimensionError(MilvusError):
    """Vector dimension mismatch."""
    def __init__(self, expected: int, actual: int):
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Invalid vector dimension: expected {expected}, got {actual}"
        )
```

---

## Test Strategy

### Test Categories

1. **Unit Tests**: Mock MilvusClient, test manager logic
2. **Integration Tests**: Real Milvus instance (Docker)
3. **Performance Tests**: Benchmark search latency

### Test Fixtures

```python
# conftest.py
import pytest
from pymilvus import MilvusClient

@pytest.fixture
def milvus_client():
    """Create Milvus client for testing."""
    client = MilvusClient(uri="http://localhost:19530")
    yield client
    # Cleanup: drop test collections
    for name in client.list_collections():
        if name.startswith("test_"):
            client.drop_collection(name)

@pytest.fixture
def test_collection(milvus_client):
    """Create test collection with sample data."""
    collection_name = "test_documents"
    # ... setup logic
    yield collection_name
    # Cleanup
    milvus_client.drop_collection(collection_name)

@pytest.fixture
def sample_vectors():
    """Generate sample vectors for testing."""
    import numpy as np
    dimension = 1536
    return {
        "pk": "test-001",
        "text": "This is a test document for vector search.",
        "summary": "Test document summary",
        "document": "Full document content here...",
        "source": "test",
        "source_name": "test_source",
        "lt_doc_id": "doc-001",
        "chunk_id": 1,
        "summary_dense": np.random.rand(dimension).tolist(),
        "text_dense": np.random.rand(dimension).tolist(),
    }
```

### Test Commands

```bash
# Run all milvus tests
pytest apps/milvus_database_controller/tests/ -v

# Run with coverage
pytest apps/milvus_database_controller/tests/ --cov=apps/milvus_database_controller --cov-report=term-missing

# Run integration tests only (requires running Milvus)
pytest apps/milvus_database_controller/tests/test_integration.py -v

# Run unit tests with mocked client
pytest apps/milvus_database_controller/tests/ -v -m "not integration"
```

---

## Integration with Other Modules

### documents_parser Integration

```python
# After document parsing, store vectors
from apps.milvus_database_controller.services import MilvusService
from apps.milvus_database_controller.dto import InsertVectorsRequest

milvus_service = MilvusService()

def store_document_vectors(document_id: str, chunks: list[dict]) -> InsertResult:
    """Store document chunk vectors in Milvus."""
    request = InsertVectorsRequest(
        collection_name="documents",
        data=[{
            "pk": f"{document_id}-{chunk['chunk_id']}",
            "text": chunk["text"],
            "summary": chunk.get("summary", ""),
            "document": chunk.get("document", ""),
            "source": "upload",
            "source_name": chunk.get("source_name", ""),
            "lt_doc_id": document_id,
            "chunk_id": chunk["chunk_id"],
            "summary_dense": chunk["summary_embedding"],
            "text_dense": chunk["text_embedding"],
        } for chunk in chunks]
    )
    return milvus_service.insert_vectors(request)
```

### rag_processing Integration

```python
# Search for relevant context
from apps.milvus_database_controller.services import MilvusService
from apps.milvus_database_controller.dto import HybridSearchRequest

milvus_service = MilvusService()

def retrieve_context(query: str, query_embedding: dict, top_k: int = 5) -> list[dict]:
    """Retrieve relevant context for RAG query."""
    request = HybridSearchRequest(
        collection_name="documents",
        query_text=query,
        query_vectors=query_embedding,
        top_k=top_k,
        output_fields=["text", "summary", "document", "source", "lt_doc_id"],
        rerank_method="rrf",
        rrf_k=60,
    )
    result = milvus_service.hybrid_search(request)
    return [item.__dict__ for item in result.items]
```

---

## Dependencies

```toml
# pyproject.toml additions
[tool.poetry.dependencies]
pymilvus = "^2.4"  # Milvus Python SDK

[tool.poetry.group.dev.dependencies]
# No additional dev dependencies needed for Milvus testing
# Integration tests use existing local Milvus instance
```

---

## Acceptance Criteria

### Core Functionality (Submodule 6.1-6.6)
- [x] MilvusClient singleton with connection pooling
- [x] Collection creation with multi-vector schema
- [x] HNSW index creation for dense vectors
- [x] Sparse index creation for BM25
- [x] Batch vector insertion
- [x] Vector search by single field
- [x] Hybrid search with RRF ranking
- [x] BM25 text search
- [x] Vector deletion by ID and filter
- [x] Comprehensive error handling
- [x] Test coverage >= 80% (achieved: 81.91%)

### API Layer (Submodule 6.7)
- [x] REST API endpoints for all MilvusService operations
- [x] Proper authentication (IsAuthenticated)
- [x] Request validation with DRF serializers
- [x] Consistent response format
- [x] Clear error messages with appropriate HTTP status codes
- [x] OpenAPI documentation via drf-yasg (swagger_auto_schema)
- [x] API tests with >= 80% coverage (30 tests, all passing)

### Integration (Future Phases)
- [ ] Integration with documents_parser (Phase 9)
- [ ] Integration with rag_processing (Phase 11)

---

## Risks & Considerations

1. **Vector Dimension**: Ensure consistency with embedding model (1536 for Qwen/OpenAI)
2. **Connection Management**: Singleton pattern for MilvusClient to reuse connections
3. **Memory Usage**: Large collections may require memory management
4. **Search Performance**: HNSW parameters need tuning for production
5. **BM25 Function**: Requires Milvus 2.4+ with BM25 support
6. **Data Consistency**: Need to sync with PostgreSQL metadata

---

## Execution Order

Recommended execution order:

1. **Submodule 6.1** (Tasks 1.1-1.7): Infrastructure setup ✅
2. **Submodule 6.2** (Tasks 2.1-2.6): Collection management ✅
3. **Submodule 6.3** (Tasks 3.1-3.5): Index management ✅
4. **Submodule 6.4** (Tasks 4.1-4.5): Vector CRUD operations ✅
5. **Submodule 6.5** (Tasks 5.1-5.4): Search operations ✅
6. **Submodule 6.6** (Tasks 6.1-6.7): Service layer and testing ✅
7. **Submodule 6.7** (Tasks 7.1-7.8): API Views Layer ✅

---

## Files to Create/Modify

### New Files

| File | Purpose | Submodule |
|------|---------|-----------|
| `apps/milvus_database_controller/constants.py` | Field/index names, defaults | 6.1 ✅ |
| `apps/milvus_database_controller/exceptions.py` | Custom exceptions | 6.1 ✅ |
| `apps/milvus_database_controller/dto.py` | Data transfer objects | 6.1 ✅ |
| `apps/milvus_database_controller/client/__init__.py` | Client module init | 6.1 ✅ |
| `apps/milvus_database_controller/client/milvus_client.py` | MilvusClient wrapper | 6.1 ✅ |
| `apps/milvus_database_controller/managers/__init__.py` | Managers module init | 6.1 ✅ |
| `apps/milvus_database_controller/managers/collection_manager.py` | Collection ops | 6.2 ✅ |
| `apps/milvus_database_controller/managers/index_manager.py` | Index ops | 6.3 ✅ |
| `apps/milvus_database_controller/managers/vector_manager.py` | Vector CRUD | 6.4 ✅ |
| `apps/milvus_database_controller/managers/search_manager.py` | Search ops | 6.5 ✅ |
| `apps/milvus_database_controller/services/__init__.py` | Services module init | 6.6 ✅ |
| `apps/milvus_database_controller/services/milvus_service.py` | Facade service | 6.6 ✅ |
| `apps/milvus_database_controller/schemas/__init__.py` | Schemas module init | 6.1 ✅ |
| `apps/milvus_database_controller/schemas/collection_schema.py` | Schema definitions | 6.1 ✅ |
| `apps/milvus_database_controller/tests/__init__.py` | Tests module init | 6.6 ✅ |
| `apps/milvus_database_controller/tests/conftest.py` | Test fixtures | 6.6 ✅ |
| `apps/milvus_database_controller/tests/test_*.py` | Test files | 6.6 ✅ |
| `apps/milvus_database_controller/views/__init__.py` | Views module init | 6.7 ✅ |
| `apps/milvus_database_controller/views/collection_views.py` | Collection endpoints | 6.7 ✅ |
| `apps/milvus_database_controller/views/vector_views.py` | Vector endpoints | 6.7 ✅ |
| `apps/milvus_database_controller/views/search_views.py` | Search endpoints | 6.7 ✅ |
| `apps/milvus_database_controller/views/health_views.py` | Health check endpoints | 6.7 ✅ |
| `apps/milvus_database_controller/serializers.py` | DRF serializers | 6.7 ✅ |
| `apps/milvus_database_controller/urls.py` | URL routing | 6.7 ✅ |
| `apps/milvus_database_controller/tests/test_api_views.py` | API tests | 6.7 ✅ |

### Modified Files

| File | Changes | Submodule |
|------|---------|-----------|
| `pyproject.toml` | Add pymilvus dependency | 6.1 ✅ |
| `config/settings/base.py` | Update MILVUS_CONFIG | 6.1 ✅ |
| `env/.env.local` | Add MILVUS_URI, MILVUS_TOKEN | 6.1 ✅ |
| `config/urls.py` | Include milvus URLs | 6.7 ✅ |

---

*Generated: 2026-02-26*
*Last Updated: 2026-02-26 - Completed Submodule 6.7: API Views Layer*
*Plan for Phase 6: Milvus Database Controller*
