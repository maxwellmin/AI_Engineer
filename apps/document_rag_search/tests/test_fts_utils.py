"""
Tests for full-text search utility functions.

This module tests the FTS utility functions in fts_utils.py,
including search functions, batch updates, and statistics.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.db import connection

from apps.document_rag_search.constants import DEFAULT_FTS_CONFIG, DEFAULT_TOP_K
from apps.document_rag_search.retrievers.fts_utils import (
    batch_update_search_vectors,
    get_fts_stats,
    get_search_queryset,
    has_search_vector_field,
    search_chunks_by_keyword,
    search_chunks_by_like,
    update_search_vector,
)
from apps.documents_parser.models import Document, DocumentChunk


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def test_user(db):
    """Create a test user."""
    User = get_user_model()
    return User.objects.create_user(
        username="test_fts_user",
        email="test_fts@example.com",
        password="testpass123",
    )


@pytest.fixture
def test_document(db, test_user):
    """Create a test document."""
    return Document.objects.create(
        user=test_user,
        name="test_fts_document.pdf",
        original_name="Test FTS Document.pdf",
        file_path="documents/test_fts_document.pdf",
        file_size=1024000,
        file_type="pdf",
        file_hash="test_fts_hash_123",
        status=Document.Status.DONE,
    )


@pytest.fixture
def test_chunks(db, test_document):
    """Create test document chunks with various content."""
    chunks = [
        DocumentChunk.objects.create(
            document=test_document,
            chunk_index=i,
            content=content,
            content_hash=f"hash_{i}",
            char_count=len(content),
        )
        for i, content in enumerate(
            [
                "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
                "Deep learning uses neural networks with multiple layers to process complex patterns.",
                "Natural language processing allows computers to understand and generate human language.",
                "Computer vision enables machines to interpret and analyze visual information from the world.",
                "Reinforcement learning trains agents through rewards and penalties in an environment.",
            ]
        )
    ]
    return chunks


# =============================================================================
# has_search_vector_field Tests
# =============================================================================


class TestHasSearchVectorField:
    """Tests for has_search_vector_field function."""

    def test_returns_true_when_field_exists(self):
        """Test that function returns True when search_vector field exists."""
        result = has_search_vector_field()
        assert result is True

    @patch("apps.document_rag_search.retrievers.fts_utils.DocumentChunk")
    def test_returns_false_when_field_missing(self, mock_chunk_model):
        """Test that function returns False when search_vector field doesn't exist."""
        del mock_chunk_model.search_vector
        result = has_search_vector_field()
        assert result is False


# =============================================================================
# search_chunks_by_keyword Tests
# =============================================================================


@pytest.mark.django_db
class TestSearchChunksByKeyword:
    """Tests for search_chunks_by_keyword function."""

    def test_returns_empty_list_for_empty_query(self):
        """Test that empty query returns empty list."""
        result = search_chunks_by_keyword(query="")
        assert result == []

    def test_returns_empty_list_for_whitespace_query(self):
        """Test that whitespace-only query returns empty list."""
        result = search_chunks_by_keyword(query="   ")
        assert result == []

    def test_returns_results_for_matching_query(self, test_chunks):
        """Test that matching query returns results."""
        # First update search vectors for the test chunks
        for chunk in test_chunks:
            update_search_vector(str(chunk.id))

        result = search_chunks_by_keyword(query="machine learning", top_k=5)

        assert len(result) > 0
        assert all("chunk_id" in r for r in result)
        assert all("document_id" in r for r in result)
        assert all("text" in r for r in result)
        assert all("score" in r for r in result)

    def test_filters_by_user_id(self, test_chunks, test_user):
        """Test that user_id filter is applied correctly."""
        # Update search vectors
        for chunk in test_chunks:
            update_search_vector(str(chunk.id))

        result = search_chunks_by_keyword(
            query="machine learning",
            user_id=str(test_user.id),
            top_k=5,
        )

        # All results should belong to the user
        assert all(r["document_id"] for r in result)

    def test_filters_by_document_ids(self, test_chunks, test_document):
        """Test that document_ids filter is applied correctly."""
        # Update search vectors
        for chunk in test_chunks:
            update_search_vector(str(chunk.id))

        result = search_chunks_by_keyword(
            query="machine learning",
            document_ids=[str(test_document.id)],
            top_k=5,
        )

        # All results should be from the specified document
        assert all(r["document_id"] == str(test_document.id) for r in result)

    def test_respects_top_k_limit(self, test_chunks):
        """Test that top_k parameter limits results."""
        # Update search vectors
        for chunk in test_chunks:
            update_search_vector(str(chunk.id))

        result = search_chunks_by_keyword(query="learning", top_k=2)

        assert len(result) <= 2

    def test_applies_min_rank_filter(self, test_chunks):
        """Test that min_rank filters low-scoring results."""
        # Update search vectors
        for chunk in test_chunks:
            update_search_vector(str(chunk.id))

        # Use a high min_rank to filter results
        result = search_chunks_by_keyword(
            query="learning",
            min_rank=0.5,
            top_k=10,
        )

        # With high min_rank, we might get fewer or no results
        assert all(r["score"] >= 0.5 for r in result)

    def test_returns_correct_result_structure(self, test_chunks):
        """Test that result has correct structure."""
        # Update search vectors
        for chunk in test_chunks:
            update_search_vector(str(chunk.id))

        result = search_chunks_by_keyword(query="machine learning", top_k=1)

        if result:
            item = result[0]
            assert "chunk_id" in item
            assert "document_id" in item
            assert "text" in item
            assert "score" in item
            assert "source" in item
            assert "metadata" in item
            assert "chunk_index" in item["metadata"]


