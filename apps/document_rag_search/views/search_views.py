"""
API views for document RAG search endpoints.

This module provides REST API endpoints for document RAG search operations,
including simple search, hybrid search, advanced search, and search suggestions.
"""

from __future__ import annotations

import logging
from typing import Any

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.document_rag_search.dto import (
    AdvancedSearchRequest,
    HybridSearchRequest,
    SearchSuggestionsRequest,
)
from apps.document_rag_search.exceptions import (
    EmptyQueryError,
    InvalidDateRangeError,
    InvalidQueryError,
    NoResultsError,
    QueryTooLongError,
    QueryTooShortError,
    SearchError,
    SearchServiceError,
)
from apps.document_rag_search.serializers import (
    AdvancedSearchRequestSerializer,
    ErrorResponseSerializer,
    HealthCheckResponseSerializer,
    HybridSearchRequestSerializer,
    SearchResponseSerializer,
    SearchSuggestionsRequestSerializer,
    SearchSuggestionsResponseSerializer,
    SimpleSearchRequestSerializer,
)
from apps.document_rag_search.services import SearchService


logger = logging.getLogger(__name__)


# =============================================================================
# Search Views
# =============================================================================


class SimpleSearchView(APIView):
    """Simple vector search endpoint.

    POST /api/v1/search/simple/

    Performs a simple vector-only search using Milvus.
    This is the fastest search option for quick queries.

    Request body:
        {
            "query": "What is machine learning?",
            "top_k": 10,
            "user_id": "uuid-here"  // optional, for access control
        }

    Response:
        {
            "results": [...],
            "total": 5,
            "query_time_ms": 45.2,
            "retrievers_used": ["vector"]
        }
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=SimpleSearchRequestSerializer,
        responses={
            200: SearchResponseSerializer,
            400: ErrorResponseSerializer,
            401: "Authentication required",
            500: ErrorResponseSerializer,
        },
        operation_description="""Perform a simple vector-only search using Milvus.

This is the fastest search option for quick queries. Only uses vector similarity
search via Milvus, without keyword or graph retrieval.

**Use cases:**
- Quick semantic search
- Find similar documents
- Natural language queries

