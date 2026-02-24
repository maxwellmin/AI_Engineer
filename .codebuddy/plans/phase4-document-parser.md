# Phase 4: Document Parser Module Implementation Plan

## Overview

Implement document parser module for melon RAG project, including document upload, parsing, storage, metadata management, and deduplication.

## Status: ⏳ Submodule 3 in progress (Submodule 1-2 completed)

## Dependencies

- Phase 2: Basic Setup ✅
- Phase 3: User Management Module ✅

---

## Module Features

1. **Document Upload API**: Support user document upload
2. **Document Parsing**: Support PDF/DOCX/TXT format parsing
3. **Metadata Management**: Store document metadata to PostgreSQL
4. **Document Deduplication**: Document-level deduplication based on file hash
5. **Chunking Strategy**: Split documents into logical chunks

---

## Task Breakdown

### Submodule 1: Data Models & Infrastructure ✅

| # | Task | Description | Status |
|---|------|-------------|--------|
| 1.1 | Add document parsing dependencies | Add pypdf, python-docx, chardet to pyproject.toml | ✅ Done |
| 1.2 | Create Document model | Define document metadata model (id, name, path, size, type, status, hash, user) | ✅ Done |
| 1.3 | Create DocumentChunk model | Define document chunk model (document FK, content, chunk_index, metadata) | ✅ Done |
| 1.4 | Create DocumentStatus enum | Define document status (uploaded, processing, processed, failed, cancelled, done) | ✅ Done |

### Submodule 2: Document Storage Service ✅

| # | Task | Description | Status |
|---|------|-------------|--------|
| 2.1 | Implement file storage service | Encapsulate file upload, storage, deletion logic | ✅ Done |
| 2.2 | Implement Hash calculation service | Calculate file SHA256 for deduplication | ✅ Done |
| 2.3 | Implement deduplication service | Check if file already exists (based on hash + user) | ✅ Done |

### Submodule 3: Document Parsing Service (Current)

| # | Task | Description | Status |
|---|------|-------------|--------|
| 3.1 | Implement PDF parser | Use pypdf to parse PDF documents | ❌ Pending |
| 3.2 | Implement DOCX parser | Use python-docx to parse Word documents | ❌ Pending |
| 3.3 | Implement TXT parser | Parse plain text files with encoding detection | ❌ Pending |
| 3.4 | Implement Chunking service | Split documents into chunks (recursive character splitting) | ❌ Pending |

### Submodule 4: API Endpoints

| # | Task | Description | Status |
|---|------|-------------|--------|
| 4.1 | Create document upload API | POST /api/v1/documents/ | ❌ Pending |
| 4.2 | Create document list API | GET /api/v1/documents/ | ❌ Pending |
| 4.3 | Create document detail API | GET /api/v1/documents/{id}/ | ❌ Pending |
| 4.4 | Create document delete API | DELETE /api/v1/documents/{id}/ | ❌ Pending |

### Submodule 5: Testing & Acceptance

| # | Task | Description | Status |
|---|------|-------------|--------|
| 5.1 | Create test factories | Use factory_boy to create test data | ✅ Done |
| 5.2 | Write model tests | Test Document and DocumentChunk models | ❌ Pending |
| 5.3 | Write service tests | Test parsing, storage, deduplication services | ⚡ Partial |
| 5.4 | Write API tests | Test all API endpoints | ❌ Pending |

---

## Data Model Design

### Document Model

```python
class Document(models.Model):
    """Document metadata model."""

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        DONE = "done", "Done"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents")

    # File information
    name = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.PositiveBigIntegerField()  # bytes
    file_type = models.CharField(max_length=50)  # pdf, docx, txt

    # Deduplication
    file_hash = models.CharField(max_length=64, db_index=True)  # SHA256

    # Status tracking
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)
    error_message = models.TextField(blank=True, default="")

    # Metadata
    title = models.CharField(max_length=500, blank=True, default="")
    description = models.TextField(blank=True, default="")
    author = models.CharField(max_length=255, blank=True, default="")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "documents"
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["file_hash"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "file_hash"], name="unique_user_document_hash")
        ]
```

### DocumentChunk Model

```python
class DocumentChunk(models.Model):
    """Document chunk model for text segmentation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")

    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    content_hash = models.CharField(max_length=64, db_index=True)  # SHA256

    # Chunk metadata
    char_count = models.PositiveIntegerField()
    token_count = models.PositiveIntegerField(default=0)
    page_number = models.PositiveIntegerField(null=True, blank=True)

    # For vector storage reference (populated later)
    vector_id = models.CharField(max_length=100, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "document_chunks"
        indexes = [
            models.Index(fields=["document", "chunk_index"]),
            models.Index(fields=["content_hash"]),
        ]
        ordering = ["chunk_index"]
```

