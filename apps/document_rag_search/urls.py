"""
URL routing for Document RAG Search API.

This module defines URL patterns for the document RAG search endpoints.

API Endpoints:
    POST /api/v1/search/simple/      - Simple vector search
    POST /api/v1/search/hybrid/      - Hybrid search with RRF fusion
    POST /api/v1/search/advanced/    - Advanced search with filters
    GET  /api/v1/search/suggestions/ - Search suggestions (auto-complete)
    GET  /api/v1/search/health/      - Health check for search service
"""

from __future__ import annotations

from django.urls import path

from apps.document_rag_search.views import (
    AdvancedSearchView,
    HealthCheckView,
    HybridSearchView,
    SearchSuggestionsView,
    SimpleSearchView,
)

app_name = "document_rag_search"

urlpatterns = [
    # POST /api/v1/search/simple/ - Simple vector search
    path(
        "simple/",
        SimpleSearchView.as_view(),
        name="simple",
    ),
    # POST /api/v1/search/hybrid/ - Hybrid search with RRF fusion
    path(
        "hybrid/",
        HybridSearchView.as_view(),
        name="hybrid",
    ),
    # POST /api/v1/search/advanced/ - Advanced search with filters
    path(
        "advanced/",
        AdvancedSearchView.as_view(),
        name="advanced",
    ),
    # GET /api/v1/search/suggestions/ - Search suggestions
    path(
        "suggestions/",
        SearchSuggestionsView.as_view(),
        name="suggestions",
    ),
    # GET /api/v1/search/health/ - Health check for search service
    path(
        "health/",
        HealthCheckView.as_view(),
        name="health",
    ),
]
