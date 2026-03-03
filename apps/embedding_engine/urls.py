"""
URL routing for embedding engine API.
"""

from __future__ import annotations

from django.urls import path

from apps.embedding_engine.views import (
    EmbedBatchView,
    EmbedQueryView,
    EmbedTextView,
    EmbeddingHealthView,
    SupportedModelsView,
)

app_name = "embedding_engine"

urlpatterns = [
    # Health check
    path(
        "health/",
        EmbeddingHealthView.as_view(),
        name="health",
    ),
    # Single text embedding
    path(
        "embed/",
        EmbedTextView.as_view(),
        name="embed",
    ),
    # Batch text embedding
    path(
        "embed-batch/",
        EmbedBatchView.as_view(),
        name="embed_batch",
    ),
    # Query embedding
    path(
        "embed-query/",
        EmbedQueryView.as_view(),
        name="embed_query",
    ),
    # Supported models
    path(
        "models/",
        SupportedModelsView.as_view(),
        name="models",
    ),
]
