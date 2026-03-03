"""
API serializers for Milvus database controller.

This module defines all DRF serializers for request validation and response
formatting in the Milvus API endpoints.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers


# =============================================================================
# Collection Serializers
# =============================================================================


class CreateCollectionSerializer(serializers.Serializer):
    """Request serializer for collection creation."""

    collection_name = serializers.CharField(
        max_length=255,
        help_text="Name of the collection to create",
    )
    dimension = serializers.IntegerField(
        default=1536,
        min_value=1,
        max_value=32768,
        help_text="Dimension of dense vector fields",
    )
    description = serializers.CharField(
        default="",
        allow_blank=True,
        max_length=1000,
        help_text="Description of the collection",
    )
    create_indexes = serializers.BooleanField(
        default=True,
        help_text="Whether to create indexes automatically",
    )


class CollectionInfoSerializer(serializers.Serializer):
    """Response serializer for collection info."""

    name = serializers.CharField(help_text="Collection name")
    description = serializers.CharField(help_text="Collection description")
    num_entities = serializers.IntegerField(help_text="Number of entities in collection")
    schema = serializers.DictField(help_text="Collection schema fields")
    loaded = serializers.BooleanField(help_text="Whether collection is loaded into memory")


class CollectionStatsSerializer(serializers.Serializer):
    """Response serializer for collection statistics."""

    collection_name = serializers.CharField(help_text="Collection name")
    row_count = serializers.IntegerField(help_text="Number of rows in collection")
    index_info = serializers.ListField(help_text="Index information")
    loaded = serializers.BooleanField(help_text="Whether collection is loaded")


class CollectionListItemSerializer(serializers.Serializer):
    """Serializer for collection list item."""

    name = serializers.CharField(help_text="Collection name")


class CollectionListSerializer(serializers.Serializer):
    """Response serializer for collection list."""

    collections = CollectionListItemSerializer(many=True)
    total = serializers.IntegerField(help_text="Total number of collections")


# =============================================================================
# Vector Serializers
# =============================================================================


class VectorDataSerializer(serializers.Serializer):
    """Serializer for single vector data."""

    pk = serializers.CharField(
        max_length=255,
        help_text="Primary key of the vector",
    )
    text = serializers.CharField(
        help_text="Full text content",
    )
    summary = serializers.CharField(
        allow_blank=True,
        default="",
        help_text="Document summary",
    )
    document = serializers.CharField(
        allow_blank=True,
        default="",
        help_text="Original document content",
    )
    source = serializers.CharField(
        max_length=100,
        default="upload",
        help_text="Source type (e.g., 'upload', 'web_crawl')",
    )
    source_name = serializers.CharField(
        max_length=255,
        allow_blank=True,
        default="",
        help_text="Source name or filename",
    )
    lt_doc_id = serializers.CharField(
        max_length=255,
        allow_blank=True,
        default="",
        help_text="Link to PostgreSQL document ID",
    )
    chunk_id = serializers.IntegerField(
        default=0,
        min_value=0,
        help_text="Chunk sequence number",
    )
    summary_dense = serializers.ListField(
        child=serializers.FloatField(),
        allow_empty=False,
        help_text="Summary embedding vector",
    )
    text_dense = serializers.ListField(
        child=serializers.FloatField(),
        allow_empty=False,
        help_text="Text embedding vector",
    )
    text_sparse = serializers.DictField(
        child=serializers.FloatField(),
        required=False,
        help_text="Sparse vector for BM25 search (index -> value mapping)",
    )

    def validate_summary_dense(self, value: list[float]) -> list[float]:
        """Validate summary_dense vector dimension."""
        if len(value) != 1536:
            raise serializers.ValidationError(
                f"summary_dense must have 1536 dimensions, got {len(value)}"
            )
        return value

    def validate_text_dense(self, value: list[float]) -> list[float]:
        """Validate text_dense vector dimension."""
        if len(value) != 1536:
            raise serializers.ValidationError(
                f"text_dense must have 1536 dimensions, got {len(value)}"
            )
        return value


class InsertVectorsSerializer(serializers.Serializer):
    """Request serializer for vector insertion."""

    collection_name = serializers.CharField(
        max_length=255,
        help_text="Name of the target collection",
    )
    data = VectorDataSerializer(
        many=True,
        help_text="List of vector records to insert",
    )

    def validate_data(self, value: list[dict]) -> list[dict]:
        """Validate data list is not empty."""
        if not value:
            raise serializers.ValidationError("Data list cannot be empty")
        if len(value) > 10000:
            raise serializers.ValidationError("Maximum 10000 vectors per request")
        return value


class UpsertVectorsSerializer(InsertVectorsSerializer):
    """Request serializer for vector upsertion."""

    pass


class QueryVectorsSerializer(serializers.Serializer):
    """Request serializer for vector query."""

    collection_name = serializers.CharField(
        max_length=255,
        help_text="Name of the target collection",
    )
    filter_expr = serializers.CharField(
        help_text="Filter expression to match vectors",
    )
    output_fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
        help_text="Fields to include in results",
    )
    limit = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=1000,
        help_text="Maximum number of results",
    )
    offset = serializers.IntegerField(
        default=0,
        min_value=0,
        help_text="Offset for pagination",
    )


class DeleteVectorsByIdsSerializer(serializers.Serializer):
    """Request serializer for deleting vectors by IDs."""

    collection_name = serializers.CharField(
        max_length=255,
        help_text="Name of the target collection",
    )
    ids = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
        help_text="List of primary keys to delete",
    )

    def validate_ids(self, value: list[str]) -> list[str]:
        """Validate ids list."""
        if len(value) > 10000:
            raise serializers.ValidationError("Maximum 10000 IDs per request")
        return value


class DeleteVectorsByFilterSerializer(serializers.Serializer):
    """Request serializer for deleting vectors by filter."""

    collection_name = serializers.CharField(
        max_length=255,
        help_text="Name of the target collection",
    )
    filter_expr = serializers.CharField(
        help_text="Filter expression to match vectors to delete",
    )


# =============================================================================
# Search Serializers
# =============================================================================


class VectorSearchSerializer(serializers.Serializer):
    """Request serializer for vector search."""

    collection_name = serializers.CharField(
        max_length=255,
        help_text="Name of the collection to search",
    )
    query_vector = serializers.ListField(
        child=serializers.FloatField(),
        allow_empty=False,
        help_text="Query embedding vector",
    )
    anns_field = serializers.CharField(
        default="text_dense",
        help_text="Vector field to search (e.g., 'text_dense', 'summary_dense')",
    )
    top_k = serializers.IntegerField(
        default=10,
        min_value=1,
        max_value=100,
        help_text="Number of results to return",
    )
    filter_expr = serializers.CharField(
        default="",
        allow_blank=True,
        help_text="Optional filter expression",
    )
    output_fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
        help_text="Fields to include in results",
    )

    def validate_query_vector(self, value: list[float]) -> list[float]:
        """Validate query vector dimension."""
        if len(value) != 1536:
            raise serializers.ValidationError(
                f"query_vector must have 1536 dimensions, got {len(value)}"
            )
        return value


class HybridSearchSerializer(serializers.Serializer):
    """Request serializer for hybrid search."""

    collection_name = serializers.CharField(
        max_length=255,
        help_text="Name of the collection to search",
    )
    query_text = serializers.CharField(
        help_text="Original query text for BM25 search",
    )
    query_vectors = serializers.DictField(
        child=serializers.ListField(child=serializers.FloatField()),
        help_text="Query vectors keyed by field name (e.g., {'text_dense': [...]})",
    )
    top_k = serializers.IntegerField(
        default=10,
        min_value=1,
        max_value=100,
        help_text="Number of results to return",
    )
    filter_expr = serializers.CharField(
        default="",
        allow_blank=True,
        help_text="Optional filter expression",
    )
    output_fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
        help_text="Fields to include in results",
    )
    rerank_method = serializers.ChoiceField(
        choices=["rrf", "weighted"],
        default="rrf",
        help_text="Reranking method",
    )
    rrf_k = serializers.IntegerField(
        default=60,
        min_value=1,
        help_text="RRF parameter for reciprocal rank fusion",
    )
    weights = serializers.ListField(
        child=serializers.FloatField(),
        required=False,
        allow_null=True,
        help_text="Weights for weighted reranking (sum should be 1.0)",
    )

    def validate_query_vectors(self, value: dict) -> dict:
        """Validate query vectors."""
        if not value:
            raise serializers.ValidationError("query_vectors cannot be empty")

        for field_name, vector in value.items():
            if len(vector) != 1536:
                raise serializers.ValidationError(
                    f"Vector for field '{field_name}' must have 1536 dimensions, "
                    f"got {len(vector)}"
                )

        return value

    def validate_weights(self, value: list[float] | None) -> list[float] | None:
        """Validate weights sum to 1.0."""
        if value is not None:
            if len(value) < 2:
                raise serializers.ValidationError("At least 2 weights are required")
            weight_sum = sum(value)
            if abs(weight_sum - 1.0) > 0.001:
                raise serializers.ValidationError(
                    f"Weights must sum to 1.0, got {weight_sum}"
                )
        return value


class DocumentSearchSerializer(serializers.Serializer):
    """Request serializer for document-specific search."""

    collection_name = serializers.CharField(
        max_length=255,
        help_text="Name of the collection to search",
    )
    document_id = serializers.CharField(
        help_text="PostgreSQL document ID to search within",
    )
    query_vector = serializers.ListField(
        child=serializers.FloatField(),
        allow_empty=False,
        help_text="Query embedding vector",
    )
    top_k = serializers.IntegerField(
        default=5,
        min_value=1,
        max_value=50,
        help_text="Number of results to return",
    )

    def validate_query_vector(self, value: list[float]) -> list[float]:
        """Validate query vector dimension."""
        if len(value) != 1536:
            raise serializers.ValidationError(
                f"query_vector must have 1536 dimensions, got {len(value)}"
            )
        return value


# =============================================================================
# Response Serializers
# =============================================================================


class SearchResultItemSerializer(serializers.Serializer):
    """Serializer for single search result item."""

    pk = serializers.CharField(help_text="Primary key of the result")
    distance = serializers.FloatField(help_text="Similarity distance/score")
    text = serializers.CharField(help_text="Full text content")
    summary = serializers.CharField(help_text="Document summary")
    document = serializers.CharField(help_text="Original document content")
    source = serializers.CharField(help_text="Source type")
    source_name = serializers.CharField(help_text="Source name")
    lt_doc_id = serializers.CharField(help_text="Link to PostgreSQL document ID")
    chunk_id = serializers.IntegerField(help_text="Chunk sequence number")


class SearchResultSerializer(serializers.Serializer):
    """Response serializer for search result."""

    items = SearchResultItemSerializer(many=True, help_text="Search result items")
    total = serializers.IntegerField(help_text="Total number of results")
    query_time_ms = serializers.FloatField(help_text="Query execution time in milliseconds")


class HybridSearchResultSerializer(serializers.Serializer):
    """Response serializer for hybrid search result."""

    items = SearchResultItemSerializer(many=True, help_text="Search result items")
    total = serializers.IntegerField(help_text="Total number of results")
    query_time_ms = serializers.FloatField(help_text="Query execution time in milliseconds")
    search_details = serializers.DictField(
        required=False,
        help_text="Details about individual search results",
    )


class InsertResultSerializer(serializers.Serializer):
    """Response serializer for insert result."""

    inserted_count = serializers.IntegerField(help_text="Number of vectors inserted")
    inserted_ids = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of primary keys of inserted vectors",
    )


class UpsertResultSerializer(serializers.Serializer):
    """Response serializer for upsert result."""

    upserted_count = serializers.IntegerField(help_text="Number of vectors upserted")
    upserted_ids = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of primary keys of upserted vectors",
    )


class DeleteResultSerializer(serializers.Serializer):
    """Response serializer for delete result."""

    deleted_count = serializers.IntegerField(help_text="Number of vectors deleted")


class QueryResultItemSerializer(serializers.Serializer):
    """Serializer for single query result item."""

    pk = serializers.CharField(help_text="Primary key")
    text = serializers.CharField(required=False, help_text="Text content")
    summary = serializers.CharField(required=False, help_text="Summary")
    document = serializers.CharField(required=False, help_text="Document content")
    source = serializers.CharField(required=False, help_text="Source type")
    source_name = serializers.CharField(required=False, help_text="Source name")
    lt_doc_id = serializers.CharField(required=False, help_text="Document ID")
    chunk_id = serializers.IntegerField(required=False, help_text="Chunk ID")


class QueryResultSerializer(serializers.Serializer):
    """Response serializer for query result."""

    items = serializers.ListField(help_text="Query result items")
    total = serializers.IntegerField(help_text="Total number of matching items")


class HealthCheckSerializer(serializers.Serializer):
    """Response serializer for health check."""

    status = serializers.CharField(help_text="Health status ('healthy' or 'unhealthy')")
    connected = serializers.BooleanField(help_text="Whether connected to Milvus")
    collections_count = serializers.IntegerField(
        allow_null=True,
        help_text="Number of collections (null if not connected)",
    )
    error = serializers.CharField(
        allow_null=True,
        required=False,
        help_text="Error message if unhealthy",
    )


# =============================================================================
# Load/Release Serializers
# =============================================================================


class LoadCollectionSerializer(serializers.Serializer):
    """Response serializer for load collection."""

    message = serializers.CharField(help_text="Status message")
    collection_name = serializers.CharField(help_text="Collection name")
    loaded = serializers.BooleanField(help_text="Whether collection is loaded")


class ReleaseCollectionSerializer(serializers.Serializer):
    """Response serializer for release collection."""

    message = serializers.CharField(help_text="Status message")
    collection_name = serializers.CharField(help_text="Collection name")
    released = serializers.BooleanField(help_text="Whether collection is released")


class DropCollectionSerializer(serializers.Serializer):
    """Response serializer for drop collection."""

    message = serializers.CharField(help_text="Status message")
    collection_name = serializers.CharField(help_text="Collection name")
    dropped = serializers.BooleanField(help_text="Whether collection is dropped")


class ErrorSerializer(serializers.Serializer):
    """Generic error response serializer."""

    error = serializers.CharField(help_text="Error message")
    detail = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Detailed error information",
    )
