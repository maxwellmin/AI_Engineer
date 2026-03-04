# Manual Test Cases for Document Pipeline Manager

This document provides manual test cases for the Document Pipeline Manager API endpoints.

## Prerequisites

1. **Server running**: `poetry run python manage.py runserver`
2. **Services running**: PostgreSQL, Milvus, Neo4j, MinIO
3. **Authenticated user**: Obtain JWT token first

## Authentication

```bash
# Login to get JWT token
curl -X POST http://localhost:8000/api/v1/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123"
  }'

# Response contains access token
# Set as environment variable
export TOKEN="<your_access_token>"
```

---

## Test Case 1: Health Check

**Purpose**: Verify pipeline service is healthy

### Request

```bash
curl -X GET http://localhost:8000/api/v1/pipeline/health/ \
  -H "Authorization: Bearer $TOKEN"
```

### Expected Response

```json
{
    "status": "healthy",
    "database_connected": true,
    "milvus_connected": true,
    "neo4j_connected": true,
    "active_pipelines": 0
}
```

### Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 401 | Unauthorized |

---

## Test Case 2: Execute Pipeline

**Purpose**: Execute full pipeline for a document

### Prerequisites

- Document must exist in the system
- Document status should be `uploaded`

### Request

```bash
# First, upload a document (if not already done)
curl -X POST http://localhost:8000/api/v1/documents/upload/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/test.pdf"

# Note the document_id from response

# Execute pipeline
curl -X POST http://localhost:8000/api/v1/pipeline/execute/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "<document_uuid>"
  }'
```

### Expected Response (Success)

```json
{
    "document_id": "12345678-1234-5678-1234-567812345678",
    "status": "completed",
    "current_step": "extract",
    "started_at": "2026-03-05T10:00:00Z",
    "completed_at": "2026-03-05T10:00:05Z",
    "total_duration_ms": 5000,
    "steps": [
        {
            "step_name": "parse",
            "step_order": 1,
            "status": "completed",
            "duration_ms": 1500,
            "error_message": "",
            "output_data": {"text_length": 5000, "page_count": 10}
        },
        {
            "step_name": "chunk",
            "step_order": 2,
            "status": "completed",
            "duration_ms": 800,
            "error_message": "",
            "output_data": {"chunk_count": 15}
        },
        {
            "step_name": "embed",
            "step_order": 3,
            "status": "completed",
            "duration_ms": 1200,
            "error_message": "",
            "output_data": {"embedded_count": 15}
        },
        {
            "step_name": "vectorize",
            "step_order": 4,
            "status": "completed",
            "duration_ms": 500,
            "error_message": "",
            "output_data": {"vectorized_count": 15}
        },
        {
            "step_name": "graph",
            "step_order": 5,
            "status": "completed",
            "duration_ms": 600,
            "error_message": "",
            "output_data": {"chunks_created": 15}
        },
        {
            "step_name": "extract",
            "step_order": 6,
            "status": "completed",
            "duration_ms": 400,
            "error_message": "",
            "output_data": {"entities_extracted": 5}
        }
    ],
    "error_message": "",
    "retry_count": 0
}
```

### Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Invalid request (missing document_id) |
| 401 | Unauthorized |
| 404 | Document not found |
| 500 | Pipeline execution failed |

---

## Test Case 3: Get Pipeline Status

**Purpose**: Check current pipeline status for a document

### Request

```bash
curl -X GET http://localhost:8000/api/v1/pipeline/status/<document_id>/ \
  -H "Authorization: Bearer $TOKEN"
```

### Expected Response (Running)

```json
{
    "document_id": "12345678-1234-5678-1234-567812345678",
    "status": "running",
    "current_step": "embed",
    "started_at": "2026-03-05T10:00:00Z",
    "completed_at": null,
    "total_duration_ms": 0,
    "steps": [
        {
            "step_name": "parse",
            "step_order": 1,
            "status": "completed",
            "duration_ms": 1500,
            "error_message": ""
        },
        {
            "step_name": "chunk",
            "step_order": 2,
            "status": "completed",
            "duration_ms": 800,
            "error_message": ""
        },
        {
            "step_name": "embed",
            "step_order": 3,
            "status": "running",
            "duration_ms": 0,
            "error_message": ""
        }
    ],
    "error_message": "",
    "retry_count": 0
}
```

