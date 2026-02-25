"""API views for object storage controller."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

from apps.object_storage_controller.backends.base import PresignedUrlResult
from apps.object_storage_controller.exceptions import StorageError
from apps.object_storage_controller.serializers import (
    PresignedDownloadRequestSerializer,
    PresignedDownloadResponseSerializer,
    PresignedUploadRequestSerializer,
    PresignedUploadResponseSerializer,
    UploadConfirmRequestSerializer,
    UploadConfirmResponseSerializer,
)
from apps.object_storage_controller.services.factory import get_storage_backend

logger = logging.getLogger(__name__)


def _generate_file_path(file_name: str, user_id: str) -> str:
    """Generate unique file path with date structure.

    Args:
        file_name: Original file name
        user_id: User ID for organization

    Returns:
        Generated file path like 'documents/2026/02/25/uuid-filename.pdf'
    """
    # Get file extension
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""

    # Generate date path
    date_path = datetime.now().strftime("%Y/%m/%d")

    # Generate unique prefix
    unique_prefix = uuid.uuid4().hex[:8]

    # Build file path
    safe_name = os.path.basename(file_name)
    return f"documents/{date_path}/{unique_prefix}-{safe_name}"


class PresignedUploadView(APIView):
    """Generate presigned URL for file upload."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Generate a presigned URL for direct file upload to S3",
        request_body=PresignedUploadRequestSerializer,
        responses={200: PresignedUploadResponseSerializer},
        tags=["Storage"],
    )
    def post(self, request: Request) -> Response:
        """Generate presigned upload URL.

        Frontend can use this URL to upload file directly to S3.
        After upload, call /confirm-upload/ to register the document.
        """
        serializer = PresignedUploadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_name = serializer.validated_data["file_name"]
        file_type = serializer.validated_data.get("file_type", "application/octet-stream")
        file_size = serializer.validated_data["file_size"]

        # Generate unique file path
        file_path = _generate_file_path(file_name, str(request.user.id))

        # Get storage backend and generate presigned URL
        backend = get_storage_backend()
        result: PresignedUrlResult = backend.get_presigned_url(
            file_path=file_path,
            expires_in=settings.PRESIGNED_URL_EXPIRY,
            method="PUT",
        )

        logger.info(
            f"Generated presigned upload URL for user {request.user.id}: "
            f"'{file_name}' -> '{file_path}'"
        )

        return Response(
            {
                "upload_url": result.url,
                "file_path": file_path,
                "expires_in": result.expires_in,
            },
            status=status.HTTP_200_OK,
        )


class PresignedDownloadView(APIView):
    """Generate presigned URL for file download."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Generate a presigned URL for direct file download from S3",
        query_serializer=PresignedDownloadRequestSerializer,
        responses={200: PresignedDownloadResponseSerializer},
        tags=["Storage"],
    )
    def get(self, request: Request) -> Response:
        """Generate presigned download URL.

        Frontend can use this URL to download file directly from S3.
        """
        serializer = PresignedDownloadRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        file_path = serializer.validated_data["file_path"]
        expires_in = serializer.validated_data.get("expires_in", settings.PRESIGNED_URL_EXPIRY)

        # Get storage backend
        backend = get_storage_backend()

        # Check if file exists
        if not backend.exists(file_path):
            return Response(
                {"error": "File not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Generate presigned URL
        result: PresignedUrlResult = backend.get_presigned_url(
            file_path=file_path,
            expires_in=expires_in,
            method="GET",
        )

        logger.info(
            f"Generated presigned download URL for user {request.user.id}: '{file_path}'"
        )

        return Response(
            {
                "download_url": result.url,
                "expires_in": result.expires_in,
            },
            status=status.HTTP_200_OK,
        )


class UploadConfirmView(APIView):
    """Confirm file upload and create document record."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Confirm file upload and create document record",
        request_body=UploadConfirmRequestSerializer,
        responses={201: UploadConfirmResponseSerializer},
        tags=["Storage"],
    )
    def post(self, request: Request) -> Response:
        """Confirm upload and create document metadata.

        After frontend uploads file using presigned URL, call this endpoint
        to create document metadata in the database.
        """
        serializer = UploadConfirmRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_path = serializer.validated_data["file_path"]
        file_name = serializer.validated_data["file_name"]
        file_size = serializer.validated_data["file_size"]
        file_type = serializer.validated_data.get("file_type", "")
        title = serializer.validated_data.get("title", "")
        description = serializer.validated_data.get("description", "")

        # Get storage backend and verify file exists
        backend = get_storage_backend()

        if not backend.exists(file_path):
            return Response(
                {"error": "Uploaded file not found in storage"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get actual file size from storage
        actual_size = backend.get_file_size(file_path)

        # Verify size matches
        if actual_size != file_size:
            logger.warning(
                f"File size mismatch for '{file_path}': "
                f"reported {file_size}, actual {actual_size}"
            )

        # Import here to avoid circular imports
        from apps.documents_parser.models import Document

        # Create document record
        document = Document.objects.create(
            user=request.user,
            name=file_name,
            original_name=file_name,
            file_path=file_path,
            file_size=actual_size,
            file_type=file_type or file_name.rsplit(".", 1)[-1].lower(),
            status=Document.Status.UPLOADED,
            title=title,
            description=description,
        )

        logger.info(
            f"Confirmed upload for user {request.user.id}: "
            f"'{file_name}' -> Document {document.id}"
        )

        return Response(
            {
                "id": document.id,
                "name": document.name,
                "file_path": document.file_path,
                "file_size": document.file_size,
                "file_type": document.file_type,
                "status": document.status,
                "message": "Document uploaded successfully",
            },
            status=status.HTTP_201_CREATED,
        )
