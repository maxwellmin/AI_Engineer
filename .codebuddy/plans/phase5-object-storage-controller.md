# Phase 5: Object Storage Controller Implementation Plan

## Overview

Implement object storage controller module for melon RAG project, providing S3-compatible file storage with MinIO for development and AWS S3 for production.

## Status: ⏳ Ready for Implementation

## Dependencies

- Phase 2: Basic Setup ✅
- Phase 3: User Management Module ✅
- Phase 4: Document Parser Module ✅ (integration required)

---

## Design Decisions (Confirmed with Max)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| MinIO Configuration | Reuse existing | Use Milvus MinIO with separate bucket |
| Storage Strategy | Direct S3 upload | Upload directly to S3/MinIO, no local copy |
| Presigned URL API | Required | Enable frontend direct upload/download |

---

## Current State Analysis

### Existing Infrastructure

| Component | Status | Notes |
|-----------|--------|-------|
| MinIO in docker-compose.yml | Configured | Port 9000 (API), 9001 (Console) |
| S3 environment variables | Defined | Not used in settings |
| django-storages | Not installed | Need to add |
| boto3 | Not installed | Need to add |
| storage.py (documents_parser) | Local FS only | Need abstraction layer |

### Current Storage Flow

```
Document Upload → documents_parser/services/storage.py
                → Local File System (MEDIA_ROOT/documents/YYYY/MM/DD/)
```

### Target Storage Flow

```
Document Upload → object_storage_controller/services/s3_client.py
                → MinIO (dev) / AWS S3 (prod)
                → documents_parser uses storage backend abstraction

Frontend Direct Upload (via Presigned URL):
Frontend → Presigned URL API → MinIO/S3
        → Callback API → documents_parser (metadata only)
```

---

## Module Features

1. **S3-Compatible Storage**: Support MinIO (dev) and AWS S3 (prod)
2. **File Upload**: Direct upload to S3, support multipart for large files
3. **File Download**: Download files via presigned URLs
4. **File Deletion**: Delete files from storage
5. **Presigned URLs**: Generate time-limited upload/download URLs for frontend
6. **Bucket Management**: Create and manage storage buckets
7. **Backend Abstraction**: Interface for switching between storage backends

---

## Task Breakdown

### Submodule 1: Infrastructure Setup

| # | Task | Description | Status |
|---|------|-------------|--------|
| 1.1 | Add dependencies | Add django-storages, boto3, moto to pyproject.toml | ⏳ |
| 1.2 | Add S3 settings | Configure S3 settings in base.py and local.py | ⏳ |
| 1.3 | Update environment variables | Add S3_* variables to .env_local.env | ⏳ |
| 1.4 | Create Django app | Create object_storage_controller app structure | ⏳ |
| 1.5 | Create bucket init script | Script to create melon-documents bucket in MinIO | ⏳ |

### Submodule 2: S3 Client Service

| # | Task | Description | Status |
|---|------|-------------|--------|
| 2.1 | Create S3 client wrapper | Encapsulate boto3 client with connection management | ⏳ |
| 2.2 | Implement file upload | Upload file content to S3 | ⏳ |
| 2.3 | Implement file download | Download file content from S3 | ⏳ |
| 2.4 | Implement file deletion | Delete single file from S3 | ⏳ |
| 2.5 | Implement presigned URLs | Generate upload/download presigned URLs | ⏳ |
| 2.6 | Implement bucket operations | Create bucket, check exists, list objects | ⏳ |
| 2.7 | Create custom exceptions | S3-specific exception classes | ⏳ |

### Submodule 3: Storage Backend Abstraction

| # | Task | Description | Status |
|---|------|-------------|--------|
| 3.1 | Define storage interface | Abstract base class for storage backends | ⏳ |
| 3.2 | Implement S3 storage backend | Integrate S3 client service | ⏳ |
| 3.3 | Implement local storage backend | Fallback for local development | ⏳ |
| 3.4 | Create storage factory | Factory for backend selection | ⏳ |

### Submodule 4: API Endpoints

| # | Task | Description | Status |
|---|------|-------------|--------|
| 4.1 | Create presigned upload URL API | POST /api/v1/storage/presigned-upload/ | ⏳ |
| 4.2 | Create presigned download URL API | GET /api/v1/storage/presigned-download/ | ⏳ |
| 4.3 | Create upload confirm API | POST /api/v1/storage/confirm-upload/ | ⏳ |
| 4.4 | Add URL routing | Configure urls.py | ⏳ |

### Submodule 5: Documents Parser Integration

