"""
Data Transfer Objects (DTOs) for document RAG search module.

This module defines all dataclasses used for request and response objects
in the document RAG search module API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# =============================================================================
# Request DTOs
# =============================================================================


@dataclass(frozen=True)
class SearchQuery:
    """Search query with text and optional embedding.

    Represents a search query that can be used across multiple retrievers.
    The embedding is optional and will be generated if not provided.

    Attributes:
        text: The search query text.
        embedding: Pre-computed embedding vector (optional).
        user_id: User ID for access control filtering (optional).
    """

    text: str
    embedding: list[float] | None = None
    user_id: str | None = None


@dataclass(frozen=True)
class HybridSearchRequest:
    """Request for hybrid search with multiple retrievers.

    Hybrid search combines results from multiple retrievers (vector, keyword, graph)
    and fuses them using RRF (Reciprocal Rank Fusion) ranking.

    Attributes:
        query: The search query text.
        top_k: Maximum number of results to return.
        use_vector: Whether to include vector (Milvus) retrieval.
        use_keyword: Whether to include keyword (PostgreSQL FTS) retrieval.
        use_graph: Whether to include graph (Neo4j) retrieval.
        filters: Optional filters for the search (user_id, document_ids, etc.).
        rrf_k: RRF parameter for fusion ranking (default: 60).
        weights: Optional weights for each retriever (e.g., {"vector": 0.5}).
    """

    query: str
    top_k: int = 10
    use_vector: bool = True
    use_keyword: bool = True
    use_graph: bool = False
    filters: dict[str, Any] = field(default_factory=dict)
    rrf_k: int = 60
    weights: dict[str, float] | None = None


@dataclass(frozen=True)
class AdvancedSearchRequest:
    """Request for advanced search with filters and options.

    Advanced search provides more granular control over search parameters
    and supports filtering by user, document, date range, and file types.

    Attributes:
        query: The search query text.
        top_k: Maximum number of results to return.
        use_vector: Whether to include vector retrieval.
        use_keyword: Whether to include keyword retrieval.
        use_graph: Whether to include graph retrieval.
        user_id: Filter by user ID (optional).
        document_ids: Filter by specific document IDs (optional).
        date_from: Filter documents created after this date (optional).
        date_to: Filter documents created before this date (optional).
        file_types: Filter by file types (e.g., ["pdf", "docx"]) (optional).
        rrf_k: RRF parameter for fusion ranking.
        expand_context: Whether to include neighbor chunks in results.
        context_window: Number of neighbor chunks to include on each side.
    """

    query: str
    top_k: int = 10
    use_vector: bool = True
    use_keyword: bool = True
    use_graph: bool = False
    user_id: str | None = None
    document_ids: list[str] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    file_types: list[str] | None = None
    rrf_k: int = 60
    expand_context: bool = False
    context_window: int = 1


@dataclass(frozen=True)
class SearchSuggestionsRequest:
    """Request for search suggestions (auto-complete).

    Attributes:
        prefix: The query prefix to generate suggestions for.
        limit: Maximum number of suggestions to return.
    """

    prefix: str
    limit: int = 5


# =============================================================================
# Response DTOs
# =============================================================================


@dataclass(frozen=True)
class SearchResultItem:
    """Single search result item.

    Represents a single chunk retrieved from the search operation,
    with its relevance score and metadata.

    Attributes:
        chunk_id: Unique identifier for the document chunk.
        document_id: ID of the parent document.
        text: The text content of the chunk.
        score: Relevance score (0.0 to 1.0).
        source: Source file name or identifier.
        metadata: Additional metadata (page number, chunk index, etc.).
        retriever_scores: Individual scores from each retriever.
    """

    chunk_id: str
    document_id: str
    text: str
    score: float
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    retriever_scores: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResponse:
    """Response for search operations.

    Contains the search results along with metadata about the search operation.

    Attributes:
        results: List of search result items.
        total: Total number of results.
        query_time_ms: Query execution time in milliseconds.
        retrievers_used: List of retrievers used in the search.
    """

    results: list[SearchResultItem]
    total: int
    query_time_ms: float
    retrievers_used: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RetrieverResult:
    """Result from a single retriever.

    Represents the output from a single retriever before fusion.

    Attributes:
        retriever_name: Name of the retriever (vector, keyword, graph).
        items: List of result items from this retriever.
        query_time_ms: Query execution time in milliseconds.
        total: Total number of items found.
        error: Error message if the retriever failed (optional).
    """

    retriever_name: str
    items: list[dict[str, Any]]
    query_time_ms: float
    total: int
    error: str | None = None


@dataclass(frozen=True)
class RankedResult:
    """Result after RRF ranking.

    Represents a result item after being ranked by the fusion algorithm.

    Attributes:
        chunk_id: Unique identifier for the document chunk.
        document_id: ID of the parent document.
        text: The text content of the chunk.
        score: Fused relevance score (0.0 to 1.0).
        source: Source file name or identifier.
        metadata: Additional metadata.
        retriever_scores: Individual scores from each retriever.
    """

    chunk_id: str
    document_id: str
    text: str
    score: float
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    retriever_scores: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchSuggestionsResponse:
    """Response for search suggestions.

    Attributes:
        suggestions: List of suggested search terms.
        total: Total number of suggestions available.
    """

    suggestions: list[str]
    total: int


# =============================================================================
# Configuration DTOs
# =============================================================================


@dataclass(frozen=True)
class RetrieverConfig:
    """Configuration for a single retriever.

    Attributes:
        enabled: Whether this retriever is enabled.
        timeout: Timeout in seconds for retriever operations.
    """

    enabled: bool = True
    timeout: int = 10


@dataclass(frozen=True)
class VectorRetrieverConfig(RetrieverConfig):
    """Configuration for vector retriever.

    Attributes:
        collection_name: Milvus collection name to search.
        anns_field: Vector field to search (text_dense, summary_dense).
        nprobe: Number of clusters to probe in IVF search.
    """

    collection_name: str = "documents"
    anns_field: str = "text_dense"
    nprobe: int = 10


@dataclass(frozen=True)
class KeywordRetrieverConfig(RetrieverConfig):
    """Configuration for keyword retriever.

    Attributes:
        fts_config: PostgreSQL FTS configuration name.
    """

    fts_config: str = "simple"


@dataclass(frozen=True)
class GraphRetrieverConfig(RetrieverConfig):
    """Configuration for graph retriever.

    Attributes:
        max_depth: Maximum depth for graph traversal.
        entity_limit: Maximum number of entities to consider.
    """

    max_depth: int = 2
    entity_limit: int = 10


@dataclass(frozen=True)
class SearchConfig:
    """Configuration for search operations.

    Contains all configuration parameters for the search module.

    Attributes:
        default_top_k: Default number of results to return.
        default_rrf_k: Default RRF parameter.
        max_query_length: Maximum allowed query length.
        min_query_length: Minimum required query length.
        vector_weight: Default weight for vector retriever.
        keyword_weight: Default weight for keyword retriever.
        graph_weight: Default weight for graph retriever.
        enable_suggestions: Whether search suggestions are enabled.
        context_expansion_enabled: Whether context expansion is enabled.
        context_window: Number of neighbor chunks to include.
    """

    default_top_k: int = 10
    default_rrf_k: int = 60
    max_query_length: int = 500
    min_query_length: int = 2
    vector_weight: float = 0.4
    keyword_weight: float = 0.3
    graph_weight: float = 0.3
    enable_suggestions: bool = True
    context_expansion_enabled: bool = False
    context_window: int = 1


# =============================================================================
# Helper Functions
# =============================================================================


def create_search_result_item(
    chunk_id: str,
    document_id: str,
    text: str,
    score: float,
    source: str = "",
    metadata: dict[str, Any] | None = None,
    retriever_scores: dict[str, float] | None = None,
) -> SearchResultItem:
    """Create a SearchResultItem with default values.

    Args:
        chunk_id: Unique identifier for the chunk.
        document_id: ID of the parent document.
        text: Text content of the chunk.
        score: Relevance score.
        source: Source file name.
        metadata: Additional metadata.
        retriever_scores: Scores from individual retrievers.

    Returns:
        A new SearchResultItem instance.
    """
    return SearchResultItem(
        chunk_id=chunk_id,
        document_id=document_id,
        text=text,
        score=score,
        source=source,
        metadata=metadata or {},
        retriever_scores=retriever_scores or {},
    )


def create_search_response(
    results: list[SearchResultItem],
    query_time_ms: float,
    retrievers_used: list[str] | None = None,
) -> SearchResponse:
    """Create a SearchResponse with computed total.

    Args:
        results: List of search result items.
        query_time_ms: Query execution time in milliseconds.
        retrievers_used: List of retrievers used.

    Returns:
        A new SearchResponse instance.
    """
    return SearchResponse(
        results=results,
        total=len(results),
        query_time_ms=query_time_ms,
        retrievers_used=retrievers_used or [],
    )
