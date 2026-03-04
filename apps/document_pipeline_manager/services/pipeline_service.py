"""
Pipeline Service for Document Processing.

This module provides the PipelineService class as a high-level facade
for all pipeline operations, offering a clean API for the API layer.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.document_pipeline_manager.dto import (
    ExecutePipelineRequest,
    PipelineConfig,
    PipelineStatusResponse,
    PipelineHistoryResponse,
    PipelineHealthResponse,
)
from apps.document_pipeline_manager.exceptions import PipelineError
from apps.document_pipeline_manager.models import PipelineExecution, PipelineStep
from apps.document_pipeline_manager.orchestrator import PipelineOrchestrator
from apps.documents_parser.models import Document

logger = logging.getLogger(__name__)


class PipelineService:
    """
    High-level facade service for document pipeline operations.

    Provides a unified interface for pipeline execution, monitoring,
    and management. This service wraps the PipelineOrchestrator and
    handles DTO conversions and error handling.

    Example:
        >>> service = PipelineService()
        >>> # Execute pipeline
        >>> response = service.execute_pipeline(
        ...     ExecutePipelineRequest(document_id="abc-123")
        ... )
        >>> print(response.status)
        'completed'
    """

    def __init__(self, config: PipelineConfig | None = None) -> None:
        """
        Initialize the pipeline service.

        Args:
            config: Optional pipeline configuration. Uses defaults if not provided.
        """
        self._config = config or PipelineConfig()
        self._orchestrator: PipelineOrchestrator | None = None

    @property
    def orchestrator(self) -> PipelineOrchestrator:
        """Get or create PipelineOrchestrator instance."""
        if self._orchestrator is None:
            self._orchestrator = PipelineOrchestrator(self._config)
        return self._orchestrator

    def execute_pipeline(
        self,
        request: ExecutePipelineRequest,
    ) -> PipelineStatusResponse:
        """
        Execute full pipeline for a document.

        Args:
            request: ExecutePipelineRequest with document_id.

        Returns:
            PipelineStatusResponse with execution details.

        Raises:
            PipelineError: If execution fails.
        """
        logger.info(f"[PipelineService] Executing pipeline for document {request.document_id}")

        try:
            execution = self.orchestrator.execute(request.document_id)
            return self._build_status_response(execution)
        except Exception as e:
            logger.exception(f"[PipelineService] Pipeline execution failed: {e}")
            return PipelineStatusResponse(
                document_id=request.document_id,
                status="failed",
                current_step="",
                error_message=str(e),
            )

    def get_pipeline_status(
        self,
        document_id: str,
    ) -> PipelineStatusResponse:
        """
        Get current pipeline status for a document.

        Args:
            document_id: UUID of the document.

        Returns:
            PipelineStatusResponse with current status.
        """
        logger.debug(f"[PipelineService] Getting status for document {document_id}")

        try:
            execution = PipelineExecution.objects.get(document_id=document_id)
            return self._build_status_response(execution)
        except PipelineExecution.DoesNotExist:
            return PipelineStatusResponse(
                document_id=document_id,
                status="not_found",
                current_step="",
                steps=[],
                error_message="Pipeline execution not found",
            )

    def retry_pipeline(
        self,
        document_id: str,
        step_name: str | None = None,
    ) -> PipelineStatusResponse:
        """
        Retry a failed pipeline.

        Args:
            document_id: UUID of the document.
            step_name: Optional specific step to retry.
                       If None, retries from the failed step.

        Returns:
            PipelineStatusResponse with new execution status.
        """
        logger.info(
            f"[PipelineService] Retrying pipeline for document {document_id}, "
            f"step: {step_name or 'from_failed'}"
        )

        try:
            if step_name:
                execution = self.orchestrator.retry_step(document_id, step_name)
            else:
                execution = self.orchestrator.retry_from_failed(document_id)

            return self._build_status_response(execution)

        except PipelineExecution.DoesNotExist:
            return PipelineStatusResponse(
                document_id=document_id,
                status="not_found",
                current_step="",
                error_message="Pipeline execution not found",
            )
        except Exception as e:
            logger.exception(f"[PipelineService] Retry failed: {e}")
            return PipelineStatusResponse(
                document_id=document_id,
                status="failed",
                current_step="",
                error_message=str(e),
            )

    def cancel_pipeline(
        self,
        document_id: str,
    ) -> PipelineStatusResponse:
        """
        Cancel a running pipeline.

        Args:
            document_id: UUID of the document.

        Returns:
            PipelineStatusResponse with cancelled status.
        """
        logger.info(f"[PipelineService] Cancelling pipeline for document {document_id}")

        try:
            execution = self.orchestrator.cancel(document_id)
            return self._build_status_response(execution)
        except PipelineExecution.DoesNotExist:
            return PipelineStatusResponse(
                document_id=document_id,
                status="not_found",
                current_step="",
                error_message="Pipeline execution not found",
            )
        except ValueError as e:
            return PipelineStatusResponse(
                document_id=document_id,
                status="error",
                current_step="",
                error_message=str(e),
            )
        except Exception as e:
            logger.exception(f"[PipelineService] Cancel failed: {e}")
            return PipelineStatusResponse(
                document_id=document_id,
                status="error",
                current_step="",
                error_message=str(e),
            )

    def get_pipeline_history(
        self,
        document_id: str,
        limit: int = 10,
    ) -> PipelineHistoryResponse:
        """
        Get execution history for a document.

        Note: In the current design, each document has only one execution
        (OneToOne relationship). This method is provided for future
        extensibility when multiple executions per document may be supported.

        Args:
            document_id: UUID of the document.
            limit: Maximum number of history records to return.

        Returns:
            PipelineHistoryResponse with execution history.
        """
        logger.debug(f"[PipelineService] Getting history for document {document_id}")

        executions = []

        try:
            execution = PipelineExecution.objects.get(document_id=document_id)

            executions.append({
                "execution_id": str(execution.id),
                "status": execution.status,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "total_duration_ms": execution.total_duration_ms,
                "error_message": execution.error_message,
                "error_step": execution.error_step,
                "retry_count": execution.retry_count,
                "created_at": execution.created_at.isoformat(),
            })

        except PipelineExecution.DoesNotExist:
            pass

        return PipelineHistoryResponse(
            document_id=document_id,
            executions=executions,
            total_count=len(executions),
        )

    def health_check(self) -> PipelineHealthResponse:
        """
        Check pipeline health status.

        Returns:
            PipelineHealthResponse with health information.
        """
        # Check database connection
        database_connected = self._check_database()

        # Check active pipelines
        active_count = PipelineExecution.objects.filter(
            status=PipelineExecution.Status.RUNNING
        ).count()

        # Determine overall status
        if database_connected:
            status = "healthy"
        else:
            status = "unhealthy"

        return PipelineHealthResponse(
            status=status,
            database_connected=database_connected,
            milvus_connected=True,  # Would need actual check
            neo4j_connected=True,  # Would need actual check
            active_pipelines=active_count,
        )

    def list_recent_executions(
        self,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        List recent pipeline executions.

        Args:
            status: Optional status filter.
            limit: Maximum number of records to return.

        Returns:
            List of execution summaries.
        """
        queryset = PipelineExecution.objects.all()

        if status:
            queryset = queryset.filter(status=status)

        queryset = queryset.order_by("-created_at")[:limit]

        executions = []
        for execution in queryset:
            executions.append({
                "execution_id": str(execution.id),
                "document_id": str(execution.document_id),
                "status": execution.status,
                "current_step": execution.current_step,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "total_duration_ms": execution.total_duration_ms,
                "error_message": execution.error_message[:100] if execution.error_message else "",
                "created_at": execution.created_at.isoformat(),
            })

        return executions

    def get_document_pipeline_summary(
        self,
        document_id: str,
    ) -> dict[str, Any]:
        """
        Get a summary of the pipeline status for a document.

        This is a convenience method that returns a simpler structure
        than get_pipeline_status, suitable for quick status checks.

        Args:
            document_id: UUID of the document.

        Returns:
            Dictionary with pipeline summary.
        """
        try:
            execution = PipelineExecution.objects.get(document_id=document_id)

            # Count steps by status
            completed_steps = execution.steps.filter(
                status=PipelineStep.Status.COMPLETED
            ).count()
            total_steps = execution.steps.count()

            return {
                "document_id": document_id,
                "status": execution.status,
                "current_step": execution.current_step,
                "progress": {
                    "completed_steps": completed_steps,
                    "total_steps": total_steps,
                    "percentage": int((completed_steps / total_steps * 100) if total_steps > 0 else 0),
                },
                "error": {
                    "step": execution.error_step,
                    "message": execution.error_message[:200] if execution.error_message else "",
                } if execution.error_message else None,
                "timing": {
                    "started_at": execution.started_at.isoformat() if execution.started_at else None,
                    "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                    "duration_ms": execution.total_duration_ms,
                },
            }

        except PipelineExecution.DoesNotExist:
            return {
                "document_id": document_id,
                "status": "not_found",
                "error": {"step": None, "message": "Pipeline execution not found"},
            }

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _build_status_response(
        self,
        execution: PipelineExecution,
    ) -> PipelineStatusResponse:
        """
        Build response DTO from execution model.

        Args:
            execution: PipelineExecution model instance.

        Returns:
            PipelineStatusResponse DTO.
        """
        steps = []
        for step in execution.steps.all():
            steps.append({
                "step_name": step.step_name,
                "step_order": step.step_order,
                "status": step.status,
                "duration_ms": step.duration_ms,
                "error_message": step.error_message,
                "output_data": step.output_data,
            })

        return PipelineStatusResponse(
            document_id=str(execution.document_id),
            status=execution.status,
            current_step=execution.current_step,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            total_duration_ms=execution.total_duration_ms,
            steps=steps,
            error_message=execution.error_message,
            retry_count=execution.retry_count,
        )

    def _check_database(self) -> bool:
        """
        Check database connection.

        Returns:
            True if database is connected.
        """
        try:
            # Simple query to check connection
            PipelineExecution.objects.count()
            return True
        except Exception:
            return False
