"""
Search API views for Milvus database controller.

This module provides REST API endpoints for Milvus search operations.
"""

from __future__ import annotations

import logging
import time

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.milvus_database_controller.exceptions import (
    CollectionNotFoundError,
    MilvusError,
)
from apps.milvus_database_controller.serializers import (
    DocumentSearchSerializer,
    ErrorSerializer,
    HybridSearchResultSerializer,
    HybridSearchSerializer,
    SearchResultItemSerializer,
    SearchResultSerializer,
    VectorSearchSerializer,
)
from apps.milvus_database_controller.services.milvus_service import MilvusService

logger = logging.getLogger(__name__)


def _format_search_result_item(item: object) -> dict:
    """Format a search result item for response.

    Args:
        item: SearchResultItem dataclass instance

    Returns:
        Dictionary with item data
    """
    return {
        "pk": item.id,
        "distance": item.distance,
        "text": item.text,
        "summary": item.summary,
        "document": item.document,
        "source": item.source,
        "source_name": item.source_name,
        "lt_doc_id": item.lt_doc_id,
        "chunk_id": item.chunk_id,
    }


class VectorSearchView(APIView):
    """Perform vector similarity search."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Perform vector similarity search",
        request_body=VectorSearchSerializer,
        responses={
            200: SearchResultSerializer,
            400: ErrorSerializer,
            404: ErrorSerializer,
            500: ErrorSerializer,
        },
        tags=["Milvus - Search"],
    )
    def post(self, request: Request) -> Response:
        """Perform vector search."""
        serializer = VectorSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        collection_name = serializer.validated_data["collection_name"]
        query_vector = serializer.validated_data["query_vector"]
        anns_field = serializer.validated_data["anns_field"]
        top_k = serializer.validated_data["top_k"]
        filter_expr = serializer.validated_data["filter_expr"]
        output_fields = serializer.validated_data.get("output_fields")

        try:
            service = MilvusService()

            if not service.has_collection(collection_name):
                raise CollectionNotFoundError(collection_name)

            start_time = time.time()

            result = service.search(
                collection_name=collection_name,
                query_vector=query_vector,
                anns_field=anns_field,
                top_k=top_k,
                filter_expr=filter_expr,
                output_fields=output_fields,
            )

            query_time_ms = (time.time() - start_time) * 1000

            return Response(
                {
                    "items": [_format_search_result_item(item) for item in result.items],
                    "total": result.total,
                    "query_time_ms": query_time_ms,
                },
                status=status.HTTP_200_OK,
            )

        except CollectionNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except MilvusError as e:
            logger.error(f"Failed to perform vector search: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class HybridSearchView(APIView):
    """Perform hybrid search across multiple vector fields."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Perform hybrid search combining dense vectors and BM25",
        request_body=HybridSearchSerializer,
        responses={
            200: HybridSearchResultSerializer,
            400: ErrorSerializer,
            404: ErrorSerializer,
            500: ErrorSerializer,
        },
        tags=["Milvus - Search"],
    )
    def post(self, request: Request) -> Response:
        """Perform hybrid search."""
        serializer = HybridSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        collection_name = serializer.validated_data["collection_name"]
        query_text = serializer.validated_data["query_text"]
        query_vectors = serializer.validated_data["query_vectors"]
        top_k = serializer.validated_data["top_k"]
        filter_expr = serializer.validated_data["filter_expr"]
        output_fields = serializer.validated_data.get("output_fields")
        rerank_method = serializer.validated_data["rerank_method"]
        rrf_k = serializer.validated_data["rrf_k"]
        weights = serializer.validated_data.get("weights")

        try:
            service = MilvusService()

            if not service.has_collection(collection_name):
                raise CollectionNotFoundError(collection_name)

            start_time = time.time()

            result = service.hybrid_search(
                collection_name=collection_name,
                query_text=query_text,
                query_vectors=query_vectors,
                top_k=top_k,
                filter_expr=filter_expr,
                output_fields=output_fields,
                rerank_method=rerank_method,
                rrf_k=rrf_k,
                weights=weights,
            )

            query_time_ms = (time.time() - start_time) * 1000

            response_data = {
                "items": [_format_search_result_item(item) for item in result.items],
                "total": result.total,
                "query_time_ms": query_time_ms,
            }

            if result.search_details:
                response_data["search_details"] = result.search_details

            return Response(response_data, status=status.HTTP_200_OK)

        except CollectionNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except MilvusError as e:
            logger.error(f"Failed to perform hybrid search: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DocumentSearchView(APIView):
    """Search within a specific document's chunks."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Search for chunks within a specific document",
        request_body=DocumentSearchSerializer,
        responses={
            200: SearchResultSerializer,
            400: ErrorSerializer,
            404: ErrorSerializer,
            500: ErrorSerializer,
        },
        tags=["Milvus - Search"],
    )
    def post(self, request: Request) -> Response:
        """Search within a document."""
        serializer = DocumentSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        collection_name = serializer.validated_data["collection_name"]
        document_id = serializer.validated_data["document_id"]
        query_vector = serializer.validated_data["query_vector"]
        top_k = serializer.validated_data["top_k"]

        try:
            service = MilvusService()

            if not service.has_collection(collection_name):
                raise CollectionNotFoundError(collection_name)

            start_time = time.time()

            result = service.search_by_document(
                collection_name=collection_name,
                document_id=document_id,
                query_vector=query_vector,
                top_k=top_k,
            )

            query_time_ms = (time.time() - start_time) * 1000

            return Response(
                {
                    "items": [_format_search_result_item(item) for item in result.items],
                    "total": result.total,
                    "query_time_ms": query_time_ms,
                },
                status=status.HTTP_200_OK,
            )

        except CollectionNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except MilvusError as e:
            logger.error(f"Failed to search within document: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
