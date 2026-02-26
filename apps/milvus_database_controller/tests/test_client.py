"""
Tests for MilvusClient wrapper.

This module tests the MilvusClientWrapper singleton class.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from apps.milvus_database_controller.client.milvus_client import MilvusClientWrapper
from apps.milvus_database_controller.exceptions import (
    MilvusConnectionError,
)

if TYPE_CHECKING:
    pass


@pytest.mark.unit
class TestMilvusClientWrapper:
    """Test MilvusClientWrapper class."""

    def test_singleton_pattern(self) -> None:
        """Test that MilvusClientWrapper is a singleton."""
        # Reset singleton first
        MilvusClientWrapper.reset_instance()

        client1 = MilvusClientWrapper()
        client2 = MilvusClientWrapper()

        assert client1 is client2
        assert MilvusClientWrapper.get_instance() is client1

        # Cleanup
        MilvusClientWrapper.reset_instance()

    def test_reset_instance(self) -> None:
        """Test that reset_instance creates a new instance."""
        client1 = MilvusClientWrapper()
        MilvusClientWrapper.reset_instance()
        client2 = MilvusClientWrapper()

        assert client1 is not client2

        # Cleanup
        MilvusClientWrapper.reset_instance()

    def test_config_loading(self) -> None:
        """Test that configuration is loaded from Django settings."""
        from django.conf import settings

        client = MilvusClientWrapper()
        config = client.config

        assert "uri" in config
        assert "timeout" in config
        assert config["uri"] == settings.MILVUS_URI

        # Cleanup
        MilvusClientWrapper.reset_instance()

    def test_config_property_returns_copy(self) -> None:
        """Test that config property returns a copy."""
        client = MilvusClientWrapper()
        config1 = client.config
        config2 = client.config

        assert config1 == config2
        assert config1 is not config2  # Should be different objects

        # Cleanup
        MilvusClientWrapper.reset_instance()

    @patch("apps.milvus_database_controller.client.milvus_client.PyMilvusClient")
    def test_connection_success(self, mock_milvus_client: MagicMock) -> None:
        """Test successful connection to Milvus."""
        mock_instance = MagicMock()
        mock_milvus_client.return_value = mock_instance

        MilvusClientWrapper.reset_instance()
        client = MilvusClientWrapper()

        # Trigger connection by calling a method
        mock_instance.has_collection.return_value = True
        result = client.has_collection("test_collection")

        assert result is True
        mock_milvus_client.assert_called_once()

        # Cleanup
        MilvusClientWrapper.reset_instance()

    @patch("apps.milvus_database_controller.client.milvus_client.PyMilvusClient")
    def test_connection_failure(self, mock_milvus_client: MagicMock) -> None:
        """Test connection failure handling."""
        from pymilvus import exceptions as milvus_exceptions

        mock_milvus_client.side_effect = milvus_exceptions.MilvusException(
            message="Connection refused"
        )

        MilvusClientWrapper.reset_instance()
        client = MilvusClientWrapper()

        with pytest.raises(MilvusConnectionError):
            client._get_client()

        # Cleanup
        MilvusClientWrapper.reset_instance()


@pytest.mark.unit
class TestMilvusClientWrapperOperations:
    """Test MilvusClientWrapper operations."""

    @patch("apps.milvus_database_controller.client.milvus_client.PyMilvusClient")
    def test_list_collections(self, mock_milvus_client: MagicMock) -> None:
        """Test list_collections operation."""
        mock_instance = MagicMock()
        mock_instance.list_collections.return_value = ["collection1", "collection2"]
        mock_milvus_client.return_value = mock_instance

        MilvusClientWrapper.reset_instance()
        client = MilvusClientWrapper()
        collections = client.list_collections()

        assert collections == ["collection1", "collection2"]
        mock_instance.list_collections.assert_called_once()

        # Cleanup
        MilvusClientWrapper.reset_instance()

    @patch("apps.milvus_database_controller.client.milvus_client.PyMilvusClient")
    def test_has_collection(self, mock_milvus_client: MagicMock) -> None:
        """Test has_collection operation."""
        mock_instance = MagicMock()
        mock_instance.has_collection.return_value = True
        mock_milvus_client.return_value = mock_instance

        MilvusClientWrapper.reset_instance()
        client = MilvusClientWrapper()
        result = client.has_collection("test_collection")

        assert result is True
        mock_instance.has_collection.assert_called_once_with("test_collection")

        # Cleanup
        MilvusClientWrapper.reset_instance()

    @patch("apps.milvus_database_controller.client.milvus_client.PyMilvusClient")
    def test_insert(self, mock_milvus_client: MagicMock) -> None:
        """Test insert operation."""
        mock_instance = MagicMock()
        mock_instance.insert.return_value = {"ids": ["id1", "id2"]}
        mock_milvus_client.return_value = mock_instance

        MilvusClientWrapper.reset_instance()
        client = MilvusClientWrapper()
        result = client.insert(
            collection_name="test_collection",
            data=[{"pk": "id1", "text": "text1"}],
        )

        assert result == {"ids": ["id1", "id2"]}
        mock_instance.insert.assert_called_once()

        # Cleanup
        MilvusClientWrapper.reset_instance()

    @patch("apps.milvus_database_controller.client.milvus_client.PyMilvusClient")
    def test_search(self, mock_milvus_client: MagicMock) -> None:
        """Test search operation."""
        mock_instance = MagicMock()
        mock_instance.search.return_value = [[{"id": "id1", "distance": 0.1}]]
        mock_milvus_client.return_value = mock_instance

        MilvusClientWrapper.reset_instance()
        client = MilvusClientWrapper()
        result = client.search(
            collection_name="test_collection",
            data=[[0.1, 0.2, 0.3]],
            anns_field="text_dense",
            limit=10,
        )

        assert result == [[{"id": "id1", "distance": 0.1}]]
        mock_instance.search.assert_called_once()

        # Cleanup
        MilvusClientWrapper.reset_instance()
