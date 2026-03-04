"""
Model Managers for Document Pipeline Manager.

This module defines custom managers for pipeline models with
useful query methods.
"""

from __future__ import annotations

from django.db import models


class PipelineExecutionManager(models.Manager):
    """Custom manager for PipelineExecution model."""

    def get_for_document(self, document_id: str) -> models.QuerySet:
        """
        Get pipeline execution for a specific document.

        Args:
            document_id: UUID of the document.

        Returns:
            QuerySet with the pipeline execution.
        """
        return self.get_queryset().filter(document_id=document_id)

    def get_running(self) -> models.QuerySet:
        """
        Get all currently running pipeline executions.

        Returns:
            QuerySet of running executions.
        """
        return self.get_queryset().filter(status=self.model.Status.RUNNING)

    def get_pending(self) -> models.QuerySet:
        """
        Get all pending pipeline executions.

        Returns:
            QuerySet of pending executions.
        """
        return self.get_queryset().filter(status=self.model.Status.PENDING)

    def get_failed(self) -> models.QuerySet:
        """
        Get all failed pipeline executions.

        Returns:
            QuerySet of failed executions.
        """
        return self.get_queryset().filter(status=self.model.Status.FAILED)

    def get_completed(self) -> models.QuerySet:
        """
        Get all completed pipeline executions.

        Returns:
            QuerySet of completed executions.
        """
        return self.get_queryset().filter(status=self.model.Status.COMPLETED)

    def get_active(self) -> models.QuerySet:
        """
        Get all active (pending or running) pipeline executions.

        Returns:
            QuerySet of active executions.
        """
        return self.get_queryset().filter(
            status__in=[self.model.Status.PENDING, self.model.Status.RUNNING]
        )

    def count_by_status(self) -> dict[str, int]:
        """
        Count executions by status.

        Returns:
            Dictionary with status counts.
        """
        return dict(
            self.get_queryset()
            .values("status")
            .annotate(count=models.Count("id"))
            .values_list("status", "count")
        )

    def get_average_duration(self) -> float:
        """
        Get average duration of completed executions in milliseconds.

        Returns:
            Average duration in milliseconds, or 0 if no completed executions.
        """
        result = (
            self.get_queryset()
            .filter(status=self.model.Status.COMPLETED)
            .aggregate(avg_duration=models.Avg("total_duration_ms"))
        )
        return result.get("avg_duration") or 0


class PipelineStepManager(models.Manager):
    """Custom manager for PipelineStep model."""

    def get_for_execution(self, execution_id: str) -> models.QuerySet:
        """
        Get all steps for a specific execution.

        Args:
            execution_id: UUID of the pipeline execution.

        Returns:
            QuerySet of steps ordered by step_order.
        """
        return self.get_queryset().filter(execution_id=execution_id).order_by("step_order")

    def get_by_name(self, execution_id: str, step_name: str) -> models.QuerySet:
        """
        Get a specific step by name for an execution.

        Args:
            execution_id: UUID of the pipeline execution.
            step_name: Name of the step.

        Returns:
            QuerySet with the step.
        """
        return self.get_queryset().filter(execution_id=execution_id, step_name=step_name)

    def get_failed(self, execution_id: str | None = None) -> models.QuerySet:
        """
        Get all failed steps.

        Args:
            execution_id: Optional execution ID to filter by.

        Returns:
            QuerySet of failed steps.
        """
        queryset = self.get_queryset().filter(status=self.model.Status.FAILED)
        if execution_id:
            queryset = queryset.filter(execution_id=execution_id)
        return queryset

    def get_running(self, execution_id: str | None = None) -> models.QuerySet:
        """
        Get all running steps.

        Args:
            execution_id: Optional execution ID to filter by.

        Returns:
            QuerySet of running steps.
        """
        queryset = self.get_queryset().filter(status=self.model.Status.RUNNING)
        if execution_id:
            queryset = queryset.filter(execution_id=execution_id)
        return queryset

    def get_completed(self, execution_id: str | None = None) -> models.QuerySet:
        """
        Get all completed steps.

        Args:
            execution_id: Optional execution ID to filter by.

        Returns:
            QuerySet of completed steps.
        """
        queryset = self.get_queryset().filter(status=self.model.Status.COMPLETED)
        if execution_id:
            queryset = queryset.filter(execution_id=execution_id)
        return queryset

    def get_pending(self, execution_id: str | None = None) -> models.QuerySet:
        """
        Get all pending steps.

        Args:
            execution_id: Optional execution ID to filter by.

        Returns:
            QuerySet of pending steps.
        """
        queryset = self.get_queryset().filter(status=self.model.Status.PENDING)
        if execution_id:
            queryset = queryset.filter(execution_id=execution_id)
        return queryset

    def get_skipped(self, execution_id: str | None = None) -> models.QuerySet:
        """
        Get all skipped steps.

        Args:
            execution_id: Optional execution ID to filter by.

        Returns:
            QuerySet of skipped steps.
        """
        queryset = self.get_queryset().filter(status=self.model.Status.SKIPPED)
        if execution_id:
            queryset = queryset.filter(execution_id=execution_id)
        return queryset

    def count_by_status(self, execution_id: str | None = None) -> dict[str, int]:
        """
        Count steps by status.

        Args:
            execution_id: Optional execution ID to filter by.

        Returns:
            Dictionary with status counts.
        """
        queryset = self.get_queryset()
        if execution_id:
            queryset = queryset.filter(execution_id=execution_id)
        return dict(
            queryset.values("status")
            .annotate(count=models.Count("id"))
            .values_list("status", "count")
        )

    def get_total_duration(self, execution_id: str) -> int:
        """
        Get total duration of all steps for an execution.

        Args:
            execution_id: UUID of the pipeline execution.

        Returns:
            Total duration in milliseconds.
        """
        result = self.get_for_execution(execution_id).aggregate(
            total=models.Sum("duration_ms")
        )
        return result.get("total") or 0

    def get_average_duration_by_step(self) -> dict[str, float]:
        """
        Get average duration for each step type.

        Returns:
            Dictionary mapping step names to average durations in milliseconds.
        """
        result = (
            self.get_queryset()
            .filter(status=self.model.Status.COMPLETED)
            .values("step_name")
            .annotate(avg_duration=models.Avg("duration_ms"))
        )
        return {item["step_name"]: item["avg_duration"] or 0 for item in result}
