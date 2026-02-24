from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Document(models.Model):
    """
    Document metadata model.

    Stores information about uploaded documents including file details,
    processing status, and deduplication hash.
    """

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        DONE = "done", "Done"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    # File information
    name = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.PositiveBigIntegerField()  # bytes
    file_type = models.CharField(max_length=50)  # pdf, docx, txt

    # Deduplication
    file_hash = models.CharField(max_length=64, db_index=True)  # SHA256

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED,
    )
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
            models.UniqueConstraint(
                fields=["user", "file_hash"],
                name="unique_user_document_hash",
            )
        ]

    def __str__(self) -> str:
        return f"{self.original_name} ({self.status})"


class DocumentChunk(models.Model):
    """
    Document chunk model for text segmentation.

    Stores individual chunks of text extracted from documents,
    with metadata for vector storage reference.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
    )

    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    content_hash = models.CharField(max_length=64, db_index=True)  # SHA256

    # Chunk metadata
    char_count = models.PositiveIntegerField()
    token_count = models.PositiveIntegerField(default=0)
    page_number = models.PositiveIntegerField(null=True, blank=True)

    # For vector storage reference (populated later by embedding engine)
    vector_id = models.CharField(max_length=100, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "document_chunks"
        indexes = [
            models.Index(fields=["document", "chunk_index"]),
            models.Index(fields=["content_hash"]),
        ]
        ordering = ["chunk_index"]

    def __str__(self) -> str:
        return f"Chunk {self.chunk_index} of {self.document.name}"