**Request example:**
```json
{
    "query": "What is machine learning?",
    "top_k": 10,
    "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response example:**
```json
{
    "results": [
        {
            "chunk_id": "uuid-here",
            "document_id": "uuid-doc",
            "text": "Machine learning is a subset...",
            "score": 0.95,
            "source": "report.pdf",
            "metadata": {"chunk_index": 5, "page_number": 12},
            "retriever_scores": {"vector": 0.92}
        }
    ],
    "total": 5,
    "query_time_ms": 45.2,
    "retrievers_used": ["vector"]
}
```
""",
        operation_summary="Simple vector search",
        tags=["Search"],
        security=[{"Bearer": []}],
    )
    def post(self, request: Request) -> Response:
        """Execute simple vector search.

        Args:
            request: HTTP request with search query.

        Returns:
            Response with search results.
        """
        serializer = SimpleSearchRequestSerializer(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                f"Simple search validation failed for user {request.user.id}: "
                f"{serializer.errors}"
            )
            return Response(
                {
                    "error": "validation_error",
                    "message": "Invalid request parameters",
                    "details": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        try:
            service = SearchService()
            response = service.search(
                query=data["query"],
                top_k=data.get("top_k", 10),
                user_id=str(data["user_id"]) if data.get("user_id") else None,
            )

            return Response(
                self._format_response(response),
                status=status.HTTP_200_OK,
            )

        except EmptyQueryError:
            return Response(
                {
                    "error": "empty_query",
                    "message": "Query cannot be empty",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except QueryTooShortError as e:
            return Response(
                {
                    "error": "query_too_short",
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except QueryTooLongError as e:
            return Response(
                {
                    "error": "query_too_long",
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SearchError as e:
            logger.exception(f"Search error in simple search: {e}")
            return Response(
                {
                    "error": "search_error",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _format_response(self, response: Any) -> dict[str, Any]:
        """Format SearchResponse for JSON output.

        Args:
            response: SearchResponse DTO.

        Returns:
            Dictionary for JSON response.
        """
        return {
            "results": [
                {
                    "chunk_id": str(item.chunk_id),
                    "document_id": str(item.document_id),
                    "text": item.text,
                    "score": item.score,
                    "source": item.source,
                    "metadata": item.metadata,
                    "retriever_scores": item.retriever_scores,
                }
                for item in response.results
            ],
            "total": response.total,
            "query_time_ms": response.query_time_ms,
            "retrievers_used": response.retrievers_used,
        }


class HybridSearchView(APIView):
    """Hybrid search endpoint with multiple retrievers.

    POST /api/v1/search/hybrid/

    Performs hybrid search combining results from multiple retrievers
    (vector, keyword, graph) and fuses them using RRF (Reciprocal Rank Fusion).

    Request body:
        {
            "query": "What is machine learning?",
            "top_k": 10,
            "use_vector": true,
            "use_keyword": true,
            "use_graph": false,
            "filters": {
                "user_id": "uuid-here",
                "document_ids": ["uuid-1", "uuid-2"]
            },
            "rrf_k": 60,
            "weights": {
                "vector": 0.4,
                "keyword": 0.3,
                "graph": 0.3
            }
        }

    Response:
        {
            "results": [...],
            "total": 15,
            "query_time_ms": 120.5,
            "retrievers_used": ["vector", "keyword"]
        }
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=HybridSearchRequestSerializer,
        responses={
            200: SearchResponseSerializer,
            400: ErrorResponseSerializer,
            401: "Authentication required",
            500: ErrorResponseSerializer,
        },
        operation_description="""Perform hybrid search combining multiple retrievers with RRF fusion.

**Retriever Types:**
- **Vector**: Semantic similarity search via Milvus (dense embeddings)
- **Keyword**: Full-text search via PostgreSQL FTS
- **Graph**: Entity-based retrieval via Neo4j knowledge graph

**RRF (Reciprocal Rank Fusion):**
Fuses results using the formula: `score(d) = sum(weight / (k + rank))`

Default: k=60, weights={vector: 0.4, keyword: 0.3, graph: 0.3}

**Request example:**
```json
{
    "query": "What is machine learning?",
    "top_k": 10,
    "use_vector": true,
    "use_keyword": true,
    "use_graph": false,
    "filters": {
        "document_ids": ["550e8400-e29b-41d4-a716-446655440000"]
    },
    "rrf_k": 60,
    "weights": {"vector": 0.5, "keyword": 0.5}
}
```
""",
        operation_summary="Hybrid search with RRF fusion",
        tags=["Search"],
        security=[{"Bearer": []}],
    )
    def post(self, request: Request) -> Response:
        """Execute hybrid search with multiple retrievers.

        Args:
            request: HTTP request with search query and options.

        Returns:
            Response with fused search results.
        """
        serializer = HybridSearchRequestSerializer(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                f"Hybrid search validation failed for user {request.user.id}: "
                f"{serializer.errors}"
            )
            return Response(
                {
                    "error": "validation_error",
                    "message": "Invalid request parameters",
                    "details": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        try:
            # Build HybridSearchRequest DTO
            hybrid_request = HybridSearchRequest(
                query=data["query"],
                top_k=data.get("top_k", 10),
                use_vector=data.get("use_vector", True),
                use_keyword=data.get("use_keyword", True),
                use_graph=data.get("use_graph", False),
                filters=self._build_filters(data.get("filters")),
                rrf_k=data.get("rrf_k", 60),
                weights=self._build_weights(data.get("weights")),
            )

            service = SearchService()
            response = service.hybrid_search(hybrid_request)

            return Response(
                self._format_response(response),
                status=status.HTTP_200_OK,
            )

        except EmptyQueryError:
            return Response(
                {
                    "error": "empty_query",
                    "message": "Query cannot be empty",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except QueryTooShortError as e:
            return Response(
                {
                    "error": "query_too_short",
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except QueryTooLongError as e:
            return Response(
                {
                    "error": "query_too_long",
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SearchError as e:
            logger.exception(f"Search error in hybrid search: {e}")
            return Response(
                {
                    "error": "search_error",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _build_filters(self, filters_data: dict[str, Any] | None) -> dict[str, Any]:
        """Build filters dictionary from serializer data.

        Args:
            filters_data: Filters data from serializer.

        Returns:
            Filters dictionary for HybridSearchRequest.
        """
        if not filters_data:
            return {}

        filters: dict[str, Any] = {}

        if filters_data.get("user_id"):
            filters["user_id"] = str(filters_data["user_id"])

        if filters_data.get("document_ids"):
            filters["document_ids"] = [
                str(doc_id) for doc_id in filters_data["document_ids"]
            ]

        if filters_data.get("date_from"):
            filters["date_from"] = filters_data["date_from"]

        if filters_data.get("date_to"):
            filters["date_to"] = filters_data["date_to"]

        if filters_data.get("file_types"):
            filters["file_types"] = filters_data["file_types"]

        return filters

    def _build_weights(
        self, weights_data: dict[str, float] | None
    ) -> dict[str, float] | None:
        """Build weights dictionary from serializer data.

        Args:
            weights_data: Weights data from serializer.

        Returns:
            Weights dictionary or None.
        """
        if not weights_data:
            return None

        weights: dict[str, float] = {}

        if "vector" in weights_data:
            weights["vector"] = weights_data["vector"]

        if "keyword" in weights_data:
            weights["keyword"] = weights_data["keyword"]

        if "graph" in weights_data:
            weights["graph"] = weights_data["graph"]

        return weights if weights else None

    def _format_response(self, response: Any) -> dict[str, Any]:
        """Format SearchResponse for JSON output.

        Args:
            response: SearchResponse DTO.

        Returns:
            Dictionary for JSON response.
        """
        return {
            "results": [
                {
                    "chunk_id": str(item.chunk_id),
                    "document_id": str(item.document_id),
                    "text": item.text,
                    "score": item.score,
                    "source": item.source,
                    "metadata": item.metadata,
                    "retriever_scores": item.retriever_scores,
                }
                for item in response.results
            ],
            "total": response.total,
            "query_time_ms": response.query_time_ms,
            "retrievers_used": response.retrievers_used,
        }


class AdvancedSearchView(APIView):
    """Advanced search endpoint with filters and options.

    POST /api/v1/search/advanced/

    Performs advanced search with granular filtering capabilities
    and optional context expansion to include neighbor chunks.

    Request body:
        {
            "query": "What is machine learning?",
            "top_k": 10,
            "use_vector": true,
            "use_keyword": true,
            "use_graph": false,
            "user_id": "uuid-here",
            "document_ids": ["uuid-1", "uuid-2"],
            "date_from": "2026-01-01T00:00:00Z",
            "date_to": "2026-12-31T23:59:59Z",
            "file_types": ["pdf", "docx"],
            "rrf_k": 60,
            "expand_context": true,
            "context_window": 1
        }

    Response:
        {
            "results": [...],
            "total": 8,
            "query_time_ms": 150.3,
            "retrievers_used": ["vector", "keyword"]
        }
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=AdvancedSearchRequestSerializer,
        responses={
            200: SearchResponseSerializer,
            400: "Invalid request parameters",
            401: "Authentication required",
            500: "Search error",
        },
        operation_description="Perform advanced search with granular filtering capabilities "
                             "and optional context expansion.",
        operation_summary="Advanced search with filters",
        tags=["Search"],
    )
    def post(self, request: Request) -> Response:
        """Execute advanced search with filters.

        Args:
            request: HTTP request with search query and filters.

        Returns:
            Response with filtered search results.
        """
        serializer = AdvancedSearchRequestSerializer(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                f"Advanced search validation failed for user {request.user.id}: "
                f"{serializer.errors}"
            )
            return Response(
                {
                    "error": "validation_error",
                    "message": "Invalid request parameters",
                    "details": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        try:
            # Build AdvancedSearchRequest DTO
            advanced_request = AdvancedSearchRequest(
                query=data["query"],
                top_k=data.get("top_k", 10),
                use_vector=data.get("use_vector", True),
                use_keyword=data.get("use_keyword", True),
                use_graph=data.get("use_graph", False),
                user_id=str(data["user_id"]) if data.get("user_id") else None,
                document_ids=[
                    str(doc_id) for doc_id in data["document_ids"]
                ] if data.get("document_ids") else None,
                date_from=data.get("date_from"),
                date_to=data.get("date_to"),
                file_types=data.get("file_types"),
                rrf_k=data.get("rrf_k", 60),
                expand_context=data.get("expand_context", False),
                context_window=data.get("context_window", 1),
            )

            service = SearchService()
            response = service.advanced_search(advanced_request)

            return Response(
                self._format_response(response),
                status=status.HTTP_200_OK,
            )

        except InvalidDateRangeError as e:
            return Response(
                {
                    "error": "invalid_date_range",
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except EmptyQueryError:
            return Response(
                {
                    "error": "empty_query",
                    "message": "Query cannot be empty",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except QueryTooShortError as e:
            return Response(
                {
                    "error": "query_too_short",
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except QueryTooLongError as e:
            return Response(
                {
                    "error": "query_too_long",
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SearchError as e:
            logger.exception(f"Search error in advanced search: {e}")
            return Response(
                {
                    "error": "search_error",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _format_response(self, response: Any) -> dict[str, Any]:
        """Format SearchResponse for JSON output.

        Args:
            response: SearchResponse DTO.

        Returns:
            Dictionary for JSON response.
        """
        return {
            "results": [
                {
                    "chunk_id": str(item.chunk_id),
                    "document_id": str(item.document_id),
                    "text": item.text,
                    "score": item.score,
                    "source": item.source,
                    "metadata": item.metadata,
                    "retriever_scores": item.retriever_scores,
                }
                for item in response.results
            ],
            "total": response.total,
            "query_time_ms": response.query_time_ms,
            "retrievers_used": response.retrievers_used,
        }


class SearchSuggestionsView(APIView):
    """Search suggestions endpoint.

    GET /api/v1/search/suggestions/

    Returns search suggestions based on query prefix using
    PostgreSQL trigram similarity for auto-complete functionality.

    Query params:
        - prefix: Query prefix (required, min 2 characters)
        - limit: Maximum suggestions to return (default: 5, max: 20)

    Response:
        {
            "suggestions": [
                "machine learning algorithms",
                "machine learning models",
                "machine learning applications"
            ],
            "total": 3
        }
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "prefix",
                openapi.IN_QUERY,
                description="Query prefix to generate suggestions for",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "limit",
                openapi.IN_QUERY,
                description="Maximum number of suggestions to return (default: 5, max: 20)",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: SearchSuggestionsResponseSerializer,
            400: "Invalid request parameters",
            401: "Authentication required",
            500: "Search error",
        },
        operation_description="Get search suggestions based on query prefix for auto-complete.",
        operation_summary="Get search suggestions",
        tags=["Search"],
    )
    def get(self, request: Request) -> Response:
        """Get search suggestions based on prefix.

        Args:
            request: HTTP request with prefix query parameter.

        Returns:
            Response with suggested search terms.
        """
        serializer = SearchSuggestionsRequestSerializer(data=request.query_params)

        if not serializer.is_valid():
            logger.warning(
                f"Search suggestions validation failed for user {request.user.id}: "
                f"{serializer.errors}"
            )
            return Response(
                {
                    "error": "validation_error",
                    "message": "Invalid request parameters",
                    "details": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        try:
            suggestions_request = SearchSuggestionsRequest(
                prefix=data["prefix"],
                limit=data.get("limit", 5),
            )

            service = SearchService()
            response = service.get_search_suggestions(suggestions_request)

            return Response(
                {
                    "suggestions": response.suggestions,
                    "total": response.total,
                },
                status=status.HTTP_200_OK,
            )

        except SearchError as e:
            logger.exception(f"Search error in suggestions: {e}")
            return Response(
                {
                    "error": "search_error",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class HealthCheckView(APIView):
    """Health check endpoint for search service.

    GET /api/v1/search/health/

    Returns the health status of all retriever components.

    Response:
        {
            "vector": true,
            "keyword": true,
            "graph": false,
            "overall": true
        }
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: HealthCheckResponseSerializer,
            401: "Authentication required",
        },
        operation_description="Check health status of all retriever components.",
        operation_summary="Health check",
        tags=["Search"],
    )
    def get(self, request: Request) -> Response:
        """Check health of search service components.

        Args:
            request: HTTP request.

        Returns:
            Response with health status of each retriever.
        """
        try:
            service = SearchService()
            health_status = service.health_check()

            return Response(health_status, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Health check failed: {e}")
            return Response(
                {
                    "vector": False,
                    "keyword": False,
                    "graph": False,
                    "overall": False,
                    "error": str(e),
                },
                status=status.HTTP_200_OK,  # Still return 200, just with error
            )
