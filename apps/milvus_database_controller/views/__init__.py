"""
Views module for Milvus database controller API.

This module contains all API views for Milvus operations.
"""

from __future__ import annotations

from apps.milvus_database_controller.views.collection_views import (
    CollectionDetailView,
    CollectionListView,
    CollectionStatsView,
    CreateCollectionView,
    DropCollectionView,
    LoadCollectionView,
    ReleaseCollectionView,
)
from apps.milvus_database_controller.views.health_views import HealthView
from apps.milvus_database_controller.views.search_views import (
    DocumentSearchView,
    HybridSearchView,
    VectorSearchView,
)
from apps.milvus_database_controller.views.vector_views import (
    DeleteVectorsView,
    GetVectorView,
    InsertVectorsView,
    QueryVectorsView,
    UpsertVectorsView,
)

__all__ = [
    # Collection views
    "CollectionListView",
    "CreateCollectionView",
    "CollectionDetailView",
    "CollectionStatsView",
    "LoadCollectionView",
    "ReleaseCollectionView",
    "DropCollectionView",
    # Vector views
    "InsertVectorsView",
    "UpsertVectorsView",
    "QueryVectorsView",
    "GetVectorView",
    "DeleteVectorsView",
    # Search views
    "VectorSearchView",
    "HybridSearchView",
    "DocumentSearchView",
    # Health views
    "HealthView",
]
