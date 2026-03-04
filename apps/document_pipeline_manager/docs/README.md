# Document Pipeline Manager

Document Pipeline Manager is a Django module that orchestrates the end-to-end document processing pipeline for the Melon RAG system.

## Overview

This module coordinates all document processing steps from file upload to knowledge graph construction:

1. **Parse** - Extract text content from documents
2. **Chunk** - Split text into manageable chunks
3. **Embed** - Generate vector embeddings for chunks
4. **Vectorize** - Store vectors in Milvus
5. **Graph** - Create knowledge graph nodes in Neo4j
6. **Extract** - Extract entities and relationships (Mock implementation)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    API Views Layer                           │
│  - PipelineExecuteView                                       │
│  - PipelineStatusView                                        │
│  - PipelineRetryView                                         │
│  - PipelineCancelView                                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 PipelineService (Facade)                     │
│  - execute_pipeline(document_id)                            │
│  - get_pipeline_status(document_id)                         │
│  - retry_pipeline(document_id)                              │
│  - cancel_pipeline(document_id)                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 PipelineOrchestrator                         │
│  - Sequential step execution                                │
│  - Error handling and retry                                 │
│  - State management                                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Runners    │ │   Models     │ │  Extractors  │
│  (6 steps)   │ │  (State)     │ │   (Mock)     │
└──────────────┘ └──────────────┘ └──────────────┘
```

## Installation

The module is part of the Melon Django project. Ensure the following dependencies are installed:

- Django REST Framework
- drf-yasg (for API documentation)
- PostgreSQL
- Milvus
- Neo4j

## Configuration

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    'apps.document_pipeline_manager',
]
```

Pipeline configuration in `settings/base.py`:

```python
PIPELINE_CONFIG = {
    "MAX_RETRIES": 3,
    "TIMEOUT_SECONDS": 300,
    "BATCH_SIZE": 20,
    "ENABLE_ENTITY_EXTRACTION": True,
}
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/pipeline/execute/` | Execute pipeline for a document |
| GET | `/api/v1/pipeline/status/{document_id}/` | Get pipeline status |
| POST | `/api/v1/pipeline/retry/{document_id}/` | Retry failed pipeline |
| POST | `/api/v1/pipeline/cancel/{document_id}/` | Cancel running pipeline |
| GET | `/api/v1/pipeline/history/{document_id}/` | Get execution history |
| GET | `/api/v1/pipeline/summary/{document_id}/` | Get pipeline summary |
| GET | `/api/v1/pipeline/health/` | Health check |
| GET | `/api/v1/pipeline/recent/` | List recent executions |

### Execute Pipeline

```bash
curl -X POST /api/v1/pipeline/execute/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "<uuid>"}'
```

Response:
```json
{
    "document_id": "<uuid>",
    "status": "completed",
    "current_step": "extract",
    "started_at": "2026-03-05T10:00:00Z",
    "completed_at": "2026-03-05T10:00:05Z",
    "total_duration_ms": 5000,
    "steps": [
        {"step_name": "parse", "status": "completed", "duration_ms": 1500},
        {"step_name": "chunk", "status": "completed", "duration_ms": 800},
        {"step_name": "embed", "status": "completed", "duration_ms": 1200},
        {"step_name": "vectorize", "status": "completed", "duration_ms": 500},
        {"step_name": "graph", "status": "completed", "duration_ms": 600},
        {"step_name": "extract", "status": "completed", "duration_ms": 400}
    ],
    "error_message": "",
    "retry_count": 0
}
```

### Get Pipeline Status

```bash
curl -X GET /api/v1/pipeline/status/<document_id>/ \
  -H "Authorization: Bearer <token>"
```

## Models

### PipelineExecution

Tracks overall pipeline execution for a document.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| document | FK | OneToOne to Document |
| status | Enum | pending, running, completed, failed, cancelled |
| current_step | String | Currently executing step |
| started_at | DateTime | Execution start time |
| completed_at | DateTime | Execution end time |
| total_duration_ms | Integer | Total duration in milliseconds |
| error_message | Text | Error message if failed |
| error_step | String | Step where error occurred |
| retry_count | Integer | Number of retry attempts |

### PipelineStep

Tracks individual step execution details.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| execution | FK | Foreign key to PipelineExecution |
| step_name | String | Name of the step |
| step_order | Integer | Execution order |
| status | Enum | pending, running, completed, failed, skipped |
| started_at | DateTime | Step start time |
| completed_at | DateTime | Step end time |
| duration_ms | Integer | Duration in milliseconds |
| input_data | JSON | Input summary |
| output_data | JSON | Output summary |
| error_message | Text | Error message if failed |

## Usage Examples

### Python API

```python
from apps.document_pipeline_manager.services import PipelineService
from apps.document_pipeline_manager.dto import ExecutePipelineRequest

# Execute pipeline
service = PipelineService()
result = service.execute_pipeline(
    ExecutePipelineRequest(document_id="abc-123")
)

print(f"Status: {result.status}")
print(f"Duration: {result.total_duration_ms}ms")

# Get status
status = service.get_pipeline_status("abc-123")
print(f"Current step: {status.current_step}")

# Cancel pipeline
service.cancel_pipeline("abc-123")

# Retry failed pipeline
service.retry_pipeline("abc-123", step_name="embed")
```

### Django Shell

```python
from apps.document_pipeline_manager.orchestrator import PipelineOrchestrator

orchestrator = PipelineOrchestrator()
execution = orchestrator.execute("document-uuid")

print(f"Status: {execution.status}")
print(f"Steps: {execution.steps.count()}")
```

## Pipeline Steps

### 1. ParseStep
- **Input**: Document file
- **Output**: Extracted text content
- **External**: `documents_parser.parsers`

### 2. ChunkStep
- **Input**: Text content
- **Output**: DocumentChunk records
- **External**: `documents_parser.chunking`

### 3. EmbedStep
- **Input**: Chunks
- **Output**: Vector embeddings
- **External**: `embedding_engine`

### 4. VectorizeStep
- **Input**: Embeddings
- **Output**: Milvus vector IDs
- **External**: `milvus_database_controller`

### 5. GraphStep
- **Input**: Document and chunks
- **Output**: Neo4j nodes
- **External**: `neo4j_database_controller`

### 6. ExtractStep
- **Input**: Chunks
- **Output**: Entity nodes
- **External**: `MockEntityExtractor` (placeholder for LLM)

## Error Handling

Pipeline errors are tracked at both execution and step levels:

```python
# Check for execution error
if execution.status == "failed":
    print(f"Failed at step: {execution.error_step}")
    print(f"Error: {execution.error_message}")

# Check step-level errors
for step in execution.steps.all():
    if step.status == "failed":
        print(f"Step {step.step_name} failed: {step.error_message}")
```

## Retry Mechanism

Failed pipelines can be retried:

```python
# Retry from failed step
service.retry_pipeline(document_id)

# Retry specific step
service.retry_pipeline(document_id, step_name="embed")
```

## Testing

Run tests:

```bash
# All pipeline tests
pytest apps/document_pipeline_manager/tests/ -v

# With coverage
pytest apps/document_pipeline_manager/tests/ --cov=apps.document_pipeline_manager

# Specific test file
pytest apps/document_pipeline_manager/tests/test_models.py -v
```

## Future Enhancements

1. **Async Execution**: Celery integration for background processing
2. **LLM Integration**: Replace MockEntityExtractor with real NER
3. **Parallel Steps**: Execute independent steps concurrently
4. **Webhook Notifications**: Callback on pipeline completion
5. **Batch Processing**: Process multiple documents in one pipeline

## License

Part of the Melon RAG project.
