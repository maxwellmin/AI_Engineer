"""
API serializers for document RAG search module.

This module defines all DRF serializers for request validation and response
formatting in the RAG search API endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from rest_framework import serializers

from apps.document_rag_search.constants import (
    DEFAULT_RRF_K,
    DEFAULT_TOP_K,
    MAX_QUERY_LENGTH,
    MIN_QUERY_LENGTH,
)


# =============================================================================
# Filter Serializers
# =============================================================================


class SearchFiltersSerializer(serializers.Serializer):
    """Serializer for search filters.

    Filters can be applied to narrow down search results based on
    user, documents, or other criteria.

    Attributes:
        user_id: Filter by user ID (UUID string).
        document_ids: Filter by specific document IDs (list of UUIDs).
        date_from: Filter documents created after this date (ISO 8601).
        date_to: Filter documents created before this date (ISO 8601).
        file_types: Filter by file types (e.g., ['pdf', 'docx']).
    """

    user_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Filter by user ID",
    )
    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_null=True,
        allow_empty=True,
        help_text="Filter by specific document IDs",
    )
    date_from = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Filter documents created after this date (ISO 8601)",
    )
    date_to = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Filter documents created before this date (ISO 8601)",
    )
    file_types = serializers.ListField(
        child=serializers.CharField(max_length=20),
        required=False,
        allow_null=True,
        allow_empty=True,
        help_text="Filter by file types (e.g., ['pdf', 'docx'])",
    )

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate date range.

        Args:
            data: Validated data dictionary.

        Returns:
            Validated data.

        Raises:
            ValidationError: If date_from is after date_to.
        """
        date_from = data.get("date_from")
        date_to = data.get("date_to")

        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError(
                {"date_to": "date_to must be after date_from"}
            )

        return data


class RetrieverWeightsSerializer(serializers.Serializer):
    """Serializer for retriever weights configuration.

    Allows customizing the weight of each retriever in the fusion process.
    Weights should be positive numbers; they will be normalized to sum to 1.0.

    Attributes:
        vector: Weight for vector retriever (Milvus).
        keyword: Weight for keyword retriever (PostgreSQL FTS).
        graph: Weight for graph retriever (Neo4j).
    """

    vector = serializers.FloatField(
        required=False,
        min_value=0.0,
        max_value=1.0,
        help_text="Weight for vector retriever",
    )
    keyword = serializers.FloatField(
        required=False,
        min_value=0.0,
        max_value=1.0,
        help_text="Weight for keyword retriever",
    )
    graph = serializers.FloatField(
        required=False,
        min_value=0.0,
        max_value=1.0,
        help_text="Weight for graph retriever",
    )


# =============================================================================
# Request Serializers
# =============================================================================


class SimpleSearchRequestSerializer(serializers.Serializer):
    """Request serializer for simple vector search.

    Simple search uses only vector retrieval for quick queries.
    For more control, use hybrid search instead.

    Attributes:
        query: Search query text.
        top_k: Maximum number of results to return.
        user_id: Optional user filter for access control.
    """

    query = serializers.CharField(
        max_length=MAX_QUERY_LENGTH,
        help_text="Search query text",
    )
    top_k = serializers.IntegerField(
        default=DEFAULT_TOP_K,
        min_value=1,
        max_value=100,
        help_text="Maximum number of results to return",
    )
    user_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Optional user filter for access control",
    )

    def validate_query(self, value: str) -> str:
        """Validate query length.

        Args:
            value: Query text.

        Returns:
            Validated query text.

        Raises:
            ValidationError: If query is too short or empty.
        """
        stripped = value.strip()
        if len(stripped) < MIN_QUERY_LENGTH:
            raise serializers.ValidationError(
                f"Query must be at least {MIN_QUERY_LENGTH} characters"
            )
        return stripped


