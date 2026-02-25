"""API serializers for object storage controller."""

from __future__ import annotations

import os

from rest_framework import serializers


class PresignedUploadRequestSerializer(serializers.Serializer):
    """Request serializer for presigned upload URL."""

    file_name = serializers.CharField(max_length=255, help_text="Original file name")
    file_type = serializers.CharField(
        max_length=100,
        required=False,
        default="application/octet-stream",
        help_text="MIME type of the file",
    )
    file_size = serializers.IntegerField(
        min_value=1,
        max_value=100 * 1024 * 1024,  # 100MB max
        help_text="File size in bytes",
    )

    def validate_file_name(self, value: str) -> str:
        """Validate file name and extension."""
        # Get file extension
        ext = value.rsplit(".", 1)[-1].lower() if "." in value else ""

        # Allowed extensions
        allowed_extensions = ["pdf", "docx", "doc", "txt", "md"]
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )

        return value


class PresignedUploadResponseSerializer(serializers.Serializer):
    """Response serializer for presigned upload URL."""

    upload_url = serializers.URLField(help_text="Presigned URL for direct upload")
    file_path = serializers.CharField(help_text="Object key/path for the file")
    expires_in = serializers.IntegerField(help_text="URL expiry time in seconds")


class PresignedDownloadRequestSerializer(serializers.Serializer):
    """Request serializer for presigned download URL."""

    file_path = serializers.CharField(help_text="Object key/path of the file")
    expires_in = serializers.IntegerField(
        min_value=60,
        max_value=86400,  # 24 hours max
        default=3600,
        required=False,
        help_text="URL expiry time in seconds",
    )


class PresignedDownloadResponseSerializer(serializers.Serializer):
    """Response serializer for presigned download URL."""

    download_url = serializers.URLField(help_text="Presigned URL for direct download")
    expires_in = serializers.IntegerField(help_text="URL expiry time in seconds")


class UploadConfirmRequestSerializer(serializers.Serializer):
    """Request serializer for upload confirmation."""

    file_path = serializers.CharField(help_text="Object key/path of the uploaded file")
    file_name = serializers.CharField(max_length=255, help_text="Original file name")
    file_size = serializers.IntegerField(help_text="File size in bytes")
    file_type = serializers.CharField(
        max_length=50,
        required=False,
        default="",
        help_text="File type/extension",
    )
    title = serializers.CharField(
        max_length=500,
        required=False,
        default="",
        help_text="Document title",
    )
    description = serializers.CharField(
        required=False,
        default="",
        help_text="Document description",
    )


class UploadConfirmResponseSerializer(serializers.Serializer):
    """Response serializer for upload confirmation."""

    id = serializers.UUIDField(help_text="Document ID")
    name = serializers.CharField(help_text="Document name")
    file_path = serializers.CharField(help_text="Object key/path of the file")
    file_size = serializers.IntegerField(help_text="File size in bytes")
    file_type = serializers.CharField(help_text="File type/extension")
    status = serializers.CharField(help_text="Document status")
    message = serializers.CharField(required=False, help_text="Success message")
