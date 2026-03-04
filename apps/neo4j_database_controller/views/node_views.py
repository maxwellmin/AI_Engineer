"""
Node API views for Neo4j operations.

This module provides REST API endpoints for node CRUD operations.
"""

import logging

from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.neo4j_database_controller.constants import VALID_NODE_LABELS
from apps.neo4j_database_controller.dto import DeleteResult, NodeInfo
from apps.neo4j_database_controller.exceptions import (
    InvalidNodeLabelError,
    NodeNotFoundError,
)
from apps.neo4j_database_controller.serializers import (
    BatchCreateNodesSerializer,
    BatchNodeResponseSerializer,
    CreateNodeSerializer,
    DeleteNodeQuerySerializer,
    DeleteResponseSerializer,
    NodeFilterSerializer,
    NodeListResponseSerializer,
    NodeResponseSerializer,
    UpdateNodeSerializer,
)
from apps.neo4j_database_controller.services import Neo4jService

logger = logging.getLogger(__name__)


class NodeViewSet(viewsets.ViewSet):
    """ViewSet for Neo4j node operations.

    Provides endpoints for:
    - Creating nodes (single and batch)
    - Retrieving nodes by ID or label
    - Updating nodes
    - Deleting nodes

    All endpoints require authentication.
    """

    service: Neo4jService = None

    def get_service(self) -> Neo4jService:
        """Get or create Neo4jService instance."""
        if self.service is None:
            self.service = Neo4jService()
        return self.service

    @swagger_auto_schema(
        operation_description="Create a single node",
        request_body=CreateNodeSerializer,
        responses={201: NodeResponseSerializer, 400: "Bad Request"},
        tags=["Neo4j Nodes"],
    )
    @action(detail=False, methods=["post"])
    def create_node(self, request):
        """Create a single node.

        POST /api/v1/neo4j/nodes/create/
        """
        serializer = CreateNodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = self.get_service()

        try:
            result = service.create_node(
                label=data["label"],
                properties=data["properties"],
                merge=data.get("merge", False),
            )

            response_data = {
                "id": result.node.id,
                "label": result.node.label,
                "properties": result.node.properties,
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except InvalidNodeLabelError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Failed to create node: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Batch create nodes",
        request_body=BatchCreateNodesSerializer,
        responses={201: BatchNodeResponseSerializer, 400: "Bad Request"},
        tags=["Neo4j Nodes"],
    )
    @action(detail=False, methods=["post"])
    def batch_create(self, request):
        """Batch create nodes.

        POST /api/v1/neo4j/nodes/batch-create/
        """
        serializer = BatchCreateNodesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = self.get_service()

        try:
            result = service.create_nodes_batch(
                label=data["label"],
                nodes=data["nodes"],
                batch_size=data.get("batch_size", 1000),
            )

            nodes_data = [
                {"id": n.id, "label": n.label, "properties": n.properties}
                for n in result.nodes
            ]

            response_data = {
                "nodes": nodes_data,
                "created_count": result.created_count,
                "failed_count": result.failed_count,
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to batch create nodes: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Get a node by label and ID",
        responses={
            200: NodeResponseSerializer,
            404: "Node not found",
        },
        manual_parameters=[
            openapi.Parameter(
                "label",
                openapi.IN_PATH,
                description="Node label",
                type=openapi.TYPE_STRING,
                enum=list(VALID_NODE_LABELS),
            ),
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description="Node ID",
                type=openapi.TYPE_STRING,
            ),
        ],
        tags=["Neo4j Nodes"],
    )
    def retrieve(self, request, label=None, node_id=None):
        """Get a node by ID.

        GET /api/v1/neo4j/nodes/{label}/{id}/
        """
        if not label or not node_id:
            return Response(
                {"error": "Both label and node_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = self.get_service()

        try:
            node = service.get_node_by_id_or_raise(node_id, label)

            response_data = {
                "id": node.id,
                "label": node.label,
                "properties": node.properties,
            }

            return Response(response_data)

        except NodeNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except InvalidNodeLabelError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="List nodes by label with optional filters",
        query_serializer=NodeFilterSerializer,
        responses={200: NodeListResponseSerializer},
        manual_parameters=[
            openapi.Parameter(
                "label",
                openapi.IN_PATH,
                description="Node label",
                type=openapi.TYPE_STRING,
                enum=list(VALID_NODE_LABELS),
            ),
        ],
        tags=["Neo4j Nodes"],
    )
    @action(detail=False, methods=["get"], url_path=r"(?P<label>\w+)")
    def list_by_label(self, request, label=None):
        """List nodes by label.

        GET /api/v1/neo4j/nodes/{label}/
        """
        serializer = NodeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        filters = serializer.validated_data
        service = self.get_service()

        try:
            from apps.neo4j_database_controller.managers import NodeManager

            manager = NodeManager()
            order_direction = "DESC" if filters.get("order_desc", False) else "ASC"
            nodes = manager.get_nodes_by_label(
                label=label,
                filters=filters.get("filters", {}),
                order_by=filters.get("order_by", ""),
                order_direction=order_direction,
                offset=filters.get("skip", 0),
                limit=filters.get("limit", 100),
            )

            total = manager.count_nodes(label=label, filters=filters.get("filters", {}))

            nodes_data = [
                {"id": n.id, "label": n.label, "properties": n.properties}
                for n in nodes
            ]

            response_data = {
                "nodes": nodes_data,
                "count": len(nodes_data),
                "total": total,
            }

            return Response(response_data)

        except InvalidNodeLabelError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Failed to list nodes: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Update a node's properties",
        request_body=UpdateNodeSerializer,
        responses={200: NodeResponseSerializer, 404: "Node not found"},
        manual_parameters=[
            openapi.Parameter(
                "label",
                openapi.IN_PATH,
                description="Node label",
                type=openapi.TYPE_STRING,
                enum=list(VALID_NODE_LABELS),
            ),
            openapi.Parameter(
                "node_id",
                openapi.IN_PATH,
                description="Node ID",
                type=openapi.TYPE_STRING,
            ),
        ],
        tags=["Neo4j Nodes"],
    )
    def update_node(self, request, label=None, node_id=None):
        """Update a node.

        PATCH /api/v1/neo4j/nodes/{label}/{id}/update/
        """
        if not label or not node_id:
            return Response(
                {"error": "Both label and node_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = UpdateNodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = self.get_service()

        try:
            node = service.update_node(
                node_id=node_id,
                label=label,
                properties=data["properties"],
                merge=data.get("merge", True),
            )

            response_data = {
                "id": node.id,
                "label": node.label,
                "properties": node.properties,
            }

            return Response(response_data)

        except NodeNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to update node: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Delete a node",
        query_serializer=DeleteNodeQuerySerializer,
        responses={200: DeleteResponseSerializer, 404: "Node not found"},
        manual_parameters=[
            openapi.Parameter(
                "label",
                openapi.IN_PATH,
                description="Node label",
                type=openapi.TYPE_STRING,
                enum=list(VALID_NODE_LABELS),
            ),
            openapi.Parameter(
                "node_id",
                openapi.IN_PATH,
                description="Node ID",
                type=openapi.TYPE_STRING,
            ),
        ],
        tags=["Neo4j Nodes"],
    )
    def delete_node(self, request, label=None, node_id=None):
        """Delete a node.

        DELETE /api/v1/neo4j/nodes/{label}/{id}/delete/
        """
        if not label or not node_id:
            return Response(
                {"error": "Both label and node_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DeleteNodeQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        force = serializer.validated_data.get("force", False)
        service = self.get_service()

        try:
            result = service.delete_node(node_id=node_id, label=label, force=force)

            response_data = {
                "deleted": result.deleted,
                "deleted_count": result.deleted_count,
            }

            return Response(response_data)

        except NodeNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to delete node: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
