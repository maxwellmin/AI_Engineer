"""
Query API views for Neo4j graph operations.

This module provides REST API endpoints for graph query operations
optimized for RAG pipeline.
"""

import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.neo4j_database_controller.constants import VALID_NODE_LABELS
from apps.neo4j_database_controller.serializers import (
    DocumentGraphQuerySerializer,
    DocumentGraphResponseSerializer,
    EntityContextQuerySerializer,
    EntityContextResponseSerializer,
    FindPathSerializer,
    NeighborQuerySerializer,
    NodeResponseSerializer,
    PathResponseSerializer,
    SearchEntitiesSerializer,
)
from apps.neo4j_database_controller.services import Neo4jService

logger = logging.getLogger(__name__)


class QueryViewSet(viewsets.ViewSet):
    """ViewSet for Neo4j graph query operations.

    Provides endpoints for:
    - Path finding (shortest path, all paths)
    - Node neighbors
    - Entity context for RAG
    - Document subgraph
    - Entity search
    """

    service: Neo4jService = None

    def get_service(self) -> Neo4jService:
        """Get or create Neo4jService instance."""
        if self.service is None:
            self.service = Neo4jService()
        return self.service

    @swagger_auto_schema(
        operation_description="Find the shortest path between two nodes",
        request_body=FindPathSerializer,
        responses={200: PathResponseSerializer, 404: "No path found"},
        tags=["Neo4j Query"],
    )
    @action(detail=False, methods=["post"])
    def shortest_path(self, request):
        """Find shortest path between two nodes.

        POST /api/v1/neo4j/query/path/shortest/
        """
        serializer = FindPathSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = self.get_service()

        try:
            path = service.find_shortest_path(
                from_node_id=data["from_node_id"],
                from_node_label=data["from_node_label"],
                to_node_id=data["to_node_id"],
                to_node_label=data["to_node_label"],
                max_depth=data.get("max_depth", 5),
                relationship_types=data.get("relationship_types"),
            )

            if path is None:
                return Response(
                    {"error": "No path found between the specified nodes"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            response_data = {
                "nodes": [
                    {"id": n.id, "label": n.label, "properties": n.properties}
                    for n in path.nodes
                ],
                "relationships": [
                    {
                        "id": r.id,
                        "rel_type": r.rel_type,
                        "from_node_id": r.from_node_id,
                        "to_node_id": r.to_node_id,
                        "properties": r.properties,
                    }
                    for r in path.relationships
                ],
                "length": path.length,
            }

            return Response(response_data)

        except Exception as e:
            logger.error(f"Failed to find shortest path: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Find all paths between two nodes",
        request_body=FindPathSerializer,
        responses={200: PathResponseSerializer(many=True)},
        tags=["Neo4j Query"],
    )
    @action(detail=False, methods=["post"])
    def all_paths(self, request):
        """Find all paths between two nodes.

        POST /api/v1/neo4j/query/path/all/
        """
        serializer = FindPathSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = self.get_service()

        try:
            from apps.neo4j_database_controller.managers import QueryManager

            manager = QueryManager()
            paths = manager.find_all_paths(
                from_node_id=data["from_node_id"],
                from_node_label=data["from_node_label"],
                to_node_id=data["to_node_id"],
                to_node_label=data["to_node_label"],
                max_depth=data.get("max_depth", 5),
                relationship_types=data.get("relationship_types"),
                limit=data.get("limit", 10),
            )

            paths_data = [
                {
                    "nodes": [
                        {"id": n.id, "label": n.label, "properties": n.properties}
                        for n in p.nodes
                    ],
                    "relationships": [
                        {
                            "id": r.id,
                            "rel_type": r.rel_type,
                            "from_node_id": r.from_node_id,
                            "to_node_id": r.to_node_id,
                            "properties": r.properties,
                        }
                        for r in p.relationships
                    ],
                    "length": p.length,
                }
                for p in paths
            ]

            return Response(paths_data)

        except Exception as e:
            logger.error(f"Failed to find all paths: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Get neighboring nodes",
        query_serializer=NeighborQuerySerializer,
        responses={200: NodeResponseSerializer(many=True)},
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
        tags=["Neo4j Query"],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"neighbors/(?P<label>\w+)/(?P<node_id>[^/.]+)",
    )
    def neighbors(self, request, label=None, node_id=None):
        """Get neighboring nodes.

        GET /api/v1/neo4j/query/neighbors/{label}/{id}/
        """
        serializer = NeighborQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = self.get_service()

        try:
            neighbors = service.get_node_neighbors(
                node_id=node_id,
                node_label=label,
                direction=data.get("direction", "BOTH"),
                relationship_types=data.get("relationship_types"),
                limit=data.get("limit", 100),
            )

            neighbors_data = [
                {"id": n.id, "label": n.label, "properties": n.properties}
                for n in neighbors
            ]

            return Response(neighbors_data)

        except Exception as e:
            logger.error(f"Failed to get neighbors: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Get entity context for RAG queries",
        query_serializer=EntityContextQuerySerializer,
        responses={200: EntityContextResponseSerializer, 404: "Entity not found"},
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description="Entity ID",
                type=openapi.TYPE_STRING,
            ),
        ],
        tags=["Neo4j Query"],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"entity-context/(?P<entity_id>[^/.]+)",
    )
    def entity_context(self, request, entity_id=None):
        """Get entity context for RAG.

        GET /api/v1/neo4j/query/entity-context/{id}/
        """
        serializer = EntityContextQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = self.get_service()

        try:
            context = service.get_entity_context(
                entity_id=entity_id,
                include_chunks=data.get("include_chunks", True),
                include_related_entities=data.get("include_related_entities", True),
                include_concepts=data.get("include_concepts", True),
                max_depth=data.get("max_depth", 2),
            )

            if context is None:
                return Response(
                    {"error": f"Entity '{entity_id}' not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            response_data = {
                "entity": {
                    "id": context.entity.id,
                    "label": context.entity.label,
                    "properties": context.entity.properties,
                },
                "mentioned_in": [
                    {"id": c.id, "label": c.label, "properties": c.properties}
                    for c in context.mentioned_in
                ],
                "related_entities": [
                    {
                        "entity": {
                            "id": e.id,
                            "label": e.label,
                            "properties": e.properties,
                        },
                        "relation_type": rel_type,
                    }
                    for e, rel_type in context.related_entities
                ],
                "concepts": [
                    {"id": c.id, "label": c.label, "properties": c.properties}
                    for c in context.concepts
                ],
            }

            return Response(response_data)

        except Exception as e:
            logger.error(f"Failed to get entity context: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Get document subgraph for RAG",
        query_serializer=DocumentGraphQuerySerializer,
        responses={200: DocumentGraphResponseSerializer, 404: "Document not found"},
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description="Document ID",
                type=openapi.TYPE_STRING,
            ),
        ],
        tags=["Neo4j Query"],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"document-graph/(?P<document_id>[^/.]+)",
    )
    def document_graph(self, request, document_id=None):
        """Get document subgraph for RAG.

        GET /api/v1/neo4j/query/document-graph/{id}/
        """
        serializer = DocumentGraphQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = self.get_service()

        try:
            graph = service.get_document_graph(
                document_id=document_id,
                include_chunks=data.get("include_chunks", True),
                include_entities=data.get("include_entities", True),
                include_concepts=data.get("include_concepts", True),
            )

            if graph is None:
                return Response(
                    {"error": f"Document '{document_id}' not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            response_data = {
                "document": {
                    "id": graph.document.id,
                    "label": graph.document.label,
                    "properties": graph.document.properties,
                },
                "chunks": [
                    {"id": c.id, "label": c.label, "properties": c.properties}
                    for c in graph.chunks
                ],
                "entities": [
                    {"id": e.id, "label": e.label, "properties": e.properties}
                    for e in graph.entities
                ],
                "concepts": [
                    {"id": c.id, "label": c.label, "properties": c.properties}
                    for c in graph.concepts
                ],
                "relationships": [
                    {
                        "id": r.id,
                        "rel_type": r.rel_type,
                        "from_node_id": r.from_node_id,
                        "to_node_id": r.to_node_id,
                        "properties": r.properties,
                    }
                    for r in graph.relationships
                ],
            }

            return Response(response_data)

        except Exception as e:
            logger.error(f"Failed to get document graph: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Search entities by name",
        request_body=SearchEntitiesSerializer,
        responses={200: NodeResponseSerializer(many=True)},
        tags=["Neo4j Query"],
    )
    @action(detail=False, methods=["post"])
    def search_entities(self, request):
        """Search entities by name.

        POST /api/v1/neo4j/query/search-entities/
        """
        serializer = SearchEntitiesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = self.get_service()

        try:
            entities = service.search_entities(
                name=data["name"],
                entity_type=data.get("entity_type"),
                limit=data.get("limit", 10),
            )

            entities_data = [
                {"id": e.id, "label": e.label, "properties": e.properties}
                for e in entities
            ]

            return Response(entities_data)

        except Exception as e:
            logger.error(f"Failed to search entities: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Find entities related to a given entity",
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description="Entity ID",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "max_depth",
                openapi.IN_QUERY,
                description="Maximum traversal depth",
                type=openapi.TYPE_INTEGER,
                default=2,
            ),
            openapi.Parameter(
                "limit",
                openapi.IN_QUERY,
                description="Maximum results",
                type=openapi.TYPE_INTEGER,
                default=20,
            ),
        ],
        responses={200: NodeResponseSerializer(many=True)},
        tags=["Neo4j Query"],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"related-entities/(?P<entity_id>[^/.]+)",
    )
    def related_entities(self, request, entity_id=None):
        """Find entities related to a given entity.

        GET /api/v1/neo4j/query/related-entities/{id}/
        """
        max_depth = int(request.query_params.get("max_depth", 2))
        limit = int(request.query_params.get("limit", 20))

        service = self.get_service()

        try:
            entities = service.find_related_entities(
                entity_id=entity_id,
                max_depth=max_depth,
                limit=limit,
            )

            entities_data = [
                {"id": e.id, "label": e.label, "properties": e.properties}
                for e in entities
            ]

            return Response(entities_data)

        except Exception as e:
            logger.error(f"Failed to find related entities: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Get chunks by entity names",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "entity_names": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description="List of entity names to search for",
                ),
                "limit": openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Maximum chunks to return",
                    default=20,
                ),
            },
            required=["entity_names"],
        ),
        responses={200: NodeResponseSerializer(many=True)},
        tags=["Neo4j Query"],
    )
    @action(detail=False, methods=["post"])
    def chunks_by_entities(self, request):
        """Get chunks that mention any of the given entities.

        POST /api/v1/neo4j/query/chunks-by-entities/
        """
        entity_names = request.data.get("entity_names", [])
        limit = request.data.get("limit", 20)

        if not entity_names:
            return Response(
                {"error": "entity_names is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = self.get_service()

        try:
            chunks = service.get_chunks_by_entities(
                entity_names=entity_names,
                limit=limit,
            )

            chunks_data = [
                {"id": c.id, "label": c.label, "properties": c.properties}
                for c in chunks
            ]

            return Response(chunks_data)

        except Exception as e:
            logger.error(f"Failed to get chunks by entities: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
