"""
Health check API view for Milvus database controller.

This module provides health check endpoint for Milvus connection.
"""

from __future__ import annotations

import logging

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.milvus_database_controller.serializers import (
    ErrorSerializer,
    HealthCheckSerializer,
)
from apps.milvus_database_controller.services.milvus_service import MilvusService

logger = logging.getLogger(__name__)


class HealthView(APIView):
    """Health check for Milvus connection."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Check Milvus connection health",
        responses={
            200: HealthCheckSerializer,
            503: HealthCheckSerializer,
        },
        tags=["Milvus - Health"],
    )
    def get(self, request: Request) -> Response:
        """Get Milvus health status."""
        service = MilvusService()
        health = service.health_check()

        if health.get("status") == "healthy":
            return Response(
                {
                    "status": health["status"],
                    "connected": health["connected"],
                    "collections_count": health.get("collections_count"),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "status": health["status"],
                    "connected": health["connected"],
                    "collections_count": None,
                    "error": health.get("error"),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
