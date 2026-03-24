"""
Pytest fixtures for document RAG search module tests.

This module provides shared fixtures for testing the search module components,
following the patterns established in other modules (Milvus, Neo4j, Embedding).

Fixtures are organized into categories:
1. Django Model Fixtures - Real database objects for integration tests
2. Mock Service Fixtures - Mocked external services for unit tests
3. DTO Fixtures - Sample data transfer objects
4. Search Service Fixtures - Configured service instances
5. API Test Fixtures - Authentication and client setup
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.document_rag_search.dto import (
    AdvancedSearchRequest,
    HybridSearchRequest,
    RankedResult,
    RetrieverResult,
    SearchConfig,
    SearchQuery,
    SearchResponse,
    SearchResultItem,
    SearchSuggestionsRequest,
    SearchSuggestionsResponse,
)


# =============================================================================
# Django Model Fixtures
# =============================================================================


@pytest.fixture
@pytest.mark.django_db
def test_user():
    """Create a test user for document operations.

    Returns:
        User: Test user instance.
    """
    from apps.accounts.tests.factories import UserFactory

    return UserFactory.create_user(
        username="search_testuser",
        email="search_testuser@example.com",
        password="testpass123",
    )


@pytest.fixture
@pytest.mark.django_db
def test_document(test_user):
    """Create a test document for search operations.

    Args:
        test_user: Test user fixture.

    Returns:
        Document: Test document instance.
    """
    from apps.documents_parser.models import Document

    return Document.objects.create(
        user=test_user,
        name="test_search_document.pdf",
        original_name="Test Search Document.pdf",
        file_path="documents/test_search_document.pdf",
        file_size=1024000,
        file_type="pdf",
        file_hash="test_hash_search_001",
        status=Document.Status.DONE,
    )


@pytest.fixture
@pytest.mark.django_db
def test_document_with_chunks(test_user):
    """Create a test document with multiple chunks for search testing.

    Creates a document with 5 chunks containing searchable content.

    Args:
        test_user: Test user fixture.

    Returns:
        tuple: (Document, list[DocumentChunk]) - Document and its chunks.
    """
    from apps.documents_parser.models import Document, DocumentChunk

    doc = Document.objects.create(
        user=test_user,
        name="ml_document.pdf",
        original_name="Machine Learning Guide.pdf",
        file_path="documents/ml_document.pdf",
        file_size=2048000,
        file_type="pdf",
        file_hash="ml_doc_hash_001",
        status=Document.Status.DONE,
    )

    chunks = []
    chunk_texts = [
        "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
        "Deep learning uses neural networks with multiple layers to process complex patterns.",
        "Natural language processing allows computers to understand and generate human language.",
        "Computer vision enables machines to interpret and understand visual information from the world.",
        "Reinforcement learning trains agents through rewards and penalties in an environment.",
    ]

    for i, text in enumerate(chunk_texts):
        chunk = DocumentChunk.objects.create(
            document=doc,
            content=text,
            chunk_index=i,
            content_hash=f"chunk_hash_{i}",
            char_count=len(text),
            token_count=len(text.split()),
            page_number=i + 1,
        )
        chunks.append(chunk)

    return doc, chunks


@pytest.fixture
@pytest.mark.django_db
def multiple_test_documents(test_user):
    """Create multiple test documents with chunks for filtering tests.

    Args:
        test_user: Test user fixture.

    Returns:
        list[Document]: List of test documents.
    """
    from apps.documents_parser.models import Document, DocumentChunk

    documents = []
    doc_data = [
        ("python_basics.pdf", "Python Basics", "pdf"),
        ("javascript_guide.docx", "JavaScript Guide", "docx"),
        ("data_science.txt", "Data Science Notes", "txt"),
    ]

    for name, title, file_type in doc_data:
        doc = Document.objects.create(
            user=test_user,
            name=name,
            original_name=title,
            file_path=f"documents/{name}",
            file_size=1024000,
            file_type=file_type,
            file_hash=f"hash_{name}",
            status=Document.Status.DONE,
        )

        # Create a chunk for each document
        DocumentChunk.objects.create(
            document=doc,
            content=f"Content of {title} - This is searchable text.",
            chunk_index=0,
            content_hash=f"chunk_hash_{name}",
            char_count=50,
            token_count=8,
        )

        documents.append(doc)

    return documents


# =============================================================================
# Mock Service Fixtures
# =============================================================================


@pytest.fixture
def mock_milvus_service():
    """Create a mock MilvusService for testing.

    Returns:
        MagicMock: Mocked MilvusService instance.
    """
    mock_service = MagicMock()

    # Mock search result
    mock_search_item = MagicMock()
    mock_search_item.id = str(uuid4())
    mock_search_item.lt_doc_id = str(uuid4())
    mock_search_item.text = "Machine learning is a subset of artificial intelligence."
    mock_search_item.distance = 0.15
    mock_search_item.summary = "ML overview"
    mock_search_item.document = "AI Document"
    mock_search_item.source = "upload"
    mock_search_item.source_name = "ai_guide.pdf"
    mock_search_item.chunk_id = 0

    mock_search_result = MagicMock()
    mock_search_result.items = [mock_search_item]
    mock_search_result.total = 1
    mock_search_result.query_time_ms = 50.0

    mock_service.search.return_value = mock_search_result

    # Mock hybrid_search result
    mock_hybrid_result = MagicMock()
    mock_hybrid_result.items = [mock_search_item]
    mock_hybrid_result.total = 1
    mock_hybrid_result.query_time_ms = 80.0

    mock_service.hybrid_search.return_value = mock_hybrid_result

    # Mock health_check
    mock_service.health_check.return_value = {"connected": True}
    mock_service.has_collection.return_value = True

    return mock_service


@pytest.fixture
def mock_neo4j_service():
    """Create a mock Neo4jService for testing.

    Returns:
        MagicMock: Mocked Neo4jService instance.
    """
    mock_service = MagicMock()

    # Mock entity search result
    mock_entity = MagicMock()
    mock_entity.id = str(uuid4())
    mock_entity.properties = {"name": "Machine Learning"}

    mock_service.search_entities.return_value = [mock_entity]

    # Mock entity context
    mock_chunk_node = MagicMock()
    mock_chunk_node.id = str(uuid4())
    mock_chunk_node.properties = {
        "document_id": str(uuid4()),
        "text": "ML context text",
        "chunk_index": 0,
        "page_number": 1,
    }

    mock_context = MagicMock()
    mock_context.mentioned_in = [mock_chunk_node]
    mock_context.related_entities = []

    mock_service.get_entity_context.return_value = mock_context

    # Mock health_check
    mock_service.health_check.return_value = {"connected": True}

    return mock_service


@pytest.fixture
def mock_embedding_service():
    """Create a mock EmbeddingService for testing.

    Returns:
        MagicMock: Mocked EmbeddingService instance.
    """
    mock_service = MagicMock()

    mock_result = MagicMock()
    mock_result.embedding = [0.1] * 1536  # 1536-dimensional embedding
    mock_result.token_count = 10

    mock_service.embed_query.return_value = mock_result

    return mock_service


# =============================================================================
# DTO Fixtures
# =============================================================================


@pytest.fixture
def sample_search_query() -> SearchQuery:
    """Create a sample SearchQuery for testing.

    Returns:
        SearchQuery: Sample query with text and embedding.
    """
    return SearchQuery(
        text="What is machine learning?",
        embedding=[0.1] * 1536,
        user_id=None,
    )


@pytest.fixture
def sample_search_query_no_embedding() -> SearchQuery:
    """Create a sample SearchQuery without embedding.

    Returns:
        SearchQuery: Sample query with text only.
    """
    return SearchQuery(
        text="What is machine learning?",
        embedding=None,
        user_id=None,
    )


@pytest.fixture
def sample_search_query_with_user() -> SearchQuery:
    """Create a sample SearchQuery with user_id filter.

    Returns:
        SearchQuery: Sample query with user_id.
    """
    return SearchQuery(
        text="What is machine learning?",
        embedding=[0.1] * 1536,
        user_id=str(uuid4()),
    )


@pytest.fixture
def sample_hybrid_search_request() -> HybridSearchRequest:
    """Create a sample HybridSearchRequest for testing.

    Returns:
        HybridSearchRequest: Sample request with default options.
    """
    return HybridSearchRequest(
        query="What is machine learning?",
        top_k=10,
        use_vector=True,
        use_keyword=True,
        use_graph=False,
        filters={},
        rrf_k=60,
    )


@pytest.fixture
def sample_hybrid_search_request_all_retrievers() -> HybridSearchRequest:
    """Create a sample HybridSearchRequest with all retrievers enabled.

    Returns:
        HybridSearchRequest: Sample request with all retrievers.
    """
    return HybridSearchRequest(
        query="Explain deep learning",
        top_k=5,
        use_vector=True,
        use_keyword=True,
        use_graph=True,
        filters={},
        rrf_k=60,
    )


@pytest.fixture
def sample_advanced_search_request() -> AdvancedSearchRequest:
    """Create a sample AdvancedSearchRequest for testing.

    Returns:
        AdvancedSearchRequest: Sample request with filters.
    """
    return AdvancedSearchRequest(
        query="What is machine learning?",
        top_k=10,
        use_vector=True,
        use_keyword=True,
        use_graph=False,
        user_id=str(uuid4()),
        document_ids=[str(uuid4()), str(uuid4())],
        expand_context=False,
        context_window=1,
    )


@pytest.fixture
def sample_retriever_result() -> RetrieverResult:
    """Create a sample RetrieverResult for testing.

    Returns:
        RetrieverResult: Sample result with one item.
    """
    chunk_id = str(uuid4())
    doc_id = str(uuid4())

    return RetrieverResult(
        retriever_name="vector",
        items=[
            {
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "text": "Machine learning is a subset of artificial intelligence.",
                "score": 0.85,
                "source": "ai_guide.pdf",
                "metadata": {"chunk_index": 0, "page_number": 1},
            }
        ],
        query_time_ms=50.0,
        total=1,
    )


@pytest.fixture
def sample_retriever_results() -> dict[str, RetrieverResult]:
    """Create multiple RetrieverResults for fusion testing.

    Returns:
        dict[str, RetrieverResult]: Results from multiple retrievers.
    """
    chunk_id_1 = str(uuid4())
    chunk_id_2 = str(uuid4())
    doc_id_1 = str(uuid4())
    doc_id_2 = str(uuid4())

    vector_result = RetrieverResult(
        retriever_name="vector",
        items=[
            {
                "chunk_id": chunk_id_1,
                "document_id": doc_id_1,
                "text": "Machine learning basics.",
                "score": 0.90,
                "source": "ml_book.pdf",
                "metadata": {"chunk_index": 0},
            },
            {
                "chunk_id": chunk_id_2,
                "document_id": doc_id_2,
                "text": "Deep learning fundamentals.",
                "score": 0.85,
                "source": "dl_book.pdf",
                "metadata": {"chunk_index": 0},
            },
        ],
        query_time_ms=30.0,
        total=2,
    )

    keyword_result = RetrieverResult(
        retriever_name="keyword",
        items=[
            {
                "chunk_id": chunk_id_1,
                "document_id": doc_id_1,
                "text": "Machine learning basics.",
                "score": 0.75,
                "source": "ml_book.pdf",
                "metadata": {"chunk_index": 0},
            },
            {
                "chunk_id": str(uuid4()),
                "document_id": str(uuid4()),
                "text": "AI and machine learning applications.",
                "score": 0.70,
                "source": "ai_article.pdf",
                "metadata": {"chunk_index": 0},
            },
        ],
        query_time_ms=20.0,
        total=2,
    )

    return {
        "vector": vector_result,
        "keyword": keyword_result,
    }


@pytest.fixture
def sample_ranked_result() -> RankedResult:
    """Create a sample RankedResult for testing.

    Returns:
        RankedResult: Sample ranked result.
    """
    return RankedResult(
        chunk_id=str(uuid4()),
        document_id=str(uuid4()),
        text="Machine learning is a subset of artificial intelligence.",
        score=0.85,
        source="ai_guide.pdf",
        metadata={"chunk_index": 0, "page_number": 1},
        retriever_scores={"vector": 0.90, "keyword": 0.75},
    )


@pytest.fixture
def sample_search_response() -> SearchResponse:
    """Create a sample SearchResponse for testing.

    Returns:
        SearchResponse: Sample response with results.
    """
    return SearchResponse(
        results=[
            SearchResultItem(
                chunk_id=str(uuid4()),
                document_id=str(uuid4()),
                text="Machine learning is a subset of artificial intelligence.",
                score=0.85,
                source="ai_guide.pdf",
                metadata={"chunk_index": 0, "page_number": 1},
                retriever_scores={"vector": 0.90},
            )
        ],
        total=1,
        query_time_ms=100.0,
        retrievers_used=["vector"],
    )


@pytest.fixture
def sample_search_config() -> SearchConfig:
    """Create a sample SearchConfig for testing.

    Returns:
        SearchConfig: Sample configuration.
    """
    return SearchConfig(
        default_top_k=10,
        default_rrf_k=60,
        max_query_length=500,
        min_query_length=2,
        vector_weight=0.4,
        keyword_weight=0.3,
        graph_weight=0.3,
        enable_suggestions=True,
        context_expansion_enabled=False,
        context_window=1,
    )


# =============================================================================
# Search Service Fixtures
# =============================================================================


@pytest.fixture
def search_service_with_mocks(
    mock_milvus_service,
    mock_neo4j_service,
    mock_embedding_service,
):
    """Create a SearchService with all external services mocked.

    Args:
        mock_milvus_service: Mock MilvusService fixture.
        mock_neo4j_service: Mock Neo4jService fixture.
        mock_embedding_service: Mock EmbeddingService fixture.

    Yields:
        SearchService: Service instance with mocked dependencies.
    """
    with (
        patch(
            "apps.document_rag_search.services.search_service.EmbeddingService",
            return_value=mock_embedding_service,
        ),
        patch(
            "apps.document_rag_search.retrievers.vector_retriever.MilvusService",
            return_value=mock_milvus_service,
        ),
        patch(
            "apps.document_rag_search.retrievers.keyword_retriever.DocumentChunk",
        ),
        patch(
            "apps.document_rag_search.retrievers.graph_retriever.Neo4jService",
            return_value=mock_neo4j_service,
        ),
    ):
        from apps.document_rag_search.services import SearchService

        yield SearchService()


@pytest.fixture
def vector_retriever_with_mock(mock_milvus_service, mock_embedding_service):
    """Create a VectorRetriever with mocked dependencies.

    Args:
        mock_milvus_service: Mock MilvusService fixture.
        mock_embedding_service: Mock EmbeddingService fixture.

    Yields:
        VectorRetriever: Retriever instance with mocked dependencies.
    """
    with (
        patch(
            "apps.document_rag_search.retrievers.vector_retriever.MilvusService",
            return_value=mock_milvus_service,
        ),
        patch(
            "apps.document_rag_search.retrievers.vector_retriever.EmbeddingService",
            return_value=mock_embedding_service,
        ),
    ):
        from apps.document_rag_search.retrievers import VectorRetriever

        yield VectorRetriever()


@pytest.fixture
def keyword_retriever_mock():
    """Create a KeywordRetriever with mocked Django models.

    Yields:
        KeywordRetriever: Retriever instance.
    """
    from apps.document_rag_search.retrievers import KeywordRetriever

    yield KeywordRetriever()


@pytest.fixture
def graph_retriever_with_mock(mock_neo4j_service):
    """Create a GraphRetriever with mocked Neo4jService.

    Args:
        mock_neo4j_service: Mock Neo4jService fixture.

    Yields:
        GraphRetriever: Retriever instance with mocked dependencies.
    """
    with patch(
        "apps.document_rag_search.retrievers.graph_retriever.Neo4jService",
        return_value=mock_neo4j_service,
    ):
        from apps.document_rag_search.retrievers import GraphRetriever

        yield GraphRetriever()


# =============================================================================
# API Test Fixtures
# =============================================================================


@pytest.fixture
def api_client() -> APIClient:
    """Unauthenticated DRF API client.

    Returns:
        APIClient: Unauthenticated API client instance.
    """
    return APIClient()


@pytest.fixture
def authenticated_client(api_client: APIClient, test_user) -> APIClient:
    """API client authenticated as test_user via JWT.

    Args:
        api_client: Unauthenticated API client.
        test_user: Test user fixture.

    Returns:
        APIClient: Authenticated API client instance.
    """
    refresh = RefreshToken.for_user(test_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


# =============================================================================
# Mock Document Chunk Fixture
# =============================================================================


@pytest.fixture
def mock_document_chunk():
    """Create a mock DocumentChunk for testing without database.

    Returns:
        MagicMock: Mocked DocumentChunk instance.
    """
    mock_chunk = MagicMock()
    mock_chunk.id = uuid4()
    mock_chunk.document_id = uuid4()
    mock_chunk.content = "Sample chunk content about machine learning algorithms."
    mock_chunk.chunk_index = 0
    mock_chunk.char_count = 50
    mock_chunk.page_number = 1
    mock_chunk.document.original_name = "test_document.pdf"

    return mock_chunk


@pytest.fixture
def mock_document():
    """Create a mock Document for testing without database.

    Returns:
        MagicMock: Mocked Document instance.
    """
    mock_doc = MagicMock()
    mock_doc.id = uuid4()
    mock_doc.original_name = "test_document.pdf"
    mock_doc.file_type = "pdf"

    return mock_doc


# =============================================================================
# Pytest Markers Configuration
# =============================================================================


def pytest_configure(config):
    """Configure custom pytest markers for the search module.

    Args:
        config: Pytest config object.
    """
    config.addinivalue_line(
        "markers",
        "unit: mark test as unit test (mocked external services)",
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires real services)",
    )
    config.addinivalue_line(
        "markers",
        "api: mark test as API endpoint test",
    )
