"""
Tests for embedding engine API views.

This module tests the HTTP API endpoints for the embedding engine.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.embedding_engine.dto import (
    BatchEmbeddingResult,
    EmbeddingResult,
)


@pytest.mark.unit
@pytest.mark.django_db
class TestEmbeddingHealthView:
    """Tests for the health check endpoint."""

    def test_health_check_healthy(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test healthy health check response."""
        mock_health_result = {
            "healthy": True,
            "provider": "mock",
            "model": "text-embedding-v1",
            "dimension": 1536,
            "latency_ms": 10.5,
        }

        with patch(
            "apps.embedding_engine.views.embedding_views.EmbeddingService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.health_check.return_value = mock_health_result
            mock_service_class.return_value = mock_service

            response = authenticated_client.get("/api/v1/embedding/health/")

            assert response.status_code == status.HTTP_200_OK
            assert response.data["healthy"] is True

    def test_health_check_unauthenticated(self, api_client: APIClient) -> None:
        """Test that health check requires authentication."""
        response = api_client.get("/api/v1/embedding/health/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_health_check_unhealthy(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test unhealthy health check response."""
        mock_health_result = {
            "healthy": False,
            "provider": "qwen",
            "model": "text-embedding-v1",
            "dimension": 1536,
            "latency_ms": 100.0,
            "error": "API connection failed",
        }

        with patch(
            "apps.embedding_engine.views.embedding_views.EmbeddingService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.health_check.return_value = mock_health_result
            mock_service_class.return_value = mock_service

            response = authenticated_client.get("/api/v1/embedding/health/")

            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert response.data["healthy"] is False


@pytest.mark.unit
@pytest.mark.django_db
class TestEmbedTextView:
    """Tests for the single text embedding endpoint."""

    def test_embed_text_success(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test successful text embedding."""
        mock_result = EmbeddingResult(
            embedding=[0.1] * 1536,
            dimension=1536,
            model="text-embedding-v1",
            tokens_used=10,
        )

        with patch(
            "apps.embedding_engine.views.embedding_views.EmbeddingService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.embed_text.return_value = mock_result
            mock_service_class.return_value = mock_service

            response = authenticated_client.post(
                "/api/v1/embedding/embed/",
                {"text": "Hello world", "task_type": "retrieval.document"},
                format="json",
            )

            assert response.status_code == status.HTTP_200_OK
            assert len(response.data["embedding"]) == 1536
            assert response.data["dimension"] == 1536

    def test_embed_text_unauthenticated(self, api_client: APIClient) -> None:
        """Test that embed requires authentication."""
        response = api_client.post(
            "/api/v1/embedding/embed/",
            {"text": "Hello world"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_embed_text_missing_text(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test validation error when text is missing."""
        response = authenticated_client.post(
            "/api/v1/embedding/embed/",
            {},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_embed_text_empty_text(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test validation error when text is empty."""
        response = authenticated_client.post(
            "/api/v1/embedding/embed/",
            {"text": ""},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.unit
@pytest.mark.django_db
class TestEmbedBatchView:
    """Tests for the batch embedding endpoint."""

    def test_embed_batch_success(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test successful batch embedding."""
        mock_result = BatchEmbeddingResult(
            embeddings=[[0.1] * 1536, [0.2] * 1536],
            dimension=1536,
            model="text-embedding-v1",
            total_tokens=20,
            success_count=2,
        )

        with patch(
            "apps.embedding_engine.views.embedding_views.EmbeddingService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.embed_texts.return_value = mock_result
            mock_service_class.return_value = mock_service

            response = authenticated_client.post(
                "/api/v1/embedding/embed-batch/",
                {
                    "texts": ["Hello", "World"],
                    "task_type": "retrieval.document",
                    "batch_size": 20,
                },
                format="json",
            )

            assert response.status_code == status.HTTP_200_OK
            assert len(response.data["embeddings"]) == 2

    def test_embed_batch_unauthenticated(self, api_client: APIClient) -> None:
        """Test that batch embed requires authentication."""
        response = api_client.post(
            "/api/v1/embedding/embed-batch/",
            {"texts": ["Hello"]},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_embed_batch_empty_texts(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test validation error when texts is empty."""
        response = authenticated_client.post(
            "/api/v1/embedding/embed-batch/",
            {"texts": []},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.unit
@pytest.mark.django_db
class TestEmbedQueryView:
    """Tests for the query embedding endpoint."""

    def test_embed_query_success(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test successful query embedding."""
        mock_result = EmbeddingResult(
            embedding=[0.1] * 1536,
            dimension=1536,
            model="text-embedding-v1",
            tokens_used=10,
        )

        with patch(
            "apps.embedding_engine.views.embedding_views.EmbeddingService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.embed_query.return_value = mock_result
            mock_service_class.return_value = mock_service

            response = authenticated_client.post(
                "/api/v1/embedding/embed-query/",
                {"query": "What is machine learning?"},
                format="json",
            )

            assert response.status_code == status.HTTP_200_OK
            assert len(response.data["embedding"]) == 1536

    def test_embed_query_unauthenticated(self, api_client: APIClient) -> None:
        """Test that query embed requires authentication."""
        response = api_client.post(
            "/api/v1/embedding/embed-query/",
            {"query": "What is AI?"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.unit
@pytest.mark.django_db
class TestSupportedModelsView:
    """Tests for the supported models endpoint."""

    def test_get_supported_models(
        self,
        authenticated_client: APIClient,
    ) -> None:
        """Test getting supported models."""
        with patch(
            "apps.embedding_engine.views.embedding_views.EmbeddingService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_supported_models.return_value = [
                "text-embedding-v1",
                "text-embedding-v3",
            ]
            mock_service_class.return_value = mock_service

            response = authenticated_client.get("/api/v1/embedding/models/")

            assert response.status_code == status.HTTP_200_OK
            assert "models" in response.data
            assert "text-embedding-v1" in response.data["models"]

    def test_get_supported_models_unauthenticated(
        self, api_client: APIClient
    ) -> None:
        """Test that models endpoint requires authentication."""
        response = api_client.get("/api/v1/embedding/models/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
