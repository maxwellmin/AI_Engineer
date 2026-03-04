"""
Relationship API views for Neo4j operations.

This module provides REST API endpoints for relationship CRUD operations.
"""

import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.neo4j_database_controller.dto import DeleteResult
from apps.neo4j_database_controller.exceptions import (
    RelationshipNotFoundError,
)
from apps.neo4j_database_controller.serializers import (
    BatchCreateRelationshipsSerializer,
    BatchRelationshipResponseSerializer,
    CreateRelationshipSerializer,
    DeleteRelationshipsQuerySerializer,
    DeleteResponseSerializer,
    RelationshipFilterSerializer,
    RelationshipResponseSerializer,
    UpdateRelationshipSerializer,
)
from apps.neo4j_database_controller.services import Neo4jService

logger = logging.getLogger(__name__)


class RelationshipViewSet(viewsets.ViewSet):
    """ViewSet for Neo4j relationship operations.

    Provides endpoints for:
    - Creating relationships (single and batch)
    - Retrieving relationships by ID or node
    - Updating relationships
    - Deleting relationships
    """

    service: Neo4jService = None

    def get_service(self) -> Neo4jService:
        """Get or create Neo4jService instance."""
        if self.service is None:
            self.service = Neo4jService()
        return self.service

    @swagger_auto_schema(
        operation_description="Create a single relationship",
        request_body=CreateRelationshipSerializer,
        responses={201: RelationshipResponseSerializer, 400: "Bad Request"},
        tags=["Neo4j Relationships"],
    )
    @action(detail=False, methods=["post"])
    def create_relationship(self, request):
        """Create a single relationship.

        POST /api/v1/neo4j/relationships/create/
        """
        serializer = CreateRelationshipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = self.get_service()

        try:
            result = service.create_relationship(
                rel_type=data["rel_type"],
                from_node_id=data["from_node_id"],
                from_node_label=data["from_node_label"],
                to_node_id=data["to_node_id"],
                to_node_label=data["to_node_label"],
                properties=data.get("properties", {}),
                merge=data.get("merge", False),
            )

            response_data = {
                "id": result.relationship.id,
                "rel_type": result.relationship.rel_type,
                "from_node_id": result.relationship.from_node_id,
                "from_node_label": result.relationship.from_node_label,
                "to_node_id": result.relationship.to_node_id,
                "to_node_label": result.relationship.to_node_label,
                "properties": result.relationship.properties,
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Batch create relationships",
        request_body=BatchCreateRelationshipsSerializer,
        responses={201: BatchRelationshipResponseSerializer, 400: "Bad Request"},
        tags=["Neo4j Relationships"],
    )
    @action(detail=False, methods=["post"])
    def batch_create(self, request):
        """Batch create relationships.

        POST /api/v1/neo4j/relationships/batch-create/
        """
        serializer = BatchCreateRelationshipsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = self.get_service()

        try:
            from apps.neo4j_database_controller.dto import CreateRelationshipRequest

            relationships = [
                CreateRelationshipRequest(
                    rel_type=rel["rel_type"],
                    from_node_id=rel["from_node_id"],
                    from_node_label=rel["from_node_label"],
                    to_node_id=rel["to_node_id"],
                    to_node_label=rel["to_node_label"],
                    properties=rel.get("properties", {}),
                )
                for rel in data["relationships"]
            ]

            from apps.neo4j_database_controller.managers import RelationshipManager

            manager = RelationshipManager()
            result = manager.create_relationships_batch(
                relationships=relationships,
                batch_size=data.get("batch_size", 1000),
            )

            rels_data = [
                {
                    "id": r.id,
                    "rel_type": r.rel_type,
                    "from_node_id": r.from_node_id,
                    "from_node_label": r.from_node_label,
                    "to_node_id": r.to_node_id,
                    "to_node_label": r.to_node_label,
                    "properties": r.properties,
                }
                for r in result.relationships
            ]

            response_data = {
                "relationships": rels_data,
                "created_count": result.created_count,
                "failed_count": result.failed_count,
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to batch create relationships: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Get a relationship by ID",
        responses={
            200: RelationshipResponseSerializer,
            404: "Relationship not found",
        },
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description="Relationship ID (Neo4j internal ID)",
                type=openapi.TYPE_INTEGER,
            ),
        ],
        tags=["Neo4j Relationships"],
    )
    def retrieve(self, request, pk=None):
        """Get a relationship by ID.

        GET /api/v1/neo4j/relationships/{id}/
        """
        try:
            rel_id = int(pk)
        except ValueError:
            return Response(
                {"error": "Invalid relationship ID. Must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = self.get_service()

        try:
            from apps.neo4j_database_controller.managers import RelationshipManager

            manager = RelationshipManager()
            rel = manager.get_relationship_by_id_or_raise(rel_id)

            response_data = {
                "id": rel.id,
                "rel_type": rel.rel_type,
                "from_node_id": rel.from_node_id,
                "from_node_label": rel.from_node_label,
                "to_node_id": rel.to_node_id,
                "to_node_label": rel.to_node_label,
                "properties": rel.properties,
            }

            return Response(response_data)

        except RelationshipNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="Get relationships for a node",
        query_serializer=RelationshipFilterSerializer,
        responses={200: RelationshipResponseSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter(
                "node_id",
                openapi.IN_PATH,
                description="Node ID",
                type=openapi.TYPE_STRING,
            ),
        ],
        tags=["Neo4j Relationships"],
    )
    @action(detail=False, methods=["get"], url_path=r"from/(?P<node_id>[^/.]+)")
    def get_from_node(self, request, node_id=None):
        """Get relationships for a node.

        GET /api/v1/neo4j/relationships/from/{node_id}/
        """
        serializer = RelationshipFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        filters = serializer.validated_data
        service = self.get_service()

        try:
            from apps.neo4j_database_controller.managers import RelationshipManager

            manager = RelationshipManager()
            rels = manager.get_relationships(
                node_id=node_id,
                node_label=filters.get("node_label"),
                direction=filters.get("direction", "BOTH"),
                rel_type=filters.get("rel_type"),
                limit=filters.get("limit", 100),
            )

            rels_data = [
                {
                    "id": r.id,
                    "rel_type": r.rel_type,
                    "from_node_id": r.from_node_id,
                    "from_node_label": r.from_node_label,
                    "to_node_id": r.to_node_id,
                    "to_node_label": r.to_node_label,
                    "properties": r.properties,
                }
                for r in rels
            ]

            return Response(rels_data)

        except Exception as e:
            logger.error(f"Failed to get relationships: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Update a relationship's properties",
        request_body=UpdateRelationshipSerializer,
        responses={200: RelationshipResponseSerializer, 404: "Relationship not found"},
        tags=["Neo4j Relationships"],
    )
    @action(detail=True, methods=["patch"])
    def update_relationship(self, request, pk=None):
        """Update a relationship.

        PATCH /api/v1/neo4j/relationships/{id}/update/
        """
        try:
            rel_id = int(pk)
        except ValueError:
            return Response(
                {"error": "Invalid relationship ID. Must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = UpdateRelationshipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            from apps.neo4j_database_controller.managers import RelationshipManager

            manager = RelationshipManager()
            rel = manager.update_relationship(
                rel_id=rel_id,
                properties=data["properties"],
                merge=data.get("merge", True),
            )

            response_data = {
                "id": rel.id,
                "rel_type": rel.rel_type,
                "from_node_id": rel.from_node_id,
                "from_node_label": rel.from_node_label,
                "to_node_id": rel.to_node_id,
                "to_node_label": rel.to_node_label,
                "properties": rel.properties,
            }

            return Response(response_data)

        except RelationshipNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to update relationship: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Delete a relationship by ID",
        responses={200: DeleteResponseSerializer, 404: "Relationship not found"},
        tags=["Neo4j Relationships"],
    )
    @action(detail=True, methods=["delete"])
    def delete_relationship(self, request, pk=None):
        """Delete a relationship.

        DELETE /api/v1/neo4j/relationships/{id}/delete/
        """
        try:
            rel_id = int(pk)
        except ValueError:
            return Response(
                {"error": "Invalid relationship ID. Must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = self.get_service()

        try:
            result = service.delete_relationship(rel_id=rel_id)

            response_data = {
                "deleted": result.deleted,
                "deleted_count": result.deleted_count,
            }

            return Response(response_data)

        except RelationshipNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to delete relationship: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Delete relationships by filter",
        query_serializer=DeleteRelationshipsQuerySerializer,
        responses={200: DeleteResponseSerializer},
        tags=["Neo4j Relationships"],
    )
    @action(detail=False, methods=["delete"])
    def delete_by_filter(self, request):
        """Delete relationships matching filter.

        DELETE /api/v1/neo4j/relationships/delete-by-filter/
        """
        serializer = DeleteRelationshipsQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        if not data.get("node_id"):
            return Response(
                {"error": "node_id is required for filtering"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from apps.neo4j_database_controller.managers import RelationshipManager

            manager = RelationshipManager()
            result = manager.delete_relationships_by_filter(
                node_id=data["node_id"],
                node_label=data.get("node_label"),
                direction=data.get("direction", "BOTH"),
                rel_type=data.get("rel_type"),
            )

            response_data = {
                "deleted": result.deleted,
                "deleted_count": result.deleted_count,
            }

            return Response(response_data)

        except Exception as e:
            logger.error(f"Failed to delete relationships by filter: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