class HybridSearchRequestSerializer(serializers.Serializer):
    """Request serializer for hybrid search with multiple retrievers.

    Hybrid search combines results from multiple retrievers (vector, keyword, graph)
    and fuses them using RRF (Reciprocal Rank Fusion) ranking.

    Attributes:
        query: Search query text.
        top_k: Maximum number of results to return.
        use_vector: Whether to include vector (Milvus) retrieval.
        use_keyword: Whether to include keyword (PostgreSQL FTS) retrieval.
        use_graph: Whether to include graph (Neo4j) retrieval.
        filters: Optional filters for search results.
        rrf_k: RRF parameter for fusion ranking.
        weights: Optional weights for each retriever.
    """

    query = serializers.CharField(
        max_length=MAX_QUERY_LENGTH,
        help_text="Search query text",
    )
    top_k = serializers.IntegerField(
        default=DEFAULT_TOP_K,
        min_value=1,
        max_value=100,
        help_text="Maximum number of results to return",
    )
    use_vector = serializers.BooleanField(
        default=True,
        help_text="Whether to include vector (Milvus) retrieval",
    )
    use_keyword = serializers.BooleanField(
        default=True,
        help_text="Whether to include keyword (PostgreSQL FTS) retrieval",
    )
    use_graph = serializers.BooleanField(
        default=False,
        help_text="Whether to include graph (Neo4j) retrieval",
    )
    filters = SearchFiltersSerializer(
        required=False,
        allow_null=True,
        help_text="Optional filters for search results",
    )
    rrf_k = serializers.IntegerField(
        default=DEFAULT_RRF_K,
        min_value=1,
        max_value=1000,
        help_text="RRF parameter for fusion ranking (default: 60)",
    )
    weights = RetrieverWeightsSerializer(
        required=False,
        allow_null=True,
        help_text="Optional weights for each retriever in fusion",
    )

    def validate_query(self, value: str) -> str:
        """Validate query length.

        Args:
            value: Query text.

        Returns:
            Validated query text.

        Raises:
            ValidationError: If query is too short or empty.
        """
        stripped = value.strip()
        if len(stripped) < MIN_QUERY_LENGTH:
            raise serializers.ValidationError(
                f"Query must be at least {MIN_QUERY_LENGTH} characters"
            )
        return stripped

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate that at least one retriever is enabled.

        Args:
            data: Validated data dictionary.

        Returns:
            Validated data.

        Raises:
            ValidationError: If no retrievers are enabled.
        """
        if not any([
            data.get("use_vector", True),
            data.get("use_keyword", True),
            data.get("use_graph", False),
        ]):
            raise serializers.ValidationError(
                "At least one retriever must be enabled"
            )
        return data


class AdvancedSearchRequestSerializer(serializers.Serializer):
    """Request serializer for advanced search with filters and options.

    Advanced search provides granular control over search parameters
    and supports filtering by user, document, date range, and file types.
    Also supports optional context expansion to include neighbor chunks.

    Attributes:
        query: Search query text.
        top_k: Maximum number of results to return.
        use_vector: Whether to include vector retrieval.
        use_keyword: Whether to include keyword retrieval.
        use_graph: Whether to include graph retrieval.
        user_id: Filter by user ID.
        document_ids: Filter by specific document IDs.
        date_from: Filter documents created after this date.
        date_to: Filter documents created before this date.
        file_types: Filter by file types.
        rrf_k: RRF parameter for fusion ranking.
        expand_context: Whether to include neighbor chunks in results.
        context_window: Number of neighbor chunks to include on each side.
    """

    query = serializers.CharField(
        max_length=MAX_QUERY_LENGTH,
        help_text="Search query text",
    )
    top_k = serializers.IntegerField(
        default=DEFAULT_TOP_K,
        min_value=1,
        max_value=100,
        help_text="Maximum number of results to return",
    )
    use_vector = serializers.BooleanField(
        default=True,
        help_text="Whether to include vector retrieval",
    )
    use_keyword = serializers.BooleanField(
        default=True,
        help_text="Whether to include keyword retrieval",
    )
    use_graph = serializers.BooleanField(
        default=False,
        help_text="Whether to include graph retrieval",
    )

    # Filters
    user_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Filter by user ID",
    )
    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_null=True,
        allow_empty=True,
        help_text="Filter by specific document IDs",
    )
    date_from = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Filter documents created after this date (ISO 8601)",
    )
    date_to = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Filter documents created before this date (ISO 8601)",
    )
    file_types = serializers.ListField(
        child=serializers.CharField(max_length=20),
        required=False,
        allow_null=True,
        allow_empty=True,
        help_text="Filter by file types (e.g., ['pdf', 'docx'])",
    )

    # Options
    rrf_k = serializers.IntegerField(
        default=DEFAULT_RRF_K,
        min_value=1,
        max_value=1000,
        help_text="RRF parameter for fusion ranking",
    )
    expand_context = serializers.BooleanField(
        default=False,
        help_text="Whether to include neighbor chunks in results",
    )
    context_window = serializers.IntegerField(
        default=1,
        min_value=0,
        max_value=5,
        help_text="Number of neighbor chunks to include on each side",
    )

    def validate_query(self, value: str) -> str:
        """Validate query length.

        Args:
            value: Query text.

        Returns:
            Validated query text.

        Raises:
            ValidationError: If query is too short or empty.
        """
        stripped = value.strip()
        if len(stripped) < MIN_QUERY_LENGTH:
            raise serializers.ValidationError(
                f"Query must be at least {MIN_QUERY_LENGTH} characters"
            )
        return stripped

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate date range and retriever selection.

        Args:
            data: Validated data dictionary.

        Returns:
            Validated data.

        Raises:
            ValidationError: If date_from > date_to or no retrievers enabled.
        """
        date_from = data.get("date_from")
        date_to = data.get("date_to")

        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError(
                {"date_to": "date_to must be after date_from"}
            )

        if not any([
            data.get("use_vector", True),
            data.get("use_keyword", True),
            data.get("use_graph", False),
        ]):
            raise serializers.ValidationError(
                "At least one retriever must be enabled"
            )

        return data


