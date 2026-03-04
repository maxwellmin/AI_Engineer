"""
Health check API views for Neo4j operations.

This module provides REST API endpoints for health checks and statistics.
"""

import logging

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.neo4j_database_controller.serializers import (
    HealthCheckResponseSerializer,
)
from apps.neo4j_database_controller.services import Neo4jService

logger = logging.getLogger(__name__)


class HealthViewSet(viewsets.ViewSet):
    """ViewSet for Neo4j health check operations.

    Provides endpoints for:
    - Connection health check
    - Graph statistics
    - Schema initialization
    """

    service: Neo4jService = None

    def get_service(self) -> Neo4jService:
        """Get or create Neo4jService instance."""
        if self.service is None:
            self.service = Neo4jService()
        return self.service

    @swagger_auto_schema(
        operation_description="Check Neo4j connection health",
        responses={200: HealthCheckResponseSerializer},
        tags=["Neo4j Health"],
    )
    def list(self, request):
        """Check Neo4j connection health.

        GET /api/v1/neo4j/health/
        """
        service = self.get_service()

        try:
            health = service.health_check()
            return Response(health)

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return Response(
                {
                    "status": "unhealthy",
                    "connected": False,
                    "error": str(e),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    @swagger_auto_schema(
        operation_description="Get Neo4j graph statistics",
        responses={200: "Graph statistics"},
        tags=["Neo4j Health"],
    )
    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get graph statistics.

        GET /api/v1/neo4j/health/stats/
        """
        service = self.get_service()

        try:
            stats = service.get_graph_stats()
            return Response(stats)

        except Exception as e:
            logger.error(f"Failed to get graph stats: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @swagger_auto_schema(
        operation_description="Initialize Neo4j schema (indexes and constraints)",
        responses={200: "Schema initialization result"},
        tags=["Neo4j Health"],
    )
    @action(detail=False, methods=["post"])
    def init_schema(self, request):
        """Initialize Neo4j schema.

        POST /api/v1/neo4j/health/init-schema/
        """
        service = self.get_service()

        try:
            result = service.initialize_schema()
            return Response(result)

        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
