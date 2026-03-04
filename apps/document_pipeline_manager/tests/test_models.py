"""
Tests for Pipeline Models.

This module tests PipelineExecution and PipelineStep models.
"""

from __future__ import annotations

import pytest
from django.utils import timezone

from apps.document_pipeline_manager.models import PipelineExecution, PipelineStep
from apps.documents_parser.models import Document


@pytest.mark.django_db
class TestPipelineExecution:
    """Tests for PipelineExecution model."""

    def test_create_execution(self, test_document):
        """Test creating a pipeline execution."""
        execution = PipelineExecution.objects.create(
            document=test_document,
            status=PipelineExecution.Status.PENDING,
        )

        assert execution.id is not None
        assert execution.status == PipelineExecution.Status.PENDING
        assert execution.document == test_document
        assert execution.current_step == ""
        assert execution.started_at is None
        assert execution.completed_at is None
        assert execution.total_duration_ms == 0
        assert execution.error_message == ""
        assert execution.error_step == ""
        assert execution.retry_count == 0
        assert execution.created_at is not None
        assert execution.updated_at is not None

    def test_execution_str(self, test_execution):
        """Test string representation."""
        assert str(test_execution.document_id) in str(test_execution)

    def test_execution_status_choices(self, test_document):
        """Test all status choices."""
        statuses = [
            PipelineExecution.Status.PENDING,
            PipelineExecution.Status.RUNNING,
            PipelineExecution.Status.COMPLETED,
            PipelineExecution.Status.FAILED,
            PipelineExecution.Status.CANCELLED,
        ]

        for status in statuses:
            execution = PipelineExecution.objects.create(
                document=test_document,
                status=status,
            )
            assert execution.status == status

    def test_one_to_one_relationship(self, test_document):
        """Test that each document has only one execution."""
        execution1 = PipelineExecution.objects.create(
            document=test_document,
            status=PipelineExecution.Status.PENDING,
        )

        # Attempting to create another should fail
        with pytest.raises(Exception):
            PipelineExecution.objects.create(
                document=test_document,
                status=PipelineExecution.Status.PENDING,
            )

    def test_cascade_delete(self, test_document):
        """Test that execution is deleted when document is deleted."""
        execution = PipelineExecution.objects.create(
            document=test_document,
            status=PipelineExecution.Status.PENDING,
        )
        execution_id = execution.id

        test_document.delete()

        assert not PipelineExecution.objects.filter(id=execution_id).exists()

    def test_timing_fields(self, test_document):
        """Test timing fields."""
        now = timezone.now()

        execution = PipelineExecution.objects.create(
            document=test_document,
            status=PipelineExecution.Status.COMPLETED,
            started_at=now,
            completed_at=now,
            total_duration_ms=5000,
        )

        assert execution.started_at == now
        assert execution.completed_at == now
        assert execution.total_duration_ms == 5000

    def test_error_tracking(self, test_document):
        """Test error tracking fields."""
        execution = PipelineExecution.objects.create(
            document=test_document,
            status=PipelineExecution.Status.FAILED,
            error_step="embed",
            error_message="Embedding generation failed",
            retry_count=3,
        )

        assert execution.error_step == "embed"
        assert execution.error_message == "Embedding generation failed"
        assert execution.retry_count == 3

    def test_execution_with_steps(self, test_execution_running):
        """Test execution with step records."""
        execution = test_execution_running

        assert execution.steps.count() == 6
        assert execution.steps.filter(status=PipelineStep.Status.COMPLETED).count() == 2
        assert execution.steps.filter(status=PipelineStep.Status.RUNNING).count() == 1
        assert execution.steps.filter(status=PipelineStep.Status.PENDING).count() == 3