# =============================================================================
# search_chunks_by_like Tests
# =============================================================================


@pytest.mark.django_db
class TestSearchChunksByLike:
    """Tests for search_chunks_by_like function (fallback search)."""

    def test_returns_empty_list_for_empty_query(self):
        """Test that empty query returns empty list."""
        result = search_chunks_by_like(query="")
        assert result == []

    def test_returns_empty_list_for_whitespace_query(self):
        """Test that whitespace-only query returns empty list."""
        result = search_chunks_by_like(query="   ")
        assert result == []

    def test_returns_results_for_matching_query(self, test_chunks):
        """Test that matching query returns results using LIKE."""
        result = search_chunks_by_like(query="machine learning", top_k=5)

        assert len(result) > 0
        assert all("chunk_id" in r for r in result)
        assert all("score" in r for r in result)

    def test_respects_top_k_limit(self, test_chunks):
        """Test that top_k parameter limits results."""
        result = search_chunks_by_like(query="learning", top_k=2)

        assert len(result) <= 2

    def test_filters_by_user_id(self, test_chunks, test_user):
        """Test that user_id filter is applied correctly."""
        result = search_chunks_by_like(
            query="machine learning",
            user_id=str(test_user.id),
            top_k=5,
        )

        assert all(r["document_id"] for r in result)

    def test_filters_by_document_ids(self, test_chunks, test_document):
        """Test that document_ids filter is applied correctly."""
        result = search_chunks_by_like(
            query="machine learning",
            document_ids=[str(test_document.id)],
            top_k=5,
        )

        assert all(r["document_id"] == str(test_document.id) for r in result)

    def test_calculates_term_frequency_score(self, test_chunks):
        """Test that LIKE search calculates score based on term frequency."""
        result = search_chunks_by_like(query="learning", top_k=5)

        # Scores should be positive integers (term frequency counts)
        assert all(r["score"] > 0 for r in result)

    def test_handles_short_terms(self, test_chunks):
        """Test that terms shorter than 2 chars are ignored."""
        # "a" is a short term that should be ignored
        result = search_chunks_by_like(query="a", top_k=5)

        # Should return empty because "a" is too short
        assert result == []


# =============================================================================
# get_search_queryset Tests
# =============================================================================


@pytest.mark.django_db
class TestGetSearchQueryset:
    """Tests for get_search_queryset function."""

    def test_returns_queryset_for_valid_query(self, test_chunks):
        """Test that valid query returns a queryset."""
        # Update search vectors
        for chunk in test_chunks:
            update_search_vector(str(chunk.id))

        queryset = get_search_queryset(query="machine learning")

        assert queryset is not None
        assert hasattr(queryset, "count")

    def test_returns_empty_queryset_for_empty_query(self):
        """Test that empty query returns empty queryset."""
        queryset = get_search_queryset(query="")

        assert queryset.count() == 0

    def test_can_chain_filters(self, test_chunks):
        """Test that returned queryset can be chained with filters."""
        # Update search vectors
        for chunk in test_chunks:
            update_search_vector(str(chunk.id))

        queryset = get_search_queryset(query="learning")
        filtered = queryset.filter(char_count__gt=50)

        assert hasattr(filtered, "count")


# =============================================================================
# update_search_vector Tests
# =============================================================================


