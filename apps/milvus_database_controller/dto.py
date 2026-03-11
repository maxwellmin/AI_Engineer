"""
Data Transfer Objects (DTOs) for Milvus database controller.

This module defines all dataclasses used for request and response objects
in the Milvus database controller API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# =============================================================================
# Request DTOs
# =============================================================================


@dataclass(frozen=True)
class CreateCollectionRequest:
    """Request to create a new collection.

    Attributes:
        collection_name: Name of the collection to create.
        dimension: Dimension of dense vector fields.
        auto_id: Whether to auto-generate primary keys.
        enable_dynamic_field: Whether to enable dynamic field schema.
        description: Description of the collection.
    """

    collection_name: str
    dimension: int = 1536
    auto_id: bool = False
    enable_dynamic_field: bool = True
    description: str = ""


@dataclass(frozen=True)
class InsertVectorsRequest:
    """Request to insert vectors into collection.

    Attributes:
        collection_name: Name of the target collection.
        data: List of vector records to insert.
            Each record should contain:
            - pk: Primary key (str)
            - text: Full text content (str)
            - summary: Document summary (str)
            - document: Original document content (str)
            - source: Source type (str)
            - source_name: Source name (str)
            - lt_doc_id: Link to PostgreSQL document ID (str)
            - chunk_id: Chunk sequence number (int)
            - summary_dense: Summary embedding vector (list[float])
            - text_dense: Text embedding vector (list[float])
    """

    collection_name: str
    data: list[dict[str, Any]]


@dataclass(frozen=True)
class UpsertVectorsRequest:
    """Request to upsert (insert or update) vectors.

    Attributes:
        collection_name: Name of the target collection.
        data: List of vector records to upsert.
    """

    collection_name: str
    data: list[dict[str, Any]]


@dataclass(frozen=True)
class DeleteVectorsRequest:
    """Request to delete vectors from collection.

    Attributes:
        collection_name: Name of the target collection.
        ids: List of primary keys to delete.
    """

    collection_name: str
    ids: list[str]


@dataclass(frozen=True)
class DeleteVectorsByFilterRequest:
    """Request to delete vectors by filter expression.

    Attributes:
        collection_name: Name of the target collection.
        filter_expr: Filter expression to match vectors to delete.
    """

    collection_name: str
    filter_expr: str


@dataclass(frozen=True)
class SearchRequest:
    """Request for single vector field search.

    Attributes:
        collection_name: Name of the collection to search.
        query_vector: Query vector for similarity search.
        anns_field: Vector field to search (e.g., "summary_dense", "text_dense").
        top_k: Number of results to return.
        filter_expr: Optional filter expression.
        output_fields: Fields to include in results.
        search_params: Additional search parameters.
    """

    collection_name: str
    query_vector: list[float]
    anns_field: str
    top_k: int = 10
    filter_expr: str = ""
    output_fields: list[str] | None = None
    search_params: dict[str, Any] | None = None


@dataclass(frozen=True)
class HybridSearchRequest:
    """Request for hybrid search across multiple vector fields.

    Attributes:
        collection_name: Name of the collection to search.
        query_text: Original query text (for BM25).
        query_vectors: Query vectors keyed by field name.
            e.g., {"summary_dense": [...], "text_dense": [...]}
        top_k: Number of results to return.
        filter_expr: Optional filter expression.
        output_fields: Fields to include in results.
        rerank_method: Reranking method ("rrf" or "weighted").
        rrf_k: RRF parameter for reciprocal rank fusion.
        weights: Weights for weighted reranking (sum should be 1.0).
    """

    collection_name: str
    query_text: str
    query_vectors: dict[str, list[float]]
    top_k: int = 10
    filter_expr: str = ""
    output_fields: list[str] | None = None
    rerank_method: str = "rrf"
    rrf_k: int = 60
    weights: list[float] | None = None


@dataclass(frozen=True)
class BM25SearchRequest:
    """Request for BM25 sparse vector search.

    Attributes:
        collection_name: Name of the collection to search.
        query_text: Query text for BM25 search.
        top_k: Number of results to return.
        filter_expr: Optional filter expression.
        output_fields: Fields to include in results.
    """

    collection_name: str
    query_text: str
    top_k: int = 10
    filter_expr: str = ""
    output_fields: list[str] | None = None


@dataclass(frozen=True)
class QueryRequest:
    """Request to query vectors by filter expression.

    Attributes:
        collection_name: Name of the collection to query.
        filter_expr: Filter expression to match vectors.
        output_fields: Fields to include in results.
        limit: Maximum number of results.
        offset: Offset for pagination.
    """

    collection_name: str
    filter_expr: str
    output_fields: list[str] | None = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetVectorRequest:
    """Request to retrieve a single vector by ID.

    Attributes:
        collection_name: Name of the collection.
        pk: Primary key of the vector to retrieve.
        output_fields: Fields to include in result.
    """

    collection_name: str
    pk: str
    output_fields: list[str] | None = None


# =============================================================================
# Response DTOs
# =============================================================================


@dataclass(frozen=True)
class CollectionInfo:
    """Information about a collection.

    Attributes:
        name: Name of the collection.
        description: Description of the collection.
        num_entities: Number of entities in the collection.
        schema: Collection schema information.
        loaded: Whether the collection is loaded into memory.
    """

    name: str
    description: str
    num_entities: int
    schema: dict[str, Any]
    loaded: bool


@dataclass(frozen=True)
class InsertResult:
    """Result of vector insertion.

    Attributes:
        inserted_count: Number of vectors inserted.
        inserted_ids: List of primary keys of inserted vectors.
    """

    inserted_count: int
    inserted_ids: list[str]


@dataclass(frozen=True)
class UpsertResult:
    """Result of vector upsertion.

    Attributes:
        upserted_count: Number of vectors upserted.
        upserted_ids: List of primary keys of upserted vectors.
    """

    upserted_count: int
    upserted_ids: list[str]


@dataclass(frozen=True)
class DeleteResult:
    """Result of vector deletion.

    Attributes:
        deleted_count: Number of vectors deleted.
    """

    deleted_count: int


@dataclass(frozen=True)
class SearchResultItem:
    """Single search result item.

    Attributes:
        id: Primary key of the result.
        distance: Similarity distance/score.
        text: Full text content.
        summary: Document summary.
        document: Original document content.
        source: Source type.
        source_name: Source name.
        lt_doc_id: Link to PostgreSQL document ID.
        chunk_id: Chunk sequence number.
    """

    id: str
    distance: float
    text: str = ""
    summary: str = ""
    document: str = ""
    source: str = ""
    source_name: str = ""
    lt_doc_id: str = ""
    chunk_id: int = 0


@dataclass(frozen=True)
class SearchResult:
    """Result of vector search.

    Attributes:
        items: List of search result items.
        total: Total number of results.
        query_time_ms: Query execution time in milliseconds.
    """

    items: list[SearchResultItem]
    total: int
    query_time_ms: float = 0.0


@dataclass(frozen=True)
class HybridSearchResult:
    """Result of hybrid search.

    Attributes:
        items: List of search result items with combined scores.
        total: Total number of results.
        query_time_ms: Query execution time in milliseconds.
        search_details: Details about individual search results.
    """

    items: list[SearchResultItem]
    total: int
    query_time_ms: float = 0.0
    search_details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class QueryResult:
    """Result of vector query.

    Attributes:
        items: List of query result items.
        total: Total number of matching items.
    """

    items: list[dict[str, Any]]
    total: int


@dataclass(frozen=True)
class VectorRecord:
    """A single vector record with all fields.

    Attributes:
        pk: Primary key.
        text: Full text content.
        summary: Document summary.
        document: Original document content.
        source: Source type.
        source_name: Source name.
        lt_doc_id: Link to PostgreSQL document ID.
        chunk_id: Chunk sequence number.
        summary_dense: Summary embedding vector.
        text_dense: Text embedding vector.
    """

    pk: str
    text: str
    summary: str
    document: str
    source: str
    source_name: str
    lt_doc_id: str
    chunk_id: int
    summary_dense: list[float]
    text_dense: list[float]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Milvus insertion.

        Note: For nullable SPARSE_FLOAT_VECTOR fields in Milvus, omitting the field
        is equivalent to null. We do not include text_sparse when BM25 is not used.
        """
        return {
            "pk": self.pk,
            "text": self.text,
            "summary": self.summary,
            "document": self.document,
            "source": self.source,
            "source_name": self.source_name,
            "lt_doc_id": self.lt_doc_id,
            "chunk_id": self.chunk_id,
            "summary_dense": self.summary_dense,
            "text_dense": self.text_dense,
            # text_sparse is omitted for nullable sparse vector field
            # When BM25 is implemented, add "text_sparse": sparse_vector_dict
        }


