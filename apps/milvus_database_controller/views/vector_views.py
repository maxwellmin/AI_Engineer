"""
Vector API views for Milvus database controller.

This module provides REST API endpoints for Milvus vector CRUD operations.
"""

from __future__ import annotations

import logging

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.milvus_database_controller.constants import FieldName
from apps.milvus_database_controller.exceptions import (
    CollectionNotFoundError,
    MilvusError,
)
from apps.milvus_database_controller.serializers import (
    DeleteResultSerializer,
    DeleteVectorsByIdsSerializer,
    DeleteVectorsByFilterSerializer,
    ErrorSerializer,
    InsertResultSerializer,
    InsertVectorsSerializer,
    QueryResultSerializer,
    QueryVectorsSerializer,
    UpsertResultSerializer,
    UpsertVectorsSerializer,
)
from apps.milvus_database_controller.services.milvus_service import MilvusService

logger = logging.getLogger(__name__)


class InsertVectorsView(APIView):
    """Insert vectors into a collection."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Insert vectors into a Milvus collection",
        request_body=InsertVectorsSerializer,
        responses={
            201: InsertResultSerializer,
            400: ErrorSerializer,
            404: ErrorSerializer,
            500: ErrorSerializer,
        },
        tags=["Milvus - Vectors"],
    )
    def post(self, request: Request) -> Response:
        """Insert vectors into collection."""
        serializer = InsertVectorsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        collection_name = serializer.validated_data["collection_name"]
        data = serializer.validated_data["data"]

        try:
            service = MilvusService()

            if not service.has_collection(collection_name):
                raise CollectionNotFoundError(collection_name)

            result = service.insert_vectors(
                collection_name=collection_name,
                data=data,
            )

            logger.info(
                f"User {request.user.id} inserted {result.inserted_count} vectors "
                f"into '{collection_name}'"
            )

            return Response(
                {
                    "inserted_count": result.inserted_count,
                    "inserted_ids": result.inserted_ids,
                },
                status=status.HTTP_201_CREATED,
            )

        except CollectionNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except MilvusError as e:
            logger.error(f"Failed to insert vectors: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UpsertVectorsView(APIView):
    """Upsert (insert or update) vectors in a collection."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Upsert vectors into a Milvus collection",
        request_body=UpsertVectorsSerializer,
        responses={
            200: UpsertResultSerializer,
            400: ErrorSerializer,
            404: ErrorSerializer,
            500: ErrorSerializer,
        },
        tags=["Milvus - Vectors"],
    )
    def post(self, request: Request) -> Response:
        """Upsert vectors into collection."""
        serializer = UpsertVectorsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        collection_name = serializer.validated_data["collection_name"]
        data = serializer.validated_data["data"]

        try:
            service = MilvusService()

            if not service.has_collection(collection_name):
                raise CollectionNotFoundError(collection_name)

            result = service.upsert_vectors(
                collection_name=collection_name,
                data=data,
            )

            logger.info(
                f"User {request.user.id} upserted {result.upserted_count} vectors "
                f"into '{collection_name}'"
            )

            return Response(
                {
                    "upserted_count": result.upserted_count,
                    "upserted_ids": result.upserted_ids,
                },
                status=status.HTTP_200_OK,
            )

        except CollectionNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except MilvusError as e:
            logger.error(f"Failed to upsert vectors: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class QueryVectorsView(APIView):
    """Query vectors by filter expression."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Query vectors by filter expression",
        request_body=QueryVectorsSerializer,
        responses={
            200: QueryResultSerializer,
            400: ErrorSerializer,
            404: ErrorSerializer,
            500: ErrorSerializer,
        },
        tags=["Milvus - Vectors"],
    )
    def post(self, request: Request) -> Response:
        """Query vectors by filter."""
        serializer = QueryVectorsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        collection_name = serializer.validated_data["collection_name"]
        filter_expr = serializer.validated_data["filter_expr"]
        output_fields = serializer.validated_data.get("output_fields")
        limit = serializer.validated_data["limit"]
        offset = serializer.validated_data["offset"]

        try:
            service = MilvusService()

            if not service.has_collection(collection_name):
                raise CollectionNotFoundError(collection_name)

            result = service.query_vectors(
                collection_name=collection_name,
                filter_expr=filter_expr,
                output_fields=output_fields,
                limit=limit,
                offset=offset,
            )

            return Response(
                {
                    "items": result.items,
                    "total": result.total,
                },
                status=status.HTTP_200_OK,
            )

        except CollectionNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except MilvusError as e:
            logger.error(f"Failed to query vectors: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GetVectorView(APIView):
    """Get a single vector by primary key."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get a single vector by primary key",
        responses={
            200: QueryResultSerializer,
            404: ErrorSerializer,
            500: ErrorSerializer,
        },
        tags=["Milvus - Vectors"],
    )
    def get(self, request: Request, pk: str) -> Response:
        """Get single vector by primary key."""
        # Get collection name from query params
        collection_name = request.query_params.get("collection_name")
        if not collection_name:
            return Response(
                {"error": "collection_name query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        output_fields = request.query_params.getlist("output_fields")
        if not output_fields:
            output_fields = None

        try:
            service = MilvusService()

            if not service.has_collection(collection_name):
                raise CollectionNotFoundError(collection_name)

            result = service.get_vector(
                collection_name=collection_name,
                pk=pk,
                output_fields=output_fields,
            )

            if result is None:
                return Response(
                    {"error": f"Vector with pk '{pk}' not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response(
                result,
                status=status.HTTP_200_OK,
            )

        except CollectionNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except MilvusError as e:
            logger.error(f"Failed to get vector: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DeleteVectorsView(APIView):
    """Delete vectors from a collection."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Delete vectors by IDs or filter expression",
        request_body=DeleteVectorsByIdsSerializer,
        responses={
            200: DeleteResultSerializer,
            400: ErrorSerializer,
            404: ErrorSerializer,
            500: ErrorSerializer,
        },
        tags=["Milvus - Vectors"],
    )
    def post(self, request: Request) -> Response:
        """Delete vectors by IDs or filter.

        Accepts either:
        - ids: List of primary keys to delete
        - filter_expr: Filter expression to match vectors to delete
        """
        # Check which delete method is being used
        if "ids" in request.data:
            serializer = DeleteVectorsByIdsSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            collection_name = serializer.validated_data["collection_name"]
            ids = serializer.validated_data["ids"]

            try:
                service = MilvusService()

                if not service.has_collection(collection_name):
                    raise CollectionNotFoundError(collection_name)

                result = service.delete_vectors(
                    collection_name=collection_name,
                    ids=ids,
                )

                logger.info(
                    f"User {request.user.id} deleted {result.deleted_count} vectors "
                    f"from '{collection_name}' by IDs"
                )

                return Response(
                    {"deleted_count": result.deleted_count},
                    status=status.HTTP_200_OK,
                )

            except CollectionNotFoundError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_404_NOT_FOUND,
                )
            except MilvusError as e:
                logger.error(f"Failed to delete vectors: {e}")
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        elif "filter_expr" in request.data:
            serializer = DeleteVectorsByFilterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            collection_name = serializer.validated_data["collection_name"]
            filter_expr = serializer.validated_data["filter_expr"]

            try:
                service = MilvusService()

                if not service.has_collection(collection_name):
                    raise CollectionNotFoundError(collection_name)

                result = service.delete_vectors_by_filter(
                    collection_name=collection_name,
                    filter_expr=filter_expr,
                )

                logger.info(
                    f"User {request.user.id} deleted {result.deleted_count} vectors "
                    f"from '{collection_name}' by filter"
                )

                return Response(
                    {"deleted_count": result.deleted_count},
                    status=status.HTTP_200_OK,
                )

            except CollectionNotFoundError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_404_NOT_FOUND,
                )
            except MilvusError as e:
                logger.error(f"Failed to delete vectors: {e}")
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        else:
            return Response(
                {"error": "Either 'ids' or 'filter_expr' is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
