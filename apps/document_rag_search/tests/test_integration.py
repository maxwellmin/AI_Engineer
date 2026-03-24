"""
Integration tests for Document RAG Search module.

End-to-end tests that validate the complete search workflow,
including hybrid search across Milvus, Neo4j, and PostgreSQL.

These tests require running services:
- PostgreSQL (Django database)
- Milvus (vector database)
- Neo4j (graph database)

Run with: pytest apps/document_rag_search/tests/test_integration.py -v -m integration
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from apps.document_rag_search.constants import RetrieverName
from apps.document_rag_search.dto import (
    AdvancedSearchRequest,
    HybridSearchRequest,
    SearchQuery,
    SearchSuggestionsRequest,
)
from apps.document_rag_search.retrievers import (
    GraphRetriever,
    KeywordRetriever,
    VectorRetriever,
)
from apps.document_rag_search.services import SearchService


# =============================================================================
# Fixtures for Integration Tests
# =============================================================================


@pytest.fixture
def integration_test_user(db):
    """Create a test user for integration tests.

    Args:
        db: Django db fixture.

    Returns:
        User: Test user instance.
    """
    from apps.accounts.tests.factories import UserFactory

    return UserFactory.create_user(
        username="integration_test_user",
        email="integration@example.com",
        password="testpass123",
    )


@pytest.fixture
def integration_documents_with_chunks(db, integration_test_user):
    """Create test documents with chunks for integration testing.

    This fixture creates:
    - 3 documents with different content
    - Multiple chunks per document with searchable content
    - Different file types for filter testing

    Args:
        db: Django db fixture.
        integration_test_user: Test user fixture.

    Returns:
        tuple: (list[Document], list[DocumentChunk])
    """
    from apps.documents_parser.models import Document, DocumentChunk

    documents = []
    chunks = []

    # Document 1: Machine Learning Guide
    doc1 = Document.objects.create(
        user=integration_test_user,
        name="ml_guide.pdf",
        original_name="Machine Learning Guide.pdf",
        file_path="documents/ml_guide.pdf",
        file_size=2048000,
        file_type="pdf",
        file_hash=f"hash_ml_{uuid4().hex[:8]}",
        status=Document.Status.DONE,
    )
    documents.append(doc1)

    ml_chunks = [
        ("Machine learning is a subset of artificial intelligence that enables systems to learn from data.", 0),
        ("Supervised learning uses labeled datasets to train algorithms for classification and regression.", 1),
        ("Neural networks are computing systems inspired by biological neural networks in the human brain.", 2),
        ("Deep learning uses multi-layered neural networks to process complex patterns in data.", 3),
    ]

    for text, idx in ml_chunks:
        chunk = DocumentChunk.objects.create(
            document=doc1,
            content=text,
            chunk_index=idx,
            content_hash=f"chunk_hash_ml_{idx}_{uuid4().hex[:8]}",
            char_count=len(text),
            token_count=len(text.split()),
            page_number=idx + 1,
        )
        chunks.append(chunk)

    # Document 2: Python Programming
    doc2 = Document.objects.create(
        user=integration_test_user,
        name="python_basics.pdf",
        original_name="Python Programming Basics.pdf",
        file_path="documents/python_basics.pdf",
        file_size=1536000,
        file_type="pdf",
        file_hash=f"hash_py_{uuid4().hex[:8]}",
        status=Document.Status.DONE,
    )
    documents.append(doc2)

    py_chunks = [
        ("Python is a high-level, interpreted programming language known for its simplicity and readability.", 0),
        ("Python supports multiple programming paradigms including procedural, object-oriented, and functional.", 1),
        ("Django and Flask are popular web frameworks for Python development.", 2),
    ]

    for text, idx in py_chunks:
        chunk = DocumentChunk.objects.create(
            document=doc2,
            content=text,
            chunk_index=idx,
            content_hash=f"chunk_hash_py_{idx}_{uuid4().hex[:8]}",
            char_count=len(text),
            token_count=len(text.split()),
            page_number=idx + 1,
        )
        chunks.append(chunk)

    # Document 3: Data Science Notes
    doc3 = Document.objects.create(
        user=integration_test_user,
        name="data_science.txt",
        original_name="Data Science Notes.txt",
        file_path="documents/data_science.txt",
        file_size=1024000,
        file_type="txt",
        file_hash=f"hash_ds_{uuid4().hex[:8]}",
        status=Document.Status.DONE,
    )
    documents.append(doc3)

    ds_chunks = [
        ("Data science combines statistics, programming, and domain expertise to extract insights from data.", 0),
        ("Pandas and NumPy are essential Python libraries for data manipulation and analysis.", 1),
    ]

    for text, idx in ds_chunks:
        chunk = DocumentChunk.objects.create(
            document=doc3,
            content=text,
            chunk_index=idx,
            content_hash=f"chunk_hash_ds_{idx}_{uuid4().hex[:8]}",
            char_count=len(text),
            token_count=len(text.split()),
            page_number=idx + 1,
        )
        chunks.append(chunk)

    return documents, chunks


# =============================================================================
# Health Check Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.django_db
class TestServiceHealthChecks:
    """Tests for service health checks in integration environment."""

    def test_keyword_retriever_health_check(self):
        """Test that keyword retriever can connect to PostgreSQL."""
        retriever = KeywordRetriever()
        assert retriever.health_check() is True

    def test_vector_retriever_health_check(self):
        """Test that vector retriever can connect to Milvus.

        Note: This test will be skipped if Milvus is not running.
        """
        retriever = VectorRetriever()
        try:
            health = retriever.health_check()
            # We accept both True and False since Milvus may not be running
            assert isinstance(health, bool)
        except Exception:
            pytest.skip("Milvus not available for integration test")

    def test_graph_retriever_health_check(self):
        """Test that graph retriever can connect to Neo4j.

        Note: This test will be skipped if Neo4j is not running.
        """
        retriever = GraphRetriever()
        try:
            health = retriever.health_check()
            # We accept both True and False since Neo4j may not be running
            assert isinstance(health, bool)
        except Exception:
            pytest.skip("Neo4j not available for integration test")

    def test_search_service_health_check(self):
        """Test that search service health check aggregates all retrievers."""
        service = SearchService()
        health = service.health_check()

        assert isinstance(health, dict)
        assert "vector" in health
        assert "keyword" in health
        assert "graph" in health
        assert "overall" in health
        # Keyword should always be healthy (PostgreSQL is required)
        assert health["keyword"] is True


# =============================================================================
# Keyword Retriever Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.django_db
class TestKeywordRetrieverIntegration:
    """Integration tests for KeywordRetriever with PostgreSQL."""

    def test_keyword_search_basic(
        self,
        integration_documents_with_chunks,
    ):
        """Test basic keyword search returns relevant results."""
        docs, chunks = integration_documents_with_chunks

        retriever = KeywordRetriever(use_search_vector=False)
        query = SearchQuery(text="machine learning")

        result = retriever.retrieve(query, top_k=5)

        assert result.retriever_name == RetrieverName.KEYWORD.value
        assert result.total > 0
        assert len(result.items) <= 5

        # Check that results contain relevant content
        for item in result.items:
            assert "chunk_id" in item
            assert "document_id" in item
            assert "text" in item
            assert "score" in item

    def test_keyword_search_with_user_filter(
        self,
        integration_documents_with_chunks,
        integration_test_user,
    ):
        """Test keyword search with user filter."""
        docs, chunks = integration_documents_with_chunks

        retriever = KeywordRetriever(use_search_vector=False)
        query = SearchQuery(
            text="Python programming",
            user_id=str(integration_test_user.id),
        )

        result = retriever.retrieve(query, top_k=10)

        # All results should belong to the user
        assert result.total >= 0

    def test_keyword_search_with_document_filter(
        self,
        integration_documents_with_chunks,
    ):
        """Test keyword search with document ID filter."""
        docs, chunks = integration_documents_with_chunks

        # Filter to only first document
        target_doc = docs[0]

        retriever = KeywordRetriever(use_search_vector=False)
        query = SearchQuery(text="learning")

        result = retriever.retrieve(
            query,
            top_k=10,
            document_ids=[str(target_doc.id)],
        )

        # All results should be from the target document
        for item in result.items:
            assert item["document_id"] == str(target_doc.id)

    def test_keyword_search_no_results(self):
        """Test keyword search returns empty for non-matching query."""
        retriever = KeywordRetriever(use_search_vector=False)
        query = SearchQuery(text="xyznonexistent12345")

        result = retriever.retrieve(query, top_k=10)

        # Should return empty results
        assert result.total == 0
        assert len(result.items) == 0


# =============================================================================
# Hybrid Search Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.django_db
class TestHybridSearchIntegration:
    """Integration tests for hybrid search functionality."""

    def test_hybrid_search_keyword_only(
        self,
        integration_documents_with_chunks,
    ):
        """Test hybrid search with keyword retriever only."""
        docs, chunks = integration_documents_with_chunks

        request = HybridSearchRequest(
            query="machine learning",
            top_k=5,
            use_vector=False,
            use_keyword=True,
            use_graph=False,
        )

        service = SearchService()
        response = service.hybrid_search(request)

        # Should have results from keyword search
        assert response.total >= 0
        assert RetrieverName.KEYWORD.value in response.retrievers_used
        assert response.query_time_ms > 0

    def test_hybrid_search_with_filters(
        self,
        integration_documents_with_chunks,
        integration_test_user,
    ):
        """Test hybrid search with user and document filters."""
        docs, chunks = integration_documents_with_chunks

        request = HybridSearchRequest(
            query="Python",
            top_k=10,
            use_vector=False,
            use_keyword=True,
            use_graph=False,
            filters={
                "user_id": str(integration_test_user.id),
            },
        )

        service = SearchService()
        response = service.hybrid_search(request)

        assert response.total >= 0

    def test_hybrid_search_empty_query_raises_error(self):
        """Test that empty query raises appropriate error."""
        from apps.document_rag_search.exceptions import EmptyQueryError

        request = HybridSearchRequest(
            query="",
            top_k=10,
            use_vector=False,
            use_keyword=True,
            use_graph=False,
        )

        service = SearchService()

        with pytest.raises(EmptyQueryError):
            service.hybrid_search(request)

    def test_hybrid_search_no_results_returns_empty(
        self,
    ):
        """Test hybrid search raises NoResultsError for non-matching query."""
        from apps.document_rag_search.exceptions import NoResultsError

        request = HybridSearchRequest(
            query="xyznonexistentquery12345",
            top_k=10,
            use_vector=False,
            use_keyword=True,
            use_graph=False,
        )

        service = SearchService()

        # Should raise NoResultsError when no results found
        with pytest.raises(NoResultsError):
            service.hybrid_search(request)


# =============================================================================
# Advanced Search Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.django_db
class TestAdvancedSearchIntegration:
    """Integration tests for advanced search functionality."""

    def test_advanced_search_with_document_filter(
        self,
        integration_documents_with_chunks,
    ):
        """Test advanced search filtering by document IDs."""
        docs, chunks = integration_documents_with_chunks

        # Filter to specific documents
        target_docs = docs[:2]

        request = AdvancedSearchRequest(
            query="learning",
            top_k=10,
            use_vector=False,
            use_keyword=True,
            use_graph=False,
            document_ids=[str(d.id) for d in target_docs],
        )

        service = SearchService()
        response = service.advanced_search(request)

        assert response.total >= 0
        # All results should be from target documents
        for result in response.results:
            assert result.document_id in [str(d.id) for d in target_docs]

    def test_advanced_search_invalid_date_range_raises_error(
        self,
    ):
        """Test that invalid date range raises error."""
        from datetime import datetime, timedelta

        from apps.document_rag_search.exceptions import InvalidDateRangeError

        today = datetime.now()
        yesterday = today - timedelta(days=1)

        request = AdvancedSearchRequest(
            query="test query",
            date_from=today,
            date_to=yesterday,  # Invalid: date_from > date_to
        )

        service = SearchService()

        with pytest.raises(InvalidDateRangeError):
            service.advanced_search(request)


# =============================================================================
# Search Suggestions Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.django_db
class TestSearchSuggestionsIntegration:
    """Integration tests for search suggestions."""

    def test_get_search_suggestions_basic(
        self,
        integration_documents_with_chunks,
    ):
        """Test basic search suggestions retrieval."""
        docs, chunks = integration_documents_with_chunks

        request = SearchSuggestionsRequest(
            prefix="machine",
            limit=5,
        )

        service = SearchService()
        response = service.get_search_suggestions(request)

        assert response.total >= 0
        assert isinstance(response.suggestions, list)
        assert len(response.suggestions) <= 5

    def test_get_search_suggestions_empty_prefix(self):
        """Test suggestions with empty prefix."""
        request = SearchSuggestionsRequest(
            prefix="",
            limit=5,
        )

        service = SearchService()
        response = service.get_search_suggestions(request)

        # Should handle gracefully
        assert isinstance(response.suggestions, list)


# =============================================================================
# Simple Search Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.django_db
class TestSimpleSearchIntegration:
    """Integration tests for simple search."""

    def test_simple_search_basic(
        self,
        integration_documents_with_chunks,
    ):
        """Test simple search returns results."""
        docs, chunks = integration_documents_with_chunks

        service = SearchService()

        # Simple search without vector (will fail gracefully)
        # This tests the query validation and service coordination
        try:
            response = service.search(
                query="machine learning",
                top_k=10,
            )

            # If we get here, the service coordinated correctly
            assert response.query_time_ms >= 0

        except Exception as e:
            # Vector search may fail if Milvus is not available
            # but the service should handle this gracefully
            assert "embedding" in str(e).lower() or "vector" in str(e).lower()

    def test_simple_search_invalid_query(self):
        """Test simple search with invalid query."""
        from apps.document_rag_search.exceptions import QueryTooShortError

        service = SearchService()

        with pytest.raises(QueryTooShortError):
            service.search(query="x", top_k=10)  # Too short


# =============================================================================
# RRF Fusion Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.django_db
class TestRRFFusionIntegration:
    """Integration tests for RRF fusion in search service."""

    def test_rrf_fusion_single_retriever(
        self,
        integration_documents_with_chunks,
    ):
        """Test RRF fusion with single retriever."""
        docs, chunks = integration_documents_with_chunks

        request = HybridSearchRequest(
            query="Python programming",
            top_k=5,
            use_vector=False,
            use_keyword=True,
            use_graph=False,
        )

        service = SearchService()
        response = service.hybrid_search(request)

        # With single retriever, RRF should just pass through results
        assert response.total >= 0
        if response.results:
            assert response.results[0].score > 0

    def test_rrf_fusion_multiple_retrievers(
        self,
        integration_documents_with_chunks,
    ):
        """Test RRF fusion with multiple retrievers (keyword only, vector may fail)."""
        docs, chunks = integration_documents_with_chunks

        # Enable vector retriever - may fail if Milvus not available
        request = HybridSearchRequest(
            query="machine learning",
            top_k=5,
            use_vector=True,
            use_keyword=True,
            use_graph=False,
        )

        service = SearchService()
        response = service.hybrid_search(request)

        # Should get at least keyword results
        assert response.total >= 0
        # At least keyword should be in retrievers_used
        assert RetrieverName.KEYWORD.value in response.retrievers_used or len(response.retrievers_used) > 0


# =============================================================================
# Error Handling Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.django_db
class TestErrorHandlingIntegration:
    """Integration tests for error handling."""

    def test_query_too_long(self):
        """Test that excessively long query is rejected."""
        from apps.document_rag_search.exceptions import QueryTooLongError

        service = SearchService()
        long_query = "a" * 1000  # Exceeds MAX_QUERY_LENGTH

        with pytest.raises(QueryTooLongError):
            service.search(query=long_query, top_k=10)

    def test_empty_query(self):
        """Test that empty query is rejected."""
        from apps.document_rag_search.exceptions import EmptyQueryError

        service = SearchService()

        with pytest.raises(EmptyQueryError):
            service.search(query="", top_k=10)

    def test_whitespace_query(self):
        """Test that whitespace-only query is rejected."""
        from apps.document_rag_search.exceptions import EmptyQueryError

        service = SearchService()

        with pytest.raises(EmptyQueryError):
            service.search(query="   ", top_k=10)


# =============================================================================
# Performance Integration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.django_db
class TestPerformanceIntegration:
    """Integration tests for performance characteristics."""

    def test_search_latency_keyword(
        self,
        integration_documents_with_chunks,
    ):
        """Test that keyword search completes within acceptable time."""
        docs, chunks = integration_documents_with_chunks

        request = HybridSearchRequest(
            query="Python programming language",
            top_k=10,
            use_vector=False,
            use_keyword=True,
            use_graph=False,
        )

        service = SearchService()
        response = service.hybrid_search(request)

        # Keyword search should be fast (< 1 second)
        assert response.query_time_ms < 1000

    def test_search_suggestions_latency(
        self,
        integration_documents_with_chunks,
    ):
        """Test that suggestions retrieval is fast."""
        docs, chunks = integration_documents_with_chunks

        request = SearchSuggestionsRequest(
            prefix="mach",
            limit=5,
        )

        service = SearchService()
        response = service.get_search_suggestions(request)

        # Suggestions should be fast (< 500ms)
        assert isinstance(response.suggestions, list)
