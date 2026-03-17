# Phase 10: Document RAG Search Module Implementation Plan

## Overview

Implement document RAG search module for melon RAG project, providing hybrid search functionality combining Milvus vector search, Neo4j graph traversal, and PostgreSQL full-text search with RRF (Reciprocal Rank Fusion) ranking.

## Status: Ready for Implementation

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Phase 2: Basic Setup | ✅ Completed | Django project structure ready |
| Phase 3: User Management Module | ✅ Completed | Authentication available |
| Phase 4: Document Parser Module | ✅ Completed | DocumentChunk model available |
| Phase 5: Object Storage Controller | ✅ Completed | File storage ready |
| Phase 6: Milvus Database Controller | ✅ Completed | SearchManager with vector/hybrid/BM25 search |
| Phase 7: Neo4j Database Controller | ✅ Completed | QueryManager with graph queries |
| Phase 8: Embedding Engine | ✅ Completed | EmbeddingService with embed_query |
| Phase 9: Document Pipeline Manager | ✅ Completed | Documents processed and indexed |

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Search Architecture** | Three-Level Retrieval | Milvus (vector) + Neo4j (graph) + PostgreSQL (FTS) |
| **Fusion Strategy** | RRF (Reciprocal Rank Fusion) | Standard algorithm, well-tested, easy to tune |
| **Service Pattern** | Facade (SearchService) | Matches MilvusService/Neo4jService architecture |
| **Retriever Pattern** | Strategy Pattern | Extensible retriever architecture |
| **PostgreSQL FTS** | Django SearchVector | Built-in FTS support, no extra dependencies |
| **Result Type** | UnifiedSearchResult | Consistent result format across all retrievers |
| **API Design** | REST API first | Primary use via HTTP API, service layer import supported |

---

## Architecture Design

### Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    External API Consumers                    │
│              (curl, Postman, Frontend)                       │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Views Layer                           │
│  - SearchViews (search, hybrid, advanced search)            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    SearchService (Facade)                    │
│  - Unified search interface                                  │
│  - Result fusion and ranking                                 │
│  - Query coordination                                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┬───────────────┐
          ▼               ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Vector     │ │    Graph     │ │   Keyword    │ │    RRF       │
│   Retriever  │ │   Retriever  │ │   Retriever  │ │   Ranker     │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────────────┘
       │                │                │
       └────────────────┴────────────────┴──────────────┐
                                                        │
                                                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Modules                          │
│  - MilvusService (vector search, BM25)                       │
│  - Neo4jService (graph queries)                              │
│  - EmbeddingService (query embedding)                        │
│  - DocumentChunk model (PostgreSQL FTS)                      │
└─────────────────────────────────────────────────────────────┘
```

### Search Flow Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Hybrid Search Flow                                   │
└─────────────────────────────────────────────────────────────────────────┘

User Query (HTTP POST)
    │
    ▼
┌─────────────────────┐
│  Query Processing   │  ← SearchService
│  - Query parsing    │     - Extract entities (optional)
│  - Normalization    │     - Identify search scope
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Query Embedding    │  ← EmbeddingService.embed_query()
│  - Dense vector     │     Returns: [0.1, 0.2, ...] (1536 dims)
└──────────┬──────────┘
           │
           ├──────────────────────────────┐
           │                              │
           ▼                              ▼
┌─────────────────────┐         ┌─────────────────────┐
│  Vector Retrieval   │         │   Graph Retrieval   │
│  - Milvus search    │         │   - Neo4j queries   │
│  - top_k=20         │         │   - Entity context  │
└──────────┬──────────┘         └──────────┬──────────┘
           │                              │
           │                              │
           ▼                              ▼
┌─────────────────────┐         ┌─────────────────────┐
│  Keyword Retrieval  │         │   Chunk Mapping     │
│  - PostgreSQL FTS   │         │   - Get chunk IDs   │
│  - top_k=20         │         │   from entities     │
└──────────┬──────────┘         └──────────┬──────────┘
           │                              │
           └──────────────┬───────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    RRF Fusion                                │
│  - Combine rankings from all retrievers                     │
│  - k=60 (default parameter)                                 │
│  - Score = sum(1 / (k + rank))                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────┐
│  Result Assembly    │  ← SearchService
│  - Deduplication    │     - Remove duplicates by chunk_id
│  - Re-ranking       │     - Optional cross-encoder rerank
│  - Context expand   │     - Include neighbor chunks
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Response Format    │
│  - Unified result   │  ← UnifiedSearchResult
│  - Sources + scores │
└─────────────────────┘
```

---

## Submodule Breakdown

### Submodule 10.1: Infrastructure Setup

**Goal**: Establish foundation for RAG search operations

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 1.1 | Create constants.py | Define search types, ranking methods, defaults | 1h | ⏳ Pending |
| 1.2 | Create exceptions.py | Custom exception classes for search errors | 1h | ⏳ Pending |
| 1.3 | Create dto.py | Dataclasses for requests and responses | 2h | ⏳ Pending |
| 1.4 | Update settings | Add SEARCH_CONFIG to base.py | 0.5h | ⏳ Pending |
| 1.5 | Create app structure | Create directory structure for RAG search module | 0.5h | ⏳ Pending |

**Acceptance Criteria**:
- [ ] All constants defined with Enum pattern (matching Phase 6/7/8/9)
- [ ] Exception hierarchy matches established pattern
- [ ] DTOs are frozen dataclasses
- [ ] Configuration added to settings
- [ ] Directory structure created

**Files Created**:
- `apps/document_rag_search/__init__.py`
- `apps/document_rag_search/apps.py`
- `apps/document_rag_search/constants.py`
- `apps/document_rag_search/exceptions.py`
- `apps/document_rag_search/dto.py`