class SearchSuggestionsRequestSerializer(serializers.Serializer):
    """Request serializer for search suggestions (auto-complete).

    Uses PostgreSQL trigram similarity to find similar text
    from existing document chunks.

    Attributes:
        prefix: Query prefix to generate suggestions for.
        limit: Maximum number of suggestions to return.
    """

    prefix = serializers.CharField(
        max_length=100,
        help_text="Query prefix to generate suggestions for",
    )
    limit = serializers.IntegerField(
        default=5,
        min_value=1,
        max_value=20,
        help_text="Maximum number of suggestions to return",
    )

    def validate_prefix(self, value: str) -> str:
        """Validate prefix length.

        Args:
            value: Prefix text.

        Returns:
            Validated prefix text.

        Raises:
            ValidationError: If prefix is too short.
        """
        stripped = value.strip()
        if len(stripped) < MIN_QUERY_LENGTH:
            raise serializers.ValidationError(
                f"Prefix must be at least {MIN_QUERY_LENGTH} characters"
            )
        return stripped


# =============================================================================
# Response Serializers
# =============================================================================


class RetrieverScoresSerializer(serializers.Serializer):
    """Serializer for individual retriever scores.

    Shows the score assigned by each retriever that found this result.

    Attributes:
        vector: Score from vector retriever (if applicable).
        keyword: Score from keyword retriever (if applicable).
        graph: Score from graph retriever (if applicable).
    """

    vector = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="Score from vector retriever",
    )
    keyword = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="Score from keyword retriever",
    )
    graph = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="Score from graph retriever",
    )


class SearchResultMetadataSerializer(serializers.Serializer):
    """Serializer for search result metadata.

    Contains additional metadata about the search result chunk.

    Attributes:
        chunk_index: Index of this chunk in the document.
        page_number: Page number in the original document (if applicable).
        char_count: Character count of the chunk.
        token_count: Token count of the chunk.
    """

    chunk_index = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Index of this chunk in the document",
    )
    page_number = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Page number in the original document",
    )
    char_count = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Character count of the chunk",
    )
    token_count = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Token count of the chunk",
    )


