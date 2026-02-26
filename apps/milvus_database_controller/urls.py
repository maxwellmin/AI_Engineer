"""
URL configuration for milvus_database_controller app.
"""

from __future__ import annotations

from django.urls import path

from apps.milvus_database_controller.views import (
    CollectionDetailView,
    CollectionListView,
    CollectionStatsView,
    CreateCollectionView,
    DeleteVectorsView,
    DocumentSearchView,
    DropCollectionView,
    GetVectorView,
    HealthView,
    HybridSearchView,
    InsertVectorsView,
    LoadCollectionView,
    QueryVectorsView,
    ReleaseCollectionView,
    UpsertVectorsView,
    VectorSearchView,
)

app_name = "milvus_database_controller"

urlpatterns = [
    # Health check
    path(
        "health/",
        HealthView.as_view(),
        name="health",
    ),
    # Collection endpoints
    path(
        "collections/",
        CollectionListView.as_view(),
        name="collection-list",
    ),
    path(
        "collections/create/",
        CreateCollectionView.as_view(),
        name="collection-create",
    ),
    path(
        "collections/<str:name>/",
        CollectionDetailView.as_view(),
        name="collection-detail",
    ),
    path(
        "collections/<str:name>/stats/",
        CollectionStatsView.as_view(),
        name="collection-stats",
    ),
    path(
        "collections/<str:name>/load/",
        LoadCollectionView.as_view(),
        name="collection-load",
    ),
    path(
        "collections/<str:name>/release/",
        ReleaseCollectionView.as_view(),
        name="collection-release",
    ),
    path(
        "collections/<str:name>/delete/",
        DropCollectionView.as_view(),
        name="collection-delete",
    ),
    # Vector endpoints
    path(
        "vectors/insert/",
        InsertVectorsView.as_view(),
        name="vector-insert",
    ),
    path(
        "vectors/upsert/",
        UpsertVectorsView.as_view(),
        name="vector-upsert",
    ),
    path(
        "vectors/query/",
        QueryVectorsView.as_view(),
        name="vector-query",
    ),
    path(
        "vectors/delete/",
        DeleteVectorsView.as_view(),
        name="vector-delete",
    ),
    # Note: Must come after specific paths to avoid matching "delete" as pk
    path(
        "vectors/<str:pk>/",
        GetVectorView.as_view(),
        name="vector-detail",
    ),
    # Search endpoints
    path(
        "search/vector/",
        VectorSearchView.as_view(),
        name="search-vector",
    ),
    path(
        "search/hybrid/",
        HybridSearchView.as_view(),
        name="search-hybrid",
    ),
    path(
        "search/document/",
        DocumentSearchView.as_view(),
        name="search-document",
    ),
]
