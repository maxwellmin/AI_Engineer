"""
API views for document parser endpoints.

Provides REST API endpoints for document upload, listing,
detail, deletion, download, and presigned URL operations.

Storage Backend Modes:
    - S3 Mode (USE_S3_STORAGE=true):
        - Presigned URLs are real S3 presigned URLs
        - Frontend can directly download via presigned URL
        - is_presigned=True in response

    - Local Mode (USE_S3_STORAGE=false):
        - Presigned URLs are relative paths (e.g., /media/documents/...)
        - Frontend must use authenticated download API
        - is_presigned=False in response
"""

from __future__ import annotations

import logging

from django.http import FileResponse, HttpResponse
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
from apps.object_storage_controller.services.factory import get_storage_backend
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


class DocumentPresignedUrlView(APIView):
    """
    Document presigned URL endpoint.

    GET /api/v1/documents/{id}/presigned-url/

    Returns presigned URL for document download.

    Response format varies by storage backend:

    S3 Mode (is_presigned=True):
        {
            "url": "https://s3.amazonaws.com/bucket/documents/...?signature=...",
            "expires_in": 3600,
            "method": "GET",
            "backend_type": "s3",
            "is_presigned": true
        }
        Frontend: Use URL directly for download

    Local Mode (is_presigned=False):
        {
            "url": "/media/documents/2026/02/24/report.pdf",
            "expires_in": 0,
            "method": "GET",
            "backend_type": "local",
            "is_presigned": false
        }
        Frontend: Use /api/v1/documents/{id}/download/ for authenticated download
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, id) -> Response:
        """Generate presigned URL for document download."""
        try:
            document = Document.objects.get(id=id, user=request.user)
        except Document.DoesNotExist:
            return Response(
                {"error": "Document not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        backend = get_storage_backend()
        result = backend.get_presigned_url(
            file_path=document.file_path,
            expires_in=3600,
            method="GET",
        )

        logger.info(
            f"Generated presigned URL for document {document.id} "
            f"(backend: {result.backend_type})"
        )

        return Response(
            {
                "url": result.url,
                "expires_in": result.expires_in,
                "method": result.method,
                "backend_type": result.backend_type,
                "is_presigned": result.is_presigned,
            }
        )


class DocumentDownloadView(APIView):
    """
    Document download endpoint for Local storage mode.

    GET /api/v1/documents/{id}/download/

    Downloads document file with authentication. This endpoint is used
    when storage backend is Local (is_presigned=False).

    In S3 mode, frontend should use presigned URLs directly instead.

    Returns:
        - 200: File content as attachment
        - 400: S3 mode - use presigned URL endpoint instead
        - 401: Authentication required
        - 404: Document not found
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, id) -> HttpResponse:
        """Download document file."""
        try:
            document = Document.objects.get(id=id, user=request.user)
        except Document.DoesNotExist:
            return Response(
                {"error": "Document not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        backend = get_storage_backend()

        # S3 mode: redirect to presigned URL endpoint
        if backend.backend_type == "s3":
            logger.warning(
                f"Download endpoint called in S3 mode for document {document.id}. "
                f"Use presigned URL endpoint instead."
            )
            return Response(
                {
                    "error": "Download endpoint is for Local storage mode only. "
                    "Use presigned URL endpoint: GET /api/v1/documents/{id}/presigned-url/",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            content = backend.read(document.file_path)
        except Exception as e:
            logger.error(f"Failed to read file {document.file_path}: {e}")
            return Response(
                {"error": "Failed to read file"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Determine content type
        content_type = "application/octet-stream"
        if document.file_type == "pdf":
            content_type = "application/pdf"
        elif document.file_type in ("docx", "doc"):
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif document.file_type == "txt":
            content_type = "text/plain"
        elif document.file_type == "md":
            content_type = "text/markdown"

        logger.info(
            f"Downloaded document {document.id} by user {request.user.id} "
            f"(backend: {document.storage_backend})"
        )

        response = HttpResponse(
            content,
            content_type=content_type,
        )
        response["Content-Disposition"] = f'attachment; filename="{document.original_name}"'
        response["Content-Length"] = len(content)
        return response
