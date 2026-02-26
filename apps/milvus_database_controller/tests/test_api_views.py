"""
API tests for Milvus database controller views.

This module contains tests for all Milvus API endpoints.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.milvus_database_controller.constants import DEFAULT_DENSE_DIMENSION, FieldName
from apps.milvus_database_controller.dto import (
    CollectionInfo,
    DeleteResult,
    HybridSearchResult,
    InsertResult,
    QueryResult,
    SearchResult,
    SearchResultItem,
    UpsertResult,
)

if TYPE_CHECKING:
    from apps.accounts.tests.factories import UserFactory


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_vector() -> list[float]:
    """Generate a sample dense vector.

    Returns:
        Sample vector of default dimension.
    """
    return [random.random() for _ in range(DEFAULT_DENSE_DIMENSION)]


@pytest.fixture
def sample_vector_data(sample_vector: list[float]) -> dict[str, Any]:
    """Generate sample vector data for API requests.

    Args:
        sample_vector: Sample dense vector.

    Returns:
        Dictionary with vector data.
    """
    return {
        "pk": "test-pk-001",
        "text": "Sample text for testing",
        "summary": "Sample summary",
        "document": "Full document content",
        "source": "test",
        "source_name": "test_source.pdf",
        "lt_doc_id": "doc-001",
        "chunk_id": 1,
        "summary_dense": sample_vector,
        "text_dense": sample_vector,
    }


@pytest.fixture
def mock_milvus_service():
    """Create a mock MilvusService.

    Returns:
        Mocked MilvusService instance.
    """
    with patch(
        "apps.milvus_database_controller.views.collection_views.MilvusService"
    ) as mock:
        yield mock

    with patch(
        "apps.milvus_database_controller.views.vector_views.MilvusService"
    ) as mock:
        yield mock

    with patch(
        "apps.milvus_database_controller.views.search_views.MilvusService"
    ) as mock:
        yield mock

    with patch(
        "apps.milvus_database_controller.views.health_views.MilvusService"
    ) as mock:
        yield mock


# =============================================================================
# Health View Tests
# =============================================================================


@pytest.mark.django_db
class TestHealthView:
    """Tests for HealthView endpoint."""

    def test_health_check_healthy(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test health check returns healthy status."""
        with patch(
            "apps.milvus_database_controller.views.health_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.health_check.return_value = {
                "status": "healthy",
                "connected": True,
                "collections_count": 3,
            }

            response = authenticated_client.get("/api/v1/milvus/health/")

            assert response.status_code == status.HTTP_200_OK
            assert response.data["status"] == "healthy"
            assert response.data["connected"] is True
            assert response.data["collections_count"] == 3

    def test_health_check_unhealthy(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test health check returns unhealthy status on connection failure."""
        with patch(
            "apps.milvus_database_controller.views.health_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.health_check.return_value = {
                "status": "unhealthy",
                "connected": False,
                "error": "Connection refused",
            }

            response = authenticated_client.get("/api/v1/milvus/health/")

            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert response.data["status"] == "unhealthy"
            assert response.data["connected"] is False

    def test_health_check_unauthenticated(
        self,
        api_client: APIClient,
    ) -> None:
        """Test health check requires authentication."""
        response = api_client.get("/api/v1/milvus/health/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Collection View Tests
# =============================================================================


@pytest.mark.django_db
class TestCollectionListView:
    """Tests for collection list endpoint."""

    def test_list_collections_success(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test listing collections successfully."""
        with patch(
            "apps.milvus_database_controller.views.collection_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.list_collections.return_value = ["documents", "chat_history"]

            response = authenticated_client.get("/api/v1/milvus/collections/")

            assert response.status_code == status.HTTP_200_OK
            assert response.data["total"] == 2
            assert len(response.data["collections"]) == 2

    def test_list_collections_empty(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test listing collections when empty."""
        with patch(
            "apps.milvus_database_controller.views.collection_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.list_collections.return_value = []

            response = authenticated_client.get("/api/v1/milvus/collections/")

            assert response.status_code == status.HTTP_200_OK
            assert response.data["total"] == 0


@pytest.mark.django_db
class TestCreateCollectionView:
    """Tests for create collection endpoint."""

    def test_create_collection_success(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test creating a collection successfully."""
        with patch(
            "apps.milvus_database_controller.views.collection_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = False
            mock_service.create_collection.return_value = True
            mock_service.get_collection_info.return_value = CollectionInfo(
                name="test_collection",
                description="Test collection",
                num_entities=0,
                schema={"fields": []},
                loaded=True,
            )

            data = {
                "collection_name": "test_collection",
                "dimension": 1536,
                "description": "Test collection",
            }

            response = authenticated_client.post(
                "/api/v1/milvus/collections/create/",
                data,
                format="json",
            )

            assert response.status_code == status.HTTP_201_CREATED
            assert response.data["name"] == "test_collection"

    def test_create_collection_already_exists(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test creating a collection that already exists."""
        with patch(
            "apps.milvus_database_controller.views.collection_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = True

            data = {
                "collection_name": "existing_collection",
                "dimension": 1536,
            }

            response = authenticated_client.post(
                "/api/v1/milvus/collections/create/",
                data,
                format="json",
            )

            assert response.status_code == status.HTTP_409_CONFLICT

    def test_create_collection_invalid_dimension(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test creating a collection with invalid dimension."""
        data = {
            "collection_name": "test_collection",
            "dimension": 0,  # Invalid
        }

        response = authenticated_client.post(
            "/api/v1/milvus/collections/create/",
            data,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCollectionDetailView:
    """Tests for collection detail endpoint."""

    def test_get_collection_info_success(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test getting collection info successfully."""
        with patch(
            "apps.milvus_database_controller.views.collection_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = True
            mock_service.get_collection_info.return_value = CollectionInfo(
                name="documents",
                description="Document vectors",
                num_entities=100,
                schema={"fields": ["pk", "text"]},
                loaded=True,
            )

            response = authenticated_client.get("/api/v1/milvus/collections/documents/")

            assert response.status_code == status.HTTP_200_OK
            assert response.data["name"] == "documents"
            assert response.data["num_entities"] == 100

    def test_get_collection_info_not_found(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test getting info for non-existent collection."""
        with patch(
            "apps.milvus_database_controller.views.collection_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = False

            response = authenticated_client.get(
                "/api/v1/milvus/collections/nonexistent/"
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCollectionLoadReleaseViews:
    """Tests for collection load and release endpoints."""

    def test_load_collection_success(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test loading a collection successfully."""
        with patch(
            "apps.milvus_database_controller.views.collection_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = True
            mock_service.load_collection.return_value = True

            response = authenticated_client.post(
                "/api/v1/milvus/collections/documents/load/"
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data["loaded"] is True

    def test_release_collection_success(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test releasing a collection successfully."""
        with patch(
            "apps.milvus_database_controller.views.collection_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = True
            mock_service.release_collection.return_value = True

            response = authenticated_client.post(
                "/api/v1/milvus/collections/documents/release/"
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data["released"] is True

    def test_drop_collection_success(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test dropping a collection successfully."""
        with patch(
            "apps.milvus_database_controller.views.collection_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = True
            mock_service.drop_collection.return_value = True

            response = authenticated_client.delete(
                "/api/v1/milvus/collections/documents/delete/"
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data["dropped"] is True


# =============================================================================
# Vector View Tests
# =============================================================================


@pytest.mark.django_db
class TestInsertVectorsView:
    """Tests for insert vectors endpoint."""

    def test_insert_vectors_success(
        self,
        authenticated_client: APIClient,
        sample_vector_data: dict[str, Any],
    ) -> None:
        """Test inserting vectors successfully."""
        with patch(
            "apps.milvus_database_controller.views.vector_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = True
            mock_service.insert_vectors.return_value = InsertResult(
                inserted_count=1,
                inserted_ids=["test-pk-001"],
            )

            data = {
                "collection_name": "documents",
                "data": [sample_vector_data],
            }

            response = authenticated_client.post(
                "/api/v1/milvus/vectors/insert/",
                data,
                format="json",
            )

            assert response.status_code == status.HTTP_201_CREATED
            assert response.data["inserted_count"] == 1

    def test_insert_vectors_collection_not_found(
        self,
        authenticated_client: APIClient,
        sample_vector_data: dict[str, Any],
    ) -> None:
        """Test inserting vectors to non-existent collection."""
        with patch(
            "apps.milvus_database_controller.views.vector_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = False

            data = {
                "collection_name": "nonexistent",
                "data": [sample_vector_data],
            }

            response = authenticated_client.post(
                "/api/v1/milvus/vectors/insert/",
                data,
                format="json",
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_insert_vectors_invalid_dimension(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test inserting vectors with invalid dimension."""
        data = {
            "collection_name": "documents",
            "data": [
                {
                    "pk": "test-001",
                    "text": "Sample text",
                    "summary": "Summary",
                    "document": "Document",
                    "source": "test",
                    "source_name": "test.pdf",
                    "lt_doc_id": "doc-001",
                    "chunk_id": 1,
                    "summary_dense": [0.1] * 100,  # Wrong dimension
                    "text_dense": [0.1] * 100,
                }
            ],
        }

        response = authenticated_client.post(
            "/api/v1/milvus/vectors/insert/",
            data,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUpsertVectorsView:
    """Tests for upsert vectors endpoint."""

    def test_upsert_vectors_success(
        self,
        authenticated_client: APIClient,
        sample_vector_data: dict[str, Any],
    ) -> None:
        """Test upserting vectors successfully."""
        with patch(
            "apps.milvus_database_controller.views.vector_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = True
            mock_service.upsert_vectors.return_value = UpsertResult(
                upserted_count=1,
                upserted_ids=["test-pk-001"],
            )

            data = {
                "collection_name": "documents",
                "data": [sample_vector_data],
            }

            response = authenticated_client.post(
                "/api/v1/milvus/vectors/upsert/",
                data,
                format="json",
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data["upserted_count"] == 1


@pytest.mark.django_db
class TestQueryVectorsView:
    """Tests for query vectors endpoint."""

    def test_query_vectors_success(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test querying vectors successfully."""
        with patch(
            "apps.milvus_database_controller.views.vector_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = True
            mock_service.query_vectors.return_value = QueryResult(
                items=[{"pk": "test-001", "text": "Sample"}],
                total=1,
            )

            data = {
                "collection_name": "documents",
                "filter_expr": 'source == "test"',
                "limit": 10,
            }

            response = authenticated_client.post(
                "/api/v1/milvus/vectors/query/",
                data,
                format="json",
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data["total"] == 1


@pytest.mark.django_db
class TestGetVectorView:
    """Tests for get vector endpoint."""

    def test_get_vector_success(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test getting a single vector successfully."""
        with patch(
            "apps.milvus_database_controller.views.vector_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = True
            mock_service.get_vector.return_value = {
                "pk": "test-001",
                "text": "Sample text",
                "source": "test",
            }

            response = authenticated_client.get(
                "/api/v1/milvus/vectors/test-001/?collection_name=documents"
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data["pk"] == "test-001"

    def test_get_vector_not_found(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test getting a non-existent vector."""
        with patch(
            "apps.milvus_database_controller.views.vector_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = True
            mock_service.get_vector.return_value = None

            response = authenticated_client.get(
                "/api/v1/milvus/vectors/nonexistent/?collection_name=documents"
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_vector_missing_collection(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test getting vector without collection_name parameter."""
        response = authenticated_client.get("/api/v1/milvus/vectors/test-001/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestDeleteVectorsView:
    """Tests for delete vectors endpoint."""

    def test_delete_vectors_by_ids_success(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test deleting vectors by IDs successfully."""
        with patch(
            "apps.milvus_database_controller.views.vector_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = True
            mock_service.delete_vectors.return_value = DeleteResult(deleted_count=2)

            data = {
                "collection_name": "documents",
                "ids": ["test-001", "test-002"],
            }

            response = authenticated_client.post(
                "/api/v1/milvus/vectors/delete/",
                data,
                format="json",
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data["deleted_count"] == 2

    def test_delete_vectors_by_filter_success(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test deleting vectors by filter successfully."""
        with patch(
            "apps.milvus_database_controller.views.vector_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = True
            mock_service.delete_vectors_by_filter.return_value = DeleteResult(
                deleted_count=5
            )

            data = {
                "collection_name": "documents",
                "filter_expr": 'source == "test"',
            }

            response = authenticated_client.post(
                "/api/v1/milvus/vectors/delete/",
                data,
                format="json",
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data["deleted_count"] == 5

    def test_delete_vectors_missing_params(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test deleting vectors without required params."""
        data = {
            "collection_name": "documents",
        }

        response = authenticated_client.post(
            "/api/v1/milvus/vectors/delete/",
            data,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Search View Tests
# =============================================================================


@pytest.mark.django_db
class TestVectorSearchView:
    """Tests for vector search endpoint."""

    def test_vector_search_success(
        self,
        authenticated_client: APIClient,
        sample_vector: list[float],
    ) -> None:
        """Test vector search successfully."""
        with patch(
            "apps.milvus_database_controller.views.search_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = True
            mock_service.search.return_value = SearchResult(
                items=[
                    SearchResultItem(
                        id="test-001",
                        distance=0.95,
                        text="Sample text",
                        summary="Summary",
                        document="Document",
                        source="test",
                        source_name="test.pdf",
                        lt_doc_id="doc-001",
                        chunk_id=1,
                    )
                ],
                total=1,
                query_time_ms=15.5,
            )

            data = {
                "collection_name": "documents",
                "query_vector": sample_vector,
                "anns_field": "text_dense",
                "top_k": 10,
            }

            response = authenticated_client.post(
                "/api/v1/milvus/search/vector/",
                data,
                format="json",
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data["total"] == 1
            assert response.data["items"][0]["pk"] == "test-001"

    def test_vector_search_invalid_dimension(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test vector search with invalid dimension."""
        data = {
            "collection_name": "documents",
            "query_vector": [0.1] * 100,  # Wrong dimension
            "top_k": 10,
        }

        response = authenticated_client.post(
            "/api/v1/milvus/search/vector/",
            data,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestHybridSearchView:
    """Tests for hybrid search endpoint."""

    def test_hybrid_search_success(
        self,
        authenticated_client: APIClient,
        sample_vector: list[float],
    ) -> None:
        """Test hybrid search successfully."""
        with patch(
            "apps.milvus_database_controller.views.search_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = True
            mock_service.hybrid_search.return_value = HybridSearchResult(
                items=[
                    SearchResultItem(
                        id="test-001",
                        distance=0.92,
                        text="Sample text",
                        summary="Summary",
                        document="Document",
                        source="test",
                        source_name="test.pdf",
                        lt_doc_id="doc-001",
                        chunk_id=1,
                    )
                ],
                total=1,
                query_time_ms=25.5,
                search_details={"rrf_k": 60},
            )

            data = {
                "collection_name": "documents",
                "query_text": "What is machine learning?",
                "query_vectors": {
                    "text_dense": sample_vector,
                    "summary_dense": sample_vector,
                },
                "top_k": 10,
                "rerank_method": "rrf",
            }

            response = authenticated_client.post(
                "/api/v1/milvus/search/hybrid/",
                data,
                format="json",
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data["total"] == 1
            assert "search_details" in response.data

    def test_hybrid_search_invalid_weights(
        self,
        authenticated_client: APIClient,
        sample_vector: list[float],
    ) -> None:
        """Test hybrid search with invalid weights."""
        data = {
            "collection_name": "documents",
            "query_text": "What is machine learning?",
            "query_vectors": {
                "text_dense": sample_vector,
            },
            "rerank_method": "weighted",
            "weights": [0.3, 0.3],  # Doesn't sum to 1.0
        }

        response = authenticated_client.post(
            "/api/v1/milvus/search/hybrid/",
            data,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestDocumentSearchView:
    """Tests for document search endpoint."""

    def test_document_search_success(
        self,
        authenticated_client: APIClient,
        sample_vector: list[float],
    ) -> None:
        """Test document search successfully."""
        with patch(
            "apps.milvus_database_controller.views.search_views.MilvusService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.has_collection.return_value = True
            mock_service.search_by_document.return_value = SearchResult(
                items=[
                    SearchResultItem(
                        id="test-001",
                        distance=0.88,
                        text="Sample text",
                        summary="Summary",
                        document="Document",
                        source="test",
                        source_name="test.pdf",
                        lt_doc_id="doc-001",
                        chunk_id=1,
                    )
                ],
                total=1,
                query_time_ms=10.5,
            )

            data = {
                "collection_name": "documents",
                "document_id": "doc-001",
                "query_vector": sample_vector,
                "top_k": 5,
            }

            response = authenticated_client.post(
                "/api/v1/milvus/search/document/",
                data,
                format="json",
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data["total"] == 1


# =============================================================================
# Integration Tests (require running Milvus)
# =============================================================================


@pytest.mark.integration
@pytest.mark.django_db
class TestMilvusAPIIntegration:
    """Integration tests that require a running Milvus instance."""

    def test_full_collection_lifecycle(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test complete collection lifecycle: create, get, drop."""
        import uuid

        collection_name = f"test_api_{uuid.uuid4().hex[:8]}"

        try:
            # Create collection
            create_response = authenticated_client.post(
                "/api/v1/milvus/collections/create/",
                {
                    "collection_name": collection_name,
                    "dimension": 1536,
                    "description": "Test collection for API tests",
                },
                format="json",
            )
            assert create_response.status_code == status.HTTP_201_CREATED

            # Get collection info
            info_response = authenticated_client.get(
                f"/api/v1/milvus/collections/{collection_name}/"
            )
            assert info_response.status_code == status.HTTP_200_OK
            assert info_response.data["name"] == collection_name

        finally:
            # Cleanup: Drop collection
            authenticated_client.delete(
                f"/api/v1/milvus/collections/{collection_name}/delete/"
            )
