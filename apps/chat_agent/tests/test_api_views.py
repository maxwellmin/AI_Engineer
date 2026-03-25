"""
Tests for API views.
"""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.api
@pytest.mark.django_db
class TestConversationAPI:
    """Tests for Conversation API endpoints."""

    def test_list_conversations(self, authenticated_client, test_conversation):
        """Test listing conversations."""
        url = reverse("conversation-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Response may be paginated or not depending on pagination class
        if "results" in response.data:
            assert len(response.data["results"]) == 1
        else:
            assert len(response.data) >= 1

    def test_create_conversation(self, authenticated_client):
        """Test creating a conversation."""
        url = reverse("conversation-list")
        data = {
            "title": "New Conversation",
            "agent_type": "text_rag",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "New Conversation"
        assert response.data["agent_type"] == "text_rag"

    def test_get_conversation(self, authenticated_client, test_conversation):
        """Test getting a conversation."""
        url = reverse("conversation-detail", kwargs={"pk": test_conversation.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(test_conversation.id)

    def test_get_conversation_not_found(self, authenticated_client):
        """Test getting a non-existent conversation."""
        import uuid

        url = reverse("conversation-detail", kwargs={"pk": uuid.uuid4()})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_conversation(self, authenticated_client, test_conversation):
        """Test deleting a conversation."""
        url = reverse("conversation-detail", kwargs={"pk": test_conversation.id})
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_unauthorized_access(self, api_client, test_conversation):
        """Test accessing without authentication."""
        url = reverse("conversation-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_other_user_conversation(
        self,
        authenticated_client,
        test_conversation,
        test_user2,
    ):
        """Test accessing another user's conversation."""
        from apps.chat_agent.services import ConversationService

        # Re-authenticate as test_user2
        authenticated_client.force_authenticate(user=test_user2)

        url = reverse("conversation-detail", kwargs={"pk": test_conversation.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.api
@pytest.mark.django_db
class TestMessageAPI:
    """Tests for Message API endpoints."""

    def test_list_messages(
        self,
        authenticated_client,
        test_conversation_with_messages,
    ):
        """Test listing messages for a conversation."""
        conversation, messages = test_conversation_with_messages
        url = reverse("conversation-messages", kwargs={"pk": conversation.id})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Check pagination
        assert "results" in response.data or len(response.data) > 0

    def test_send_message_sync(self, authenticated_client, test_conversation):
        """Test sending a message synchronously."""
        # Skip this test for now - requires async mocking
        # The actual WebSocket endpoint will be tested separately
        pytest.skip("Requires async mocking setup")
