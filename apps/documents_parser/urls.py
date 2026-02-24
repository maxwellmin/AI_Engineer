"""
URL configuration for documents_parser app.
"""

from __future__ import annotations

from django.urls import path

from apps.documents_parser.views import (
    DocumentDeleteView,
    DocumentDetailView,
    DocumentListCreateView,
)

app_name = "documents_parser"

urlpatterns = [
    # GET /api/v1/documents/ - List documents
    # POST /api/v1/documents/ - Upload document
    path(
        "",
        DocumentListCreateView.as_view(),
        name="list",
    ),
    # GET /api/v1/documents/{id}/ - Get document detail
    path(
        "<uuid:id>/",
        DocumentDetailView.as_view(),
        name="detail",
    ),
    # DELETE /api/v1/documents/{id}/delete/ - Delete document
    path(
        "<uuid:id>/delete/",
        DocumentDeleteView.as_view(),
        name="delete",
    ),
]
