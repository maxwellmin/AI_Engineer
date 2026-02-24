"""
API views for document parser endpoints.

Provides REST API endpoints for document upload, listing,
detail, and deletion operations.
"""

from __future__ import annotations

import logging

from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents_parser.models import Document
from apps.documents_parser.serializers import (
    DocumentDetailSerializer,
    DocumentListSerializer,
    DocumentUploadSerializer,
)
from apps.documents_parser.services.storage import delete_file
from core.permissions import IsOwner

logger = logging.getLogger(__name__)


class DocumentListCreateView(APIView):
    """
    Document list and create endpoint.

    GET /api/v1/documents/
        - List user's documents with pagination
        - Query params: status, page, page_size

    POST /api/v1/documents/
        - Upload a new document
        - Request (multipart/form-data): file, title, description

    Returns:
        - GET: 200 with paginated document list
        - POST: 201 for new document, 200 for duplicate
        - 400: Validation error
        - 401: Authentication required

    Supported file types: pdf, docx, doc, txt, md
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request) -> Response:
        """List user's documents with optional filtering."""
        from core.pagination import StandardPagination

        queryset = Document.objects.filter(user=request.user)

        # Filter by status if provided
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Order by most recent first
        queryset = queryset.order_by("-created_at")

        # Paginate
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)

        serializer = DocumentListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request) -> Response:
        """Handle document upload."""
        serializer = DocumentUploadSerializer(
            data=request.data,
            context={"request": request},
        )

        if not serializer.is_valid():
            logger.warning(
                f"Document upload validation failed for user {request.user.id}: "
                f"{serializer.errors}"
            )
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        document = serializer.save()

        # Check deduplication result from context
        dup_result = serializer.context.get("deduplication_result")

        if dup_result and dup_result.is_duplicate:
            logger.info(
                f"Duplicate document detected for user {request.user.id}: "
                f"existing doc {dup_result.existing_document_id}"
            )
            return Response(
                {
                    "id": str(document.id),
                    "name": document.name,
                    "original_name": document.original_name,
                    "file_type": document.file_type,
                    "file_size": document.file_size,
                    "status": document.status,
                    "message": "Document already exists",
                    "created_at": document.created_at,
                },
                status=status.HTTP_200_OK,
            )

        logger.info(
            f"Document uploaded successfully: {document.id} "
            f"by user {request.user.id}"
        )

        return Response(
            {
                "id": str(document.id),
                "name": document.name,
                "original_name": document.original_name,
                "file_type": document.file_type,
                "file_size": document.file_size,
                "status": document.status,
                "title": document.title,
                "description": document.description,
                "created_at": document.created_at,
            },
            status=status.HTTP_201_CREATED,
        )


class DocumentDetailView(generics.RetrieveAPIView):
    """
    Document detail endpoint.

    GET /api/v1/documents/{id}/

    Returns:
        - 200: Document details
        - 401: Authentication required
        - 404: Document not found

    Response format:
        {
            "id": "uuid",
            "name": "document.pdf",
            "original_name": "My Document.pdf",
            "file_size": 102400,
            "file_type": "pdf",
            "status": "processed",
            "title": "...",
            "description": "...",
            "author": "...",
            "chunks_count": 10,
            "chunks": [...],
            "error_message": "",
            "created_at": "2026-02-24T10:00:00Z",
            "updated_at": "2026-02-24T10:30:00Z"
        }
    """

    permission_classes = [IsAuthenticated, IsOwner]
    serializer_class = DocumentDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        """
        Get queryset limited to user's own documents.

        Returns:
            QuerySet of Document instances.
        """
        return Document.objects.filter(user=self.request.user).prefetch_related("chunks")


class DocumentDeleteView(generics.DestroyAPIView):
    """
    Document delete endpoint.

    DELETE /api/v1/documents/{id}/delete/

    Returns:
        - 204: Document deleted successfully
        - 401: Authentication required
        - 404: Document not found

    Note: This will also delete associated chunks (cascade delete)
    and the physical file from storage.
    """

    permission_classes = [IsAuthenticated, IsOwner]
    lookup_field = "id"

    def get_queryset(self):
        """
        Get queryset limited to user's own documents.

        Returns:
            QuerySet of Document instances.
        """
        return Document.objects.filter(user=self.request.user)

    def perform_destroy(self, instance: Document) -> None:
        """
        Delete document and associated file.

        Args:
            instance: Document instance to delete.
        """
        # Delete physical file from storage
        file_path = instance.file_path
        try:
            delete_file(file_path=file_path)
            logger.info(f"Deleted file: {file_path}")
        except Exception as e:
            # Log but don't fail - database record is still deleted
            logger.warning(f"Failed to delete file {file_path}: {e}")

        # Delete document record (chunks cascade)
        instance.delete()

        logger.info(
            f"Document deleted: {instance.id} by user {self.request.user.id}"
        )