**Files Modified**:
- `config/settings/base.py` - Add SEARCH_CONFIG

---

### Submodule 10.2: Retriever Implementations

**Goal**: Implement individual retriever components

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 2.1 | Create BaseRetriever | Abstract base class for retrievers | 1.5h | ⏳ Pending |
| 2.2 | Implement VectorRetriever | Milvus vector search wrapper | 2h | ⏳ Pending |
| 2.3 | Implement KeywordRetriever | PostgreSQL full-text search | 2.5h | ⏳ Pending |
| 2.4 | Implement GraphRetriever | Neo4j entity context retrieval | 3h | ⏳ Pending |
| 2.5 | Write retriever tests | Unit tests for each retriever | 2h | ⏳ Pending |

**Acceptance Criteria**:
- [ ] BaseRetriever interface defined with abstract methods
- [ ] VectorRetriever wraps MilvusService correctly
- [ ] KeywordRetriever uses Django SearchVector for FTS
- [ ] GraphRetriever uses Neo4jService for entity context
- [ ] All retrievers return consistent RetrieverResult format

**Retriever Interface Design**:

```python
# retrievers/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from apps.document_rag_search.dto import RetrieverResult, SearchQuery


class BaseRetriever(ABC):
    """Abstract base class for retrievers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return retriever name."""
        ...
    
    @abstractmethod
    def retrieve(
        self,
        query: SearchQuery,
        top_k: int = 10,
        **kwargs: Any,
    ) -> RetrieverResult:
        """Retrieve relevant documents.
        
        Args:
            query: Search query with text and optional embedding.
            top_k: Maximum number of results to return.
            **kwargs: Additional retriever-specific parameters.
            
        Returns:
            RetrieverResult with ranked items.
        """
        ...
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if retriever is healthy and available."""
        ...
```

**Files Created**:
- `apps/document_rag_search/retrievers/__init__.py`
- `apps/document_rag_search/retrievers/base.py`
- `apps/document_rag_search/retrievers/vector_retriever.py`
- `apps/document_rag_search/retrievers/keyword_retriever.py`
- `apps/document_rag_search/retrievers/graph_retriever.py`

---

### Submodule 10.3: Fusion & Ranking

**Goal**: Implement RRF fusion and ranking logic

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 3.1 | Create RRFFusion class | Reciprocal Rank Fusion implementation | 2h | ⏳ Pending |
| 3.2 | Implement score normalization | Normalize scores from different retrievers | 1h | ⏳ Pending |
| 3.3 | Implement result deduplication | Deduplicate by chunk_id | 1.5h | ⏳ Pending |
| 3.4 | Implement context expansion | Include neighbor chunks (optional) | 2h | ⏳ Pending |
| 3.5 | Write fusion tests | Test RRF algorithm | 1.5h | ⏳ Pending |

**Acceptance Criteria**:
- [ ] RRFFusion correctly implements formula: score = sum(1 / (k + rank))
- [ ] Scores normalized to [0, 1] range
- [ ] Deduplication by chunk_id preserves highest score
- [ ] Context expansion includes prev/next chunks when available

**RRF Algorithm Design**:

```python
# ranking/rrf_fusion.py
from __future__ import annotations

from typing import Any
from dataclasses import dataclass

from apps.document_rag_search.dto import RankedResult, RetrieverResult


@dataclass(frozen=True)
class RRFConfig:
    """Configuration for RRF fusion."""
    k: int = 60  # RRF parameter
    weights: dict[str, float] | None = None  # Retriever weights


class RRFFusion:
    """Reciprocal Rank Fusion for combining multiple rankings.
    
    Formula: score(d) = sum(1 / (k + rank(d, retriever_i)))
    
    Reference: https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
    """
    
    def __init__(self, config: RRFConfig | None = None) -> None:
        """Initialize RRF fusion with config."""
        self._config = config or RRFConfig()
    
    def fuse(
        self,
        retriever_results: dict[str, RetrieverResult],
        top_k: int = 10,
    ) -> list[RankedResult]:
        """Fuse multiple retriever results using RRF.
        
        Args:
            retriever_results: Dict mapping retriever name to results.
            top_k: Maximum number of results to return.
            
        Returns:
            List of RankedResult sorted by fused score.
        """
        # Implementation details...
        pass
```

**Files Created**:
- `apps/document_rag_search/ranking/__init__.py`
- `apps/document_rag_search/ranking/rrf_fusion.py`
- `apps/document_rag_search/ranking/deduplication.py`

---

### Submodule 10.4: Search Service Layer

**Goal**: Provide unified service interface for search operations

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 4.1 | Create SearchService class | High-level facade service | 2h | ⏳ Pending |
| 4.2 | Implement search method | Unified search interface | 2h | ⏳ Pending |
| 4.3 | Implement hybrid_search | Multi-retriever search with RRF | 2.5h | ⏳ Pending |
| 4.4 | Implement advanced_search | Advanced search with filters | 2h | ⏳ Pending |
| 4.5 | Implement get_search_suggestions | Auto-complete suggestions | 1.5h | ⏳ Pending |
| 4.6 | Write service tests | Test service layer | 2h | ⏳ Pending |

**Acceptance Criteria**:
- [ ] SearchService coordinates all retrievers
- [ ] Hybrid search uses RRF fusion
- [ ] Filters support user_id, document_id, date range
- [ ] Suggestions use PostgreSQL trigram similarity

**Service Interface Design**:

