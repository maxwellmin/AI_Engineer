"""Constants for object storage operations."""

from __future__ import annotations

# File type to MIME type mapping
MIME_TYPES: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "txt": "text/plain",
    "md": "text/markdown",
    "json": "application/json",
    "xml": "application/xml",
    "html": "text/html",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
}

# Default MIME type for unknown files
DEFAULT_MIME_TYPE = "application/octet-stream"

# Allowed file extensions for document upload
ALLOWED_EXTENSIONS = ["pdf", "docx", "doc", "txt", "md"]

# Maximum file size (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024

# Presigned URL default expiry (1 hour)
DEFAULT_PRESIGNED_URL_EXPIRY = 3600

# Storage backend types
STORAGE_BACKEND_LOCAL = "local"
STORAGE_BACKEND_S3 = "s3"
