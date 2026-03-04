"""
Constants for Document Pipeline Manager.

This module defines all constant values used across the document pipeline manager,
including pipeline steps, status codes, error codes, and configuration defaults.
"""

from __future__ import annotations

from enum import Enum


# =============================================================================
# Pipeline Step Names
# =============================================================================


class PipelineStepName(str, Enum):
    """Pipeline step names in execution order."""

    UPLOAD = "upload"
    PARSE = "parse"
    CHUNK = "chunk"
    EMBED = "embed"
    VECTORIZE = "vectorize"
    GRAPH = "graph"
    EXTRACT = "extract"


class PipelineStepOrder:
    """Execution order for pipeline steps."""

    UPLOAD = 0
    PARSE = 1
    CHUNK = 2
    EMBED = 3
    VECTORIZE = 4
    GRAPH = 5
    EXTRACT = 6


# Step name to order mapping
STEP_ORDER_MAP: dict[str, int] = {
    PipelineStepName.UPLOAD.value: PipelineStepOrder.UPLOAD,
    PipelineStepName.PARSE.value: PipelineStepOrder.PARSE,
    PipelineStepName.CHUNK.value: PipelineStepOrder.CHUNK,
    PipelineStepName.EMBED.value: PipelineStepOrder.EMBED,
    PipelineStepName.VECTORIZE.value: PipelineStepOrder.VECTORIZE,
    PipelineStepName.GRAPH.value: PipelineStepOrder.GRAPH,
    PipelineStepName.EXTRACT.value: PipelineStepOrder.EXTRACT,
}


# =============================================================================
# Pipeline Status
# =============================================================================


class PipelineStatus(str, Enum):
    """Pipeline execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Pipeline step status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# =============================================================================
# Error Codes
# =============================================================================


class ErrorCode(str, Enum):
    """Pipeline error codes."""

    # Document errors
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    DOCUMENT_ALREADY_PROCESSED = "DOCUMENT_ALREADY_PROCESSED"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"

    # Step execution errors
    PARSE_ERROR = "PARSE_ERROR"
    CHUNK_ERROR = "CHUNK_ERROR"
    EMBED_ERROR = "EMBED_ERROR"
    VECTORIZE_ERROR = "VECTORIZE_ERROR"
    GRAPH_ERROR = "GRAPH_ERROR"
    EXTRACTION_ERROR = "EXTRACTION_ERROR"

    # Pipeline control errors
    PIPELINE_CANCELLED = "PIPELINE_CANCELLED"
    PIPELINE_TIMEOUT = "PIPELINE_TIMEOUT"
    PIPELINE_NOT_FOUND = "PIPELINE_NOT_FOUND"
    PIPELINE_ALREADY_RUNNING = "PIPELINE_ALREADY_RUNNING"

    # Retry errors
    MAX_RETRIES_EXCEEDED = "MAX_RETRIES_EXCEEDED"


# =============================================================================
# Entity Types (for Entity Extraction)
# =============================================================================


class EntityType(str, Enum):
    """Entity types for knowledge graph construction."""

    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    CONCEPT = "concept"
    EVENT = "event"
    PRODUCT = "product"
    UNKNOWN = "unknown"


# =============================================================================
# Default Configuration Values
# =============================================================================

# Retry settings
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF_FACTOR = 2.0
DEFAULT_MAX_RETRY_BACKOFF = 60.0  # seconds

# Timeout settings
DEFAULT_TIMEOUT_SECONDS = 300  # 5 minutes per step
DEFAULT_TOTAL_TIMEOUT_SECONDS = 1800  # 30 minutes for entire pipeline

# Batch settings
DEFAULT_BATCH_SIZE = 20  # For embedding batches

# Entity extraction settings
DEFAULT_ENTITY_CONFIDENCE_THRESHOLD = 0.7
DEFAULT_MAX_ENTITIES_PER_DOCUMENT = 100

# =============================================================================
# Pipeline Step Configuration
# =============================================================================

# Steps that require external service connections
STEP_EXTERNAL_SERVICES: dict[str, list[str]] = {
    PipelineStepName.EMBED.value: ["embedding_engine"],
    PipelineStepName.VECTORIZE.value: ["milvus"],
    PipelineStepName.GRAPH.value: ["neo4j"],
    PipelineStepName.EXTRACT.value: ["neo4j"],
}

# Steps that modify the document status
STEP_DOCUMENT_STATUS: dict[str, str] = {
    PipelineStepName.UPLOAD.value: "uploaded",
    PipelineStepName.PARSE.value: "processing",
    PipelineStepName.CHUNK.value: "processing",
    PipelineStepName.EMBED.value: "processing",
    PipelineStepName.VECTORIZE.value: "vectorized",
    PipelineStepName.GRAPH.value: "graph_built",
    PipelineStepName.EXTRACT.value: "done",
}


# =============================================================================
# Error Messages
# =============================================================================

ERROR_DOCUMENT_NOT_FOUND = "Document '{document_id}' not found"
ERROR_DOCUMENT_ALREADY_PROCESSED = "Document '{document_id}' has already been processed"
ERROR_FILE_NOT_FOUND = "File not found for document '{document_id}'"
ERROR_PIPELINE_NOT_FOUND = "Pipeline execution not found for document '{document_id}'"
ERROR_PIPELINE_ALREADY_RUNNING = "Pipeline is already running for document '{document_id}'"
ERROR_PIPELINE_CANCELLED = "Pipeline cancelled for document '{document_id}'"
ERROR_PIPELINE_TIMEOUT = "Pipeline timed out after {timeout}s for document '{document_id}'"
ERROR_STEP_FAILED = "Step '{step_name}' failed: {reason}"
ERROR_MAX_RETRIES_EXCEEDED = "Max retries ({max_retries}) exceeded for step '{step_name}'"
ERROR_INVALID_STEP = "Invalid step name: '{step_name}'"
ERROR_SERVICE_UNAVAILABLE = "Service '{service_name}' is unavailable"
