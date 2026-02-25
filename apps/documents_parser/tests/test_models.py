"""
Tests for Document and DocumentChunk models.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.documents_parser.models import Document, DocumentChunk
from apps.documents_parser.tests.factories import (
    DocumentChunkFactory,
    DocumentFactory,
)

User = get_user_model()


@pytest.mark.django_db
class TestDocumentModel:
    """Tests for Document model."""

    def test_document_create(self) -> None:
        """Test creating a document with all fields."""
        user = User.objects.create_user(username="testuser", password="testpass123")
        doc = Document.objects.create(
            user=user,
            name="test_document.pdf",
            original_name="Test Document.pdf",
            file_path="/media/documents/2026/02/24/test_document.pdf",
            file_size=102400,
            file_type="pdf",
            file_hash="a" * 64,
            title="Test Title",
            description="Test description",
            author="Test Author",
        )

        assert doc.id is not None
        assert doc.user == user
        assert doc.name == "test_document.pdf"
        assert doc.original_name == "Test Document.pdf"
        assert doc.file_size == 102400
        assert doc.file_type == "pdf"
        assert doc.file_hash == "a" * 64
        assert doc.status == Document.Status.UPLOADED
        assert doc.title == "Test Title"
        assert doc.description == "Test description"
        assert doc.author == "Test Author"

    def test_document_str_representation(self) -> None:
        """Test __str__ method returns original_name and status."""
        doc = DocumentFactory(
            original_name="My Report.pdf",
            status=Document.Status.PROCESSED,
        )

        assert str(doc) == "My Report.pdf (processed)"

    def test_document_default_status(self) -> None:
        """Test default status is 'uploaded'."""
        doc = DocumentFactory()

        assert doc.status == Document.Status.UPLOADED

    def test_document_status_choices(self) -> None:
        """Test all status choices are valid."""
        status_values = [
            Document.Status.UPLOADED,
            Document.Status.PROCESSING,
            Document.Status.PROCESSED,
            Document.Status.FAILED,
            Document.Status.CANCELLED,
            Document.Status.DONE,
        ]

        for status in status_values:
            doc = DocumentFactory(status=status)
            assert doc.status == status

    def test_document_user_cascade_delete(self) -> None:
        """Test document is deleted when user is deleted."""
        user = User.objects.create_user(username="testuser", password="testpass123")
        doc = DocumentFactory(user=user)
        doc_id = doc.id

        # Verify document exists
        assert Document.objects.filter(id=doc_id).exists()

        # Delete user
        user.delete()

        # Verify document is also deleted
        assert not Document.objects.filter(id=doc_id).exists()

    def test_document_unique_constraint_same_user_same_hash(self) -> None:
        """Test unique_user_document_hash constraint - same user, same hash should fail."""
        user = User.objects.create_user(username="testuser", password="testpass123")
        file_hash = "a" * 64

        # Create first document
        DocumentFactory(user=user, file_hash=file_hash)

        # Attempt to create second document with same user and hash
        with pytest.raises(IntegrityError):
            DocumentFactory(user=user, file_hash=file_hash)

    def test_document_unique_constraint_different_users(self) -> None:
        """Test same hash allowed for different users."""
        user1 = User.objects.create_user(username="user1", password="testpass123")
        user2 = User.objects.create_user(username="user2", password="testpass123")
        file_hash = "a" * 64

        # Create documents with same hash for different users
        doc1 = DocumentFactory(user=user1, file_hash=file_hash)
        doc2 = DocumentFactory(user=user2, file_hash=file_hash)

        # Both should exist
        assert Document.objects.filter(id=doc1.id).exists()
        assert Document.objects.filter(id=doc2.id).exists()

    def test_document_auto_timestamps(self) -> None:
        """Test created_at and updated_at are auto-populated."""
        doc = DocumentFactory()

        assert doc.created_at is not None
        assert doc.updated_at is not None

    def test_document_updated_at_changes_on_save(self) -> None:
        """Test updated_at changes when document is saved."""
        doc = DocumentFactory()
        original_updated_at = doc.updated_at

        # Update a field and save
        doc.title = "Updated Title"
        doc.save()

        assert doc.updated_at > original_updated_at

    def test_document_error_message_default_empty(self) -> None:
        """Test error_message defaults to empty string."""
        doc = DocumentFactory()

        assert doc.error_message == ""

    def test_document_error_message_can_be_set(self) -> None:
        """Test error_message can be set when processing fails."""
        doc = DocumentFactory(
            status=Document.Status.FAILED,
            error_message="Failed to parse PDF: corrupted file",
        )

        assert doc.error_message == "Failed to parse PDF: corrupted file"

    def test_document_factory_creates_valid_instance(self) -> None:
        """Test DocumentFactory creates a valid Document instance."""
        doc = DocumentFactory()

        assert isinstance(doc, Document)
        assert doc.user is not None
        assert doc.name is not None
        assert doc.original_name is not None
        assert doc.file_path is not None
        assert doc.file_size > 0
        assert doc.file_type in ["pdf", "docx", "txt"]
        assert len(doc.file_hash) == 64

    def test_document_storage_backend_default_s3(self) -> None:
        """Test storage_backend defaults to 's3'."""
        doc = DocumentFactory()

        assert doc.storage_backend == "s3"

    def test_document_storage_backend_can_be_local(self) -> None:
        """Test storage_backend can be set to 'local'."""
        doc = DocumentFactory(storage_backend="local")

        assert doc.storage_backend == "local"

    def test_document_storage_metadata_default_empty_dict(self) -> None:
        """Test storage_metadata defaults to empty dict."""
        doc = DocumentFactory()

        assert doc.storage_metadata == {}

    def test_document_storage_metadata_can_store_etag(self) -> None:
        """Test storage_metadata can store S3 ETag."""
        doc = DocumentFactory(
            storage_backend="s3",
            storage_metadata={"etag": "abc123def456", "version_id": "v1"}
        )

        assert doc.storage_metadata["etag"] == "abc123def456"
        assert doc.storage_metadata["version_id"] == "v1"

    def test_document_storage_backend_valid_choices(self) -> None:
        """Test storage_backend accepts valid values."""
        # Test both valid values
        doc_s3 = DocumentFactory(storage_backend="s3")
        doc_local = DocumentFactory(storage_backend="local")

        assert doc_s3.storage_backend == "s3"
        assert doc_local.storage_backend == "local"


@pytest.mark.django_db
class TestDocumentChunkModel:
    """Tests for DocumentChunk model."""

    def test_chunk_create(self) -> None:
        """Test creating a chunk with all fields."""
        doc = DocumentFactory()
        chunk = DocumentChunk.objects.create(
            document=doc,
            chunk_index=0,
            content="This is the first chunk of text.",
            content_hash="b" * 64,
            char_count=32,
            token_count=7,
            page_number=1,
            vector_id="vec_12345",
        )

        assert chunk.id is not None
        assert chunk.document == doc
        assert chunk.chunk_index == 0
        assert chunk.content == "This is the first chunk of text."
        assert chunk.content_hash == "b" * 64
        assert chunk.char_count == 32
        assert chunk.token_count == 7
        assert chunk.page_number == 1
        assert chunk.vector_id == "vec_12345"

    def test_chunk_str_representation(self) -> None:
        """Test __str__ method returns chunk index and document name."""
        doc = DocumentFactory(name="report.pdf")
        chunk = DocumentChunkFactory(document=doc, chunk_index=5)

        assert str(chunk) == "Chunk 5 of report.pdf"

    def test_chunk_document_cascade_delete(self) -> None:
        """Test chunks are deleted when document is deleted."""
        doc = DocumentFactory()
        chunk1 = DocumentChunkFactory(document=doc)
        chunk2 = DocumentChunkFactory(document=doc)
        chunk_ids = [chunk1.id, chunk2.id]

        # Verify chunks exist
        assert DocumentChunk.objects.filter(id__in=chunk_ids).count() == 2

        # Delete document
        doc.delete()

        # Verify chunks are also deleted
        assert DocumentChunk.objects.filter(id__in=chunk_ids).count() == 0

    def test_chunk_default_ordering(self) -> None:
        """Test chunks are ordered by chunk_index."""
        doc = DocumentFactory()
        # Create chunks in non-sequential order
        DocumentChunkFactory(document=doc, chunk_index=2)
        DocumentChunkFactory(document=doc, chunk_index=0)
        DocumentChunkFactory(document=doc, chunk_index=1)

        # Query chunks - should be ordered by chunk_index
        chunks = list(doc.chunks.all())

        assert chunks[0].chunk_index == 0
        assert chunks[1].chunk_index == 1
        assert chunks[2].chunk_index == 2

    def test_chunk_auto_timestamp(self) -> None:
        """Test created_at is auto-populated."""
        chunk = DocumentChunkFactory()

        assert chunk.created_at is not None

    def test_chunk_default_values(self) -> None:
        """Test default values for optional fields."""
        doc = DocumentFactory()
        chunk = DocumentChunk.objects.create(
            document=doc,
            chunk_index=0,
            content="Test content",
            content_hash="c" * 64,
            char_count=12,
        )

        assert chunk.token_count == 0
        assert chunk.page_number is None
        assert chunk.vector_id == ""

    def test_chunk_factory_creates_valid_instance(self) -> None:
        """Test DocumentChunkFactory creates a valid chunk instance."""
        chunk = DocumentChunkFactory()

        assert isinstance(chunk, DocumentChunk)
        assert chunk.document is not None
        assert chunk.chunk_index >= 0
        assert len(chunk.content) > 0
        assert len(chunk.content_hash) == 64
        assert chunk.char_count == len(chunk.content)

    def test_chunk_related_name(self) -> None:
        """Test chunks can be accessed via document.chunks."""
        doc = DocumentFactory()
        chunk1 = DocumentChunkFactory(document=doc)
        chunk2 = DocumentChunkFactory(document=doc)

        assert doc.chunks.count() == 2
        assert chunk1 in doc.chunks.all()
        assert chunk2 in doc.chunks.all()

    def test_chunk_vector_id_default_empty(self) -> None:
        """Test vector_id defaults to empty string."""
        chunk = DocumentChunkFactory()

        assert chunk.vector_id == ""

    def test_chunk_page_number_can_be_null(self) -> None:
        """Test page_number can be null for non-page-based documents."""
        chunk = DocumentChunkFactory(page_number=None)

        assert chunk.page_number is None

    def test_multiple_documents_can_have_same_chunk_index(self) -> None:
        """Test different documents can have chunks with same chunk_index."""
        doc1 = DocumentFactory()
        doc2 = DocumentFactory()

        chunk1 = DocumentChunkFactory(document=doc1, chunk_index=0)
        chunk2 = DocumentChunkFactory(document=doc2, chunk_index=0)

        assert chunk1.chunk_index == chunk2.chunk_index
        assert chunk1.document != chunk2.document
