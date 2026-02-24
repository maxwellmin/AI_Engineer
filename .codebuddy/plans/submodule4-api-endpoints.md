# Phase 4 - Submodule 4: API Endpoints Implementation Plan

## Overview

Implement REST API endpoints for document management, including upload, list, detail, and delete operations.

## Current State

- **Models**: Document and DocumentChunk models complete
- **Services**: Storage, hash, deduplication, parsers, chunking all complete
- **Tests**: Service tests complete, API tests pending
- **Views/Serializers/URLs**: Not created yet

---

## Configuration

| Setting | Value | Source |
|---------|-------|--------|
| Max file size | Configurable | Environment variable `DOCUMENT_MAX_SIZE_MB` (default: 50MB) |
| Supported formats | pdf, docx, doc, txt, md | `ParserFactory.get_supported_types()` |
| Duplicate handling | Return existing | HTTP 200 with existing document info |

---

## Key Design Decisions

1. **Duplicate Upload Handling**: Return existing document with HTTP 200 and a `message` field indicating "Document already exists". No new record created.

2. **File Size Limit**: Configured via `DOCUMENT_MAX_SIZE_MB` environment variable. Default 50MB if not set.

3. **View Architecture**: Use DRF generic views for standard CRUD operations. Use APIView for upload with custom flow.

---

## Implementation Tasks

### Task 1: Create Serializers

**File**: `apps/documents_parser/serializers.py`

Create 4 serializers:

1. **DocumentUploadSerializer** (Write)
   - Fields: `file` (FileField), `title` (optional), `description` (optional)
   - Validation: file type (via ParserFactory.is_supported), file size (via env var)
   - Method: `create()` - orchestrate upload flow (save file, create Document record)

2. **DocumentListSerializer** (Read)
   - Fields: id, name, file_type, file_size, status, title, created_at
   - Lightweight for list view

3. **DocumentDetailSerializer** (Read)
   - Fields: id, name, original_name, file_size, file_type, status, title, description, author, chunks_count, error_message, created_at, updated_at
   - Full document info

4. **DocumentChunkSerializer** (Read)
   - Fields: id, chunk_index, char_count, token_count, page_number
   - For nested chunk display in detail view

---

### Task 2: Create Views

**File**: `apps/documents_parser/views.py`

#### 2.1 DocumentUploadView (APIView)

```python
class DocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request) -> Response:
        # 1. Validate and save via serializer
        # 2. Return 201 with document data
```

Flow:
1. Validate file via serializer
2. Calculate file hash
3. Check deduplication via `check_duplicate(user, file_hash)`
4. If duplicate: return HTTP 200 with existing document + message
5. If new: save file via `save_file()`, create Document record
6. Return HTTP 201 with new document data

#### 2.2 DocumentListView (ListAPIView)

```python
class DocumentListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentListSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        # Filter by user, optional status filter
```

#### 2.3 DocumentDetailView (RetrieveAPIView)

```python
class DocumentDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsOwner]
    serializer_class = DocumentDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)
```

#### 2.4 DocumentDeleteView (DestroyAPIView)

```python
class DocumentDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, IsOwner]
    lookup_field = "id"

    def perform_destroy(self, instance):
        # 1. Delete file from storage
        # 2. Delete document record (chunks cascade)
```

---

### Task 3: Create URLs

**File**: `apps/documents_parser/urls.py`

```python
app_name = "documents_parser"

urlpatterns = [
    path("", DocumentUploadView.as_view(), name="upload"),
    path("", DocumentListView.as_view(), name="list"),  # Same path, different method
    path("<uuid:id>/", DocumentDetailView.as_view(), name="detail"),
    path("<uuid:id>/", DocumentDeleteView.as_view(), name="delete"),
]
```

**Update**: `config/urls.py`
```python
path("api/v1/documents/", include("apps.documents_parser.urls")),
```

---

### Task 4: Write API Tests

**File**: `apps/documents_parser/tests/test_views.py`

Test cases:

1. **TestDocumentUpload**
   - test_upload_pdf_success
   - test_upload_docx_success
   - test_upload_txt_success
   - test_upload_unsupported_format (422)
   - test_upload_too_large (413)
   - test_upload_duplicate (returns existing)
   - test_upload_unauthenticated (401)

2. **TestDocumentList**
   - test_list_own_documents
   - test_list_with_status_filter
   - test_list_pagination
   - test_list_empty

3. **TestDocumentDetail**
   - test_detail_own_document
   - test_detail_not_found (404)
   - test_detail_other_user_document (404)

4. **TestDocumentDelete**
   - test_delete_own_document
   - test_delete_not_found (404)
   - test_delete_other_user_document (404)

---

## Critical Files to Modify

| File | Action |
|------|--------|
| `apps/documents_parser/serializers.py` | Create |
| `apps/documents_parser/views.py` | Create |
| `apps/documents_parser/urls.py` | Create |
| `config/urls.py` | Modify (include documents urls) |
| `apps/documents_parser/tests/test_views.py` | Create |

---

## API Response Format

### Upload Success (201)
```json
{
    "id": "uuid",
    "name": "document_20260224_abc123.pdf",
    "original_name": "My Document.pdf",
    "file_type": "pdf",
    "file_size": 102400,
    "status": "uploaded",
    "created_at": "2026-02-24T10:00:00Z"
}
```

### Duplicate Upload (200)
```json
{
    "id": "existing-uuid",
    "name": "document_existing.pdf",
    "original_name": "My Document.pdf",
    "status": "uploaded",
    "message": "Document already exists"
}
```

### List Response (200)
```json
{
    "count": 10,
    "next": "http://...?page=2",
    "previous": null,
    "results": [...]
}
```

### Error Response (400/401/404/422)
```json
{
    "detail": "Error message",
    "code": "ERROR_CODE"
}
```

---

## Implementation Order

1. Create `serializers.py` with validation logic
2. Create `views.py` with API endpoints
3. Create `urls.py` and register in main urls
4. Run basic manual test via curl
5. Create `test_views.py` with comprehensive tests
6. Run tests and verify coverage >= 80%

---

## Acceptance Criteria

- [ ] POST /api/v1/documents/ - Upload document (201)
- [ ] GET /api/v1/documents/ - List user documents (200)
- [ ] GET /api/v1/documents/{id}/ - Get document detail (200)
- [ ] DELETE /api/v1/documents/{id}/ - Delete document (204)
- [ ] Duplicate detection works (returns existing document)
- [ ] File validation (type, size) works
- [ ] Authentication required for all endpoints
- [ ] User can only access own documents
- [ ] Test coverage >= 80%