```python
# services/search_service.py
from __future__ import annotations

from typing import Any

from apps.document_rag_search.dto import (
    AdvancedSearchRequest,
    HybridSearchRequest,
    SearchQuery,
    SearchResponse,
    SearchSuggestionsRequest,
    SearchSuggestionsResponse,
)
from apps.document_rag_search.retrievers import (
    GraphRetriever,
    KeywordRetriever,
    VectorRetriever,
)
from apps.document_rag_search.ranking import RRFFusion


class SearchService:
    """High-level facade service for RAG search operations.
    
    This service provides a unified interface for all search operations,
    coordinating between multiple retrievers and applying fusion ranking.
    
    Example:
        >>> service = SearchService()
        >>> # Simple search
        >>> result = service.search("What is machine learning?")
        >>> # Hybrid search with graph
        >>> result = service.hybrid_search(
        ...     HybridSearchRequest(
        ...         query="What is machine learning?",
        ...         use_vector=True,
        ...         use_keyword=True,
        ...         use_graph=True,
        ...     )
        ... )
    """
    
    def __init__(self) -> None:
        """Initialize service with retrievers and fusion."""
        self._vector_retriever = VectorRetriever()
        self._keyword_retriever = KeywordRetriever()
        self._graph_retriever = GraphRetriever()
        self._fusion = RRFFusion()
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        user_id: str | None = None,
    ) -> SearchResponse:
        """Simple search using vector retrieval.
        
        Args:
            query: Search query text.
            top_k: Maximum number of results.
            user_id: Optional user filter.
            
        Returns:
            SearchResponse with results.
        """
        ...
    
    def hybrid_search(
        self,
        request: HybridSearchRequest,
    ) -> SearchResponse:
        """Hybrid search combining multiple retrievers with RRF.
        
        Args:
            request: HybridSearchRequest with query and options.
            
        Returns:
            SearchResponse with fused results.
        """
        ...
    
    def advanced_search(
        self,
        request: AdvancedSearchRequest,
    ) -> SearchResponse:
        """Advanced search with filters and options.
        
        Args:
            request: AdvancedSearchRequest with filters.
            
        Returns:
            SearchResponse with filtered results.
        """
        ...
    
    def get_search_suggestions(
        self,
        request: SearchSuggestionsRequest,
    ) -> SearchSuggestionsResponse:
        """Get search suggestions based on query prefix.
        
        Args:
            request: SearchSuggestionsRequest with prefix.
            
        Returns:
            SearchSuggestionsResponse with suggestions.
        """
        ...
```

**Files Created**:
- `apps/document_rag_search/services/__init__.py`
- `apps/document_rag_search/services/search_service.py`

---

### Submodule 10.5: API Views Layer

**Goal**: Expose search functionality through REST API endpoints

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 5.1 | Create serializers | Define request/response serializers | 2h | ⏳ Pending |
| 5.2 | Implement SearchViews | Search endpoints (search, hybrid, advanced) | 3h | ⏳ Pending |
| 5.3 | Create URL routing | URL patterns for all search endpoints | 1h | ⏳ Pending |
| 5.4 | Register with main URL config | Include search URLs in main api/urls.py | 0.5h | ⏳ Pending |
| 5.5 | Add OpenAPI documentation | Swagger/OpenAPI annotations | 1.5h | ⏳ Pending |
| 5.6 | Write API tests | Test all endpoints with pytest | 3h | ⏳ Pending |

**Acceptance Criteria**:
- [ ] All endpoints have proper authentication (IsAuthenticated)
- [ ] Request validation with DRF serializers
- [ ] Consistent response format
- [ ] OpenAPI documentation complete
- [ ] API tests cover all endpoints

**API Endpoints Design**:

```
/api/v1/search/
├── simple/                           # POST - Simple vector search
├── hybrid/                           # POST - Hybrid search (vector + keyword + graph)
├── advanced/                         # POST - Advanced search with filters
├── suggestions/                      # GET - Search suggestions
└── health/                           # GET - Health check
```

**Endpoint Details**:

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/search/simple/` | Simple vector search | IsAuthenticated |
| POST | `/api/v1/search/hybrid/` | Hybrid search with RRF | IsAuthenticated |
| POST | `/api/v1/search/advanced/` | Advanced search with filters | IsAuthenticated |
| GET | `/api/v1/search/suggestions/` | Search suggestions | IsAuthenticated |
| GET | `/api/v1/search/health/` | Health check | IsAuthenticated |

**Request/Response Examples**:

```json
// POST /api/v1/search/hybrid/
{
    "query": "What is machine learning?",
    "top_k": 10,
    "use_vector": true,
    "use_keyword": true,
    "use_graph": true,
    "filters": {
        "user_id": "uuid-here",
        "document_ids": ["uuid-1", "uuid-2"],
        "date_from": "2026-01-01",
        "date_to": "2026-12-31"
    },
    "rrf_k": 60
}

// Response (200)
{
    "results": [
        {
            "chunk_id": "uuid-here",
            "document_id": "uuid-doc",
            "text": "Machine learning is a subset...",
            "score": 0.95,
            "source": "report.pdf",
            "metadata": {
                "chunk_index": 5,
                "page_number": 12
            },
            "retriever_scores": {
                "vector": 0.92,
                "keyword": 0.88,
                "graph": 0.75
            }
        }
    ],
    "total": 10,
    "query_time_ms": 150,
    "retrievers_used": ["vector", "keyword", "graph"]
}
```

**Files Created**:
- `apps/document_rag_search/serializers.py`
- `apps/document_rag_search/views/__init__.py`
- `apps/document_rag_search/views/search_views.py`
- `apps/document_rag_search/urls.py`

**Files Modified**:
- `config/urls.py` - Include search URLs

---

### Submodule 10.6: PostgreSQL FTS Integration

**Goal**: Implement PostgreSQL full-text search for DocumentChunk

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 6.1 | Add SearchVector field | Add search vector to DocumentChunk model | 1.5h | ⏳ Pending |
| 6.2 | Create database migration | Generate and apply migration | 1h | ⏳ Pending |
| 6.3 | Implement search function | Django FTS query function | 2h | ⏳ Pending |
| 6.4 | Add search trigger | Auto-update search vector on save | 1.5h | ⏳ Pending |
| 6.5 | Write FTS tests | Test full-text search functionality | 1.5h | ⏳ Pending |

**Acceptance Criteria**:
- [ ] DocumentChunk has search_vector field
- [ ] Search vector auto-updates on text change
- [ ] FTS supports Chinese and English
- [ ] Search results ranked by relevance

**Model Update Design**:

```python
# apps/documents_parser/models.py (extension)