@dataclass(frozen=True)
class IndexInfo:
    """Information about an index.

    Attributes:
        index_name: Name of the index.
        field_name: Name of the indexed field.
        index_type: Type of index.
        metric_type: Similarity metric type.
        params: Index parameters.
    """

    index_name: str
    field_name: str
    index_type: str
    metric_type: str
    params: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Helper Functions
# =============================================================================


def create_vector_record(
    pk: str,
    text: str,
    summary_dense: list[float],
    text_dense: list[float],
    summary: str = "",
    document: str = "",
    source: str = "upload",
    source_name: str = "",
    lt_doc_id: str = "",
    chunk_id: int = 0,
) -> VectorRecord:
    """Create a VectorRecord with default values.

    Args:
        pk: Primary key.
        text: Full text content.
        summary_dense: Summary embedding vector.
        text_dense: Text embedding vector.
        summary: Document summary.
        document: Original document content.
        source: Source type.
        source_name: Source name.
        lt_doc_id: Link to PostgreSQL document ID.
        chunk_id: Chunk sequence number.

    Returns:
        VectorRecord instance.
    """
    return VectorRecord(
        pk=pk,
        text=text,
        summary=summary,
        document=document,
        source=source,
        source_name=source_name,
        lt_doc_id=lt_doc_id,
        chunk_id=chunk_id,
        summary_dense=summary_dense,
        text_dense=text_dense,
    )