@pytest.mark.django_db
class TestPipelineStep:
    """Tests for PipelineStep model."""

    def test_create_step(self, test_execution):
        """Test creating a pipeline step."""
        step = PipelineStep.objects.create(
            execution=test_execution,
            step_name="parse",
            step_order=1,
            status=PipelineStep.Status.COMPLETED,
            duration_ms=1500,
        )

        assert step.id is not None
        assert step.execution == test_execution
        assert step.step_name == "parse"
        assert step.step_order == 1
        assert step.status == PipelineStep.Status.COMPLETED
        assert step.duration_ms == 1500
        assert step.created_at is not None

    def test_step_str(self, test_execution):
        """Test string representation."""
        step = PipelineStep.objects.create(
            execution=test_execution,
            step_name="parse",
            step_order=1,
            status=PipelineStep.Status.COMPLETED,
        )
        assert "parse" in str(step)

    def test_step_status_choices(self, test_execution):
        """Test all status choices."""
        statuses = [
            PipelineStep.Status.PENDING,
            PipelineStep.Status.RUNNING,
            PipelineStep.Status.COMPLETED,
            PipelineStep.Status.FAILED,
            PipelineStep.Status.SKIPPED,
        ]

        for status in statuses:
            step = PipelineStep.objects.create(
                execution=test_execution,
                step_name=f"step_{status}",
                step_order=0,
                status=status,
            )
            assert step.status == status

    def test_step_ordering(self, test_execution):
        """Test that steps are ordered by step_order."""
        PipelineStep.objects.create(
            execution=test_execution,
            step_name="embed",
            step_order=3,
            status=PipelineStep.Status.PENDING,
        )
        PipelineStep.objects.create(
            execution=test_execution,
            step_name="parse",
            step_order=1,
            status=PipelineStep.Status.COMPLETED,
        )
        PipelineStep.objects.create(
            execution=test_execution,
            step_name="chunk",
            step_order=2,
            status=PipelineStep.Status.COMPLETED,
        )

        steps = list(test_execution.steps.all())
        assert steps[0].step_name == "parse"
        assert steps[1].step_name == "chunk"
        assert steps[2].step_name == "embed"

    def test_step_input_output_data(self, test_execution):
        """Test input_data and output_data JSON fields."""
        step = PipelineStep.objects.create(
            execution=test_execution,
            step_name="parse",
            step_order=1,
            status=PipelineStep.Status.COMPLETED,
            input_data={"file_path": "test.pdf"},
            output_data={"text_length": 5000, "page_count": 10},
        )

        assert step.input_data == {"file_path": "test.pdf"}
        assert step.output_data == {"text_length": 5000, "page_count": 10}

    def test_step_timing(self, test_execution):
        """Test step timing fields."""
        now = timezone.now()

        step = PipelineStep.objects.create(
            execution=test_execution,
            step_name="parse",
            step_order=1,
            status=PipelineStep.Status.COMPLETED,
            started_at=now,
            completed_at=now,
            duration_ms=1500,
        )

        assert step.started_at == now
        assert step.completed_at == now
        assert step.duration_ms == 1500

    def test_step_error_message(self, test_execution):
        """Test step error message."""
        step = PipelineStep.objects.create(
            execution=test_execution,
            step_name="embed",
            step_order=3,
            status=PipelineStep.Status.FAILED,
            error_message="API timeout",
        )

        assert step.error_message == "API timeout"

    def test_cascade_delete(self, test_execution):
        """Test that steps are deleted when execution is deleted."""
        step = PipelineStep.objects.create(
            execution=test_execution,
            step_name="parse",
            step_order=1,
            status=PipelineStep.Status.COMPLETED,
        )
        step_id = step.id

        test_execution.delete()

        assert not PipelineStep.objects.filter(id=step_id).exists()


@pytest.mark.django_db
class TestPipelineExecutionManager:
    """Tests for PipelineExecution manager methods."""

    def test_running_count(self, test_execution_running):
        """Test counting running executions."""
        count = PipelineExecution.objects.filter(
            status=PipelineExecution.Status.RUNNING
        ).count()
        assert count == 1

    def test_failed_count(self, test_execution_failed):
        """Test counting failed executions."""
        count = PipelineExecution.objects.filter(
            status=PipelineExecution.Status.FAILED
        ).count()
        assert count == 1

    def test_completed_count(self, test_execution_completed):
        """Test counting completed executions."""
        count = PipelineExecution.objects.filter(
            status=PipelineExecution.Status.COMPLETED
        ).count()
        assert count == 1

    def test_get_by_document(self, test_execution):
        """Test getting execution by document."""
        execution = PipelineExecution.objects.get(document=test_execution.document)
        assert execution == test_execution
