"""
Pipeline API Views.

This module provides REST API endpoints for pipeline operations.
"""

from __future__ import annotations

import logging

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.document_pipeline_manager.dto import ExecutePipelineRequest
from apps.document_pipeline_manager.serializers import (
    ExecutePipelineSerializer,
    RetryPipelineSerializer,
    PipelineStatusSerializer,
    PipelineHistorySerializer,
    PipelineHealthSerializer,
    PipelineSummarySerializer,
    RecentExecutionSerializer,
)
from apps.document_pipeline_manager.services import PipelineService

logger = logging.getLogger(__name__)


class PipelineExecuteView(APIView):
    """
    Execute pipeline for a document.

    POST /api/v1/pipeline/execute/
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=ExecutePipelineSerializer,
        responses={
            200: PipelineStatusSerializer,
            400: "Invalid request",
            500: "Pipeline execution failed",
        },
        operation_description="Execute the full document processing pipeline",
        tags=["Pipeline"],
    )
    def post(self, request):
        """Execute pipeline for a document."""
        serializer = ExecutePipelineSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"error": "Invalid request", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        document_id = str(serializer.validated_data["document_id"])

        logger.info(f"[API] Pipeline execute request from user {request.user.id} for document {document_id}")

        # Execute pipeline
        service = PipelineService()
        result = service.execute_pipeline(
            ExecutePipelineRequest(document_id=document_id)
        )

        # Build response
        response_data = {
            "document_id": result.document_id,
            "status": result.status,
            "current_step": result.current_step,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
            "total_duration_ms": result.total_duration_ms,
            "steps": result.steps,
            "error_message": result.error_message,
            "retry_count": result.retry_count,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class PipelineStatusView(APIView):
    """
    Get pipeline status for a document.

    GET /api/v1/pipeline/status/{document_id}/
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: PipelineStatusSerializer,
            404: "Pipeline execution not found",
        },
        operation_description="Get current pipeline status for a document",
        tags=["Pipeline"],
    )
    def get(self, request, document_id):
        """Get pipeline status."""
        logger.debug(f"[API] Pipeline status request for document {document_id}")

        service = PipelineService()
        result = service.get_pipeline_status(document_id)

        response_data = {
            "document_id": result.document_id,
            "status": result.status,
            "current_step": result.current_step,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
            "total_duration_ms": result.total_duration_ms,
            "steps": result.steps,
            "error_message": result.error_message,
            "retry_count": result.retry_count,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class PipelineRetryView(APIView):
    """
    Retry a failed pipeline.

    POST /api/v1/pipeline/retry/{document_id}/
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=RetryPipelineSerializer,
        responses={
            200: PipelineStatusSerializer,
            400: "Invalid request",
            404: "Pipeline execution not found",
        },
        operation_description="Retry a failed pipeline execution",
        tags=["Pipeline"],
    )
    def post(self, request, document_id):
        """Retry pipeline."""
        step_name = request.data.get("step_name")

        logger.info(
            f"[API] Pipeline retry request from user {request.user.id} "
            f"for document {document_id}, step: {step_name}"
        )

        service = PipelineService()
        result = service.retry_pipeline(document_id, step_name)

        response_data = {
            "document_id": result.document_id,
            "status": result.status,
            "current_step": result.current_step,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
            "total_duration_ms": result.total_duration_ms,
            "steps": result.steps,
            "error_message": result.error_message,
            "retry_count": result.retry_count,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class PipelineCancelView(APIView):
    """
    Cancel a running pipeline.

    POST /api/v1/pipeline/cancel/{document_id}/
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: PipelineStatusSerializer,
            400: "Cannot cancel pipeline",
            404: "Pipeline execution not found",
        },
        operation_description="Cancel a running pipeline",
        tags=["Pipeline"],
    )
    def post(self, request, document_id):
        """Cancel pipeline."""
        logger.info(
            f"[API] Pipeline cancel request from user {request.user.id} "
            f"for document {document_id}"
        )

        service = PipelineService()
        result = service.cancel_pipeline(document_id)

        response_data = {
            "document_id": result.document_id,
            "status": result.status,
            "current_step": result.current_step,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
            "total_duration_ms": result.total_duration_ms,
            "steps": result.steps,
            "error_message": result.error_message,
            "retry_count": result.retry_count,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class PipelineHistoryView(APIView):
    """
    Get pipeline execution history.

    GET /api/v1/pipeline/history/{document_id}/
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: PipelineHistorySerializer,
        },
        operation_description="Get pipeline execution history for a document",
        tags=["Pipeline"],
    )
    def get(self, request, document_id):
        """Get pipeline history."""
        logger.debug(f"[API] Pipeline history request for document {document_id}")

        service = PipelineService()
        result = service.get_pipeline_history(document_id)

        response_data = {
            "document_id": result.document_id,
            "executions": result.executions,
            "total_count": result.total_count,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class PipelineHealthView(APIView):
    """
    Pipeline health check.

    GET /api/v1/pipeline/health/
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: PipelineHealthSerializer,
        },
        operation_description="Get pipeline health status",
        tags=["Pipeline"],
    )
    def get(self, request):
        """Get pipeline health."""
        service = PipelineService()
        result = service.health_check()

        response_data = {
            "status": result.status,
            "database_connected": result.database_connected,
            "milvus_connected": result.milvus_connected,
            "neo4j_connected": result.neo4j_connected,
            "active_pipelines": result.active_pipelines,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class PipelineSummaryView(APIView):
    """
    Get pipeline summary for a document.

    GET /api/v1/pipeline/summary/{document_id}/
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: PipelineSummarySerializer,
            404: "Pipeline execution not found",
        },
        operation_description="Get a summary of pipeline status",
        tags=["Pipeline"],
    )
    def get(self, request, document_id):
        """Get pipeline summary."""
        logger.debug(f"[API] Pipeline summary request for document {document_id}")

        service = PipelineService()
        result = service.get_document_pipeline_summary(document_id)

        return Response(result, status=status.HTTP_200_OK)


class PipelineRecentView(APIView):
    """
    List recent pipeline executions.

    GET /api/v1/pipeline/recent/
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                description="Filter by status",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "limit",
                openapi.IN_QUERY,
                description="Maximum number of results",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: RecentExecutionSerializer(many=True),
        },
        operation_description="List recent pipeline executions",
        tags=["Pipeline"],
    )
    def get(self, request):
        """List recent executions."""
        status_filter = request.query_params.get("status")
        limit = int(request.query_params.get("limit", 20))

        logger.debug(
            f"[API] Pipeline recent request from user {request.user.id}, "
            f"status: {status_filter}, limit: {limit}"
        )

        service = PipelineService()
        result = service.list_recent_executions(status=status_filter, limit=limit)

        return Response(result, status=status.HTTP_200_OK)
