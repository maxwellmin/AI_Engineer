"""
Pytest fixtures for Milvus database controller tests.

This module provides shared fixtures for testing the Milvus database controller.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Generator

import pytest
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.milvus_database_controller.client import MilvusClientWrapper
from apps.milvus_database_controller.constants import (
    COLLECTION_DOCUMENTS,
    DEFAULT_DENSE_DIMENSION,
    FieldName,
)
from apps.milvus_database_controller.managers.collection_manager import CollectionManager
from apps.milvus_database_controller.managers.index_manager import IndexManager
from apps.milvus_database_controller.managers.search_manager import SearchManager
from apps.milvus_database_controller.managers.vector_manager import VectorManager
from apps.milvus_database_controller.services.milvus_service import MilvusService

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# Client Fixtures
# =============================================================================


@pytest.fixture
def milvus_client() -> Generator[MilvusClientWrapper, None, None]:
    """Create MilvusClient wrapper for testing.

    Yields:
        MilvusClientWrapper instance.
    """
    client = MilvusClientWrapper.get_instance()
    yield client
    # Cleanup: Reset singleton after tests
    MilvusClientWrapper.reset_instance()


@pytest.fixture
def test_collection_prefix() -> str:
    """Prefix for test collection names."""
    return "test_"


# =============================================================================
# Manager Fixtures
# =============================================================================


@pytest.fixture
def collection_manager(milvus_client: MilvusClientWrapper) -> CollectionManager:
    """Create CollectionManager for testing.

    Args:
        milvus_client: MilvusClientWrapper fixture.

    Returns:
        CollectionManager instance.
    """
    return CollectionManager(milvus_client)


@pytest.fixture
def index_manager(milvus_client: MilvusClientWrapper) -> IndexManager:
    """Create IndexManager for testing.

    Args:
        milvus_client: MilvusClientWrapper fixture.

    Returns:
        IndexManager instance.
    """
    return IndexManager(milvus_client)


@pytest.fixture
def vector_manager(milvus_client: MilvusClientWrapper) -> VectorManager:
    """Create VectorManager for testing.

    Args:
        milvus_client: MilvusClientWrapper fixture.

    Returns:
        VectorManager instance.
    """
    return VectorManager(milvus_client)


@pytest.fixture
def search_manager(milvus_client: MilvusClientWrapper) -> SearchManager:
    """Create SearchManager for testing.

    Args:
        milvus_client: MilvusClientWrapper fixture.

    Returns:
        SearchManager instance.
    """
    return SearchManager(milvus_client)


@pytest.fixture
def milvus_service(milvus_client: MilvusClientWrapper) -> MilvusService:
    """Create MilvusService for testing.

    Args:
        milvus_client: MilvusClientWrapper fixture.

    Returns:
        MilvusService instance.
    """
    return MilvusService(milvus_client)


# =============================================================================
# Collection Fixtures
# =============================================================================


@pytest.fixture
def test_collection_name(test_collection_prefix: str) -> str:
    """Generate a unique test collection name.

    Args:
        test_collection_prefix: Prefix for test collections.

    Returns:
        Unique test collection name.
    """
    import uuid

    return f"{test_collection_prefix}documents_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_collection(
    collection_manager: CollectionManager,
    index_manager: IndexManager,
    test_collection_name: str,
) -> Generator[str, None, None]:
    """Create a test collection with simplified schema (no sparse vector).

    Args:
        collection_manager: CollectionManager fixture.
        index_manager: IndexManager fixture.
        test_collection_name: Test collection name.

    Yields:
        Test collection name.
    """
    from dataclasses import dataclass

    from pymilvus import DataType

    from apps.milvus_database_controller.schemas.collection_schema import (
        FieldDefinition,
    )

    @dataclass(frozen=True)
    class TestCollectionSchema:
        """Test schema without sparse vector for simpler testing."""

        dimension: int = DEFAULT_DENSE_DIMENSION
        enable_dynamic_field: bool = True

        @property
        def fields(self) -> list[FieldDefinition]:
            """Get all field definitions."""
            return [
                # Primary key
                FieldDefinition(
                    name=FieldName.PK.value,
                    dtype=DataType.VARCHAR,
                    is_primary=True,
                    auto_id=False,
                    max_length=256,
                    description="Primary key",
                ),
                # Text fields
                FieldDefinition(
                    name=FieldName.TEXT.value,
                    dtype=DataType.VARCHAR,
                    max_length=65535,
                    description="Full text content",
                ),
                FieldDefinition(
                    name=FieldName.SUMMARY.value,
                    dtype=DataType.VARCHAR,
                    max_length=65535,
                    description="Document summary",
                ),
                FieldDefinition(
                    name=FieldName.DOCUMENT.value,
                    dtype=DataType.VARCHAR,
                    max_length=65535,
                    description="Original document content",
                ),
                # Source metadata
                FieldDefinition(
                    name=FieldName.SOURCE.value,
                    dtype=DataType.VARCHAR,
                    max_length=64,
                    description="Data source type",
                ),
                FieldDefinition(
                    name=FieldName.SOURCE_NAME.value,
                    dtype=DataType.VARCHAR,
                    max_length=256,
                    description="Data source name",
                ),
                # Link to PostgreSQL
                FieldDefinition(
                    name=FieldName.LT_DOC_ID.value,
                    dtype=DataType.VARCHAR,
                    max_length=256,
                    description="Link to document ID in PostgreSQL",
                ),
                # Chunk ID
                FieldDefinition(
                    name=FieldName.CHUNK_ID.value,
                    dtype=DataType.INT64,
                    description="Chunk sequence number",
                ),
                # Dense vectors only (no sparse for testing)
                FieldDefinition(
                    name=FieldName.SUMMARY_DENSE.value,
                    dtype=DataType.FLOAT_VECTOR,
                    dim=self.dimension,
                    description="Summary embedding vector",
                ),
                FieldDefinition(
                    name=FieldName.TEXT_DENSE.value,
                    dtype=DataType.FLOAT_VECTOR,
                    dim=self.dimension,
                    description="Text embedding vector",
                ),
            ]

    # Create test schema instance
    test_schema = TestCollectionSchema(
        dimension=DEFAULT_DENSE_DIMENSION,
        enable_dynamic_field=True,
    )

    try:
        collection_manager.create_collection_with_schema(
            collection_name=test_collection_name,
            schema=test_schema,
        )
    except Exception as e:
        logger.warning(f"Failed to create test collection: {e}")

    # Create indexes and load
    try:
        index_manager.create_dense_index(
            collection_name=test_collection_name,
            field_name=FieldName.SUMMARY_DENSE.value,
        )
        index_manager.create_dense_index(
            collection_name=test_collection_name,
            field_name=FieldName.TEXT_DENSE.value,
        )
        index_manager.load_collection(test_collection_name)
    except Exception as e:
        logger.warning(f"Failed to create indexes: {e}")

    yield test_collection_name

    # Cleanup: Drop test collection
    try:
        collection_manager.drop_collection(test_collection_name)
    except Exception as e:
        logger.warning(f"Failed to drop test collection: {e}")


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_vector() -> list[float]:
    """Generate a sample dense vector.

    Returns:
        Sample vector of default dimension.
    """
    import random

    return [random.random() for _ in range(DEFAULT_DENSE_DIMENSION)]


@pytest.fixture
def sample_vectors(count: int = 3) -> list[list[float]]:
    """Generate multiple sample vectors.

    Args:
        count: Number of vectors to generate.

    Returns:
        List of sample vectors.
    """
    import random

    return [
        [random.random() for _ in range(DEFAULT_DENSE_DIMENSION)]
        for _ in range(count)
    ]


@pytest.fixture
def sample_vector_record(sample_vector: list[float]) -> dict[str, Any]:
    """Generate a sample vector record for insertion.

    Args:
        sample_vector: Sample dense vector.

    Returns:
        Dictionary with vector record data.
    """
    import uuid

    return {
        "pk": f"test-{uuid.uuid4().hex[:8]}",
        "text": "This is a sample document text for testing vector operations.",
        "summary": "Sample document summary.",
        "document": "Full document content for testing purposes.",
        "source": "test",
        "source_name": "test_source",
        "lt_doc_id": "doc-test-001",
        "chunk_id": 1,
        "summary_dense": sample_vector,
        "text_dense": sample_vector,
    }


@pytest.fixture
def sample_vector_records(
    sample_vectors: list[list[float]],
) -> list[dict[str, Any]]:
    """Generate multiple sample vector records.

    Args:
        sample_vectors: List of sample vectors.

    Returns:
        List of vector record dictionaries.
    """
    import uuid

    records = []
    for i, vector in enumerate(sample_vectors):
        record = {
            "pk": f"test-{uuid.uuid4().hex[:8]}-{i}",
            "text": f"Sample document text {i} for testing.",
            "summary": f"Sample summary {i}.",
            "document": f"Full document content {i}.",
            "source": "test",
            "source_name": f"test_source_{i}",
            "lt_doc_id": f"doc-test-{i:03d}",
            "chunk_id": i,
            "summary_dense": vector,
            "text_dense": vector,
        }
        records.append(record)

    return records


# =============================================================================
# Markers
# =============================================================================


def pytest_configure(config: Any) -> None:
    """Configure custom pytest markers.

    Args:
        config: Pytest config object.
    """
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires Milvus)"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (mocked Milvus)"
    )


# =============================================================================
# API Test Fixtures
# =============================================================================


@pytest.fixture
def api_client() -> APIClient:
    """Unauthenticated DRF API client.

    Returns:
        APIClient instance.
    """
    return APIClient()


@pytest.fixture
def test_user():
    """Create a test user for API testing.

    Returns:
        User instance.
    """
    from apps.accounts.tests.factories import UserFactory

    return UserFactory.create_user(
        username="milvus_testuser",
        email="milvus_testuser@example.com",
        password="testpass123",
    )


@pytest.fixture
def authenticated_client(api_client: APIClient, test_user) -> APIClient:
    """API client authenticated as test_user via JWT.

    Args:
        api_client: Unauthenticated API client.
        test_user: Test user fixture.

    Returns:
        Authenticated APIClient instance.
    """
    refresh = RefreshToken.for_user(test_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client
