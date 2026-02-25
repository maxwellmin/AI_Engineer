"""URL configuration for object_storage_controller app."""

from __future__ import annotations

from django.urls import path

from apps.object_storage_controller.views import (
    PresignedDownloadView,
    PresignedUploadView,
    UploadConfirmView,
)

app_name = "object_storage_controller"

urlpatterns = [
    # Presigned URL endpoints
    path(
        "presigned-upload/",
        PresignedUploadView.as_view(),
        name="presigned-upload",
    ),
    path(
        "presigned-download/",
        PresignedDownloadView.as_view(),
        name="presigned-download",
    ),
    # Upload confirmation
    path(
        "confirm-upload/",
        UploadConfirmView.as_view(),
        name="confirm-upload",
    ),
]