---

## API Design

### Document Upload

```
POST /api/v1/documents/
Content-Type: multipart/form-data

Request:
{
    "file": <binary>,
    "title": "optional title",
    "description": "optional description"
}

Response 201:
{
    "id": "uuid",
    "name": "document.pdf",
    "original_name": "My Document.pdf",
    "file_size": 102400,
    "file_type": "pdf",
    "status": "uploaded",
    "created_at": "2026-02-24T10:00:00Z"
}
```

### Document List

```
GET /api/v1/documents/?status=processed&page=1

Response 200:
{
    "count": 10,
    "next": "url",
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "name": "document.pdf",
            "file_type": "pdf",
            "file_size": 102400,
            "status": "processed",
            "created_at": "2026-02-24T10:00:00Z"
        }
    ]
}
```

### Document Detail

```
GET /api/v1/documents/{id}/

Response 200:
{
    "id": "uuid",
    "name": "document.pdf",
    "original_name": "My Document.pdf",
    "file_size": 102400,
    "file_type": "pdf",
    "status": "processed",
    "title": "Document Title",
    "description": "...",
    "chunks_count": 10,
    "created_at": "2026-02-24T10:00:00Z",
    "updated_at": "2026-02-24T10:30:00Z"
}
```

---

## File Structure

```
apps/documents_parser/
├── __init__.py
├── admin.py
├── apps.py
├── models.py              # Document, DocumentChunk ✅
├── views.py               # API Views (empty)
├── serializers.py         # DRF Serializers (not created)
├── urls.py                # URL routing (not created)
├── services/
│   ├── __init__.py
│   ├── storage.py         # File storage service ✅
│   ├── hash.py            # Hash calculation service ✅
│   ├── deduplication.py   # Deduplication service ✅
│   └── parsers/           # ❌ Not created
│       ├── __init__.py
│       ├── base.py        # Base parser interface
│       ├── pdf.py         # PDF parser
│       ├── docx.py        # DOCX parser
│       └── txt.py         # TXT parser
├── chunking/              # ❌ Not created
│   ├── __init__.py
│   └── text_splitter.py   # Text chunking service
└── tests/
    ├── __init__.py
    ├── conftest.py        # Pytest fixtures ✅
    ├── factories.py       # Factory Boy factories ✅
    ├── test_hash.py       # Hash service tests ✅
    ├── test_storage.py    # Storage service tests ✅
    ├── test_deduplication.py  # Deduplication tests ✅
    ├── test_models.py     # Model tests ❌
    ├── test_parsers.py    # Parser tests ❌
    └── test_chunking.py   # Chunking tests ❌
```

---

## Dependencies

```toml
# pyproject.toml (already installed)
[tool.poetry.dependencies]
pypdf = "^5.0.0"           # PDF parsing ✅
python-docx = "^1.1.0"     # DOCX parsing ✅
chardet = "^5.2.0"         # Encoding detection ✅
langchain-text-splitters = "^1.1.0"  # Text chunking ✅
```

---

## Acceptance Criteria

- [ ] Document upload API available (POST /api/v1/documents/)
- [ ] Support PDF/DOCX/TXT format parsing
- [ ] Metadata correctly stored to PostgreSQL
- [ ] Document deduplication works (same hash not re-uploaded)
- [ ] Chunking results are logically coherent
- [ ] Test coverage >= 80%
- [ ] API documentation accessible

---

## Risks & Considerations

1. **Large file handling**: Consider file size limit, suggest max 50MB
2. **Encoding detection**: TXT files need encoding detection
3. **Concurrent upload**: Consider race condition in deduplication
4. **Storage path**: Use `MEDIA_ROOT/documents/{year}/{month}/{day}/` structure

---

## Execution Order

Recommended execution order:

1. **Submodule 1** (Tasks 1.1-1.4): Complete data models first ✅
2. **Submodule 2** (Tasks 2.1-2.3): Implement storage and deduplication services ✅
3. **Submodule 3** (Tasks 3.1-3.4): Implement parsing and chunking ⏳ Current
4. **Submodule 4** (Tasks 4.1-4.4): Implement API endpoints
5. **Submodule 5** (Tasks 5.1-5.4): Write tests

Validate after each submodule completion before proceeding to the next.
