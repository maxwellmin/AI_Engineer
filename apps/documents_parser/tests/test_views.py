"""
API tests for document parser endpoints.

Tests cover upload, list, detail, and delete operations.
"""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.documents_parser.models import Document
from apps.documents_parser.tests.factories import DocumentChunkFactory, DocumentFactory


@pytest.mark.django_db
class TestDocumentUpload:
    """Tests for document upload endpoint."""

    @pytest.fixture
    def api_client(self) -> APIClient:
        """Return unauthenticated API client."""
        return APIClient()

    @pytest.fixture
    def test_user(self):
        """Create a test user."""
        return UserFactory.create_user(
            username="uploaduser",
            email="upload@example.com",
            password="uploadpass123",
        )

    @pytest.fixture
    def authenticated_client(self, api_client: APIClient, test_user) -> APIClient:
        """Return authenticated API client."""
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(test_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    @pytest.fixture
    def temp_media(self, settings, tmp_path):
        """Override MEDIA_ROOT with temporary directory."""
        settings.MEDIA_ROOT = tmp_path / "media"
        settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
        return settings.MEDIA_ROOT

    @pytest.fixture
    def sample_pdf(self):
        """Return minimal valid PDF content."""
        return SimpleUploadedFile(
            name="test.pdf",
            content=b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF",
            content_type="application/pdf",
        )

    @pytest.fixture
    def sample_txt(self):
        """Return sample TXT content."""
        return SimpleUploadedFile(
            name="test.txt",
            content=b"This is a sample text file for testing.",
            content_type="text/plain",
        )

    @pytest.fixture
    def sample_docx(self):
        """Return minimal valid DOCX content (zip with required structure)."""
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types></Types>')
            zf.writestr("word/document.xml", '<?xml version="1.0"?><w:document></w:document>')
        buffer.seek(0)
        return SimpleUploadedFile(
            name="test.docx",
            content=buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def test_upload_pdf_success(self, authenticated_client, sample_pdf, temp_media):
        """Test successful PDF upload."""
        url = reverse("documents_parser:list")
        data = {"file": sample_pdf}

        response = authenticated_client.post(url, data, format="multipart")

        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response.data
        assert response.data["file_type"] == "pdf"
        assert response.data["status"] == "uploaded"

    def test_upload_txt_success(self, authenticated_client, sample_txt, temp_media):
        """Test successful TXT upload."""
        url = reverse("documents_parser:list")
        data = {"file": sample_txt}

        response = authenticated_client.post(url, data, format="multipart")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["file_type"] == "txt"

    def test_upload_docx_success(self, authenticated_client, sample_docx, temp_media):
        """Test successful DOCX upload."""
        url = reverse("documents_parser:list")
        data = {"file": sample_docx}

        response = authenticated_client.post(url, data, format="multipart")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["file_type"] == "docx"

    def test_upload_with_metadata(self, authenticated_client, sample_pdf, temp_media):
        """Test upload with title and description."""
        url = reverse("documents_parser:list")
        data = {
            "file": sample_pdf,
            "title": "Test Document",
            "description": "Test description",
        }

        response = authenticated_client.post(url, data, format="multipart")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "Test Document"
        assert response.data["description"] == "Test description"

    def test_upload_unsupported_format(self, authenticated_client, temp_media):
        """Test upload with unsupported file format."""
        url = reverse("documents_parser:list")
        invalid_file = SimpleUploadedFile(
            name="test.exe",
            content=b"invalid content",
            content_type="application/octet-stream",
        )
        data = {"file": invalid_file}

        response = authenticated_client.post(url, data, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "file" in response.data

    def test_upload_too_large(self, authenticated_client, temp_media, settings):
        """Test upload with file exceeding size limit."""
        # Override max file size for this test
        settings.DOCUMENT_STORAGE_CONFIG = {
            "max_file_size": 100,  # 100 bytes for easy testing
            "allowed_extensions": ["pdf", "docx", "doc", "txt", "md"],
        }

        url = reverse("documents_parser:list")
        large_file = SimpleUploadedFile(
            name="large.pdf",
            content=b"x" * 200,  # 200 bytes exceeds 100 byte limit
            content_type="application/pdf",
        )
        data = {"file": large_file}

        response = authenticated_client.post(url, data, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "file" in response.data

    def test_upload_duplicate_returns_existing(
        self, authenticated_client, test_user, sample_pdf, temp_media
    ):
        """Test duplicate upload returns existing document."""
        url = reverse("documents_parser:list")

        # First upload
        response1 = authenticated_client.post(url, {"file": sample_pdf}, format="multipart")
        assert response1.status_code == status.HTTP_201_CREATED
        doc_id = response1.data["id"]

        # Reset file pointer for second upload
        sample_pdf.seek(0)

        # Second upload with same content
        response2 = authenticated_client.post(url, {"file": sample_pdf}, format="multipart")

        assert response2.status_code == status.HTTP_200_OK
        assert response2.data["id"] == doc_id
        assert response2.data["message"] == "Document already exists"

        # Verify only one document exists in database
        assert Document.objects.filter(user=test_user).count() == 1

    def test_upload_unauthenticated(self, api_client, sample_pdf):
        """Test upload without authentication returns 401."""
        url = reverse("documents_parser:list")
        data = {"file": sample_pdf}

        response = api_client.post(url, data, format="multipart")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestDocumentList:
    """Tests for document list endpoint."""

    @pytest.fixture
    def api_client(self) -> APIClient:
        """Return unauthenticated API client."""
        return APIClient()

    @pytest.fixture
    def test_user(self):
        """Create a test user."""
        return UserFactory.create_user(
            username="listuser",
            email="list@example.com",
            password="listpass123",
        )

    @pytest.fixture
    def another_user(self):
        """Create another test user."""
        return UserFactory.create_user(
            username="anotherlistuser",
            email="anotherlist@example.com",
            password="anotherpass123",
        )

    @pytest.fixture
    def authenticated_client(self, api_client: APIClient, test_user) -> APIClient:
        """Return authenticated API client."""
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(test_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    def test_list_own_documents(self, authenticated_client, test_user):
        """Test listing user's own documents."""
        # Create documents for the user
        DocumentFactory.create_batch(3, user=test_user)

        url = reverse("documents_parser:list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) == 3

    def test_list_does_not_show_other_users_documents(
        self, authenticated_client, test_user, another_user
    ):
        """Test that list doesn't show other users' documents."""
        # Create documents for both users
        DocumentFactory.create_batch(2, user=test_user)
        DocumentFactory.create_batch(3, user=another_user)

        url = reverse("documents_parser:list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) == 2

    def test_list_with_status_filter(self, authenticated_client, test_user):
        """Test filtering documents by status."""
        DocumentFactory(user=test_user, status=Document.Status.UPLOADED)
        DocumentFactory(user=test_user, status=Document.Status.PROCESSED)
        DocumentFactory(user=test_user, status=Document.Status.PROCESSED)

        url = reverse("documents_parser:list")
        response = authenticated_client.get(url, {"status": "processed"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) == 2

    def test_list_pagination(self, authenticated_client, test_user):
        """Test list pagination."""
        DocumentFactory.create_batch(25, user=test_user)

        url = reverse("documents_parser:list")
        response = authenticated_client.get(url, {"page": 1, "page_size": 10})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) == 10
        assert response.data["pagination"]["count"] == 25

    def test_list_empty(self, authenticated_client):
        """Test listing when user has no documents."""
        url = reverse("documents_parser:list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) == 0

    def test_list_unauthenticated(self, api_client):
        """Test list without authentication returns 401."""
        url = reverse("documents_parser:list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestDocumentDetail:
    """Tests for document detail endpoint."""

    @pytest.fixture
    def api_client(self) -> APIClient:
        """Return unauthenticated API client."""
        return APIClient()

    @pytest.fixture
    def test_user(self):
        """Create a test user."""
        return UserFactory.create_user(
            username="detailuser",
            email="detail@example.com",
            password="detailpass123",
        )

    @pytest.fixture
    def another_user(self):
        """Create another test user."""
        return UserFactory.create_user(
            username="anotherdetailuser",
            email="anotherdetail@example.com",
            password="anotherpass123",
        )

    @pytest.fixture
    def authenticated_client(self, api_client: APIClient, test_user) -> APIClient:
        """Return authenticated API client."""
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(test_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    def test_detail_own_document(self, authenticated_client, test_user):
        """Test retrieving own document detail."""
        document = DocumentFactory(user=test_user)

        url = reverse("documents_parser:detail", kwargs={"id": document.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(document.id)
        assert response.data["name"] == document.name

    def test_detail_includes_chunks_count(self, authenticated_client, test_user):
        """Test that detail includes chunks count."""
        document = DocumentFactory(user=test_user)
        DocumentChunkFactory.create_batch(5, document=document)

        url = reverse("documents_parser:detail", kwargs={"id": document.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["chunks_count"] == 5

    def test_detail_not_found(self, authenticated_client):
        """Test retrieving non-existent document returns 404."""
        from uuid import uuid4

        url = reverse("documents_parser:detail", kwargs={"id": uuid4()})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_other_user_document(
        self, authenticated_client, another_user
    ):
        """Test retrieving another user's document returns 404."""
        document = DocumentFactory(user=another_user)

        url = reverse("documents_parser:detail", kwargs={"id": document.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_unauthenticated(self, api_client, test_user):
        """Test detail without authentication returns 401."""
        document = DocumentFactory(user=test_user)

        url = reverse("documents_parser:detail", kwargs={"id": document.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestDocumentDelete:
    """Tests for document delete endpoint."""

    @pytest.fixture
    def api_client(self) -> APIClient:
        """Return unauthenticated API client."""
        return APIClient()

    @pytest.fixture
    def test_user(self):
        """Create a test user."""
        return UserFactory.create_user(
            username="deleteuser",
            email="delete@example.com",
            password="deletepass123",
        )

    @pytest.fixture
    def another_user(self):
        """Create another test user."""
        return UserFactory.create_user(
            username="anotherdeleteuser",
            email="anotherdelete@example.com",
            password="anotherpass123",
        )

    @pytest.fixture
    def authenticated_client(self, api_client: APIClient, test_user) -> APIClient:
        """Return authenticated API client."""
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(test_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    @pytest.fixture
    def temp_media(self, settings, tmp_path):
        """Override MEDIA_ROOT with temporary directory."""
        settings.MEDIA_ROOT = tmp_path / "media"
        settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
        return settings.MEDIA_ROOT

    def test_delete_own_document(
        self, authenticated_client, test_user, temp_media
    ):
        """Test deleting own document."""
        document = DocumentFactory(user=test_user)

        url = reverse("documents_parser:delete", kwargs={"id": document.id})
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Document.objects.filter(id=document.id).exists()

    def test_delete_removes_file(
        self, authenticated_client, test_user, temp_media
    ):
        """Test that delete removes physical file."""
        from pathlib import Path

        # Create document with actual file
        document = DocumentFactory(
            user=test_user,
            file_path="documents/test_file.pdf",
        )

        # Create the physical file
        file_path = Path(temp_media) / "documents" / "test_file.pdf"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"test content")

        assert file_path.exists()

        url = reverse("documents_parser:delete", kwargs={"id": document.id})
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not file_path.exists()

    def test_delete_not_found(self, authenticated_client):
        """Test deleting non-existent document returns 404."""
        from uuid import uuid4

        url = reverse("documents_parser:delete", kwargs={"id": uuid4()})
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_other_user_document(
        self, authenticated_client, another_user
    ):
        """Test deleting another user's document returns 404."""
        document = DocumentFactory(user=another_user)

        url = reverse("documents_parser:delete", kwargs={"id": document.id})
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Document.objects.filter(id=document.id).exists()

    def test_delete_unauthenticated(self, api_client, test_user):
        """Test delete without authentication returns 401."""
        document = DocumentFactory(user=test_user)

        url = reverse("documents_parser:delete", kwargs={"id": document.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
