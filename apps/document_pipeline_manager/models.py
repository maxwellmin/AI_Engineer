"""
Models for Document Pipeline Manager.

This module defines database models for tracking pipeline execution state
and individual step progress.
"""

from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone

from apps.documents_parser.models import Document
from apps.document_pipeline_manager.managers import (
    PipelineExecutionManager,
    PipelineStepManager,
)


class PipelineExecution(models.Model):
    """
    Tracks overall pipeline execution for a document.

    Records the complete state of a document processing pipeline,
    including status, timing, and error information.
    """

    class Status(models.TextChoices):
        """Pipeline execution status."""

        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name="pipeline_execution",
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    current_step = models.CharField(max_length=50, default="")

    # Timing information
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_duration_ms = models.PositiveBigIntegerField(default=0)

    # Error tracking
    error_message = models.TextField(blank=True, default="")
    error_step = models.CharField(max_length=50, blank=True, default="")
    retry_count = models.PositiveIntegerField(default=0)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Custom manager
    objects = PipelineExecutionManager()

    class Meta:
        db_table = "pipeline_executions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"Pipeline for {self.document.name} ({self.status})"

    def start(self) -> None:
        """Mark pipeline as started."""
        self.status = self.Status.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at", "updated_at"])

    def complete(self) -> None:
        """Mark pipeline as completed successfully."""
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        if self.started_at:
            self.total_duration_ms = int(
                (self.completed_at - self.started_at).total_seconds() * 1000
            )
        self.save(
            update_fields=["status", "completed_at", "total_duration_ms", "updated_at"]
        )

    def fail(self, error_message: str, error_step: str = "") -> None:
        """Mark pipeline as failed with error."""
        self.status = self.Status.FAILED
        self.error_message = error_message
        self.error_step = error_step
        self.completed_at = timezone.now()
        if self.started_at:
            self.total_duration_ms = int(
                (self.completed_at - self.started_at).total_seconds() * 1000
            )
        self.save(
            update_fields=[
                "status",
                "error_message",
                "error_step",
                "completed_at",
                "total_duration_ms",
                "updated_at",
            ]
        )

    def cancel(self) -> None:
        """Mark pipeline as cancelled."""
        self.status = self.Status.CANCELLED
        self.completed_at = timezone.now()
        if self.started_at:
            self.total_duration_ms = int(
                (self.completed_at - self.started_at).total_seconds() * 1000
            )
        self.save(
            update_fields=["status", "completed_at", "total_duration_ms", "updated_at"]
        )

    def increment_retry(self) -> None:
        """Increment retry count."""
        self.retry_count = models.F("retry_count") + 1
        self.save(update_fields=["retry_count", "updated_at"])

    @property
    def is_running(self) -> bool:
        """Check if pipeline is currently running."""
        return self.status == self.Status.RUNNING

    @property
    def is_completed(self) -> bool:
        """Check if pipeline completed successfully."""
        return self.status == self.Status.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if pipeline failed."""
        return self.status == self.Status.FAILED

    @property
    def is_cancelled(self) -> bool:
        """Check if pipeline was cancelled."""
        return self.status == self.Status.CANCELLED

    @property
    def is_terminal(self) -> bool:
        """Check if pipeline is in a terminal state."""
        return self.status in [
            self.Status.COMPLETED,
            self.Status.FAILED,
            self.Status.CANCELLED,
        ]


class PipelineStep(models.Model):
    """
    Tracks individual step execution details.

    Records the state of each pipeline step, including timing,
    input/output data, and error information.
    """

    class Status(models.TextChoices):
        """Pipeline step status."""

        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    execution = models.ForeignKey(
        PipelineExecution,
        on_delete=models.CASCADE,
        related_name="steps",
    )

    # Step identification
    step_name = models.CharField(max_length=50)  # parse, chunk, embed, etc.
    step_order = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Timing information
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveBigIntegerField(default=0)

    # Input/Output data (for debugging and auditing)
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    # Custom manager
    objects = PipelineStepManager()

    class Meta:
        db_table = "pipeline_steps"
        ordering = ["step_order"]
        indexes = [
            models.Index(fields=["execution", "step_order"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["execution", "step_name"],
                name="unique_execution_step_name",
            )
        ]

    def __str__(self) -> str:
        return f"Step {self.step_name} ({self.status})"

    def start(self) -> None:
        """Mark step as started."""
        self.status = self.Status.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def complete(self, output_data: dict | None = None) -> None:
        """Mark step as completed successfully."""
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        if self.started_at:
            self.duration_ms = int(
                (self.completed_at - self.started_at).total_seconds() * 1000
            )
        if output_data:
            self.output_data = output_data
        self.save(update_fields=["status", "completed_at", "duration_ms", "output_data"])

    def fail(self, error_message: str) -> None:
        """Mark step as failed with error."""
        self.status = self.Status.FAILED
        self.error_message = error_message
        self.completed_at = timezone.now()
        if self.started_at:
            self.duration_ms = int(
                (self.completed_at - self.started_at).total_seconds() * 1000
            )
        self.save(
            update_fields=["status", "error_message", "completed_at", "duration_ms"]
        )

    def skip(self, reason: str = "") -> None:
        """Mark step as skipped."""
        self.status = self.Status.SKIPPED
        if reason:
            self.error_message = reason
        self.save(update_fields=["status", "error_message"])

    @property
    def is_running(self) -> bool:
        """Check if step is currently running."""
        return self.status == self.Status.RUNNING

    @property
    def is_completed(self) -> bool:
        """Check if step completed successfully."""
        return self.status == self.Status.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if step failed."""
        return self.status == self.Status.FAILED

    @property
    def is_skipped(self) -> bool:
        """Check if step was skipped."""
        return self.status == self.Status.SKIPPED

    @property
    def is_terminal(self) -> bool:
        """Check if step is in a terminal state."""
        return self.status in [
            self.Status.COMPLETED,
            self.Status.FAILED,
            self.Status.SKIPPED,
        ]
