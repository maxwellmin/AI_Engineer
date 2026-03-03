"""
API views for embedding engine.

This module provides HTTP API endpoints for the embedding engine,
including health check and embedding operations.
"""

from __future__ import annotations

import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.embedding_engine.dto import EmbedForStorageRequest
from apps.embedding_engine.exceptions import (
    EmbeddingAPIError,
    EmbeddingEmptyInputError,
    EmbeddingError,
    EmbeddingInputTooLongError,
)
from apps.embedding_engine.serializers import (
    BatchEmbeddingResultSerializer,
    EmbedBatchRequestSerializer,
    EmbedQueryRequestSerializer,
    EmbedRequestSerializer,
    EmbeddingResultSerializer,
    ErrorResponseSerializer,
    HealthCheckSerializer,
    SupportedModelsSerializer,
)
from apps.embedding_engine.services import EmbeddingService

logger = logging.getLogger(__name__)


class EmbeddingHealthView(APIView):
    """Health check endpoint for embedding service.

    GET /api/v1/embedding/health/

    Returns the health status of the embedding service, including
    provider type, model name, dimension, and latency.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Check embedding service health",
        operation_id="embedding_health_check",
        tags=["Embedding Engine"],
        responses={
            200: openapi.Response(
                description="Service is healthy",
                schema=HealthCheckSerializer(),
            ),
            500: openapi.Response(
                description="Service is unhealthy",
                schema=ErrorResponseSerializer(),
            ),
        },
    )
    def get(self, request: Request) -> Response:
        """Handle GET request for health check.

        Args:
            request: HTTP request.

        Returns:
            Response with health status.
        """
        service = EmbeddingService()
        result = service.health_check()

        if result.get("healthy"):
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class EmbedTextView(APIView):
    """Single text embedding endpoint.

    POST /api/v1/embedding/embed/

    Embeds a single text and returns the embedding vector.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Embed a single text",
        operation_id="embedding_embed_text",
        tags=["Embedding Engine"],
        request_body=EmbedRequestSerializer(),
        responses={
            200: openapi.Response(
                description="Text embedded successfully",
                schema=EmbeddingResultSerializer(),
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=ErrorResponseSerializer(),
            ),
            500: openapi.Response(
                description="Embedding failed",
                schema=ErrorResponseSerializer(),
            ),
        },
    )
    def post(self, request: Request) -> Response:
        """Handle POST request for single text embedding.

        Args:
            request: HTTP request with text and task_type.

        Returns:
            Response with embedding result.
        """
        serializer = EmbedRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "error": "ValidationError",
                    "message": "Invalid input data",
                    "detail": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        text = serializer.validated_data["text"]
        task_type = serializer.validated_data["task_type"]

        try:
            service = EmbeddingService()
            result = service.embed_text(text=text, task_type=task_type)

            return Response(
                EmbeddingResultSerializer(result.__dict__).data,
                status=status.HTTP_200_OK,
            )

        except EmbeddingEmptyInputError as e:
            return Response(
                {
                    "error": "EmptyInputError",
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except EmbeddingInputTooLongError as e:
            return Response(
                {
                    "error": "InputTooLongError",
                    "message": str(e),
                    "detail": {
                        "token_count": e.token_count,
                        "max_tokens": e.max_tokens,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except EmbeddingAPIError as e:
            logger.error(f"Embedding API error: {e}")
            return Response(
                {
                    "error": "APIError",
                    "message": str(e),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        except EmbeddingError as e:
            logger.error(f"Embedding error: {e}")
            return Response(
                {
                    "error": "EmbeddingError",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class EmbedBatchView(APIView):
    """Batch text embedding endpoint.

    POST /api/v1/embedding/embed-batch/

    Embeds multiple texts in batch and returns all embedding vectors.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Embed multiple texts in batch",
        operation_id="embedding_embed_batch",
        tags=["Embedding Engine"],
        request_body=EmbedBatchRequestSerializer(),
        responses={
            200: openapi.Response(
                description="Texts embedded successfully",
                schema=BatchEmbeddingResultSerializer(),
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=ErrorResponseSerializer(),
            ),
            500: openapi.Response(
                description="Embedding failed",
                schema=ErrorResponseSerializer(),
            ),
        },
    )
    def post(self, request: Request) -> Response:
        """Handle POST request for batch text embedding.

        Args:
            request: HTTP request with texts, task_type, and batch_size.

        Returns:
            Response with batch embedding result.
        """
        serializer = EmbedBatchRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "error": "ValidationError",
                    "message": "Invalid input data",
                    "detail": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        texts = serializer.validated_data["texts"]
        task_type = serializer.validated_data["task_type"]
        batch_size = serializer.validated_data["batch_size"]

        try:
            service = EmbeddingService()
            result = service.embed_texts(
                texts=texts,
                task_type=task_type,
                batch_size=batch_size,
            )

            return Response(
                BatchEmbeddingResultSerializer(result.__dict__).data,
                status=status.HTTP_200_OK,
            )

        except EmbeddingEmptyInputError as e:
            return Response(
                {
                    "error": "EmptyInputError",
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except EmbeddingAPIError as e:
            logger.error(f"Embedding API error: {e}")
            return Response(
                {
                    "error": "APIError",
                    "message": str(e),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        except EmbeddingError as e:
            logger.error(f"Embedding error: {e}")
            return Response(
                {
                    "error": "EmbeddingError",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class EmbedQueryView(APIView):
    """Query embedding endpoint (optimized for search).

    POST /api/v1/embedding/embed-query/

    Embeds a search query using the 'retrieval.query' task type
    for optimal retrieval performance.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Embed a search query (optimized for retrieval)",
        operation_id="embedding_embed_query",
        tags=["Embedding Engine"],
        request_body=EmbedQueryRequestSerializer(),
        responses={
            200: openapi.Response(
                description="Query embedded successfully",
                schema=EmbeddingResultSerializer(),
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=ErrorResponseSerializer(),
            ),
            500: openapi.Response(
                description="Embedding failed",
                schema=ErrorResponseSerializer(),
            ),
        },
    )
    def post(self, request: Request) -> Response:
        """Handle POST request for query embedding.

        Args:
            request: HTTP request with query text.

        Returns:
            Response with query embedding result.
        """
        serializer = EmbedQueryRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "error": "ValidationError",
                    "message": "Invalid input data",
                    "detail": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        query = serializer.validated_data["query"]

        try:
            service = EmbeddingService()
            result = service.embed_query(query=query)

            return Response(
                EmbeddingResultSerializer(result.__dict__).data,
                status=status.HTTP_200_OK,
            )

        except EmbeddingEmptyInputError as e:
            return Response(
                {
                    "error": "EmptyInputError",
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except EmbeddingAPIError as e:
            logger.error(f"Embedding API error: {e}")
            return Response(
                {
                    "error": "APIError",
                    "message": str(e),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        except EmbeddingError as e:
            logger.error(f"Embedding error: {e}")
            return Response(
                {
                    "error": "EmbeddingError",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SupportedModelsView(APIView):
    """Supported models endpoint.

    GET /api/v1/embedding/models/

    Returns a list of supported embedding models.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get supported embedding models",
        operation_id="embedding_supported_models",
        tags=["Embedding Engine"],
        responses={
            200: openapi.Response(
                description="List of supported models",
                schema=SupportedModelsSerializer(),
            ),
        },
    )
    def get(self, request: Request) -> Response:
        """Handle GET request for supported models.

        Args:
            request: HTTP request.

        Returns:
            Response with list of supported models.
        """
        service = EmbeddingService()
        models = service.get_supported_models()

        return Response(
            {"models": models},
            status=status.HTTP_200_OK,
        )
