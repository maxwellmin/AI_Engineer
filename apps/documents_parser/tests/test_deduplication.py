"""
Tests for deduplication service.
"""

from __future__ import annotations

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.documents_parser.services import deduplication
from apps.documents_parser.tests.factories import DocumentFactory


@pytest.mark.django_db
class TestCheckDuplicate:
    """Tests for check_duplicate function."""

    def test_returns_not_duplicate_for_new_file(self, test_user):
        """Should indicate no duplicate for new file hash."""
        result = deduplication.check_duplicate(
            user=test_user,
            file_hash="a" * 64,  # Dummy hash
        )

        assert result.is_duplicate is False
        assert result.existing_document_id is None
        assert result.existing_document_name is None

    def test_returns_duplicate_for_existing_file(self, test_user):
        """Should indicate duplicate for existing file hash."""
        # Create existing document with known hash
        file_hash = "b" * 64
        existing_doc = DocumentFactory(user=test_user, file_hash=file_hash)

        result = deduplication.check_duplicate(
            user=test_user,
            file_hash=file_hash,
        )

        assert result.is_duplicate is True
        assert str(result.existing_document_id) == str(existing_doc.id)
        assert result.existing_document_name == existing_doc.original_name

    def test_same_hash_different_user_not_duplicate(self, test_user):
        """Should not be duplicate for same hash but different user."""
        # Create document for another user
        other_user = UserFactory.create_user(username="otheruser")
        file_hash = "c" * 64
        DocumentFactory(user=other_user, file_hash=file_hash)

        result = deduplication.check_duplicate(
            user=test_user,
            file_hash=file_hash,
        )

        assert result.is_duplicate is False


@pytest.mark.django_db
class TestGetDocumentsByHash:
    """Tests for get_documents_by_hash function."""

    def test_returns_all_documents_with_hash(self, test_user):
        """Should return all documents with given hash."""
        file_hash = "d" * 64

        # Create documents with same hash for different users
        doc1 = DocumentFactory(user=test_user, file_hash=file_hash)
        other_user = UserFactory.create_user(username="otheruser")
        doc2 = DocumentFactory(user=other_user, file_hash=file_hash)

        result = deduplication.get_documents_by_hash(file_hash=file_hash)

        assert result.count() == 2
        assert doc1 in result
        assert doc2 in result

    def test_returns_empty_for_nonexistent_hash(self):
        """Should return empty queryset for non-existent hash."""
        result = deduplication.get_documents_by_hash(file_hash="e" * 64)

        assert result.count() == 0


@pytest.mark.django_db
class TestGetUserDocumentsByHash:
    """Tests for get_user_documents_by_hash function."""

    def test_returns_user_documents_with_hash(self, test_user):
        """Should return user's documents with given hash."""
        file_hash = "f" * 64
        doc = DocumentFactory(user=test_user, file_hash=file_hash)

        # Create same hash for different user
        other_user = UserFactory.create_user(username="otheruser")
        DocumentFactory(user=other_user, file_hash=file_hash)

        result = deduplication.get_user_documents_by_hash(
            user=test_user,
            file_hash=file_hash,
        )

        assert result.count() == 1
        assert doc in result

    def test_returns_empty_for_user_without_documents(self, test_user):
        """Should return empty queryset when user has no documents with hash."""
        # Create document for another user
        other_user = UserFactory.create_user(username="otheruser")
        DocumentFactory(user=other_user, file_hash="g" * 64)

        result = deduplication.get_user_documents_by_hash(
            user=test_user,
            file_hash="g" * 64,
        )

        assert result.count() == 0
