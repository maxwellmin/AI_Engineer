"""
Data Transfer Objects (DTOs) for Document Pipeline Manager.

This module defines all dataclasses used for request and response objects
in the document pipeline manager API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# =============================================================================
# Request DTOs
# =============================================================================


@dataclass(frozen=True)
class ExecutePipelineRequest:
    """Request to execute pipeline for a document.

    Attributes:
        document_id: UUID of the document to process.
    """

    document_id: str


@dataclass(frozen=True)
class RetryPipelineRequest:
    """Request to retry failed pipeline.

    Attributes:
        document_id: UUID of the document.
        step_name: Optional specific step to retry. If None, retry entire pipeline.
    """

    document_id: str
    step_name: str | None = None


@dataclass(frozen=True)
class CancelPipelineRequest:
    """Request to cancel running pipeline.

    Attributes:
        document_id: UUID of the document.
    """

    document_id: str


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for pipeline execution.

    Attributes:
        max_retries: Maximum number of retry attempts per step.
        timeout_seconds: Timeout for each step in seconds.
        total_timeout_seconds: Timeout for entire pipeline in seconds.
        batch_size: Batch size for embedding operations.
        enable_entity_extraction: Whether to enable entity extraction step.
    """

    max_retries: int = 3
    timeout_seconds: int = 300
    total_timeout_seconds: int = 1800
    batch_size: int = 20
    enable_entity_extraction: bool = True


# =============================================================================
# Response DTOs
# =============================================================================


@dataclass(frozen=True)
class StepResultDTO:
    """Result of a single pipeline step.

    Attributes:
        step_name: Name of the step.
        status: Status of the step execution.
        duration_ms: Duration in milliseconds.
        error_message: Error message if failed.
        output_data: Output data from the step.
    """

    step_name: str
    status: str
    duration_ms: int
    error_message: str = ""
    output_data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineStatusResponse:
    """Response with pipeline status.

    Attributes:
        document_id: UUID of the document.
        status: Overall pipeline status.
        current_step: Current step being executed.
        started_at: Pipeline start timestamp.
        completed_at: Pipeline completion timestamp.
        total_duration_ms: Total duration in milliseconds.
        steps: List of step results.
        error_message: Error message if failed.
        retry_count: Number of retry attempts.
    """

    document_id: str
    status: str
    current_step: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_duration_ms: int = 0
    steps: list[dict[str, Any]] = field(default_factory=list)
    error_message: str = ""
    retry_count: int = 0


@dataclass(frozen=True)
class PipelineHistoryResponse:
    """Response with pipeline execution history.

    Attributes:
        document_id: UUID of the document.
        executions: List of execution records.
        total_count: Total number of executions.
    """

    document_id: str
    executions: list[dict[str, Any]] = field(default_factory=list)
    total_count: int = 0


@dataclass(frozen=True)
class PipelineHealthResponse:
    """Response with pipeline health status.

    Attributes:
        status: Overall health status.
        database_connected: Whether PostgreSQL is connected.
        milvus_connected: Whether Milvus is connected.
        neo4j_connected: Whether Neo4j is connected.
        active_pipelines: Number of currently running pipelines.
    """

    status: str
    database_connected: bool
    milvus_connected: bool
    neo4j_connected: bool
    active_pipelines: int


# =============================================================================
# Entity Extraction DTOs
# =============================================================================


@dataclass(frozen=True)
class ExtractedEntity:
    """Represents an extracted entity.

    Attributes:
        name: Name of the entity.
        entity_type: Type of the entity (person, organization, etc.).
        description: Optional description of the entity.
        confidence: Confidence score of the extraction.
        mentions: List of chunk IDs mentioning this entity.
    """

    name: str
    entity_type: str
    description: str = ""
    confidence: float = 1.0
    mentions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExtractionResult:
    """Result of entity extraction.

    Attributes:
        entities: List of extracted entities.
        relationships: List of entity relationships.
        total_mentions: Total number of entity mentions.
    """

    entities: list[ExtractedEntity]
    relationships: list[dict[str, Any]] = field(default_factory=list)
    total_mentions: int = 0


# =============================================================================
# Step Runner DTOs
# =============================================================================


@dataclass(frozen=True)
class StepResult:
    """Result of a pipeline step execution.

    Attributes:
        success: Whether the step succeeded.
        output_data: Output data from the step.
        error_message: Error message if failed.
        duration_ms: Duration in milliseconds.
    """

    success: bool
    output_data: dict[str, Any]
    error_message: str = ""
    duration_ms: int = 0


# =============================================================================
# Helper Functions
# =============================================================================


def create_step_result(
    success: bool,
    output_data: dict[str, Any] | None = None,
    error_message: str = "",
    duration_ms: int = 0,
) -> StepResult:
    """Create a StepResult with default values.

    Args:
        success: Whether the step succeeded.
        output_data: Output data from the step.
        error_message: Error message if failed.
        duration_ms: Duration in milliseconds.

    Returns:
        StepResult instance.
    """
    return StepResult(
        success=success,
        output_data=output_data or {},
        error_message=error_message,
        duration_ms=duration_ms,
    )


def create_extracted_entity(
    name: str,
    entity_type: str,
    description: str = "",
    confidence: float = 1.0,
    mentions: list[str] | None = None,
) -> ExtractedEntity:
    """Create an ExtractedEntity with default values.

    Args:
        name: Name of the entity.
        entity_type: Type of the entity.
        description: Optional description.
        confidence: Confidence score.
        mentions: List of chunk IDs.

    Returns:
        ExtractedEntity instance.
    """
    return ExtractedEntity(
        name=name,
        entity_type=entity_type,
        description=description,
        confidence=confidence,
        mentions=mentions or [],
    )