### Expected Response (Not Found)

```json
{
    "document_id": "12345678-1234-5678-1234-567812345678",
    "status": "not_found",
    "current_step": "",
    "steps": [],
    "error_message": "Pipeline execution not found"
}
```

---

## Test Case 4: Cancel Pipeline

**Purpose**: Cancel a running pipeline

### Prerequisites

- Pipeline must be in `running` status

### Request

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/cancel/<document_id>/ \
  -H "Authorization: Bearer $TOKEN"
```

### Expected Response

```json
{
    "document_id": "12345678-1234-5678-1234-567812345678",
    "status": "cancelled",
    "current_step": "chunk",
    "started_at": "2026-03-05T10:00:00Z",
    "completed_at": "2026-03-05T10:00:02Z",
    "total_duration_ms": 2000,
    "steps": [
        {
            "step_name": "parse",
            "step_order": 1,
            "status": "completed",
            "duration_ms": 1500,
            "error_message": ""
        },
        {
            "step_name": "chunk",
            "step_order": 2,
            "status": "skipped",
            "duration_ms": 0,
            "error_message": ""
        }
    ],
    "error_message": "",
    "retry_count": 0
}
```

### Error Response (Already Completed)

```json
{
    "document_id": "12345678-1234-5678-1234-567812345678",
    "status": "error",
    "current_step": "",
    "error_message": "Cannot cancel pipeline with status: completed"
}
```

---

## Test Case 5: Retry Pipeline

**Purpose**: Retry a failed pipeline

### Prerequisites

- Pipeline must be in `failed` status

### Request (Retry from failed Step)

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/retry/<document_id>/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "step_name": "embed"
  }'
```

### Request (Retry Full Pipeline)

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/retry/<document_id>/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Expected Response

```json
{
    "document_id": "12345678-1234-5678-1234-567812345678",
    "status": "completed",
    "current_step": "extract",
    "retry_count": 1,
    "steps": [...]
}
```

---

## Test Case 6: Get Pipeline History

**Purpose**: Get execution history for a document

### Request

```bash
curl -X GET http://localhost:8000/api/v1/pipeline/history/<document_id>/ \
  -H "Authorization: Bearer $TOKEN"
```

### Expected Response

```json
{
    "document_id": "12345678-1234-5678-1234-567812345678",
    "executions": [
        {
            "execution_id": "abc123-def456",
            "status": "completed",
            "started_at": "2026-03-05T10:00:00Z",
            "completed_at": "2026-03-05T10:00:05Z",
            "total_duration_ms": 5000,
            "error_message": "",
            "error_step": "",
            "retry_count": 0,
            "created_at": "2026-03-05T10:00:00Z"
        }
    ],
    "total_count": 1
}
```

---

## Test Case 7: Get Pipeline Summary

**Purpose**: Get a concise summary of pipeline progress

### Request

```bash
curl -X GET http://localhost:8000/api/v1/pipeline/summary/<document_id>/ \
  -H "Authorization: Bearer $TOKEN"
```

### Expected Response

```json
{
    "document_id": "12345678-1234-5678-1234-567812345678",
    "status": "running",
    "current_step": "embed",
    "progress": {
        "completed_steps": 2,
        "total_steps": 6,
        "percentage": 33
    },
    "error": null,
    "timing": {
        "started_at": "2026-03-05T10:00:00Z",
        "completed_at": null,
        "duration_ms": 0
    }
}
```

---

## Test Case 8: List Recent Executions

**Purpose**: List recent pipeline executions

### Request

```bash
# List all recent
curl -X GET http://localhost:8000/api/v1/pipeline/recent/ \
  -H "Authorization: Bearer $TOKEN"

# Filter by status
curl -X GET "http://localhost:8000/api/v1/pipeline/recent/?status=failed" \
  -H "Authorization: Bearer $TOKEN"

# Limit results
curl -X GET "http://localhost:8000/api/v1/pipeline/recent/?limit=5" \
  -H "Authorization: Bearer $TOKEN"
```