| # | Task | Description | Status |
|---|------|-------------|--------|
| 5.1 | Refactor storage.py | Use storage backend abstraction | ⏳ |
| 5.2 | Update save_file function | Integrate with S3 backend | ⏳ |
| 5.3 | Update delete_file function | Integrate with S3 backend | ⏳ |
| 5.4 | Update tests | Fix documents_parser tests for S3 | ⏳ |

### Submodule 6: Testing & Acceptance

| # | Task | Description | Status |
|---|------|-------------|--------|
| 6.1 | Create test fixtures | Mock S3 client using moto | ⏳ |
| 6.2 | Write S3 client tests | Test upload, download, delete, presigned URLs | ⏳ |
| 6.3 | Write storage backend tests | Test S3 and local backends | ⏳ |
| 6.4 | Write API tests | Test presigned URL endpoints | ⏳ |
| 6.5 | Write integration tests | Test with documents_parser | ⏳ |
| 6.6 | Manual MinIO test | Verify against real MinIO instance | ⏳ |

---

## Architecture Design

### Storage Backend Interface

```python
# apps/object_storage_controller/backends/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO


@dataclass(frozen=True)
class StorageResult:
    """Immutable result of file storage operation."""
    file_path: str        # Object key in storage
    file_size: int
    file_type: str
    etag: str = ""        # S3 ETag for verification


@dataclass(frozen=True)
class PresignedUrlResult:
    """Immutable result of presigned URL generation."""
    url: str
    expires_in: int
    method: str  # 'GET' or 'PUT'


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def save(self, file_path: str, content: BinaryIO, content_type: str = "") -> StorageResult:
        """Save file content to storage."""
        pass

    @abstractmethod
    def read(self, file_path: str) -> bytes:
        """Read file content from storage."""
        pass

    @abstractmethod
    def delete(self, file_path: str) -> bool:
        """Delete file from storage."""
        pass

    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """Check if file exists in storage."""
        pass

    @abstractmethod
    def get_presigned_url(self, file_path: str, expires_in: int = 3600, method: str = "GET") -> PresignedUrlResult:
        """Generate presigned URL for upload/download."""
        pass

    @abstractmethod
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        pass
```

### S3 Client Service

```python
# apps/object_storage_controller/services/s3_client.py
from typing import BinaryIO
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from django.conf import settings


class S3Client:
    """S3-compatible storage client (MinIO/AWS S3)."""

    _instance = None  # Singleton for connection reuse

    def __new__(cls) -> "S3Client":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_client()
        return cls._instance

    def _initialize_client(self) -> None:
        """Initialize boto3 S3 client."""
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL or None,  # None for AWS S3
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION_NAME,
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )
        self._bucket_name = settings.S3_BUCKET_NAME

    def upload_file(
        self,
        file_path: str,
        content: BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file to S3, return ETag."""
        ...

    def download_file(self, file_path: str) -> bytes:
        """Download file content from S3."""
        ...

    def delete_file(self, file_path: str) -> bool:
        """Delete file from S3."""
        ...

    def generate_presigned_url(
        self,
        file_path: str,
        expires_in: int = 3600,
        http_method: str = "GET",
    ) -> str:
        """Generate presigned URL."""
        ...

    def ensure_bucket_exists(self) -> bool:
        """Create bucket if not exists."""
        ...

    def head_object(self, file_path: str) -> dict:
        """Get object metadata without downloading."""
        ...
```

### Storage Factory

```python
# apps/object_storage_controller/services/factory.py
from django.conf import settings

from apps.object_storage_controller.backends.base import StorageBackend
from apps.object_storage_controller.backends.s3 import S3StorageBackend
from apps.object_storage_controller.backends.local import LocalStorageBackend


def get_storage_backend() -> StorageBackend:
    """Get storage backend based on settings."""
    if settings.USE_S3_STORAGE:
        return S3StorageBackend()
    return LocalStorageBackend()
```

---

## Settings Configuration

### base.py Additions

```python
# S3/MinIO Object Storage Configuration
S3_ENDPOINT_URL = env.str("S3_ENDPOINT_URL", default="")  # Empty for AWS S3
S3_ACCESS_KEY_ID = env.str("S3_ACCESS_KEY_ID", default="")
S3_SECRET_ACCESS_KEY = env.str("S3_SECRET_ACCESS_KEY", default="")
S3_REGION_NAME = env.str("S3_REGION_NAME", default="us-east-1")
S3_BUCKET_NAME = env.str("S3_BUCKET_NAME", default="melon-documents")
S3_USE_SSL = env.bool("S3_USE_SSL", default=False)

# Storage backend selection
USE_S3_STORAGE = env.bool("USE_S3_STORAGE", default=False)

# Presigned URL configuration
PRESIGNED_URL_EXPIRY = env.int("PRESIGNED_URL_EXPIRY", default=3600)  # 1 hour

# File upload limits
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
```

