"""
Collection API views for Milvus database controller.

This module provides REST API endpoints for Milvus collection management.
"""

from __future__ import annotations

import logging

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.milvus_database_controller.exceptions import (
    CollectionAlreadyExistsError,
    CollectionNotFoundError,
    MilvusError,
)
from apps.milvus_database_controller.serializers import (
    CollectionInfoSerializer,
    CollectionListSerializer,
    CollectionStatsSerializer,
    CreateCollectionSerializer,
    DropCollectionSerializer,
    ErrorSerializer,
    LoadCollectionSerializer,
    ReleaseCollectionSerializer,
)
from apps.milvus_database_controller.services.milvus_service import MilvusService

logger = logging.getLogger(__name__)


class CollectionListView(APIView):
    """List all Milvus collections."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List all collections in Milvus",
        responses={
            200: CollectionListSerializer,
            500: ErrorSerializer,
        },
        tags=["Milvus - Collections"],
    )
    def get(self, request: Request) -> Response:
        """Get list of all collections."""
        try:
            service = MilvusService()
            collections = service.list_collections()

            return Response(
                {
                    "collections": [{"name": name} for name in collections],
                    "total": len(collections),
                },
                status=status.HTTP_200_OK,
            )
        except MilvusError as e:
            logger.error(f"Failed to list collections: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CreateCollectionView(APIView):
    """Create a new Milvus collection."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Create a new collection with optional indexes",
        request_body=CreateCollectionSerializer,
        responses={
            201: CollectionInfoSerializer,
            400: ErrorSerializer,
            409: ErrorSerializer,
            500: ErrorSerializer,
        },
        tags=["Milvus - Collections"],
    )
    def post(self, request: Request) -> Response:
        """Create a new collection."""
        serializer = CreateCollectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        collection_name = serializer.validated_data["collection_name"]
        dimension = serializer.validated_data["dimension"]
        description = serializer.validated_data["description"]
        create_indexes = serializer.validated_data["create_indexes"]

        try:
            service = MilvusService()

            # Check if collection already exists
            if service.has_collection(collection_name):
                raise CollectionAlreadyExistsError(collection_name)

            # Create collection
            service.create_collection(
                collection_name=collection_name,
                dimension=dimension,
                description=description,
                create_indexes=create_indexes,
            )

            logger.info(
                f"User {request.user.id} created collection '{collection_name}' "
                f"with dimension {dimension}"
            )

            # Get collection info
            info = service.get_collection_info(collection_name)

            return Response(
                {
                    "name": info.name,
                    "description": info.description,
                    "num_entities": info.num_entities,
                    "schema": info.schema,
                    "loaded": info.loaded,
                },
                status=status.HTTP_201_CREATED,
            )

        except CollectionAlreadyExistsError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_409_CONFLICT,
            )
        except MilvusError as e:
            logger.error(f"Failed to create collection: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CollectionDetailView(APIView):
    """Get detailed information about a collection."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get detailed information about a collection",
        responses={
            200: CollectionInfoSerializer,
            404: ErrorSerializer,
            500: ErrorSerializer,
        },
        tags=["Milvus - Collections"],
    )
    def get(self, request: Request, name: str) -> Response:
        """Get collection info by name."""
        try:
            service = MilvusService()

            if not service.has_collection(name):
                raise CollectionNotFoundError(name)

            info = service.get_collection_info(name)

            return Response(
                {
                    "name": info.name,
                    "description": info.description,
                    "num_entities": info.num_entities,
                    "schema": info.schema,
                    "loaded": info.loaded,
                },
                status=status.HTTP_200_OK,
            )

        except CollectionNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except MilvusError as e:
            logger.error(f"Failed to get collection info: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CollectionStatsView(APIView):
    """Get statistics for a collection."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get statistics for a collection",
        responses={
            200: CollectionStatsSerializer,
            404: ErrorSerializer,
            500: ErrorSerializer,
        },
        tags=["Milvus - Collections"],
    )
    def get(self, request: Request, name: str) -> Response:
        """Get collection statistics."""
        try:
            service = MilvusService()

            if not service.has_collection(name):
                raise CollectionNotFoundError(name)

            stats = service.get_collection_stats(name)

            return Response(
                {
                    "collection_name": name,
                    "row_count": stats.get("row_count", 0),
                    "index_info": stats.get("index_info", []),
                    "loaded": stats.get("loaded", False),
                },
                status=status.HTTP_200_OK,
            )

        except CollectionNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except MilvusError as e:
            logger.error(f"Failed to get collection stats: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LoadCollectionView(APIView):
    """Load a collection into memory."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Load a collection into memory for search",
        responses={
            200: LoadCollectionSerializer,
            404: ErrorSerializer,
            500: ErrorSerializer,
        },
        tags=["Milvus - Collections"],
    )
    def post(self, request: Request, name: str) -> Response:
        """Load collection into memory."""
        try:
            service = MilvusService()

            if not service.has_collection(name):
                raise CollectionNotFoundError(name)

            result = service.load_collection(name)

            logger.info(f"User {request.user.id} loaded collection '{name}'")

            return Response(
                {
                    "message": f"Collection '{name}' loaded successfully",
                    "collection_name": name,
                    "loaded": result,
                },
                status=status.HTTP_200_OK,
            )

        except CollectionNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except MilvusError as e:
            logger.error(f"Failed to load collection: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReleaseCollectionView(APIView):
    """Release a collection from memory."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Release a collection from memory",
        responses={
            200: ReleaseCollectionSerializer,
            404: ErrorSerializer,
            500: ErrorSerializer,
        },
        tags=["Milvus - Collections"],
    )
    def post(self, request: Request, name: str) -> Response:
        """Release collection from memory."""
        try:
            service = MilvusService()

            if not service.has_collection(name):
                raise CollectionNotFoundError(name)

            result = service.release_collection(name)

            logger.info(f"User {request.user.id} released collection '{name}'")

            return Response(
                {
                    "message": f"Collection '{name}' released successfully",
                    "collection_name": name,
                    "released": result,
                },
                status=status.HTTP_200_OK,
            )

        except CollectionNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except MilvusError as e:
            logger.error(f"Failed to release collection: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DropCollectionView(APIView):
    """Drop (delete) a collection."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Drop (delete) a collection permanently",
        responses={
            200: DropCollectionSerializer,
            404: ErrorSerializer,
            500: ErrorSerializer,
        },
        tags=["Milvus - Collections"],
    )
    def delete(self, request: Request, name: str) -> Response:
        """Drop a collection."""
        try:
            service = MilvusService()

            if not service.has_collection(name):
                raise CollectionNotFoundError(name)

            result = service.drop_collection(name)

            logger.info(f"User {request.user.id} dropped collection '{name}'")

            return Response(
                {
                    "message": f"Collection '{name}' dropped successfully",
                    "collection_name": name,
                    "dropped": result,
                },
                status=status.HTTP_200_OK,
            )

        except CollectionNotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except MilvusError as e:
            logger.error(f"Failed to drop collection: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
