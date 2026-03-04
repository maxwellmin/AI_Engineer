"""
Custom exceptions for Document Pipeline Manager.

This module defines all custom exception classes used throughout the
document pipeline manager module for proper error handling and propagation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# =============================================================================
# Base Exception
# =============================================================================


class PipelineError(Exception):
    """Base exception for all pipeline-related errors."""

    def __init__(self, message: str = "An error occurred in pipeline operation") -> None:
        self.message = message
        super().__init__(self.message)


# =============================================================================
# Document Exceptions
# =============================================================================


class DocumentNotFoundError(PipelineError):
    """Document not found."""

    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        message = f"Document '{document_id}' not found"
        super().__init__(message)


class DocumentAlreadyProcessedError(PipelineError):
    """Document already processed."""

    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        message = f"Document '{document_id}' has already been processed"
        super().__init__(message)


class FileNotFoundError(PipelineError):
    """File not found for document."""

    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        message = f"File not found for document '{document_id}'"
        super().__init__(message)


# =============================================================================
# Pipeline Execution Exceptions
# =============================================================================


class PipelineExecutionError(PipelineError):
    """Base exception for pipeline execution errors."""

    def __init__(self, document_id: str, message: str) -> None:
        self.document_id = document_id
        super().__init__(message)


class PipelineNotFoundError(PipelineExecutionError):
    """Pipeline execution not found."""

    def __init__(self, document_id: str) -> None:
        message = f"Pipeline execution not found for document '{document_id}'"
        super().__init__(document_id, message)


class PipelineAlreadyRunningError(PipelineExecutionError):
    """Pipeline is already running."""

    def __init__(self, document_id: str) -> None:
        message = f"Pipeline is already running for document '{document_id}'"
        super().__init__(document_id, message)


class PipelineCancelledError(PipelineExecutionError):
    """Pipeline was cancelled."""

    def __init__(self, document_id: str) -> None:
        message = f"Pipeline cancelled for document '{document_id}'"
        super().__init__(document_id, message)


class PipelineTimeoutError(PipelineExecutionError):
    """Pipeline execution timed out."""

    def __init__(self, document_id: str, timeout_seconds: int) -> None:
        self.timeout_seconds = timeout_seconds
        message = f"Pipeline timed out after {timeout_seconds}s for document '{document_id}'"
        super().__init__(document_id, message)


# =============================================================================
# Step Execution Exceptions
# =============================================================================


class StepExecutionError(PipelineError):
    """Error during step execution."""

    def __init__(self, step_name: str, reason: str = "") -> None:
        self.step_name = step_name
        self.reason = reason
        message = f"Step '{step_name}' failed: {reason}" if reason else f"Step '{step_name}' failed"
        super().__init__(message)


class ParseError(StepExecutionError):
    """Error during document parsing."""

    def __init__(self, reason: str = "") -> None:
        super().__init__("parse", reason)


class ChunkError(StepExecutionError):
    """Error during text chunking."""

    def __init__(self, reason: str = "") -> None:
        super().__init__("chunk", reason)


class EmbedError(StepExecutionError):
    """Error during embedding generation."""

    def __init__(self, reason: str = "") -> None:
        super().__init__("embed", reason)


class VectorizeError(StepExecutionError):
    """Error during vector storage."""

    def __init__(self, reason: str = "") -> None:
        super().__init__("vectorize", reason)


class GraphError(StepExecutionError):
    """Error during graph construction."""

    def __init__(self, reason: str = "") -> None:
        super().__init__("graph", reason)


class ExtractionError(StepExecutionError):
    """Error during entity extraction."""

    def __init__(self, reason: str = "") -> None:
        super().__init__("extract", reason)


class InvalidStepError(PipelineError):
    """Invalid step name provided."""

    def __init__(self, step_name: str) -> None:
        self.step_name = step_name
        message = f"Invalid step name: '{step_name}'"
        super().__init__(message)


# =============================================================================
# Retry Exceptions
# =============================================================================


class MaxRetriesExceededError(PipelineError):
    """Maximum retries exceeded."""

    def __init__(self, step_name: str, max_retries: int) -> None:
        self.step_name = step_name
        self.max_retries = max_retries
        message = f"Max retries ({max_retries}) exceeded for step '{step_name}'"
        super().__init__(message)


# =============================================================================
# Service Exceptions
# =============================================================================


class ServiceUnavailableError(PipelineError):
    """External service is unavailable."""

    def __init__(self, service_name: str, reason: str = "") -> None:
        self.service_name = service_name
        self.reason = reason
        reason_info = f": {reason}" if reason else ""
        message = f"Service '{service_name}' is unavailable{reason_info}"
        super().__init__(message)


# =============================================================================
# Configuration Exceptions
# =============================================================================


class ConfigurationError(PipelineError):
    """Invalid configuration."""

    def __init__(self, config_key: str, reason: str = "") -> None:
        self.config_key = config_key
        self.reason = reason
        reason_info = f": {reason}" if reason else ""
        message = f"Invalid configuration for '{config_key}'{reason_info}"
        super().__init__(message)


class MissingConfigurationError(ConfigurationError):
    """Required configuration is missing."""

    def __init__(self, config_key: str) -> None:
        message = f"Required configuration '{config_key}' is missing"
        super().__init__(config_key, message)