from django.contrib.postgres.search import SearchVectorField
from django.db.models import Value
from django.contrib.postgres.search import SearchVector

class DocumentChunk(models.Model):
    # ... existing fields ...
    
    # Full-text search vector
    search_vector = SearchVectorField(null=True, blank=True)
    
    class Meta:
        # ... existing meta ...
        indexes = [
            # ... existing indexes ...
            models.Index(fields=['search_vector']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-update search vector on save."""
        super().save(*args, **kwargs)
        # Update search vector asynchronously or via signal
        # to avoid circular dependency
```

**FTS Query Function**:

```python
# retrievers/fts_utils.py
from django.contrib.postgres.search import SearchQuery, SearchRank
from apps.documents_parser.models import DocumentChunk


def search_chunks_by_keyword(
    query: str,
    top_k: int = 10,
    user_id: str | None = None,
    document_ids: list[str] | None = None,
) -> list[dict]:
    """Search chunks using PostgreSQL full-text search.
    
    Args:
        query: Search query string.
        top_k: Maximum results.
        user_id: Optional user filter.
        document_ids: Optional document filter.
        
    Returns:
        List of chunk dictionaries with scores.
    """
    # Create search query with Chinese support
    search_query = SearchQuery(
        query,
        config='simple',  # Use 'simple' for mixed Chinese/English
    )
    
    # Build queryset
    queryset = DocumentChunk.objects.annotate(
        rank=SearchRank('search_vector', search_query)
    ).filter(
        search_vector=search_query
    ).order_by('-rank')[:top_k]
    
    # Apply filters
    if user_id:
        queryset = queryset.filter(document__user_id=user_id)
    if document_ids:
        queryset = queryset.filter(document_id__in=document_ids)
    
    return [
        {
            'chunk_id': str(chunk.id),
            'document_id': str(chunk.document_id),
            'text': chunk.text,
            'score': chunk.rank,
        }
        for chunk in queryset
    ]
```

**Files Modified**:
- `apps/documents_parser/models.py` - Add search_vector field
- `apps/documents_parser/migrations/` - New migration

**Files Created**:
- `apps/document_rag_search/retrievers/fts_utils.py`

---

### Submodule 10.7: Testing & Documentation

**Goal**: Comprehensive testing and documentation

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 7.1 | Create test fixtures | Pytest fixtures for search tests | 2h | ⏳ Pending |
| 7.2 | Write retriever tests | Test all retrievers | 2h | ⏳ Pending |
| 7.3 | Write fusion tests | Test RRF algorithm | 1.5h | ⏳ Pending |
| 7.4 | Write service tests | Test SearchService integration | 2h | ⏳ Pending |
| 7.5 | Write integration tests | End-to-end search tests | 3h | ⏳ Pending |
| 7.6 | Verify coverage | Ensure 80%+ coverage | 1h | ⏳ Pending |
| 7.7 | Create module documentation | README and API docs | 2h | ⏳ Pending |

**Acceptance Criteria**:
- [ ] Test fixtures created
- [ ] Retriever tests complete
- [ ] Fusion tests complete
- [ ] Service tests complete
- [ ] Integration tests with real services
- [ ] Test coverage >= 80%
- [ ] Documentation complete

**Test Strategy**:

```python
# tests/conftest.py
import pytest
from django.contrib.auth import get_user_model
from apps.documents_parser.models import Document, DocumentChunk
from apps.milvus_database_controller.services import MilvusService
from apps.neo4j_database_controller.services import Neo4jService
from apps.embedding_engine.services import EmbeddingService


@pytest.fixture
def test_user(db):
    """Create test user."""
    User = get_user_model()
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )


@pytest.fixture
def test_document_with_chunks(db, test_user):
    """Create test document with chunks."""
    doc = Document.objects.create(
        user=test_user,
        name="test_document.pdf",
        original_name="Test Document.pdf",
        file_path="documents/test_document.pdf",
        file_size=1024000,
        file_type="pdf",
        file_hash="abc123def456",
        status=Document.Status.DONE
    )
    
    chunks = []
    for i in range(5):
        chunk = DocumentChunk.objects.create(
            document=doc,
            text=f"Test chunk {i} content about machine learning.",
            chunk_index=i,
        )
        chunks.append(chunk)
    
    return doc, chunks


@pytest.fixture
def mock_embedding_service(monkeypatch):
    """Mock EmbeddingService for testing."""
    # Mock implementation
    pass


@pytest.fixture
def mock_milvus_service(monkeypatch):
    """Mock MilvusService for testing."""
    # Mock implementation
    pass


@pytest.fixture
def mock_neo4j_service(monkeypatch):
    """Mock Neo4jService for testing."""
    # Mock implementation
    pass
```

**Integration Test Example**:

```python
# tests/test_integration.py
import pytest
from apps.document_rag_search.services import SearchService
from apps.document_rag_search.dto import HybridSearchRequest


@pytest.mark.django_db
@pytest.mark.integration
class TestSearchIntegration:
    """Integration tests for hybrid search."""
    
    def test_hybrid_search_returns_results(
        self,
        test_document_with_chunks,
        mock_milvus_service,
        mock_neo4j_service,
        mock_embedding_service,
    ):
        """Test hybrid search returns fused results."""
        service = SearchService()
        
        request = HybridSearchRequest(
            query="What is machine learning?",
            use_vector=True,
            use_keyword=True,
            use_graph=False,  # Graph may not have data
            top_k=5,
        )
        
        response = service.hybrid_search(request)
        
        assert response.total > 0
        assert len(response.results) <= 5
        assert all(r.score > 0 for r in response.results)
```

**Files Created**:
- `apps/document_rag_search/tests/__init__.py`
- `apps/document_rag_search/tests/conftest.py`
- `apps/document_rag_search/tests/test_retrievers.py`
- `apps/document_rag_search/tests/test_fusion.py`
- `apps/document_rag_search/tests/test_service.py`
- `apps/document_rag_search/tests/test_api_views.py`
- `apps/document_rag_search/tests/test_integration.py`
- `apps/document_rag_search/docs/README.md`

---

### Submodule 10.8: Manual Test Generation

**Goal**: Generate manual test cases for search operations

**Dependencies**: Submodule 10.7 (Testing & Documentation)

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 8.1 | Invoke manual_test_generator agent | Generate manual test cases | 1h | ⏳ Pending |
| 8.2 | Create manual test document | Create apps/document_rag_search/docs/manual_test.md | 1h | ⏳ Pending |
| 8.3 | Document test scenarios | Document search, hybrid, advanced scenarios | 1.5h | ⏳ Pending |

**Acceptance Criteria**:
- [ ] Manual test document created
- [ ] Test cases for all major operations
- [ ] curl commands for API testing
- [ ] Sample queries for testing

**Files Created**:
- `apps/document_rag_search/docs/manual_test.md`

---

## File Structure

```
apps/document_rag_search/
├── __init__.py                     # App config
├── apps.py                         # Django AppConfig
├── constants.py                    # Search types, ranking methods, defaults
├── exceptions.py                   # Custom exceptions
├── dto.py                          # Data Transfer Objects
├── serializers.py                  # DRF serializers
├── urls.py                         # URL routing
│
├── retrievers/
│   ├── __init__.py
│   ├── base.py                     # BaseRetriever (ABC)
│   ├── vector_retriever.py         # VectorRetriever (Milvus)
│   ├── keyword_retriever.py        # KeywordRetriever (PostgreSQL FTS)
│   ├── graph_retriever.py          # GraphRetriever (Neo4j)
│   └── fts_utils.py                # FTS utility functions
│
├── ranking/
│   ├── __init__.py
│   ├── rrf_fusion.py               # RRFFusion class
│   └── deduplication.py            # Result deduplication
│
├── services/
│   ├── __init__.py
│   └── search_service.py           # SearchService facade
│
├── views/
│   ├── __init__.py
│   └── search_views.py             # Search API endpoints
│
├── docs/
│   ├── README.md                   # Module documentation
│   └── manual_test.md              # Manual test cases (Submodule 10.8)
│
└── tests/
    ├── __init__.py
    ├── conftest.py                 # Pytest fixtures
    ├── test_retrievers.py          # Retriever tests
    ├── test_fusion.py              # RRF fusion tests
    ├── test_service.py             # Service tests
    ├── test_api_views.py           # API tests
    └── test_integration.py         # End-to-end tests
```

---

## Constants Design

```python
# constants.py
from __future__ import annotations

from enum import Enum


# =============================================================================
# Search Types
# =============================================================================


class SearchType(str, Enum):
    """Search type for hybrid search."""
    
    VECTOR = "vector"
    KEYWORD = "keyword"
    GRAPH = "graph"


# =============================================================================
# Ranking Methods
# =============================================================================


class RankingMethod(str, Enum):
    """Ranking method for result fusion."""
    
    RRF = "rrf"  # Reciprocal Rank Fusion
    WEIGHTED = "weighted"  # Weighted average
    MAX = "max"  # Maximum score


# =============================================================================
# Default Configuration
# =============================================================================


DEFAULT_TOP_K = 10
DEFAULT_RRF_K = 60
DEFAULT_VECTOR_WEIGHT = 0.4
DEFAULT_KEYWORD_WEIGHT = 0.3
DEFAULT_GRAPH_WEIGHT = 0.3
MAX_QUERY_LENGTH = 500
MIN_QUERY_LENGTH = 2


# =============================================================================
# Retriever Names
# =============================================================================


class RetrieverName(str, Enum):
    """Retriever names for identification."""
    
    VECTOR = "vector"
    KEYWORD = "keyword"
    GRAPH = "graph"
```

---

## Exception Design

```python
# exceptions.py
from __future__ import annotations


# =============================================================================
# Base Exception
# =============================================================================


class SearchError(Exception):
    """Base exception for all search-related errors."""
    
    def __init__(self, message: str = "An error occurred in search operation") -> None:
        self.message = message
        super().__init__(self.message)


# =============================================================================
# Query Exceptions
# =============================================================================


class InvalidQueryError(SearchError):
    """Invalid search query."""
    
    def __init__(self, reason: str = "") -> None:
        self.reason = reason
        message = f"Invalid query: {reason}" if reason else "Invalid query"
        super().__init__(message)


class EmptyQueryError(InvalidQueryError):
    """Empty search query."""
    
    def __init__(self) -> None:
        super().__init__("Query cannot be empty")


class QueryTooLongError(InvalidQueryError):
    """Query exceeds maximum length."""
    
    def __init__(self, length: int, max_length: int) -> None:
        self.length = length
        self.max_length = max_length
        super().__init__(f"Query too long: {length} chars (max: {max_length})")


# =============================================================================
# Retriever Exceptions
# =============================================================================


class RetrieverError(SearchError):
    """Error during retrieval."""
    
    def __init__(self, retriever_name: str, reason: str = "") -> None:
        self.retriever_name = retriever_name
        self.reason = reason
        message = f"Retriever '{retriever_name}' failed: {reason}"
        super().__init__(message)


class VectorRetrieverError(RetrieverError):
    """Vector retriever error."""
    
    def __init__(self, reason: str = "") -> None:
        super().__init__("vector", reason)


class KeywordRetrieverError(RetrieverError):
    """Keyword retriever error."""
    
    def __init__(self, reason: str = "") -> None:
        super().__init__("keyword", reason)


class GraphRetrieverError(RetrieverError):
    """Graph retriever error."""
    
    def __init__(self, reason: str = "") -> None:
        super().__init__("graph", reason)


# =============================================================================
# Fusion Exceptions
# =============================================================================


class FusionError(SearchError):
    """Error during result fusion."""
    
    def __init__(self, reason: str = "") -> None:
        self.reason = reason
        message = f"Fusion failed: {reason}" if reason else "Fusion failed"
        super().__init__(message)


class NoResultsError(SearchError):
    """No results found from any retriever."""
    
    def __init__(self) -> None:
        super().__init__("No results found from any retriever")
```

---

## DTO Design

```python
# dto.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


# =============================================================================
# Request DTOs
# =============================================================================


@dataclass(frozen=True)
class SearchQuery:
    """Search query with text and optional embedding."""
    
    text: str
    embedding: list[float] | None = None
    user_id: str | None = None


@dataclass(frozen=True)
class HybridSearchRequest:
    """Request for hybrid search with multiple retrievers."""
    
    query: str
    top_k: int = 10
    use_vector: bool = True
    use_keyword: bool = True
    use_graph: bool = False
    filters: dict[str, Any] = field(default_factory=dict)
    rrf_k: int = 60
    weights: dict[str, float] | None = None  # Retriever weights


@dataclass(frozen=True)
class AdvancedSearchRequest:
    """Request for advanced search with filters."""
    
    query: str
    top_k: int = 10
    use_vector: bool = True
    use_keyword: bool = True
    use_graph: bool = False
    
    # Filters
    user_id: str | None = None
    document_ids: list[str] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    file_types: list[str] | None = None
    
    # Options
    rrf_k: int = 60
    expand_context: bool = False
    context_window: int = 1


@dataclass(frozen=True)
class SearchSuggestionsRequest:
    """Request for search suggestions."""
    
    prefix: str
    limit: int = 5


# =============================================================================
# Response DTOs
# =============================================================================


@dataclass(frozen=True)
class SearchResultItem:
    """Single search result item."""
    
    chunk_id: str
    document_id: str
    text: str
    score: float
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    retriever_scores: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResponse:
    """Response for search operations."""
    
    results: list[SearchResultItem]
    total: int
    query_time_ms: float
    retrievers_used: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RetrieverResult:
    """Result from a single retriever."""
    
    retriever_name: str
    items: list[dict[str, Any]]
    query_time_ms: float
    total: int
    error: str | None = None


@dataclass(frozen=True)
class RankedResult:
    """Result after RRF ranking."""
    
    chunk_id: str
    document_id: str
    text: str
    score: float
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    retriever_scores: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchSuggestionsResponse:
    """Response for search suggestions."""
    
    suggestions: list[str]
    total: int


# =============================================================================
# Configuration DTOs
# =============================================================================


@dataclass(frozen=True)
class SearchConfig:
    """Configuration for search operations."""
    
    default_top_k: int = 10
    default_rrf_k: int = 60
    max_query_length: int = 500
    min_query_length: int = 2
    vector_weight: float = 0.4
    keyword_weight: float = 0.3
    graph_weight: float = 0.3
    enable_suggestions: bool = True
```

---

## Configuration Design

### Settings (base.py)

```python
# =============================================================================
# Search Configuration
# =============================================================================

SEARCH_CONFIG = {
    # Default parameters
    "default_top_k": 10,
    "default_rrf_k": 60,
    "max_query_length": 500,
    "min_query_length": 2,
    
    # Retriever weights
    "retriever_weights": {
        "vector": 0.4,
        "keyword": 0.3,
        "graph": 0.3,
    },
    
    # Retriever settings
    "retrievers": {
        "vector": {
            "enabled": True,
            "collection_name": "documents",
            "anns_field": "text_dense",
        },
        "keyword": {
            "enabled": True,
            "fts_config": "simple",  # PostgreSQL FTS config
        },
        "graph": {
            "enabled": True,
            "max_depth": 2,
        },
    },
    
    # Context expansion
    "context_expansion": {
        "enabled": False,  # Disabled by default
        "window_size": 1,
    },
    
    # Suggestions
    "suggestions": {
        "enabled": True,
        "min_prefix_length": 2,
        "limit": 5,
    },
}
```

---

## Test Strategy

### Test Categories

| Category | Marker | Description |
|----------|--------|-------------|
| Unit Tests | `@pytest.mark.unit` | Mock dependencies, test logic |
| Integration Tests | `@pytest.mark.integration` | Real services (Milvus, Neo4j, PostgreSQL) |
| Performance Tests | `@pytest.mark.performance` | Benchmark search latency |

### Test Commands

```bash
# Run all search tests
pytest apps/document_rag_search/tests/ -v

# Run with coverage
pytest apps/document_rag_search/tests/ --cov=apps/document_rag_search --cov-report=term-missing

# Run only unit tests
pytest apps/document_rag_search/tests/ -v -m "not integration"

# Run integration tests (requires running services)
pytest apps/document_rag_search/tests/ -v -m integration

# Run with Django settings
DJANGO_SETTINGS_MODULE=config.settings.local pytest apps/document_rag_search/tests/ -v
```

---

## Integration with Other Modules

### MilvusService Integration

```python
# In VectorRetriever
from apps.milvus_database_controller.services import MilvusService
from apps.milvus_database_controller.dto import SearchRequest, HybridSearchRequest as MilvusHybridSearchRequest


class VectorRetriever(BaseRetriever):
    def __init__(self) -> None:
        self._milvus_service = MilvusService()
    
    def retrieve(
        self,
        query: SearchQuery,
        top_k: int = 10,
        **kwargs: Any,
    ) -> RetrieverResult:
        """Retrieve using Milvus vector search."""
        # Get embedding from query or generate it
        embedding = query.embedding or self._get_embedding(query.text)
        
        # Build search request
        request = SearchRequest(
            collection_name="documents",
            query_vector=embedding,
            anns_field="text_dense",
            top_k=top_k,
            filter_expr=self._build_filter(query.user_id),
        )
        
        # Execute search
        result = self._milvus_service.search(request)
        
        return RetrieverResult(
            retriever_name=self.name,
            items=[item.__dict__ for item in result.items],
            query_time_ms=result.query_time_ms,
            total=result.total,
        )
```

### Neo4jService Integration

```python
# In GraphRetriever
from apps.neo4j_database_controller.services import Neo4jService
from apps.neo4j_database_controller.dto import GetEntityContextRequest


class GraphRetriever(BaseRetriever):
    def __init__(self) -> None:
        self._neo4j_service = Neo4jService()
    
    def retrieve(
        self,
        query: SearchQuery,
        top_k: int = 10,
        **kwargs: Any,
    ) -> RetrieverResult:
        """Retrieve using Neo4j graph context."""
        # Extract entities from query (simplified for MVP)
        entities = self._extract_entities(query.text)
        
        # Get entity contexts
        chunk_ids = set()
        for entity_name in entities:
            entity_contexts = self._neo4j_service.find_entities_by_name(
                name=entity_name,
            )
            for context in entity_contexts:
                # Get chunk IDs from entity context
                if context.get("mentioned_in"):
                    chunk_ids.update(context["mentioned_in"])
        
        # Retrieve chunks by IDs
        # ...
        
        return RetrieverResult(
            retriever_name=self.name,
            items=items,
            query_time_ms=elapsed_ms,
            total=len(items),
        )
```

### EmbeddingService Integration

```python
# In VectorRetriever or SearchService
from apps.embedding_engine.services import EmbeddingService


class SearchService:
    def __init__(self) -> None:
        self._embedding_service = EmbeddingService()
    
    def _get_query_embedding(self, query_text: str) -> list[float]:
        """Generate embedding for query text."""
        result = self._embedding_service.embed_query(query_text)
        return result.embedding
```

### DocumentChunk FTS Integration

```python
# In KeywordRetriever
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from apps.documents_parser.models import DocumentChunk


class KeywordRetriever(BaseRetriever):
    def retrieve(
        self,
        query: SearchQuery,
        top_k: int = 10,
        **kwargs: Any,
    ) -> RetrieverResult:
        """Retrieve using PostgreSQL full-text search."""
        start_time = time.time()
        
        # Build search query
        search_query = SearchQuery(query.text, config='simple')
        
        # Execute search
        queryset = DocumentChunk.objects.annotate(
            rank=SearchRank('search_vector', search_query)
        ).filter(
            search_vector=search_query
        ).order_by('-rank')[:top_k]
        
        # Apply user filter if provided
        if query.user_id:
            queryset = queryset.filter(document__user_id=query.user_id)
        
        # Build result items
        items = [
            {
                'chunk_id': str(chunk.id),
                'document_id': str(chunk.document_id),
                'text': chunk.text,
                'score': chunk.rank,
                'source': chunk.document.original_name,
            }
            for chunk in queryset
        ]
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return RetrieverResult(
            retriever_name=self.name,
            items=items,
            query_time_ms=elapsed_ms,
            total=len(items),
        )
```

---

## Acceptance Criteria

### Core Functionality (Submodule 10.1-10.4)
- [ ] All constants use Enum pattern
- [ ] All exceptions inherit from SearchError
- [ ] All DTOs are frozen dataclasses
- [ ] BaseRetriever interface defined
- [ ] VectorRetriever wraps MilvusService
- [ ] KeywordRetriever uses PostgreSQL FTS
- [ ] GraphRetriever uses Neo4jService
- [ ] RRFFusion correctly implements formula
- [ ] SearchService coordinates all retrievers
- [ ] Hybrid search returns fused results

### API Layer (Submodule 10.5)
- [ ] REST API endpoints for all operations
- [ ] Proper authentication (IsAuthenticated)
- [ ] Request validation with DRF serializers
- [ ] Consistent response format
- [ ] OpenAPI documentation complete
- [ ] API tests with >= 80% coverage

### PostgreSQL FTS (Submodule 10.6)
- [ ] DocumentChunk has search_vector field
- [ ] Search vector auto-updates on text change
- [ ] FTS supports Chinese and English
- [ ] Migration created and tested

### Testing & Documentation (Submodule 10.7-10.8)
- [ ] Unit tests for all components
- [ ] Integration tests with real services
- [ ] Test coverage >= 80%
- [ ] Module documentation complete
- [ ] Manual test cases documented

---

## Risks & Considerations

| Risk | Mitigation |
|------|------------|
| Query Performance | Tune Milvus HNSW parameters, use caching for frequent queries |
| Entity Extraction Accuracy | Use simple keyword matching for MVP, plan for NER integration |
| FTS Language Support | Use 'simple' config for mixed Chinese/English, consider custom config |
| Result Quality | Tune RRF k parameter, add weights configuration |
| Graph Retrieval Latency | Limit max_depth, use query caching |
| Memory Usage | Limit top_k, implement pagination |

---

## Execution Order

Recommended execution order:

```
Phase 10.1 (Infrastructure)
    │
    ├── 1.1 constants.py
    ├── 1.2 exceptions.py
    ├── 1.3 dto.py
    ├── 1.4 Update settings
    └── 1.5 Create app structure
    │
    ▼
Phase 10.6 (PostgreSQL FTS)  ← Do this early to have FTS ready
    │
    ├── 6.1 Add SearchVector field
    ├── 6.2 Create migration
    ├── 6.3 Implement search function
    ├── 6.4 Add search trigger
    └── 6.5 Write FTS tests
    │
    ▼
Phase 10.2 (Retrievers)
    │
    ├── 2.1 BaseRetriever
    ├── 2.2 VectorRetriever
    ├── 2.3 KeywordRetriever
    ├── 2.4 GraphRetriever
    └── 2.5 Retriever tests
    │
    ▼
Phase 10.3 (Fusion)
    │
    ├── 3.1 RRFFusion class
    ├── 3.2 Score normalization
    ├── 3.3 Result deduplication
    ├── 3.4 Context expansion
    └── 3.5 Fusion tests
    │
    ▼
Phase 10.4 (Service)
    │
    ├── 4.1 SearchService class
    ├── 4.2 search method
    ├── 4.3 hybrid_search
    ├── 4.4 advanced_search
    ├── 4.5 get_search_suggestions
    └── 4.6 Service tests
    │
    ▼
Phase 10.5 (API Views)
    │
    ├── 5.1 serializers.py
    ├── 5.2 SearchViews
    ├── 5.3 URL routing
    ├── 5.4 Register URLs
    ├── 5.5 OpenAPI docs
    └── 5.6 API tests
    │
    ▼
Phase 10.7 (Testing & Docs)
    │
    ├── 7.1 Test fixtures
    ├── 7.2 Retriever tests
    ├── 7.3 Fusion tests
    ├── 7.4 Service tests
    ├── 7.5 Integration tests
    ├── 7.6 Verify coverage
    └── 7.7 Module documentation
    │
    ▼
Phase 10.8 (Manual Tests)
    │
    ├── 8.1 Invoke manual_test_generator agent
    ├── 8.2 Create manual test document
    └── 8.3 Document test scenarios
```

---

## Estimated Timeline

| Submodule | Estimated Hours | Working Days |
|-----------|-----------------|--------------|
| 10.1 Infrastructure Setup | 5h | 1 day |
| 10.2 Retriever Implementations | 11h | 2-3 days |
| 10.3 Fusion & Ranking | 8h | 1-2 days |
| 10.4 Search Service Layer | 12h | 2-3 days |
| 10.5 API Views Layer | 11h | 2-3 days |
| 10.6 PostgreSQL FTS Integration | 7.5h | 1-2 days |
| 10.7 Testing & Documentation | 13.5h | 3-4 days |
| 10.8 Manual Test Generation | 3.5h | 1 day |
| **Total** | **71.5h** | **14-19 days** |

---

## Files to Create/Modify

### New Files

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `apps/document_rag_search/constants.py` | Search constants | 60 |
| `apps/document_rag_search/exceptions.py` | Custom exceptions | 80 |
| `apps/document_rag_search/dto.py` | Data transfer objects | 150 |
| `apps/document_rag_search/serializers.py` | DRF serializers | 200 |
| `apps/document_rag_search/urls.py` | URL routing | 30 |
| `apps/document_rag_search/retrievers/base.py` | Base retriever | 60 |
| `apps/document_rag_search/retrievers/vector_retriever.py` | Vector retriever | 120 |
| `apps/document_rag_search/retrievers/keyword_retriever.py` | Keyword retriever | 100 |
| `apps/document_rag_search/retrievers/graph_retriever.py` | Graph retriever | 150 |
| `apps/document_rag_search/retrievers/fts_utils.py` | FTS utilities | 80 |
| `apps/document_rag_search/ranking/rrf_fusion.py` | RRF fusion | 120 |
| `apps/document_rag_search/ranking/deduplication.py` | Deduplication | 60 |
| `apps/document_rag_search/services/search_service.py` | Search service | 250 |
| `apps/document_rag_search/views/search_views.py` | Search endpoints | 180 |
| `apps/document_rag_search/tests/*.py` | All test files | 600 |
| `apps/document_rag_search/docs/README.md` | Documentation | 200 |
| `apps/document_rag_search/docs/manual_test.md` | Manual tests | 150 |

### Modified Files

| File | Changes |
|------|---------|
| `config/settings/base.py` | Add SEARCH_CONFIG |
| `config/urls.py` | Include search URLs |
| `apps/documents_parser/models.py` | Add search_vector field |
| `apps/documents_parser/migrations/` | New migration for FTS |

---

## Summary

Phase 10 implements the document RAG search module as the search layer for the document processing workflow:

1. **Architecture Alignment**: Follows the same layer architecture as Phase 6/7/8/9 (Constants → DTOs → Retriever → Service → API)
2. **Code Style Consistency**: Uses Enum for constants, frozen dataclasses for DTOs, exception hierarchy
3. **Integration Ready**: Coordinates all existing modules (Milvus, Neo4j, PostgreSQL, Embedding)
4. **Testing Strategy**: Comprehensive unit, integration, and E2E tests with 80%+ coverage
5. **MVP Focus**: Simple RRF fusion, basic entity extraction, PostgreSQL FTS - suitable for initial validation

**Key Features**:
- Three-level hybrid search (Vector + Keyword + Graph)
- RRF (Reciprocal Rank Fusion) for result ranking
- PostgreSQL full-text search with Chinese/English support
- Extensible retriever architecture
- Advanced search with filters and context expansion
- Search suggestions for auto-complete

**Total Estimated Time**: ~72 hours (14-19 working days)

---

*Generated: 2026-03-11*
*Plan for Phase 10: Document RAG Search Module*
*Aligned with Phase 6/7/8/9 patterns*
