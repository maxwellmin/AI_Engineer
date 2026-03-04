"""
Tests for Pipeline Orchestrator.

This module tests the PipelineOrchestrator class.
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.utils import timezone

from apps.document_pipeline_manager.models import PipelineExecution, PipelineStep
from apps.document_pipeline_manager.orchestrator import PipelineOrchestrator
from apps.document_pipeline_manager.dto import PipelineConfig
from apps.document_pipeline_manager.runners.base import StepResult


@pytest.mark.django_db
class TestPipelineOrchestrator:
    """Tests for PipelineOrchestrator."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        orchestrator = PipelineOrchestrator()

        assert orchestrator.config is not None
        assert orchestrator.config.max_retries == 3
        assert len(orchestrator.runners) == 6

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = PipelineConfig(
            max_retries=5,
            batch_size=50,
            enable_entity_extraction=False,
        )
        orchestrator = PipelineOrchestrator(config)

        assert orchestrator.config.max_retries == 5
        assert orchestrator.config.batch_size == 50

    def test_runners_order(self):
        """Test that runners are in correct order."""
        orchestrator = PipelineOrchestrator()

        expected_order = ["parse", "chunk", "embed", "vectorize", "graph", "extract"]
        actual_order = [r.step_name for r in orchestrator.runners]

        assert actual_order == expected_order

    def test_create_execution(self, test_document):
        """Test creating execution record."""
        orchestrator = PipelineOrchestrator()
        execution = orchestrator._create_execution(str(test_document.id))

        assert execution is not None
        assert execution.document == test_document
        assert execution.status == PipelineExecution.Status.PENDING
        assert execution.steps.count() == 6

    def test_create_step_record(self, test_execution):
        """Test creating step record."""
        orchestrator = PipelineOrchestrator()
        runner = orchestrator.runners[0]

        step = orchestrator._create_step_record(test_execution, runner)

        assert step is not None
        assert step.execution == test_execution
        assert step.step_name == runner.step_name
        assert step.step_order == runner.step_order
        assert step.status == PipelineStep.Status.PENDING

    def test_update_step_record_success(self, test_execution):
        """Test updating step record on success."""
        orchestrator = PipelineOrchestrator()
        runner = orchestrator.runners[0]
        step = orchestrator._create_step_record(test_execution, runner)

        result = StepResult(
            success=True,
            output_data={"text_length": 5000},
            duration_ms=1500,
        )

        orchestrator._update_step_record(step, result)
        step.refresh_from_db()

        assert step.status == PipelineStep.Status.COMPLETED
        assert step.duration_ms == 1500
        assert step.output_data == {"text_length": 5000}
        assert step.error_message == ""

    def test_update_step_record_failure(self, test_execution):
        """Test updating step record on failure."""
        orchestrator = PipelineOrchestrator()
        runner = orchestrator.runners[0]
        step = orchestrator._create_step_record(test_execution, runner)

        result = StepResult(
            success=False,
            output_data={},
            error_message="Parse failed",
            duration_ms=500,
        )

        orchestrator._update_step_record(step, result)
        step.refresh_from_db()

        assert step.status == PipelineStep.Status.FAILED
        assert step.duration_ms == 500
        assert step.error_message == "Parse failed"

    def test_handle_step_failure(self, test_execution):
        """Test handling step failure."""
        orchestrator = PipelineOrchestrator()

        result = StepResult(
            success=False,
            output_data={},
            error_message="Test error",
        )

        orchestrator._handle_step_failure(test_execution, "embed", result)
        test_execution.refresh_from_db()

        assert test_execution.status == PipelineExecution.Status.FAILED
        assert test_execution.error_step == "embed"
        assert test_execution.error_message == "Test error"
        assert test_execution.completed_at is not None

    def test_finalize_execution_success(self, test_execution):
        """Test finalizing execution on success."""
        orchestrator = PipelineOrchestrator()
        test_execution.status = PipelineExecution.Status.RUNNING
        test_execution.save()

        orchestrator._finalize_execution(test_execution, success=True)
        test_execution.refresh_from_db()

        assert test_execution.status == PipelineExecution.Status.COMPLETED
        assert test_execution.completed_at is not None
        assert test_execution.error_message == ""

    def test_finalize_execution_failure(self, test_execution):
        """Test finalizing execution on failure."""
        orchestrator = PipelineOrchestrator()
        test_execution.status = PipelineExecution.Status.RUNNING
        test_execution.save()

        orchestrator._finalize_execution(test_execution, success=False, error="Test error")
        test_execution.refresh_from_db()

        assert test_execution.status == PipelineExecution.Status.FAILED
        assert test_execution.completed_at is not None
        assert test_execution.error_message == "Test error"


