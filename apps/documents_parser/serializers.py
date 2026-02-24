"""
Serializers for document parser API endpoints.

Provides input/output serialization for document upload, listing,
detail, and deletion operations.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from rest_framework import serializers

from apps.documents_parser.models import Document, DocumentChunk
from apps.documents_parser.services.deduplication import (
    DeduplicationResult,
    check_duplicate,
)
from apps.documents_parser.services.hash import calculate_uploaded_file_hash
from apps.documents_parser.services.parsers.factory import ParserFactory
from apps.documents_parser.services.storage import save_file

logger = logging.getLogger(__name__)


def get_max_file_size() -> int:
    """
    Get maximum file size from configuration.

    Returns:
        Maximum file size in bytes.
    """
    config = getattr(settings, "DOCUMENT_STORAGE_CONFIG", {})
    return config.get("max_file_size", 100 * 1024 * 1024)  # Default 100MB


class DocumentUploadSerializer(serializers.Serializer):
    """
    Serializer for document upload.

    Fields:
        - file: Uploaded file (required)
        - title: Optional document title
        - description: Optional document description

    Validates:
        - File type is supported (pdf, docx, doc, txt, md)
        - File size does not exceed limit
    """

    file = serializers.FileField(required=True, help_text="Document file to upload")
    title = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional document title",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional document description",
    )

    def validate_file(self, value: Any) -> Any:
        """
        Validate uploaded file type and size.

        Args:
            value: Uploaded file instance.

        Returns:
            The validated file.

        Raises:
            ValidationError: If file type is not supported or size exceeds limit.
        """
        # Check file type
        filename = value.name or "unknown"
        file_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if not ParserFactory.is_supported(file_type=file_ext):
            supported = ParserFactory.get_supported_types()
            raise serializers.ValidationError(
                f"Unsupported file type '.{file_ext}'. "
                f"Supported types: {', '.join(supported)}"
            )

        # Check file size
        max_size = get_max_file_size()
        if value.size and value.size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            raise serializers.ValidationError(
                f"File size exceeds maximum allowed size of {max_size_mb:.0f}MB"
            )

        return value

    def create(self, validated_data: dict) -> Document:
        """
        Create a new Document from uploaded file.

        This method orchestrates the upload flow:
        1. Calculate file hash for deduplication
        2. Check if file already exists for user
        3. If duplicate, raise context flag (handled by view)
        4. If new, save file and create Document record

        Args:
            validated_data: Validated data from serializer.

        Returns:
            Created Document instance.

        Raises:
            ValidationError: If file validation fails.
        """
        request = self.context.get("request")
        user = request.user if request else None
        uploaded_file = validated_data["file"]

        # Calculate file hash for deduplication
        file_hash = calculate_uploaded_file_hash(uploaded_file=uploaded_file)

        # Check for duplicates
        dup_result = check_duplicate(user=user, file_hash=file_hash)

        # Store deduplication result in context for view to handle
        self.context["deduplication_result"] = dup_result
        self.context["file_hash"] = file_hash

        if dup_result.is_duplicate:
            # Return existing document (view will handle response)
            return Document.objects.get(id=dup_result.existing_document_id)

        # Save file to storage
        storage_result = save_file(
            uploaded_file=uploaded_file,
            user_id=str(user.id),
        )

        # Create Document record
        document = Document.objects.create(
            user=user,
            name=storage_result.file_path.split("/")[-1],
            original_name=uploaded_file.name or "document",
            file_path=storage_result.file_path,
            file_size=storage_result.file_size,
            file_type=storage_result.file_type,
            file_hash=file_hash,
            title=validated_data.get("title", ""),
            description=validated_data.get("description", ""),
            status=Document.Status.UPLOADED,
        )

        logger.info(
            f"Document uploaded: {document.id} by user {user.id} "
            f"({document.original_name})"
        )

        return document

    def update(self, instance: Document, validated_data: dict) -> Document:
        """
        Update is not supported for document upload.

        Raises:
            NotImplementedError: Always, as update is not supported.
        """
        raise NotImplementedError("Update is not supported for document upload.")


class DocumentListSerializer(serializers.ModelSerializer):
    """
    Serializer for document list output.

    Lightweight serializer for listing documents with essential fields.
    """

    class Meta:
        model = Document
        fields = [
            "id",
            "name",
            "original_name",
            "file_type",
            "file_size",
            "status",
            "title",
            "created_at",
        ]
        read_only_fields = fields


class DocumentChunkSerializer(serializers.ModelSerializer):
    """
    Serializer for document chunk output.

    Displays chunk metadata without full content (for list views).
    """

    class Meta:
        model = DocumentChunk
        fields = [
            "id",
            "chunk_index",
            "char_count",
            "token_count",
            "page_number",
        ]
        read_only_fields = fields


class DocumentDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for document detail output.

    Full document information including chunk count.
    """

    chunks_count = serializers.SerializerMethodField()
    chunks = DocumentChunkSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "name",
            "original_name",
            "file_size",
            "file_type",
            "status",
            "title",
            "description",
            "author",
            "chunks_count",
            "chunks",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_chunks_count(self, obj: Document) -> int:
        """
        Get the number of chunks for this document.

        Args:
            obj: Document instance.

        Returns:
            Number of chunks.
        """
        return obj.chunks.count()


class DocumentUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating document metadata.

    Only allows updating title and description, not the file itself.
    """

    class Meta:
        model = Document
        fields = ["title", "description"]

    def update(self, instance: Document, validated_data: dict) -> Document:
        """
        Update document metadata.

        Args:
            instance: Document instance to update.
            validated_data: Validated data from serializer.

        Returns:
            Updated Document instance.
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        logger.info(f"Document metadata updated: {instance.id}")
        return instance