@pytest.mark.django_db
class TestUpdateSearchVector:
    """Tests for update_search_vector function."""

    def test_updates_single_chunk(self, test_chunks):
        """Test that single chunk search_vector is updated."""
        chunk = test_chunks[0]

        result = update_search_vector(str(chunk.id))

        assert result is True

        # Refresh from database
        chunk.refresh_from_db()
        assert chunk.search_vector is not None

    def test_returns_false_for_invalid_chunk_id(self):
        """Test that invalid chunk_id returns False."""
        result = update_search_vector("00000000-0000-0000-0000-000000000000")

        assert result is False

    def test_uses_custom_fts_config(self, test_chunks):
        """Test that custom FTS config is used."""
        chunk = test_chunks[0]

        result = update_search_vector(str(chunk.id), fts_config="english")

        assert result is True


# =============================================================================
# batch_update_search_vectors Tests
# =============================================================================


@pytest.mark.django_db
class TestBatchUpdateSearchVectors:
    """Tests for batch_update_search_vectors function."""

    def test_updates_specific_chunks(self, test_chunks):
        """Test that specific chunks are updated."""
        chunk_ids = [str(c.id) for c in test_chunks[:2]]

        count = batch_update_search_vectors(chunk_ids=chunk_ids)

        assert count == 2

        # Verify chunks are updated
        for chunk in test_chunks[:2]:
            chunk.refresh_from_db()
            assert chunk.search_vector is not None

    def test_updates_all_chunks_when_no_ids_provided(self, test_chunks):
        """Test that all chunks are updated when chunk_ids is None."""
        count = batch_update_search_vectors()

        assert count >= len(test_chunks)

    def test_uses_custom_batch_size(self, test_chunks):
        """Test that custom batch_size is respected."""
        chunk_ids = [str(c.id) for c in test_chunks]

        count = batch_update_search_vectors(
            chunk_ids=chunk_ids,
            batch_size=2,
        )

        assert count == len(test_chunks)

    def test_returns_zero_for_empty_chunk_list(self):
        """Test that empty chunk_ids list returns 0."""
        count = batch_update_search_vectors(chunk_ids=[])

        assert count == 0


# =============================================================================
# get_fts_stats Tests
# =============================================================================


@pytest.mark.django_db
class TestGetFtsStats:
    """Tests for get_fts_stats function."""

    def test_returns_correct_structure(self):
        """Test that stats have correct structure."""
        stats = get_fts_stats()

        assert "total_chunks" in stats
        assert "chunks_with_vector" in stats
        assert "coverage_percentage" in stats

    def test_returns_correct_counts(self, test_chunks):
        """Test that stats return correct counts."""
        # Update all chunks
        for chunk in test_chunks:
            update_search_vector(str(chunk.id))

        stats = get_fts_stats()

        assert stats["total_chunks"] >= len(test_chunks)
        assert stats["chunks_with_vector"] >= len(test_chunks)

    def test_coverage_percentage_calculation(self):
        """Test that coverage percentage is calculated correctly."""
        stats = get_fts_stats()

        if stats["total_chunks"] > 0:
            expected = (stats["chunks_with_vector"] / stats["total_chunks"]) * 100
            assert abs(stats["coverage_percentage"] - expected) < 0.1
        else:
            assert stats["coverage_percentage"] == 0.0


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.django_db
class TestFTSIntegration:
    """Integration tests for FTS functionality."""

    def test_search_after_update(self, test_chunks):
        """Test that search works after updating search_vector."""
        # Update all chunks
        for chunk in test_chunks:
            update_search_vector(str(chunk.id))

        # Search for "neural networks"
        result = search_chunks_by_keyword(query="neural networks", top_k=5)

        # Should find the deep learning chunk
        assert len(result) > 0
        assert any("neural" in r["text"].lower() for r in result)

    def test_different_fts_configs(self, test_chunks):
        """Test that different FTS configs work."""
        chunk = test_chunks[0]

        # Update with simple config
        update_search_vector(str(chunk.id), fts_config="simple")

        chunk.refresh_from_db()
        assert chunk.search_vector is not None

    def test_like_search_as_fallback(self, test_chunks):
        """Test that LIKE search works as fallback."""
        # Don't update search vectors - use LIKE search
        result = search_chunks_by_like(query="machine learning", top_k=5)

        assert len(result) > 0

    def test_empty_results_for_no_match(self, test_chunks):
        """Test that non-matching query returns empty results."""
        # Update all chunks
        for chunk in test_chunks:
            update_search_vector(str(chunk.id))

        result = search_chunks_by_keyword(
            query="xyznonexistent123",
            top_k=5,
        )

        assert len(result) == 0