@pytest.mark.django_db
class TestPipelineOrchestratorExecute:
    """Tests for PipelineOrchestrator.execute method."""

    @patch("apps.document_pipeline_manager.orchestrator.pipeline_orchestrator.ParseStepRunner")
    @patch("apps.document_pipeline_manager.orchestrator.pipeline_orchestrator.ChunkStepRunner")
    @patch("apps.document_pipeline_manager.orchestrator.pipeline_orchestrator.EmbedStepRunner")
    @patch("apps.document_pipeline_manager.orchestrator.pipeline_orchestrator.VectorizeStepRunner")
    @patch("apps.document_pipeline_manager.orchestrator.pipeline_orchestrator.GraphStepRunner")
    @patch("apps.document_pipeline_manager.orchestrator.pipeline_orchestrator.ExtractStepRunner")
    def test_execute_success(
        self,
        mock_extract,
        mock_graph,
        mock_vectorize,
        mock_embed,
        mock_chunk,
        mock_parse,
        test_document,
    ):
        """Test successful pipeline execution."""
        # Setup mocks
        for mock_runner in [mock_parse, mock_chunk, mock_embed, mock_vectorize, mock_graph, mock_extract]:
            instance = mock_runner.return_value
            instance.step_name = mock_runner.__name__.replace("StepRunner", "").lower()
            instance.step_order = 1
            instance.execute.return_value = StepResult(
                success=True,
                output_data={},
                duration_ms=100,
            )

        orchestrator = PipelineOrchestrator()
        execution = orchestrator.execute(str(test_document.id))

        assert execution.status == PipelineExecution.Status.COMPLETED
        assert execution.completed_at is not None

    def test_execute_document_not_found(self):
        """Test execution with non-existent document."""
        orchestrator = PipelineOrchestrator()

        with pytest.raises(Exception):
            orchestrator.execute("00000000-0000-0000-0000-000000000000")


@pytest.mark.django_db
class TestPipelineOrchestratorRetry:
    """Tests for PipelineOrchestrator retry methods."""

    def test_get_runner_by_name(self):
        """Test getting runner by name."""
        orchestrator = PipelineOrchestrator()

        runner = orchestrator._get_runner_by_name("parse")
        assert runner is not None
        assert runner.step_name == "parse"

        runner = orchestrator._get_runner_by_name("nonexistent")
        assert runner is None

    def test_retry_step_not_found(self, test_document):
        """Test retrying step for non-existent execution."""
        orchestrator = PipelineOrchestrator()

        with pytest.raises(PipelineExecution.DoesNotExist):
            orchestrator.retry_step(str(test_document.id), "parse")

    def test_retry_step_max_retries(self, test_execution_failed):
        """Test retry when max retries exceeded."""
        orchestrator = PipelineOrchestrator()
        test_execution_failed.retry_count = 3
        test_execution_failed.save()

        # Should still work - we don't enforce max retries at orchestrator level
        # The service layer handles this
        execution = orchestrator.retry_step(
            str(test_execution_failed.document_id),
            "embed"
        )

        # Execution should be created/retrieved
        assert execution is not None


@pytest.mark.django_db
class TestPipelineOrchestratorCancel:
    """Tests for PipelineOrchestrator.cancel method."""

    def test_cancel_running_pipeline(self, test_execution_running):
        """Test cancelling a running pipeline."""
        orchestrator = PipelineOrchestrator()

        execution = orchestrator.cancel(str(test_execution_running.document_id))
        execution.refresh_from_db()

        assert execution.status == PipelineExecution.Status.CANCELLED
        assert execution.completed_at is not None

    def test_cancel_pending_pipeline(self, test_execution):
        """Test cancelling a pending pipeline."""
        orchestrator = PipelineOrchestrator()

        execution = orchestrator.cancel(str(test_execution.document_id))

        assert execution.status == PipelineExecution.Status.CANCELLED

    def test_cancel_completed_pipeline(self, test_execution_completed):
        """Test cancelling a completed pipeline raises error."""
        orchestrator = PipelineOrchestrator()

        with pytest.raises(ValueError, match="Cannot cancel"):
            orchestrator.cancel(str(test_execution_completed.document_id))

    def test_cancel_nonexistent_pipeline(self):
        """Test cancelling non-existent pipeline."""
        orchestrator = PipelineOrchestrator()

        with pytest.raises(PipelineExecution.DoesNotExist):
            orchestrator.cancel("00000000-0000-0000-0000-000000000000")


@pytest.mark.django_db
class TestPipelineOrchestratorGetStatus:
    """Tests for PipelineOrchestrator.get_status method."""

    def test_get_status_success(self, test_execution_running):
        """Test getting status for existing execution."""
        orchestrator = PipelineOrchestrator()

        status = orchestrator.get_status(str(test_execution_running.document_id))

        assert status["document_id"] == str(test_execution_running.document_id)
        assert status["status"] == "running"
        assert status["current_step"] == "embed"
        assert len(status["steps"]) == 6

    def test_get_status_not_found(self):
        """Test getting status for non-existent execution."""
        orchestrator = PipelineOrchestrator()

        with pytest.raises(PipelineExecution.DoesNotExist):
            orchestrator.get_status("00000000-0000-0000-0000-000000000000")

    def test_get_status_completed(self, test_execution_completed):
        """Test getting status for completed execution."""
        orchestrator = PipelineOrchestrator()

        status = orchestrator.get_status(str(test_execution_completed.document_id))

        assert status["status"] == "completed"
        assert status["total_duration_ms"] == 5000

    def test_get_status_failed(self, test_execution_failed):
        """Test getting status for failed execution."""
        orchestrator = PipelineOrchestrator()

        status = orchestrator.get_status(str(test_execution_failed.document_id))

        assert status["status"] == "failed"
        assert status["error_step"] == "embed"
        assert "timeout" in status["error_message"].lower()
