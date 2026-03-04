"""
URL routing for Document Pipeline Manager API.
"""

from __future__ import annotations

from django.urls import path

from apps.document_pipeline_manager.views import (
    PipelineExecuteView,
    PipelineStatusView,
    PipelineRetryView,
    PipelineCancelView,
    PipelineHistoryView,
    PipelineHealthView,
    PipelineSummaryView,
    PipelineRecentView,
)

app_name = "pipeline"

urlpatterns = [
    # Pipeline management endpoints
    path(
        "execute/",
        PipelineExecuteView.as_view(),
        name="execute",
    ),
    path(
        "status/<uuid:document_id>/",
        PipelineStatusView.as_view(),
        name="status",
    ),
    path(
        "retry/<uuid:document_id>/",
        PipelineRetryView.as_view(),
        name="retry",
    ),
    path(
        "cancel/<uuid:document_id>/",
        PipelineCancelView.as_view(),
        name="cancel",
    ),
    path(
        "history/<uuid:document_id>/",
        PipelineHistoryView.as_view(),
        name="history",
    ),
    path(
        "summary/<uuid:document_id>/",
        PipelineSummaryView.as_view(),
        name="summary",
    ),
    path(
        "health/",
        PipelineHealthView.as_view(),
        name="health",
    ),
    path(
        "recent/",
        PipelineRecentView.as_view(),
        name="recent",
    ),
]