### local.py Additions

```python
# Development: Use existing MinIO (shared with Milvus)
USE_S3_STORAGE = True
S3_ENDPOINT_URL = "http://localhost:9000"
S3_ACCESS_KEY_ID = "minioadmin"
S3_SECRET_ACCESS_KEY = "minioadmin"
S3_REGION_NAME = "us-east-1"
S3_BUCKET_NAME = "melon-documents"
S3_USE_SSL = False
```

### production.py Additions

```python
# Production: Use AWS S3
USE_S3_STORAGE = True
S3_USE_SSL = True
# S3_ENDPOINT_URL is empty for AWS S3 (uses default AWS endpoints)
```

---

## API Design

### Presigned Upload URL

```
POST /api/v1/storage/presigned-upload/
Content-Type: application/json

Request:
{
    "file_name": "document.pdf",
    "file_type": "application/pdf",
    "file_size": 102400
}

Response 200:
{
    "upload_url": "https://localhost:9000/melon-documents/documents/uuid.pdf?X-Amz-...",
    "file_path": "documents/2026/02/25/uuid-document.pdf",
    "expires_in": 3600
}
```

### Presigned Download URL

```
GET /api/v1/storage/presigned-download/?file_path=documents/2026/02/25/doc.pdf

Response 200:
{
    "download_url": "https://localhost:9000/melon-documents/documents/...?X-Amz-...",
    "expires_in": 3600
}
```

### Upload Confirmation

```
POST /api/v1/storage/confirm-upload/
Content-Type: application/json

Request:
{
    "file_path": "documents/2026/02/25/uuid-document.pdf",
    "file_name": "My Document.pdf",
    "file_size": 102400,
    "file_type": "pdf"
}

Response 201:
{
    "id": "uuid",
    "name": "My Document.pdf",
    "file_path": "documents/2026/02/25/uuid-document.pdf",
    "file_size": 102400,
    "file_type": "pdf",
    "status": "uploaded"
}
```

---

## File Structure

```
apps/object_storage_controller/
├── __init__.py
├── apps.py
├── urls.py                    # API URL routing
├── views.py                   # API views
├── serializers.py             # DRF serializers
├── backends/
│   ├── __init__.py
│   ├── base.py                # StorageBackend abstract class
│   ├── local.py               # Local file system backend (fallback)
│   └── s3.py                  # S3/MinIO backend
├── services/
│   ├── __init__.py
│   ├── s3_client.py           # Boto3 S3 client wrapper
│   └── factory.py             # Storage backend factory
├── exceptions.py              # Custom exceptions
├── constants.py               # Storage constants
└── tests/
    ├── __init__.py
    ├── conftest.py            # Pytest fixtures (moto mock)
    ├── test_s3_client.py      # S3 client tests
    ├── test_backends.py       # Backend tests
    ├── test_factory.py        # Factory tests
    └── test_views.py          # API tests
```

---

## Integration with Documents Parser

### Refactored storage.py

```python
# apps/documents_parser/services/storage.py
from django.core.files.uploadedfile import UploadedFile

from apps.object_storage_controller.services.factory import get_storage_backend
from apps.object_storage_controller.backends.base import StorageResult


def save_file(*, uploaded_file: UploadedFile, user_id: str) -> StorageResult:
    """Save uploaded file using configured storage backend."""
    backend = get_storage_backend()
    file_path = _generate_file_path(uploaded_file, user_id)

    return backend.save(
        file_path=file_path,
        content=uploaded_file,
        content_type=uploaded_file.content_type or "application/octet-stream",
    )


def delete_file(*, file_path: str) -> bool:
    """Delete file using configured storage backend."""
    backend = get_storage_backend()
    return backend.delete(file_path)


def file_exists(*, file_path: str) -> bool:
    """Check if file exists using configured storage backend."""
    backend = get_storage_backend()
    return backend.exists(file_path)


def _generate_file_path(uploaded_file: UploadedFile, user_id: str) -> str:
    """Generate unique file path with date structure."""
    from datetime import datetime
    import uuid

    ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
    date_path = datetime.now().strftime("%Y/%m/%d")
    unique_name = f"{uuid.uuid4().hex[:8]}-{uploaded_file.name}"

    return f"documents/{date_path}/{unique_name}"
```

