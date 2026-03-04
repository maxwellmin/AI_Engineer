# Phase 9: Document Pipeline Manager Implementation Plan

## Overview

Implement document pipeline manager module for melon RAG project, providing end-to-end document processing orchestration from upload to knowledge graph construction.

## Status: Ready for Implementation

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Phase 2: Basic Setup | ✅ Completed | Django project structure ready |
| Phase 3: User Management Module | ✅ Completed | Authentication available |
| Phase 4: Document Parser Module | ✅ Completed | Parsing, chunking, deduplication ready |
| Phase 5: Object Storage Controller | ✅ Completed | S3/MinIO storage ready |
| Phase 6: Milvus Database Controller | ✅ Completed | Vector storage ready |
| Phase 7: Neo4j Database Controller | ✅ Completed | Graph storage ready |
| Phase 8: Embedding Engine | ✅ Completed | Text vectorization ready |

---

## Design Decisions (User Confirmed)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **State Storage** | PostgreSQL (Django Model) | Reliable, transactional, queryable, suitable for MVP |
| **Task Execution** | Synchronous (MVP) | Simple implementation, suitable for initial validation |
| **Entity Extraction** | Mock Implementation | Interface ready, placeholder logic, LLM integration in future |
| **Parallel Execution** | Sequential Steps | Simpler error handling, easier debugging, MVP scope |

---

## Pipeline Flow Design

### Complete Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Document Processing Pipeline                         │
└─────────────────────────────────────────────────────────────────────────┘

User Upload
    │
    ▼
┌─────────────────────┐
│  Step 0: Upload     │  ← documents_parser + object_storage_controller
│  (file → storage)   │     - Deduplication check
└──────────┬──────────┘     - Store to S3/Local
           │                - Create Document record (status: uploaded)
           ▼
┌─────────────────────┐
│  Step 1: Parse      │  ← documents_parser.parsers
│  (file → text)      │     - Extract text content
└──────────┬──────────┘     - Extract metadata (title, author, etc.)
           │                - Update Document (status: processing)
           ▼
┌─────────────────────┐
│  Step 2: Chunk      │  ← documents_parser.chunking
│  (text → chunks)    │     - Split into chunks
└──────────┬──────────┘     - Create DocumentChunk records
           │                - Generate content_hash
           ▼
┌─────────────────────┐
│  Step 3: Embed      │  ← embedding_engine
│  (chunks → vectors) │     - Generate summary_dense
└──────────┬──────────┘     - Generate text_dense
           │                - Add vectors to chunks
           ▼
┌─────────────────────┐
│  Step 4: Vectorize  │  ← milvus_database_controller
│  (vectors → Milvus) │     - Insert into Milvus collection
└──────────┬──────────┘     - Store Milvus PK in vector_id
           │
           ▼
┌─────────────────────┐
│  Step 5: Graph      │  ← neo4j_database_controller
│  (doc → Neo4j)      │     - Create Document node
└──────────┬──────────┘     - Create Chunk nodes
           │                - Create CONTAINS relationships
           ▼
┌─────────────────────┐
│  Step 6: Extract    │  ← MockEntityExtractor (Phase 9)
│  (entities → graph) │     - Extract entities (Mock)
└──────────┬──────────┘     - Create Entity nodes
           │                - Create MENTIONS relationships
           ▼
┌─────────────────────┐
│  Finalization       │
│  (mark complete)    │     - Update Document status (done)
└─────────────────────┘     - Create PipelineExecution record
```

### Pipeline State Model

```
Document.Status:
  uploaded → processing → processed → vectorized → graph_built → done
                              ↓
                           failed
                              ↓
                           cancelled
