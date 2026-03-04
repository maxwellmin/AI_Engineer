"""
Pipeline Orchestrator for Document Processing.

This module provides the PipelineOrchestrator class that coordinates
the sequential execution of pipeline steps, handling errors, retries,
and state management.
"""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from apps.document_pipeline_manager.constants import PipelineStepName
from apps.document_pipeline_manager.dto import PipelineConfig, StepResult
from apps.document_pipeline_manager.exceptions import (
    PipelineCancelledError,
    MaxRetriesExceededError,
)
from apps.document_pipeline_manager.models import PipelineExecution, PipelineStep
from apps.document_pipeline_manager.runners import (
    ParseStepRunner,
    ChunkStepRunner,
    EmbedStepRunner,
    VectorizeStepRunner,
    GraphStepRunner,
    ExtractStepRunner,
    get_all_runners,
)
from apps.documents_parser.models import Document

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates document processing pipeline execution.

    Manages the sequential execution of pipeline steps, handling errors,
    retries, and state transitions.

    Example:
        >>> orchestrator = PipelineOrchestrator()
        >>> execution = orchestrator.execute(document_id="abc-123")
        >>> print(execution.status)
        'completed'
    """

    def __init__(self, config: PipelineConfig | None = None) -> None:
        """
        Initialize the orchestrator.

        Args:
            config: Optional pipeline configuration. Uses defaults if not provided.
        """
        self.config = config or PipelineConfig()
        self._init_runners()

    def _init_runners(self) -> None:
        """Initialize step runners in execution order."""
        self._runners = [
            ParseStepRunner(),
            ChunkStepRunner(
                chunk_size=getattr(self.config, "chunk_size", 1000),
                chunk_overlap=getattr(self.config, "chunk_overlap", 200),
            ),
            EmbedStepRunner(
                batch_size=self.config.batch_size,
            ),
            VectorizeStepRunner(
                batch_size=self.config.batch_size,
            ),
            GraphStepRunner(),
            ExtractStepRunner(
                enable_extraction=self.config.enable_entity_extraction,
            ),
        ]

        # Create name to runner mapping
        self._runner_map = {runner.step_name: runner for runner in self._runners}

    @property
    def runners(self) -> list:
        """Get list of step runners in execution order."""
        return self._runners

    def execute(self, document_id: str) -> PipelineExecution:
        """
        Execute full pipeline for a document.

        Args:
            document_id: UUID of the document to process.

        Returns:
            PipelineExecution with final status.
        """
        logger.info(f"[Pipeline] Starting execution for document {document_id}")

        # Create or get execution record
        execution = self._create_execution(document_id)

        try:
            # Update status to running
            execution.status = PipelineExecution.Status.RUNNING
            execution.started_at = timezone.now()
            execution.save(update_fields=["status", "started_at"])

            # Execute each step sequentially
            for runner in self._runners:
                # Check for cancellation
                execution.refresh_from_db()
                if execution.status == PipelineExecution.Status.CANCELLED:
                    logger.info(f"[Pipeline] Pipeline cancelled for document {document_id}")
                    break

                # Execute step
                step_record = self._create_step_record(execution, runner)
                result = runner.execute(document_id)

                # Update step record
                self._update_step_record(step_record, result)

                if not result.success:
                    # Handle failure
                    self._handle_step_failure(
                        execution, runner.step_name, result
                    )
                    return execution

                # Update execution progress
                execution.current_step = runner.step_name
                execution.save(update_fields=["current_step"])

            # All steps completed successfully
            if execution.status != PipelineExecution.Status.CANCELLED:
                self._finalize_execution(execution, success=True)

        except PipelineCancelledError:
            logger.info(f"[Pipeline] Pipeline cancelled for document {document_id}")
            self._finalize_execution(execution, success=False, error="Pipeline cancelled")

        except Exception as e:
            logger.exception(f"[Pipeline] Pipeline failed for document {document_id}")
            self._finalize_execution(execution, success=False, error=str(e))

        return execution

    def retry_step(
        self,
        document_id: str,
        step_name: str,
    ) -> PipelineExecution:
        """
        Retry a failed step.

        Args:
            document_id: UUID of the document.
            step_name: Name of the step to retry.

        Returns:
            PipelineExecution with updated status.

        Raises:
            MaxRetriesExceededError: If max retries exceeded.
        """
        logger.info(
            f"[Pipeline] Retrying step '{step_name}' for document {document_id}"
        )

        try:
            execution = PipelineExecution.objects.get(document_id=document_id)
        except PipelineExecution.DoesNotExist:
            raise ValueError(f"No execution found for document {document_id}")

        # Check retry count
        if execution.retry_count >= self.config.max_retries:
            raise MaxRetriesExceededError(step_name, self.config.max_retries)

        # Increment retry count
        execution.retry_count += 1
        execution.save(update_fields=["retry_count"])

        # Get the step to retry
        try:
            step = execution.steps.get(step_name=step_name)
        except PipelineStep.DoesNotExist:
            raise ValueError(f"Step '{step_name}' not found in execution")

        # Get the runner
        runner = self._runner_map.get(step_name)
        if not runner:
            raise ValueError(f"Unknown step: {step_name}")

        # Reset step status
        step.status = PipelineStep.Status.RUNNING
        step.started_at = timezone.now()
        step.save(update_fields=["status", "started_at"])

        # Update execution status
        execution.status = PipelineExecution.Status.RUNNING
        execution.save(update_fields=["status"])

        # Execute the step
        result = runner.execute(document_id)

        # Update step record
        self._update_step_record(step, result)

        if result.success:
            # Continue with remaining steps
            return self._continue_from_step(document_id, step_name)
        else:
            # Update execution with failure
            execution.error_message = result.error_message
            execution.error_step = step_name
            execution.status = PipelineExecution.Status.FAILED
            execution.save(update_fields=["error_message", "error_step", "status"])

            return execution

    def retry_from_failed(
        self,
        document_id: str,
    ) -> PipelineExecution:
        """
        Retry pipeline from the failed step.

        Args:
            document_id: UUID of the document.

        Returns:
            PipelineExecution with updated status.
        """
        try:
            execution = PipelineExecution.objects.get(document_id=document_id)
        except PipelineExecution.DoesNotExist:
            raise ValueError(f"No execution found for document {document_id}")

        if execution.status != PipelineExecution.Status.FAILED:
            raise ValueError("Can only retry failed executions")

        if not execution.error_step:
            raise ValueError("No failed step found in execution")

        return self.retry_step(document_id, execution.error_step)

    def cancel(self, document_id: str) -> PipelineExecution:
        """
        Cancel a running pipeline.

        Args:
            document_id: UUID of the document.

        Returns:
            PipelineExecution with cancelled status.
        """
        logger.info(f"[Pipeline] Cancelling pipeline for document {document_id}")

        try:
            execution = PipelineExecution.objects.get(document_id=document_id)
        except PipelineExecution.DoesNotExist:
            raise ValueError(f"No execution found for document {document_id}")

        if execution.status not in [
            PipelineExecution.Status.PENDING,
            PipelineExecution.Status.RUNNING,
        ]:
            raise ValueError("Can only cancel pending or running pipelines")

        # Update status to cancelled
        execution.status = PipelineExecution.Status.CANCELLED
        execution.completed_at = timezone.now()
        execution.save(update_fields=["status", "completed_at"])

        # Mark any running steps as skipped
        running_steps = execution.steps.filter(status=PipelineStep.Status.RUNNING)
        for step in running_steps:
            step.status = PipelineStep.Status.SKIPPED
            step.save(update_fields=["status"])

        return execution

    def get_status(self, document_id: str) -> dict[str, Any]:
        """
        Get current pipeline status.

        Args:
            document_id: UUID of the document.

        Returns:
            Dictionary with pipeline status.
        """
        try:
            execution = PipelineExecution.objects.get(document_id=document_id)
        except PipelineExecution.DoesNotExist:
            return {
                "document_id": document_id,
                "status": "not_found",
                "current_step": "",
                "steps": [],
                "error_message": "Pipeline execution not found",
            }

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

        return {
            "document_id": str(execution.document_id),
            "status": execution.status,
            "current_step": execution.current_step,
            "started_at": execution.started_at,
            "completed_at": execution.completed_at,
            "total_duration_ms": execution.total_duration_ms,
            "steps": steps,
            "error_message": execution.error_message,
            "error_step": execution.error_step,
            "retry_count": execution.retry_count,
        }

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _create_execution(self, document_id: str) -> PipelineExecution:
        """
        Create or get pipeline execution record.

        Args:
            document_id: UUID of the document.

        Returns:
            PipelineExecution instance.
        """
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            raise ValueError(f"Document {document_id} not found")

        # Try to get existing execution
        execution, created = PipelineExecution.objects.get_or_create(
            document=document,
            defaults={
                "status": PipelineExecution.Status.PENDING,
            },
        )

        if not created:
            # Reset execution for re-processing
            execution.status = PipelineExecution.Status.PENDING
            execution.started_at = None
            execution.completed_at = None
            execution.total_duration_ms = 0
            execution.error_message = ""
            execution.error_step = ""
            execution.current_step = ""
            execution.save()

            # Delete existing steps
            execution.steps.all().delete()

        # Create step records
        self._create_all_step_records(execution)

        return execution

    def _create_all_step_records(self, execution: PipelineExecution) -> None:
        """
        Create step records for all pipeline steps.

        Args:
            execution: PipelineExecution instance.
        """
        for runner in self._runners:
            PipelineStep.objects.create(
                execution=execution,
                step_name=runner.step_name,
                step_order=runner.step_order,
                status=PipelineStep.Status.PENDING,
            )

    def _create_step_record(
        self,
        execution: PipelineExecution,
        runner: Any,
    ) -> PipelineStep:
        """
        Update step record to running status.

        Args:
            execution: PipelineExecution instance.
            runner: Step runner instance.

        Returns:
            Updated PipelineStep instance.
        """
        step = execution.steps.get(step_name=runner.step_name)
        step.status = PipelineStep.Status.RUNNING
        step.started_at = timezone.now()
        step.save(update_fields=["status", "started_at"])

        return step

    def _update_step_record(
        self,
        step: PipelineStep,
        result: StepResult,
    ) -> None:
        """
        Update step record with execution result.

        Args:
            step: PipelineStep instance.
            result: StepResult from runner.
        """
        step.completed_at = timezone.now()
        step.duration_ms = result.duration_ms
        step.output_data = result.output_data

        if result.success:
            step.status = PipelineStep.Status.COMPLETED
            step.error_message = ""
        else:
            step.status = PipelineStep.Status.FAILED
            step.error_message = result.error_message

        step.save(
            update_fields=[
                "status",
                "completed_at",
                "duration_ms",
                "output_data",
                "error_message",
            ]
        )

    def _handle_step_failure(
        self,
        execution: PipelineExecution,
        step_name: str,
        result: StepResult,
    ) -> None:
        """
        Handle step failure.

        Args:
            execution: PipelineExecution instance.
            step_name: Name of the failed step.
            result: StepResult with failure details.
        """
        logger.error(
            f"[Pipeline] Step '{step_name}' failed for document {execution.document_id}: "
            f"{result.error_message}"
        )

        # Update execution
        execution.status = PipelineExecution.Status.FAILED
        execution.error_step = step_name
        execution.error_message = result.error_message
        execution.completed_at = timezone.now()
        execution.total_duration_ms = self._calculate_total_duration(execution)
        execution.save(
            update_fields=[
                "status",
                "error_step",
                "error_message",
                "completed_at",
                "total_duration_ms",
            ]
        )

        # Mark remaining steps as skipped
        remaining_steps = execution.steps.filter(
            step_order__gt=self._runner_map[step_name].step_order
        )
        for step in remaining_steps:
            step.status = PipelineStep.Status.SKIPPED
            step.save(update_fields=["status"])

    def _finalize_execution(
        self,
        execution: PipelineExecution,
        success: bool,
        error: str = "",
    ) -> None:
        """
        Finalize pipeline execution.

        Args:
            execution: PipelineExecution instance.
            success: Whether execution succeeded.
            error: Optional error message.
        """
        execution.completed_at = timezone.now()
        execution.total_duration_ms = self._calculate_total_duration(execution)

        if success:
            execution.status = PipelineExecution.Status.COMPLETED
            execution.error_message = ""
            execution.error_step = ""

            # Update document status
            try:
                document = Document.objects.get(id=execution.document_id)
                document.status = Document.Status.DONE
                document.save(update_fields=["status", "updated_at"])
            except Document.DoesNotExist:
                pass
        else:
            if execution.status != PipelineExecution.Status.CANCELLED:
                execution.status = PipelineExecution.Status.FAILED
            if error:
                execution.error_message = error

        execution.save()

        logger.info(
            f"[Pipeline] Execution {'completed' if success else 'failed'} for document "
            f"{execution.document_id} in {execution.total_duration_ms}ms"
        )

    def _continue_from_step(
        self,
        document_id: str,
        completed_step_name: str,
    ) -> PipelineExecution:
        """
        Continue pipeline execution from after a completed step.

        Args:
            document_id: UUID of the document.
            completed_step_name: Name of the just-completed step.

        Returns:
            PipelineExecution with final status.
        """
        execution = PipelineExecution.objects.get(document_id=document_id)

        # Find next steps to execute
        completed_order = self._runner_map[completed_step_name].step_order

        for runner in self._runners:
            if runner.step_order <= completed_order:
                continue

            # Check for cancellation
            execution.refresh_from_db()
            if execution.status == PipelineExecution.Status.CANCELLED:
                break

            # Execute step
            step_record = execution.steps.get(step_name=runner.step_name)
            result = runner.execute(document_id)

            # Update step record
            self._update_step_record(step_record, result)

            if not result.success:
                self._handle_step_failure(execution, runner.step_name, result)
                return execution

            # Update execution progress
            execution.current_step = runner.step_name
            execution.save(update_fields=["current_step"])

        # All steps completed
        if execution.status != PipelineExecution.Status.CANCELLED:
            self._finalize_execution(execution, success=True)

        return execution

    def _calculate_total_duration(self, execution: PipelineExecution) -> int:
        """
        Calculate total pipeline duration in milliseconds.

        Args:
            execution: PipelineExecution instance.

        Returns:
            Total duration in milliseconds.
        """
        if execution.started_at and execution.completed_at:
            delta = execution.completed_at - execution.started_at
            return int(delta.total_seconds() * 1000)

        # Sum up step durations
        return sum(step.duration_ms for step in execution.steps.all())
