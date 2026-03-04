"""
Base Step Runner for Document Pipeline.

This module defines the abstract base class for pipeline step runners,
providing common functionality for timing, logging, and result handling.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from apps.document_pipeline_manager.constants import PipelineStepName, PipelineStepOrder
from apps.document_pipeline_manager.dto import StepResult

logger = logging.getLogger(__name__)


class BaseStepRunner(ABC):
    """
    Abstract base class for pipeline step runners.

    Each step runner handles a specific stage of the document processing pipeline.
    Subclasses must implement the execute method and define step_name and step_order.
    """

    step_name: str = ""
    step_order: int = 0

    @abstractmethod
    def execute(self, document_id: str, **kwargs) -> StepResult:
        """
        Execute the pipeline step.

        Args:
            document_id: UUID of the document to process.
            **kwargs: Additional step-specific parameters.

        Returns:
            StepResult with execution outcome, timing, and output data.
        """
        ...

    def _get_start_time(self) -> float:
        """Get current time for timing measurement."""
        return time.time()

    def _calculate_duration_ms(self, start_time: float) -> int:
        """
        Calculate duration in milliseconds.

        Args:
            start_time: Start time from _get_start_time().

        Returns:
            Duration in milliseconds.
        """
        return int((time.time() - start_time) * 1000)

    def _log_start(self, document_id: str) -> None:
        """
        Log step start.

        Args:
            document_id: Document UUID.
        """
        logger.info(
            f"[Pipeline] Step '{self.step_name}' started for document {document_id}"
        )

    def _log_complete(self, document_id: str, duration_ms: int) -> None:
        """
        Log step completion.

        Args:
            document_id: Document UUID.
            duration_ms: Duration in milliseconds.
        """
        logger.info(
            f"[Pipeline] Step '{self.step_name}' completed for document {document_id} "
            f"in {duration_ms}ms"
        )

    def _log_failure(self, document_id: str, error: str) -> None:
        """
        Log step failure.

        Args:
            document_id: Document UUID.
            error: Error message.
        """
        logger.error(
            f"[Pipeline] Step '{self.step_name}' failed for document {document_id}: {error}"
        )

    def _create_success_result(
        self,
        output_data: dict[str, Any],
        duration_ms: int,
    ) -> StepResult:
        """
        Create a successful step result.

        Args:
            output_data: Output data from the step.
            duration_ms: Duration in milliseconds.

        Returns:
            StepResult with success=True.
        """
        return StepResult(
            success=True,
            output_data=output_data,
            error_message="",
            duration_ms=duration_ms,
        )

    def _create_failure_result(
        self,
        error_message: str,
        duration_ms: int = 0,
    ) -> StepResult:
        """
        Create a failed step result.

        Args:
            error_message: Error message describing the failure.
            duration_ms: Optional duration in milliseconds.

        Returns:
            StepResult with success=False.
        """
        return StepResult(
            success=False,
            output_data={},
            error_message=error_message,
            duration_ms=duration_ms,
        )


def get_all_runners() -> list[type[BaseStepRunner]]:
    """
    Get all step runner classes in execution order.

    Returns:
        List of step runner classes sorted by step_order.
    """
    from apps.document_pipeline_manager.runners.parse_step import ParseStepRunner
    from apps.document_pipeline_manager.runners.chunk_step import ChunkStepRunner
    from apps.document_pipeline_manager.runners.embed_step import EmbedStepRunner
    from apps.document_pipeline_manager.runners.vectorize_step import VectorizeStepRunner
    from apps.document_pipeline_manager.runners.graph_step import GraphStepRunner
    from apps.document_pipeline_manager.runners.extract_step import ExtractStepRunner

    return [
        ParseStepRunner,
        ChunkStepRunner,
        EmbedStepRunner,
        VectorizeStepRunner,
        GraphStepRunner,
        ExtractStepRunner,
    ]