```

---

## Architecture Design

### Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    External API Consumers                    │
│              (curl, Postman, Frontend)                       │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Views Layer                           │
│  - PipelineViews (trigger, status, retry, cancel)           │
│  - DocumentPipelineViews (document-specific operations)     │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 PipelineService (Facade)                     │
│  - execute_pipeline(document_id)                            │
│  - get_pipeline_status(document_id)                         │
│  - retry_failed_step(document_id, step)                     │
│  - cancel_pipeline(document_id)                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┬───────────────┐
          ▼               ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Pipeline    │ │  Pipeline    │ │    Entity    │ │   Pipeline   │
│  Orchestrator│ │  Step Runner │ │  Extractor   │ │   State Mgr  │
│              │ │              │ │   (Mock)     │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
        │                │                │                │
        └────────────────┴────────────────┴────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Modules                          │
│  - documents_parser (parse, chunk)                           │
│  - object_storage_controller (storage)                       │
│  - embedding_engine (embed)                                  │
│  - milvus_database_controller (vectorize)                    │
│  - neo4j_database_controller (graph)                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Submodule Breakdown

### Submodule 9.1: Infrastructure Setup

**Goal**: Establish foundation for pipeline operations

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 1.1 | Create constants.py | Define pipeline steps, status codes, error codes | 1h | Pending |
| 1.2 | Create exceptions.py | Custom exception classes for pipeline errors | 1h | Pending |
| 1.3 | Create dto.py | Dataclasses for requests and responses | 1.5h | Pending |
| 1.4 | Update settings | Add PIPELINE_CONFIG to base.py | 0.5h | Pending |
| 1.5 | Create app structure | Create directory structure for pipeline module | 0.5h | Pending |

**Acceptance Criteria**:
- [ ] All constants defined with Enum pattern (matching Phase 6/7/8)
- [ ] Exception hierarchy matches established pattern
- [ ] DTOs are frozen dataclasses
- [ ] Configuration added to settings
- [ ] Directory structure created

**Files Created**:
- `apps/document_pipeline_manager/__init__.py`
- `apps/document_pipeline_manager/apps.py`
- `apps/document_pipeline_manager/constants.py`
- `apps/document_pipeline_manager/exceptions.py`
- `apps/document_pipeline_manager/dto.py`

**Files Modified**:
- `config/settings/base.py` - Add PIPELINE_CONFIG

---

### Submodule 9.2: Pipeline State Management (Models)

**Goal**: Implement database models for pipeline state tracking

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 2.1 | Design PipelineExecution model | Track overall pipeline execution | 2h | Pending |
| 2.2 | Design PipelineStep model | Track individual step execution | 2h | Pending |
| 2.3 | Extend Document model | Add pipeline-related fields | 1h | Pending |
| 2.4 | Create database migrations | Generate and apply migrations | 1h | Pending |
| 2.5 | Create model managers | Custom query methods for pipeline | 1.5h | Pending |

**Acceptance Criteria**:
- [ ] PipelineExecution model tracks overall status
- [ ] PipelineStep model tracks individual step details
- [ ] Document model extended with pipeline fields
- [ ] Migrations created and tested
- [ ] Model managers provide useful query methods

**Model Design**:

```python
class PipelineExecution(models.Model):
    """Tracks overall pipeline execution for a document."""
    
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name="pipeline_execution"
    )
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    current_step = models.CharField(max_length=50, default="")
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_duration_ms = models.PositiveBigIntegerField(default=0)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    error_step = models.CharField(max_length=50, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PipelineStep(models.Model):
    """Tracks individual step execution details."""
    
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    execution = models.ForeignKey(
        PipelineExecution,
        on_delete=models.CASCADE,
        related_name="steps"
    )
    
    step_name = models.CharField(max_length=50)  # parse, chunk, embed, etc.
    step_order = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveBigIntegerField(default=0)
    
    # Results
    input_data = models.JSONField(default=dict)  # Input summary
    output_data = models.JSONField(default=dict)  # Output summary
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["step_order"]
        indexes = [
            models.Index(fields=["execution", "step_order"]),
        ]
```

**Files Created**:
- `apps/document_pipeline_manager/models.py`
- `apps/document_pipeline_manager/managers.py`

**Files Modified**:
- `apps/documents_parser/models.py` - May extend Document.status if needed

---

### Submodule 9.3: Entity Extraction (Mock Implementation)

**Goal**: Implement mock entity extraction for pipeline integration

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 3.1 | Create base extractor interface | Abstract base class for extractors | 1h | Pending |
| 3.2 | Implement MockEntityExtractor | Deterministic mock extraction | 2h | Pending |
| 3.3 | Implement extraction result models | Dataclasses for extraction results | 1h | Pending |
| 3.4 | Create entity extraction service | Service layer for extraction | 1.5h | Pending |
| 3.5 | Write unit tests | Test mock extractor | 1h | Pending |

**Acceptance Criteria**:
- [ ] BaseExtractor interface defined
- [ ] MockEntityExtractor returns deterministic results
- [ ] Extraction results structured as DTOs
- [ ] Service layer integrates with Neo4j
- [ ] Unit tests cover all scenarios

**Entity Extractor Design**:

```python
# extractors/base.py
from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass

@dataclass(frozen=True)
class ExtractedEntity:
    """Represents an extracted entity."""
    name: str
    entity_type: str  # person, organization, location, etc.
    description: str = ""
    confidence: float = 1.0
    mentions: list[str] = None  # List of chunk IDs mentioning this entity


@dataclass(frozen=True)
class ExtractionResult:
    """Result of entity extraction."""
    entities: list[ExtractedEntity]
    relationships: list[dict[str, Any]]  # Entity relationships
    total_mentions: int


class BaseEntityExtractor(ABC):
    """Abstract base class for entity extractors."""
    
    @abstractmethod
    def extract(self, text: str) -> ExtractionResult:
        """Extract entities from text."""
        ...
    
    @abstractmethod
    def extract_from_chunks(self, chunks: list[dict]) -> ExtractionResult:
        """Extract entities from multiple chunks."""
        ...
```

**Mock Implementation**:

```python
# extractors/mock_extractor.py
import hashlib
from typing import Any
from .base import BaseEntityExtractor, ExtractionResult, ExtractedEntity

class MockEntityExtractor(BaseEntityExtractor):
    """
    Mock entity extractor for development/testing.
    
    Generates deterministic fake entities based on text hash.
    """
    
    def extract(self, text: str) -> ExtractionResult:
        """Generate mock entities from text."""
        # Use hash to generate deterministic results
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # Generate 1-3 mock entities based on hash
        entity_count = (int(text_hash[0], 16) % 3) + 1
        entities = []
        
        for i in range(entity_count):
            entity_hash = hashlib.sha256(f"{text_hash}_{i}".encode()).hexdigest()
            entity_type = ["person", "organization", "location"][i % 3]
            
            entities.append(ExtractedEntity(
                name=f"MockEntity_{entity_hash[:8]}",
                entity_type=entity_type,
                description=f"Mock {entity_type} extracted from text",
                confidence=0.85 + (int(entity_hash[0], 16) % 15) / 100,
                mentions=[]
            ))
        
        return ExtractionResult(
            entities=entities,
            relationships=[],  # No relationships in mock
            total_mentions=entity_count
        )
    
    def extract_from_chunks(self, chunks: list[dict]) -> ExtractionResult:
        """Extract entities from multiple chunks."""
        all_entities = []
        
        for chunk in chunks:
            result = self.extract(chunk.get("text", ""))
            all_entities.extend(result.entities)
        
        # Deduplicate by name
        unique_entities = {e.name: e for e in all_entities}
        
        return ExtractionResult(
            entities=list(unique_entities.values()),
            relationships=[],
            total_mentions=len(all_entities)
        )
```

**Files Created**:
- `apps/document_pipeline_manager/extractors/__init__.py`
- `apps/document_pipeline_manager/extractors/base.py`
- `apps/document_pipeline_manager/extractors/mock_extractor.py`
- `apps/document_pipeline_manager/services/entity_service.py`
- `apps/document_pipeline_manager/tests/test_extractors.py`

---

### Submodule 9.4: Pipeline Step Runners

**Goal**: Implement individual pipeline step execution logic

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 4.1 | Create base step runner | Abstract base class for steps | 1h | Pending |
| 4.2 | Implement UploadStep | Handle file upload and storage | 2h | Pending |
| 4.3 | Implement ParseStep | Parse document to text | 2h | Pending |
| 4.4 | Implement ChunkStep | Split text into chunks | 2h | Pending |
| 4.5 | Implement EmbedStep | Generate embeddings | 2h | Pending |
| 4.6 | Implement VectorizeStep | Store vectors in Milvus | 2h | Pending |
| 4.7 | Implement GraphStep | Create graph nodes | 2h | Pending |
| 4.8 | Implement ExtractStep | Extract and store entities | 2h | Pending |
| 4.9 | Write unit tests | Test each step in isolation | 3h | Pending |

**Acceptance Criteria**:
- [ ] All 7 steps implemented
- [ ] Each step handles errors gracefully
- [ ] Steps log progress and timing
- [ ] Steps can be executed independently
- [ ] Unit tests for each step

**Step Runner Design**:

```python
# runners/base.py
from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass
import time
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StepResult:
    """Result of a pipeline step execution."""
    success: bool
    output_data: dict[str, Any]
    error_message: str = ""
    duration_ms: int = 0


class BaseStepRunner(ABC):
    """Abstract base class for pipeline steps."""
    
    step_name: str = ""
    step_order: int = 0
    
    @abstractmethod
    def execute(self, document_id: str, **kwargs) -> StepResult:
        """
        Execute the pipeline step.
        
        Args:
            document_id: Document UUID
            **kwargs: Additional step parameters
            
        Returns:
            StepResult with execution outcome
        """
        ...
    
    def _measure_time(self) -> tuple[float, float]:
        """Return start time for timing measurement."""
        return time.time()
    
    def _calculate_duration(self, start_time: float) -> int:
        """Calculate duration in milliseconds."""
        return int((time.time() - start_time) * 1000)
    
    def _log_start(self, document_id: str) -> None:
        """Log step start."""
        logger.info(f"Step {self.step_name} started for document {document_id}")
    
    def _log_complete(self, document_id: str, duration_ms: int) -> None:
        """Log step completion."""
        logger.info(
            f"Step {self.step_name} completed for document {document_id} "
            f"in {duration_ms}ms"
        )
```

**Example Step Implementation**:

```python
# runners/parse_step.py
from typing import Any
from django.db import transaction

from .base import BaseStepRunner, StepResult
from apps.documents_parser.models import Document
from apps.documents_parser.services.parsers import get_parser


class ParseStepRunner(BaseStepRunner):
    """Parse document to extract text content."""
    
    step_name = "parse"
    step_order = 1
    
    def execute(self, document_id: str, **kwargs) -> StepResult:
        start_time = self._measure_time()
        self._log_start(document_id)
        
        try:
            document = Document.objects.get(id=document_id)
            
            # Get appropriate parser
            parser = get_parser(document.file_type)
            
            # Parse document
            parsed_result = parser.parse(document.file_path)
            
            # Update document
            with transaction.atomic():
                document.title = parsed_result.get("title", "")
                document.author = parsed_result.get("author", "")
                document.status = Document.Status.PROCESSING
                document.save(update_fields=["title", "author", "status", "updated_at"])
            
            duration_ms = self._calculate_duration(start_time)
            self._log_complete(document_id, duration_ms)
            
            return StepResult(
                success=True,
                output_data={
                    "text_length": len(parsed_result.get("text", "")),
                    "page_count": parsed_result.get("page_count", 0),
                    "title": parsed_result.get("title", ""),
                },
                duration_ms=duration_ms
            )
            
        except Document.DoesNotExist:
            return StepResult(
                success=False,
                output_data={},
                error_message=f"Document {document_id} not found"
            )
        except Exception as e:
            logger.exception(f"Parse step failed for document {document_id}")
            return StepResult(
                success=False,
                output_data={},
                error_message=str(e)
            )
```

**Files Created**:
- `apps/document_pipeline_manager/runners/__init__.py`
- `apps/document_pipeline_manager/runners/base.py`
- `apps/document_pipeline_manager/runners/upload_step.py`
- `apps/document_pipeline_manager/runners/parse_step.py`
- `apps/document_pipeline_manager/runners/chunk_step.py`
- `apps/document_pipeline_manager/runners/embed_step.py`
- `apps/document_pipeline_manager/runners/vectorize_step.py`
- `apps/document_pipeline_manager/runners/graph_step.py`
- `apps/document_pipeline_manager/runners/extract_step.py`
- `apps/document_pipeline_manager/tests/test_runners.py`

---

### Submodule 9.5: Pipeline Orchestrator

**Goal**: Implement pipeline coordination and execution flow

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 5.1 | Create PipelineOrchestrator class | Coordinate step execution | 2h | Pending |
| 5.2 | Implement sequential execution | Execute steps in order | 2h | Pending |
| 5.3 | Implement error handling | Handle step failures | 2h | Pending |
| 5.4 | Implement retry logic | Retry failed steps | 2h | Pending |
| 5.5 | Implement cancellation | Cancel running pipeline | 1.5h | Pending |
| 5.6 | Implement progress tracking | Update execution state | 2h | Pending |
| 5.7 | Write unit tests | Test orchestration logic | 2h | Pending |

**Acceptance Criteria**:
- [ ] Orchestrator executes steps in correct order
- [ ] Failures are handled gracefully
- [ ] Retry mechanism works correctly
- [ ] Cancellation stops pipeline execution
- [ ] Progress is tracked in database

**Orchestrator Design**:

```python
# orchestrator/pipeline_orchestrator.py
from __future__ import annotations

import logging
from typing import Any
from dataclasses import dataclass

from django.db import transaction

from apps.document_pipeline_manager.models import PipelineExecution, PipelineStep
from apps.document_pipeline_manager.runners import (
    ParseStepRunner,
    ChunkStepRunner,
    EmbedStepRunner,
    VectorizeStepRunner,
    GraphStepRunner,
    ExtractStepRunner,
)
from apps.document_pipeline_manager.dto import PipelineConfig

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates document processing pipeline execution.
    
    Manages the sequential execution of pipeline steps,
    handling errors, retries, and state transitions.
    """
    
    def __init__(self, config: PipelineConfig | None = None) -> None:
        """Initialize orchestrator with optional config."""
        self.config = config or PipelineConfig()
        self._init_runners()
    
    def _init_runners(self) -> None:
        """Initialize step runners in execution order."""
        self.runners = [
            ParseStepRunner(),
            ChunkStepRunner(),
            EmbedStepRunner(),
            VectorizeStepRunner(),
            GraphStepRunner(),
            ExtractStepRunner(),
        ]
    
    def execute(self, document_id: str) -> PipelineExecution:
        """
        Execute full pipeline for a document.
        
        Args:
            document_id: Document UUID to process
            
        Returns:
            PipelineExecution with final status
        """
        # Create or get execution record
        execution = self._create_execution(document_id)
        
        try:
            # Update status to running
            execution.status = PipelineExecution.Status.RUNNING
            execution.started_at = timezone.now()
            execution.save(update_fields=["status", "started_at"])
            
            # Execute each step sequentially
            for runner in self.runners:
                # Check for cancellation
                execution.refresh_from_db()
                if execution.status == PipelineExecution.Status.CANCELLED:
                    logger.info(f"Pipeline cancelled for document {document_id}")
                    break
                
                # Execute step
                step_record = self._create_step_record(execution, runner)
                result = runner.execute(document_id)
                
                # Update step record
                self._update_step_record(step_record, result)
                
                if not result.success:
                    # Handle failure
                    self._handle_step_failure(execution, runner.step_name, result)
                    return execution
                
                # Update execution progress
                execution.current_step = runner.step_name
                execution.save(update_fields=["current_step"])
            
            # All steps completed successfully
            self._finalize_execution(execution, success=True)
            
        except Exception as e:
            logger.exception(f"Pipeline failed for document {document_id}")
            self._finalize_execution(execution, success=False, error=str(e))
        
        return execution
    
    def retry_step(
        self, 
        document_id: str, 
        step_name: str,
        max_retries: int = 3
    ) -> PipelineExecution:
        """Retry a failed step."""
        # Implementation details...
        pass
    
    def cancel(self, document_id: str) -> PipelineExecution:
        """Cancel running pipeline."""
        # Implementation details...
        pass
    
    def get_status(self, document_id: str) -> dict[str, Any]:
        """Get current pipeline status."""
        # Implementation details...
        pass
```

**Files Created**:
- `apps/document_pipeline_manager/orchestrator/__init__.py`
- `apps/document_pipeline_manager/orchestrator/pipeline_orchestrator.py`
- `apps/document_pipeline_manager/tests/test_orchestrator.py`

---

### Submodule 9.6: Pipeline Service Layer

**Goal**: Provide unified service interface for pipeline operations

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 6.1 | Create PipelineService class | High-level facade service | 2h | Pending |
| 6.2 | Implement execute_pipeline | Trigger full pipeline | 1.5h | Pending |
| 6.3 | Implement get_pipeline_status | Query pipeline state | 1h | Pending |
| 6.4 | Implement retry_pipeline | Retry failed pipeline | 1.5h | Pending |
| 6.5 | Implement cancel_pipeline | Cancel running pipeline | 1h | Pending |
| 6.6 | Implement get_pipeline_history | Get execution history | 1h | Pending |
| 6.7 | Write integration tests | Test service integration | 2h | Pending |

**Acceptance Criteria**:
- [ ] Service provides clean API for all operations
- [ ] Error handling is consistent
- [ ] Service integrates with orchestrator
- [ ] Integration tests cover all scenarios

**Service Interface**:

```python
# services/pipeline_service.py
from __future__ import annotations

from typing import Any
from dataclasses import asdict

from apps.document_pipeline_manager.models import PipelineExecution, PipelineStep
from apps.document_pipeline_manager.orchestrator import PipelineOrchestrator
from apps.document_pipeline_manager.dto import (
    ExecutePipelineRequest,
    PipelineStatusResponse,
    PipelineHistoryResponse,
)


class PipelineService:
    """
    High-level facade service for document pipeline operations.
    
    Provides a unified interface for pipeline execution, monitoring,
    and management.
    """
    
    def __init__(self) -> None:
        """Initialize service with orchestrator."""
        self.orchestrator = PipelineOrchestrator()
    
    def execute_pipeline(
        self, 
        request: ExecutePipelineRequest
    ) -> PipelineStatusResponse:
        """
        Execute full pipeline for a document.
        
        Args:
            request: ExecutePipelineRequest with document_id
            
        Returns:
            PipelineStatusResponse with execution details
        """
        execution = self.orchestrator.execute(request.document_id)
        return self._build_status_response(execution)
    
    def get_pipeline_status(
        self, 
        document_id: str
    ) -> PipelineStatusResponse:
        """
        Get current pipeline status for a document.
        
        Args:
            document_id: Document UUID
            
        Returns:
            PipelineStatusResponse with current status
        """
        try:
            execution = PipelineExecution.objects.get(document_id=document_id)
            return self._build_status_response(execution)
        except PipelineExecution.DoesNotExist:
            return PipelineStatusResponse(
                document_id=document_id,
                status="not_found",
                current_step="",
                steps=[],
                error_message="Pipeline execution not found"
            )
    
    def retry_pipeline(
        self, 
        document_id: str,
        step_name: str | None = None
    ) -> PipelineStatusResponse:
        """
        Retry failed pipeline.
        
        Args:
            document_id: Document UUID
            step_name: Optional specific step to retry
            
        Returns:
            PipelineStatusResponse with new execution status
        """
        if step_name:
            execution = self.orchestrator.retry_step(document_id, step_name)
        else:
            execution = self.orchestrator.execute(document_id)
        
        return self._build_status_response(execution)
    
    def cancel_pipeline(self, document_id: str) -> PipelineStatusResponse:
        """Cancel running pipeline."""
        execution = self.orchestrator.cancel(document_id)
        return self._build_status_response(execution)
    
    def get_pipeline_history(
        self, 
        document_id: str
    ) -> PipelineHistoryResponse:
        """Get execution history for a document."""
        # Implementation details...
        pass
    
    def _build_status_response(
        self, 
        execution: PipelineExecution
    ) -> PipelineStatusResponse:
        """Build response DTO from execution model."""
        steps = []
        for step in execution.steps.all():
            steps.append({
                "step_name": step.step_name,
                "status": step.status,
                "duration_ms": step.duration_ms,
                "error_message": step.error_message,
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
```

**Files Created**:
- `apps/document_pipeline_manager/services/__init__.py`
- `apps/document_pipeline_manager/services/pipeline_service.py`
- `apps/document_pipeline_manager/tests/test_service.py`

---

### Submodule 9.7: API Views Layer

**Goal**: Expose pipeline functionality through REST API endpoints

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 7.1 | Create serializers | Define request/response serializers | 2h | Pending |
| 7.2 | Implement PipelineViews | Pipeline management endpoints | 3h | Pending |
| 7.3 | Implement DocumentPipelineViews | Document-specific endpoints | 2h | Pending |
| 7.4 | Create URL routing | URL patterns for all endpoints | 1h | Pending |
| 7.5 | Register with main URL config | Include pipeline URLs | 0.5h | Pending |
| 7.6 | Add OpenAPI documentation | Swagger/OpenAPI annotations | 1.5h | Pending |
| 7.7 | Write API tests | Test all endpoints | 3h | Pending |

**Acceptance Criteria**:
- [ ] All endpoints have proper authentication
- [ ] Request validation with DRF serializers
- [ ] Consistent response format
- [ ] OpenAPI documentation complete
- [ ] API tests cover all endpoints

**API Endpoints Design**:

```
/api/v1/pipeline/
├── execute/                           # POST - Execute pipeline for document
├── status/{document_id}/              # GET - Get pipeline status
├── retry/{document_id}/               # POST - Retry failed pipeline
├── cancel/{document_id}/              # POST - Cancel running pipeline
├── history/{document_id}/             # GET - Get execution history
└── health/                            # GET - Health check

/api/v1/documents/{document_id}/pipeline/
├── status/                            # GET - Get pipeline status
├── execute/                           # POST - Execute pipeline
├── retry/                             # POST - Retry pipeline
└── cancel/                            # POST - Cancel pipeline
```

**Endpoint Details**:

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/pipeline/execute/` | Execute pipeline | IsAuthenticated |
| GET | `/api/v1/pipeline/status/{document_id}/` | Get status | IsAuthenticated |
| POST | `/api/v1/pipeline/retry/{document_id}/` | Retry pipeline | IsAuthenticated |
| POST | `/api/v1/pipeline/cancel/{document_id}/` | Cancel pipeline | IsAuthenticated |
| GET | `/api/v1/pipeline/history/{document_id}/` | Get history | IsAuthenticated |
| GET | `/api/v1/pipeline/health/` | Health check | IsAuthenticated |

**Execute Pipeline Request**:
```json
{
    "document_id": "uuid-here"
}
```

**Pipeline Status Response**:
```json
{
    "document_id": "uuid-here",
    "status": "running",
    "current_step": "embed",
    "started_at": "2026-03-05T10:00:00Z",
    "completed_at": null,
    "total_duration_ms": 0,
    "steps": [
        {
            "step_name": "parse",
            "status": "completed",
            "duration_ms": 1500,
            "error_message": ""
        },
        {
            "step_name": "chunk",
            "status": "completed",
            "duration_ms": 800,
            "error_message": ""
        },
        {
            "step_name": "embed",
            "status": "running",
            "duration_ms": 0,
            "error_message": ""
        }
    ],
    "error_message": "",
    "retry_count": 0
}
```

**Files Created**:
- `apps/document_pipeline_manager/serializers.py`
- `apps/document_pipeline_manager/views/__init__.py`
- `apps/document_pipeline_manager/views/pipeline_views.py`
- `apps/document_pipeline_manager/views/document_pipeline_views.py`
- `apps/document_pipeline_manager/urls.py`
- `apps/document_pipeline_manager/tests/test_api_views.py`

**Files Modified**:
- `config/urls.py` - Include pipeline URLs

---

### Submodule 9.8: Testing & Documentation

**Goal**: Comprehensive testing and documentation

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 8.1 | Create test fixtures | Pytest fixtures for pipeline tests | 2h | Pending |
| 8.2 | Write model tests | Test pipeline models | 1.5h | Pending |
| 8.3 | Write orchestrator tests | Test orchestration logic | 2h | Pending |
| 8.4 | Write integration tests | End-to-end pipeline tests | 3h | Pending |
| 8.5 | Verify coverage | Ensure 80%+ coverage | 1h | Pending |
| 8.6 | Create module documentation | README and API docs | 2h | Pending |

**Acceptance Criteria**:
- [ ] Test fixtures created
- [ ] Model tests complete
- [ ] Orchestrator tests complete
- [ ] Integration tests with real services
- [ ] Test coverage >= 80%
- [ ] Documentation complete

**Test Strategy**:

```python
# tests/conftest.py
import pytest
from django.contrib.auth import get_user_model
from apps.documents_parser.models import Document
from apps.document_pipeline_manager.models import PipelineExecution, PipelineStep


@pytest.fixture
def test_user(db):
    """Create test user."""
    User = get_user_model()
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )


@pytest.fixture
def test_document(db, test_user):
    """Create test document."""
    return Document.objects.create(
        user=test_user,
        name="test_document.pdf",
        original_name="Test Document.pdf",
        file_path="documents/test_document.pdf",
        file_size=1024000,
        file_type="pdf",
        file_hash="abc123def456",
        status=Document.Status.UPLOADED
    )


@pytest.fixture
def test_execution(db, test_document):
    """Create test pipeline execution."""
    return PipelineExecution.objects.create(
        document=test_document,
        status=PipelineExecution.Status.PENDING
    )


@pytest.fixture
def mock_file_upload():
    """Mock file upload for testing."""
    from io import BytesIO
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    content = b"Test document content for pipeline processing"
    return SimpleUploadedFile(
        "test.pdf",
        content,
        content_type="application/pdf"
    )
```

**Integration Test Example**:

```python
# tests/test_integration.py
import pytest
from django.contrib.auth import get_user_model

from apps.document_pipeline_manager.services import PipelineService
from apps.document_pipeline_manager.dto import ExecutePipelineRequest


@pytest.mark.django_db
@pytest.mark.integration
class TestPipelineIntegration:
    """Integration tests for full pipeline execution."""
    
    def test_full_pipeline_execution(
        self, 
        test_document,
        mock_file_upload,
        mock_milvus,
        mock_neo4j
    ):
        """Test complete pipeline execution from upload to graph."""
        service = PipelineService()
        
        # Execute pipeline
        request = ExecutePipelineRequest(document_id=str(test_document.id))
        response = service.execute_pipeline(request)
        
        # Verify response
        assert response.status == "completed"
        assert response.current_step == "extract"
        assert len(response.steps) == 6
        
        # Verify all steps completed
        for step in response.steps:
            assert step["status"] == "completed"
        
        # Verify document status updated
        test_document.refresh_from_db()
        assert test_document.status == Document.Status.DONE
```

**Files Created**:
- `apps/document_pipeline_manager/tests/__init__.py`
- `apps/document_pipeline_manager/tests/conftest.py`
- `apps/document_pipeline_manager/tests/test_models.py`
- `apps/document_pipeline_manager/tests/test_orchestrator.py`
- `apps/document_pipeline_manager/tests/test_integration.py`
- `apps/document_pipeline_manager/docs/README.md`

---

### Submodule 9.9: Manual Test Generation

**Goal**: Generate manual test cases for pipeline operations

**Dependencies**: Submodule 9.8 (Testing & Documentation)

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 9.1 | Invoke manual_test_generator agent | Generate manual test cases | 1h | Pending |
| 9.2 | Create manual test document | Create apps/document_pipeline_manager/docs/manual_test.md | 1h | Pending |
| 9.3 | Document test scenarios | Document pipeline execution, retry, cancel scenarios | 1.5h | Pending |

**Acceptance Criteria**:
- [ ] Manual test document created
- [ ] Test cases for all major operations
- [ ] curl commands for API testing
- [ ] Sample data for testing

**Files Created**:
- `apps/document_pipeline_manager/docs/manual_test.md`

---

## File Structure

```
apps/document_pipeline_manager/
├── __init__.py                     # App config
├── apps.py                         # Django AppConfig
├── constants.py                    # Pipeline steps, status codes, error codes
├── exceptions.py                   # Custom exceptions
├── dto.py                          # Data Transfer Objects
├── models.py                       # PipelineExecution, PipelineStep models
├── managers.py                     # Custom model managers
├── serializers.py                  # DRF serializers
├── urls.py                         # URL routing
│
├── extractors/
│   ├── __init__.py
│   ├── base.py                     # BaseEntityExtractor
│   └── mock_extractor.py           # MockEntityExtractor
│
├── runners/
│   ├── __init__.py
│   ├── base.py                     # BaseStepRunner
│   ├── upload_step.py              # Step 0: File upload
│   ├── parse_step.py               # Step 1: Parse document
│   ├── chunk_step.py               # Step 2: Split into chunks
│   ├── embed_step.py               # Step 3: Generate embeddings
│   ├── vectorize_step.py           # Step 4: Store in Milvus
│   ├── graph_step.py               # Step 5: Create graph nodes
│   └── extract_step.py             # Step 6: Extract entities
│
├── orchestrator/
│   ├── __init__.py
│   └── pipeline_orchestrator.py    # Pipeline orchestration
│
├── services/
│   ├── __init__.py
│   ├── pipeline_service.py         # High-level facade service
│   └── entity_service.py           # Entity extraction service
│
├── views/
│   ├── __init__.py
│   ├── pipeline_views.py           # Pipeline management endpoints
│   └── document_pipeline_views.py  # Document-specific endpoints
│
├── docs/
│   ├── README.md                   # Module documentation
│   └── manual_test.md              # Manual test cases (Submodule 9.9)
│
└── tests/
    ├── __init__.py
    ├── conftest.py                 # Pytest fixtures
    ├── test_models.py              # Model tests
    ├── test_extractors.py          # Extractor tests
    ├── test_runners.py             # Step runner tests
    ├── test_orchestrator.py        # Orchestrator tests
    ├── test_service.py             # Service tests
    ├── test_api_views.py           # API tests
    └── test_integration.py         # End-to-end tests
```

---

## Constants Design

```python
# constants.py
from __future__ import annotations

from enum import Enum


# =============================================================================
# Pipeline Steps
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
    
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PARSE_ERROR = "PARSE_ERROR"
    CHUNK_ERROR = "CHUNK_ERROR"
    EMBED_ERROR = "EMBED_ERROR"
    VECTORIZE_ERROR = "VECTORIZE_ERROR"
    GRAPH_ERROR = "GRAPH_ERROR"
    EXTRACTION_ERROR = "EXTRACTION_ERROR"
    PIPELINE_CANCELLED = "PIPELINE_CANCELLED"
    PIPELINE_TIMEOUT = "PIPELINE_TIMEOUT"


# =============================================================================
# Default Configuration
# =============================================================================


DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT_SECONDS = 300  # 5 minutes per step
DEFAULT_BATCH_SIZE = 20  # For embedding batches
```

---

## Exception Design

```python
# exceptions.py
from __future__ import annotations


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


# =============================================================================
# Pipeline Control Exceptions
# =============================================================================


class PipelineCancelledError(PipelineError):
    """Pipeline was cancelled."""
    
    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        message = f"Pipeline cancelled for document '{document_id}'"
        super().__init__(message)


class PipelineTimeoutError(PipelineError):
    """Pipeline execution timed out."""
    
    def __init__(self, document_id: str, timeout_seconds: int) -> None:
        self.document_id = document_id
        self.timeout_seconds = timeout_seconds
        message = f"Pipeline timed out after {timeout_seconds}s for document '{document_id}'"
        super().__init__(message)


class MaxRetriesExceededError(PipelineError):
    """Maximum retries exceeded."""
    
    def __init__(self, step_name: str, max_retries: int) -> None:
        self.step_name = step_name
        self.max_retries = max_retries
        message = f"Max retries ({max_retries}) exceeded for step '{step_name}'"
        super().__init__(message)
```

---

## DTO Design

```python
# dto.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


# =============================================================================
# Request DTOs
# =============================================================================


@dataclass(frozen=True)
class ExecutePipelineRequest:
    """Request to execute pipeline for a document."""
    
    document_id: str


@dataclass(frozen=True)
class RetryPipelineRequest:
    """Request to retry failed pipeline."""
    
    document_id: str
    step_name: Optional[str] = None  # If None, retry entire pipeline


@dataclass(frozen=True)
class CancelPipelineRequest:
    """Request to cancel running pipeline."""
    
    document_id: str


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for pipeline execution."""
    
    max_retries: int = 3
    timeout_seconds: int = 300
    batch_size: int = 20
    enable_entity_extraction: bool = True


# =============================================================================
# Response DTOs
# =============================================================================


@dataclass(frozen=True)
class StepResultDTO:
    """Result of a single pipeline step."""
    
    step_name: str
    status: str
    duration_ms: int
    error_message: str = ""
    output_data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineStatusResponse:
    """Response with pipeline status."""
    
    document_id: str
    status: str
    current_step: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration_ms: int = 0
    steps: list[dict[str, Any]] = field(default_factory=list)
    error_message: str = ""
    retry_count: int = 0


@dataclass(frozen=True)
class PipelineHistoryResponse:
    """Response with pipeline execution history."""
    
    document_id: str
    executions: list[dict[str, Any]] = field(default_factory=list)
    total_count: int = 0


@dataclass(frozen=True)
class PipelineHealthResponse:
    """Response with pipeline health status."""
    
    status: str
    database_connected: bool
    milvus_connected: bool
    neo4j_connected: bool
    active_pipelines: int
```

---

## Test Strategy

### Test Categories

| Category | Marker | Description |
|----------|--------|-------------|
| Unit Tests | `@pytest.mark.unit` | Mock dependencies, test logic |
| Integration Tests | `@pytest.mark.integration` | Real services (Milvus, Neo4j) |
| E2E Tests | `@pytest.mark.e2e` | Full pipeline execution |

### Test Commands

```bash
# Run all pipeline tests
pytest apps/document_pipeline_manager/tests/ -v

# Run with coverage
pytest apps/document_pipeline_manager/tests/ --cov=apps/document_pipeline_manager --cov-report=term-missing

# Run only unit tests
pytest apps/document_pipeline_manager/tests/ -v -m "not integration and not e2e"

# Run integration tests (requires running Milvus, Neo4j)
pytest apps/document_pipeline_manager/tests/ -v -m integration

# Run E2E tests
pytest apps/document_pipeline_manager/tests/ -v -m e2e

# Run with Django settings
DJANGO_SETTINGS_MODULE=config.settings.local pytest apps/document_pipeline_manager/tests/ -v
```

---

## Integration with Other Modules

### documents_parser Integration

```python
# Reuse existing parsers and chunking
from apps.documents_parser.services.parsers import get_parser
from apps.documents_parser.services.chunking import RecursiveCharacterTextSplitter
```

### object_storage_controller Integration

```python
# Use storage backends for file operations
from apps.object_storage_controller.services import StorageService
```

### milvus_database_controller Integration

```python
# Store vectors in Milvus
from apps.milvus_database_controller.services import MilvusService
from apps.milvus_database_controller.dto import InsertVectorsRequest
```

### neo4j_database_controller Integration

```python
# Create knowledge graph
from apps.neo4j_database_controller.services import Neo4jService
from apps.neo4j_database_controller.dto import (
    CreateNodeRequest,
    CreateRelationshipRequest,
)
```

### embedding_engine Integration

```python
# Generate embeddings
from apps.embedding_engine.services import EmbeddingService
from apps.embedding_engine.dto import EmbedForStorageRequest
```

---

## Acceptance Criteria

### Core Functionality (Submodule 9.1-9.6)
- [ ] All constants use Enum pattern
- [ ] All exceptions inherit from PipelineError
- [ ] All DTOs are frozen dataclasses
- [ ] Pipeline models track execution state
- [ ] All 7 step runners implemented
- [ ] MockEntityExtractor works correctly
- [ ] PipelineOrchestrator executes steps sequentially
- [ ] PipelineService provides clean API
- [ ] Error handling is comprehensive
- [ ] Retry mechanism works correctly
- [ ] Cancellation stops pipeline execution

### API Layer (Submodule 9.7)
- [ ] REST API endpoints for all operations
- [ ] Proper authentication (IsAuthenticated)
- [ ] Request validation with DRF serializers
- [ ] Consistent response format
- [ ] OpenAPI documentation complete
- [ ] API tests with >= 80% coverage

### Testing & Documentation (Submodule 9.8-9.9)
- [ ] Unit tests for all components
- [ ] Integration tests with real services
- [ ] Test coverage >= 80%
- [ ] Module documentation complete
- [ ] Manual test cases documented

---

## Risks & Considerations

| Risk | Mitigation |
|------|------------|
| Synchronous Execution Timeout | Set appropriate timeout, consider async in future |
| Large Document Processing | Chunk processing, progress tracking |
| Entity Extraction Accuracy | Mock implementation, plan for LLM integration |
| Pipeline State Consistency | Use database transactions, atomic updates |
| Error Recovery | Comprehensive error handling, retry mechanism |
| Performance Monitoring | Add timing metrics, log slow steps |

---

## Execution Order

Recommended execution order:

```
Phase 9.1 (Infrastructure)
    │
    ├── 1.1 constants.py
    ├── 1.2 exceptions.py
    ├── 1.3 dto.py
    ├── 1.4 Update settings
    └── 1.5 Create app structure
    │
    ▼
Phase 9.2 (Models)
    │
    ├── 2.1 PipelineExecution model
    ├── 2.2 PipelineStep model
    ├── 2.3 Extend Document model
    ├── 2.4 Create migrations
    └── 2.5 Model managers
    │
    ▼
Phase 9.3 (Entity Extraction)
    │
    ├── 3.1 Base extractor interface
    ├── 3.2 MockEntityExtractor
    ├── 3.3 Extraction result models
    ├── 3.4 Entity extraction service
    └── 3.5 Unit tests
    │
    ▼
Phase 9.4 (Step Runners)
    │
    ├── 4.1 Base step runner
    ├── 4.2 UploadStep
    ├── 4.3 ParseStep
    ├── 4.4 ChunkStep
    ├── 4.5 EmbedStep
    ├── 4.6 VectorizeStep
    ├── 4.7 GraphStep
    ├── 4.8 ExtractStep
    └── 4.9 Unit tests
    │
    ▼
Phase 9.5 (Orchestrator)
    │
    ├── 5.1 PipelineOrchestrator class
    ├── 5.2 Sequential execution
    ├── 5.3 Error handling
    ├── 5.4 Retry logic
    ├── 5.5 Cancellation
    ├── 5.6 Progress tracking
    └── 5.7 Unit tests
    │
    ▼
Phase 9.6 (Service Layer)
    │
    ├── 6.1 PipelineService class
    ├── 6.2 execute_pipeline
    ├── 6.3 get_pipeline_status
    ├── 6.4 retry_pipeline
    ├── 6.5 cancel_pipeline
    ├── 6.6 get_pipeline_history
    └── 6.7 Integration tests
    │
    ▼
Phase 9.7 (API Views)
    │
    ├── 7.1 serializers.py
    ├── 7.2 PipelineViews
    ├── 7.3 DocumentPipelineViews
    ├── 7.4 URL routing
    ├── 7.5 Register URLs
    ├── 7.6 OpenAPI docs
    └── 7.7 API tests
    │
    ▼
Phase 9.8 (Testing & Docs)
    │
    ├── 8.1 Test fixtures
    ├── 8.2 Model tests
    ├── 8.3 Orchestrator tests
    ├── 8.4 Integration tests
    ├── 8.5 Verify coverage
    └── 8.6 Module documentation
    │
    ▼
Phase 9.9 (Manual Tests)
    │
    ├── 9.1 Invoke manual_test_generator agent
    ├── 9.2 Create manual test document
    └── 9.3 Document test scenarios
```

---

## Estimated Timeline

| Submodule | Estimated Hours | Working Days |
|-----------|-----------------|--------------|
| 9.1 Infrastructure Setup | 4.5h | 1 day |
| 9.2 Pipeline State Management | 7.5h | 1-2 days |
| 9.3 Entity Extraction | 6.5h | 1-2 days |
| 9.4 Pipeline Step Runners | 17h | 3-4 days |
| 9.5 Pipeline Orchestrator | 11.5h | 2-3 days |
| 9.6 Pipeline Service Layer | 10h | 2 days |
| 9.7 API Views Layer | 13h | 2-3 days |
| 9.8 Testing & Documentation | 11.5h | 2-3 days |
| 9.9 Manual Test Generation | 3.5h | 1 day |
| **Total** | **85h** | **16-20 days** |

---

## Files to Create/Modify

### New Files

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `apps/document_pipeline_manager/constants.py` | Pipeline constants | 80 |
| `apps/document_pipeline_manager/exceptions.py` | Custom exceptions | 120 |
| `apps/document_pipeline_manager/dto.py` | Data transfer objects | 150 |
| `apps/document_pipeline_manager/models.py` | Pipeline models | 200 |
| `apps/document_pipeline_manager/managers.py` | Model managers | 100 |
| `apps/document_pipeline_manager/serializers.py` | DRF serializers | 150 |
| `apps/document_pipeline_manager/urls.py` | URL routing | 30 |
| `apps/document_pipeline_manager/extractors/base.py` | Base extractor | 50 |
| `apps/document_pipeline_manager/extractors/mock_extractor.py` | Mock implementation | 100 |
| `apps/document_pipeline_manager/runners/base.py` | Base step runner | 80 |
| `apps/document_pipeline_manager/runners/*.py` | 7 step runners | 700 |
| `apps/document_pipeline_manager/orchestrator/pipeline_orchestrator.py` | Orchestration | 250 |
| `apps/document_pipeline_manager/services/pipeline_service.py` | Service facade | 200 |
| `apps/document_pipeline_manager/services/entity_service.py` | Entity service | 100 |
| `apps/document_pipeline_manager/views/pipeline_views.py` | Pipeline endpoints | 150 |
| `apps/document_pipeline_manager/tests/*.py` | All test files | 800 |
| `apps/document_pipeline_manager/docs/README.md` | Documentation | 200 |
| `apps/document_pipeline_manager/docs/manual_test.md` | Manual tests | 150 |

### Modified Files

| File | Changes |
|------|---------|
| `config/settings/base.py` | Add PIPELINE_CONFIG |
| `config/urls.py` | Include pipeline URLs |
| `apps/documents_parser/models.py` | May extend Document.status |

---

## Summary

Phase 9 implements the document pipeline manager as the orchestration layer for the entire document processing workflow:

1. **Architecture Alignment**: Follows the same layer architecture as Phase 6/7/8 (Constants → DTOs → Managers → Service → API)
2. **Code Style Consistency**: Uses Enum for constants, frozen dataclasses for DTOs, exception hierarchy
3. **Integration Ready**: Coordinates all existing modules (documents_parser, object_storage, milvus, neo4j, embedding)
4. **Testing Strategy**: Comprehensive unit, integration, and E2E tests with 80%+ coverage
5. **MVP Focus**: Synchronous execution, mock entity extraction, sequential steps - suitable for initial validation

**Key Features**:
- Complete document processing pipeline from upload to knowledge graph
- Step-by-step execution with detailed tracking
- Comprehensive error handling and retry mechanism
- Pipeline status monitoring and cancellation support
- Ready for future async/Celery integration and LLM-based entity extraction

**Total Estimated Time**: ~85 hours (16-20 working days)

---

*Generated: 2026-03-05*
*Plan for Phase 9: Document Pipeline Manager*
*Aligned with Phase 6/7/8 patterns*