class SearchResultItemSerializer(serializers.Serializer):
    """Serializer for single search result item.

    Represents a single chunk retrieved from the search operation,
    with its relevance score and metadata.

    Attributes:
        chunk_id: Unique identifier for the document chunk.
        document_id: ID of the parent document.
        text: The text content of the chunk.
        score: Fused relevance score (0.0 to 1.0).
        source: Source file name or identifier.
        metadata: Additional metadata (page number, chunk index, etc.).
        retriever_scores: Individual scores from each retriever.
    """

    chunk_id = serializers.UUIDField(
        help_text="Unique identifier for the document chunk",
    )
    document_id = serializers.UUIDField(
        help_text="ID of the parent document",
    )
    text = serializers.CharField(
        help_text="The text content of the chunk",
    )
    score = serializers.FloatField(
        min_value=0.0,
        max_value=1.0,
        help_text="Fused relevance score (0.0 to 1.0)",
    )
    source = serializers.CharField(
        required=False,
        default="",
        help_text="Source file name or identifier",
    )
    metadata = SearchResultMetadataSerializer(
        required=False,
        allow_null=True,
        help_text="Additional metadata",
    )
    retriever_scores = RetrieverScoresSerializer(
        required=False,
        allow_null=True,
        help_text="Individual scores from each retriever",
    )


class SearchResponseSerializer(serializers.Serializer):
    """Response serializer for search operations.

    Contains the search results along with metadata about the search operation.

    Attributes:
        results: List of search result items.
        total: Total number of results.
        query_time_ms: Query execution time in milliseconds.
        retrievers_used: List of retrievers used in the search.
    """

    results = SearchResultItemSerializer(
        many=True,
        help_text="List of search result items",
    )
    total = serializers.IntegerField(
        help_text="Total number of results",
    )
    query_time_ms = serializers.FloatField(
        help_text="Query execution time in milliseconds",
    )
    retrievers_used = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of retrievers used in the search",
    )


class SearchSuggestionsResponseSerializer(serializers.Serializer):
    """Response serializer for search suggestions.

    Attributes:
        suggestions: List of suggested search terms.
        total: Total number of suggestions available.
    """

    suggestions = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of suggested search terms",
    )
    total = serializers.IntegerField(
        help_text="Total number of suggestions available",
    )


# =============================================================================
# Health Check Serializers
# =============================================================================


class HealthCheckResponseSerializer(serializers.Serializer):
    """Response serializer for health check endpoint.

    Shows the health status of each retriever component.

    Attributes:
        vector: Health status of vector retriever.
        keyword: Health status of keyword retriever.
        graph: Health status of graph retriever.
        overall: Overall health status.
    """

    vector = serializers.BooleanField(
        help_text="Health status of vector retriever",
    )
    keyword = serializers.BooleanField(
        help_text="Health status of keyword retriever",
    )
    graph = serializers.BooleanField(
        help_text="Health status of graph retriever",
    )
    overall = serializers.BooleanField(
        help_text="Overall health status (true if any retriever is healthy)",
    )


# =============================================================================
# Error Serializers
# =============================================================================


class ErrorResponseSerializer(serializers.Serializer):
    """Generic error response serializer.

    Attributes:
        error: Error type or code.
        message: Human-readable error message.
        details: Additional error details (optional).
    """

    error = serializers.CharField(
        help_text="Error type or code",
    )
    message = serializers.CharField(
        help_text="Human-readable error message",
    )
    details = serializers.DictField(
        required=False,
        allow_null=True,
        help_text="Additional error details",
    )


# =============================================================================
# Validation Error Serializers
# =============================================================================


class ValidationErrorSerializer(serializers.Serializer):
    """Serializer for validation error details.

    Used when request validation fails.

    Attributes:
        field: Field name that failed validation.
        message: Validation error message.
    """

    field = serializers.CharField(
        help_text="Field name that failed validation",
    )
    message = serializers.CharField(
        help_text="Validation error message",
    )