---

## Dependencies

```toml
# pyproject.toml additions
[tool.poetry.dependencies]
boto3 = "^1.34"              # AWS SDK for Python (S3 client)

[tool.poetry.group.dev.dependencies]
moto = { version = "^5.0", extras = ["s3"] }  # Mock S3 for tests
```

**Note**: `django-storages` is optional since we implement our own S3 client wrapper.

---

## Environment Variables

```bash
# .env_local.env additions
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_REGION_NAME=us-east-1
S3_BUCKET_NAME=melon-documents
S3_USE_SSL=false
USE_S3_STORAGE=true
PRESIGNED_URL_EXPIRY=3600
```

---

## MinIO Bucket Initialization

### Management Command

```python
# apps/object_storage_controller/management/commands/init_storage_bucket.py
from django.core.management.base import BaseCommand

from apps.object_storage_controller.services.s3_client import S3Client


class Command(BaseCommand):
    help = "Initialize S3 bucket for document storage"

    def handle(self, *args, **options):
        client = S3Client()
        if client.ensure_bucket_exists():
            self.stdout.write(
                self.style.SUCCESS(f"Bucket '{client._bucket_name}' initialized successfully")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"Bucket '{client._bucket_name}' already exists")
            )
```

### Manual Initialization

```bash
# Using MinIO client (mc)
mc alias set melon http://localhost:9000 minioadmin minioadmin
mc mb melon/melon-documents
mc policy set download melon/melon-documents  # Optional: public read
```

---

## Acceptance Criteria

- [ ] MinIO connection established (reusing existing instance)
- [ ] Bucket `melon-documents` created successfully
- [ ] File upload to S3 works
- [ ] File download from S3 works
- [ ] File deletion works
- [ ] Presigned upload URL generation works
- [ ] Presigned download URL generation works
- [ ] Storage backend abstraction allows switching between local/S3
- [ ] documents_parser integration works with new backend
- [ ] All API endpoints functional
- [ ] Test coverage >= 80%

---

## Risks & Considerations

1. **Shared MinIO**: Using same MinIO as Milvus - ensure bucket isolation
2. **Connection Pooling**: boto3 client should be reused (singleton pattern)
3. **Error Handling**: Comprehensive exception handling for S3 errors
4. **Testing**: Use moto for mocking S3 in unit tests
5. **Large Files**: Files >100MB may need multipart upload (future enhancement)
6. **Security**: Presigned URLs should have reasonable expiry times

---

## Execution Order

Recommended execution order:

1. **Submodule 1** (Tasks 1.1-1.5): Infrastructure and dependencies
2. **Submodule 2** (Tasks 2.1-2.7): S3 client service implementation
3. **Submodule 3** (Tasks 3.1-3.4): Storage backend abstraction
4. **Submodule 4** (Tasks 4.1-4.4): API endpoints
5. **Submodule 5** (Tasks 5.1-5.4): Documents parser integration
6. **Submodule 6** (Tasks 6.1-6.6): Testing and acceptance

---

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `apps/object_storage_controller/__init__.py` | App init |
| `apps/object_storage_controller/apps.py` | AppConfig |
| `apps/object_storage_controller/urls.py` | URL routing |
| `apps/object_storage_controller/views.py` | API views |
| `apps/object_storage_controller/serializers.py` | DRF serializers |
| `apps/object_storage_controller/backends/base.py` | Storage interface |
| `apps/object_storage_controller/backends/s3.py` | S3 backend |
| `apps/object_storage_controller/backends/local.py` | Local backend |
| `apps/object_storage_controller/services/s3_client.py` | S3 client |
| `apps/object_storage_controller/services/factory.py` | Factory |
| `apps/object_storage_controller/exceptions.py` | Exceptions |
| `apps/object_storage_controller/constants.py` | Constants |
| `apps/object_storage_controller/tests/conftest.py` | Fixtures |
| `apps/object_storage_controller/tests/test_*.py` | Tests |

### Modified Files

| File | Changes |
|------|---------|
| `pyproject.toml` | Add boto3, moto dependencies |
| `config/settings/base.py` | Add S3 settings |
| `config/settings/local.py` | Enable S3 for development |
| `config/urls.py` | Include object_storage_controller URLs |
| `apps/documents_parser/services/storage.py` | Use storage backend abstraction |
| `.env_local.env` | Add S3 environment variables |

---

*Generated: 2026-02-25*
*Decisions confirmed with Max: Reuse existing MinIO, Direct S3 upload, Presigned URL API required*