### Expected Response

```json
[
    {
        "execution_id": "abc123-def456",
        "document_id": "12345678-1234-5678-1234-567812345678",
        "status": "completed",
        "current_step": "extract",
        "started_at": "2026-03-05T10:00:00Z",
        "completed_at": "2026-03-05T10:00:05Z",
        "total_duration_ms": 5000,
        "error_message": "",
        "created_at": "2026-03-05T10:00:00Z"
    }
]
```

---

## Test Scenarios

### Scenario 1: Full Pipeline Execution

1. Upload a PDF document
2. Execute pipeline
3. Verify status shows all steps completed
4. Verify document status is `done`
5. Verify vectors exist in Milvus
6. Verify nodes exist in Neo4j

### Scenario 2: Pipeline Failure and Retry

1. Upload a document
2. Simulate failure (e.g., stop Milvus)
3. Execute pipeline (should fail at vectorize step)
4. Verify status is `failed`
5. Restart Milvus
6. Retry pipeline from failed step
7. Verify status is `completed`

### Scenario 3: Pipeline Cancellation

1. Upload a large document
2. Execute pipeline
3. While running, send cancel request
4. Verify status is `cancelled`
5. Verify remaining steps are `skipped`

### Scenario 4: Multiple Document Processing

1. Upload 3 different documents
2. Execute pipeline for each
3. List recent executions
4. Verify all 3 executions appear

---

## Error Handling Test Cases

### Invalid Document ID

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/execute/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "invalid-uuid"
  }'

# Expected: 400 Bad Request
```

### Missing Authentication

```bash
curl -X GET http://localhost:8000/api/v1/pipeline/health/

# Expected: 401 Unauthorized
```

### Non-existent Document

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/execute/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "00000000-0000-0000-0000-000000000000"
  }'

# Expected: 404 Not Found or error in response
```

---

## Performance Test Cases

### Large Document Processing

1. Upload a 100-page PDF
2. Execute pipeline
3. Measure total duration
4. Verify no timeout errors

### Concurrent Pipeline Execution

1. Upload 5 documents
2. Execute pipelines concurrently
3. Verify all complete successfully
4. Check database consistency

---

## Test Data

### Sample Documents

| Type | Name | Size | Purpose |
|------|------|------|---------|
| PDF | test_small.pdf | 100KB | Basic pipeline test |
| PDF | test_medium.pdf | 1MB | Performance test |
| TXT | test_text.txt | 10KB | Quick validation |
| DOCX | test_doc.docx | 50KB | Format variety |

### Expected Processing Times

| Document Size | Expected Duration |
|---------------|-------------------|
| < 100KB | 3-5 seconds |
| 100KB - 1MB | 5-15 seconds |
| 1MB - 10MB | 15-60 seconds |

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Pipeline stuck in running | Service crash | Cancel and retry |
| Embedding failure | API timeout | Check embedding service |
| Vectorize failure | Milvus down | Start Milvus service |
| Graph failure | Neo4j down | Start Neo4j service |

### Debug Commands

```bash
# Check database for stuck pipelines
DJANGO_SETTINGS_MODULE=config.settings.local poetry run python -c "
import django
django.setup()
from apps.document_pipeline_manager.models import PipelineExecution
stuck = PipelineExecution.objects.filter(status='running')
for e in stuck:
    print(f'{e.id}: {e.document_id}, started: {e.started_at}')
"

# Reset stuck pipeline
DJANGO_SETTINGS_MODULE=config.settings.local poetry run python -c "
import django
django.setup()
from apps.document_pipeline_manager.models import PipelineExecution
e = PipelineExecution.objects.get(document_id='<uuid>')
e.status = 'failed'
e.error_message = 'Manually reset'
e.save()
"
```

---

## Notes

- All endpoints require authentication
- Pipeline execution is synchronous (blocks until complete)
- Retry mechanism has max retry limit (default: 3)
- Cancellation only works on pending/running pipelines
- Each document has only one active pipeline execution

---

*Generated: 2026-03-05*
*Document Pipeline Manager Manual Tests*
