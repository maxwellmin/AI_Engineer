"""
API views for chat_agent application.
"""

from __future__ import annotations

import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.chat_agent.constants import AgentType
from apps.chat_agent.exceptions import (
    ConversationNotFoundError,
    UnauthorizedAccessError,
)
from apps.chat_agent.models import Conversation, Message
from apps.chat_agent.serializers import (
    ChatResponseSerializer,
    ConversationCreateSerializer,
    ConversationSerializer,
    MessageResponseSerializer,
    MessageSerializer,
    SendMessageSerializer,
)
from apps.chat_agent.services import ConversationService
from core.pagination import StandardPagination

logger = logging.getLogger(__name__)


class ConversationViewSet(viewsets.ModelViewSet):
    """ViewSet for Conversation CRUD operations.

    Provides:
    - List conversations (paginated)
    - Create conversation
    - Get conversation details
    - Delete conversation
    - Get conversation messages

    Endpoints:
    - GET /api/v1/chat/conversations/ - List conversations
    - POST /api/v1/chat/conversations/ - Create conversation
    - GET /api/v1/chat/conversations/{id}/ - Get conversation
    - DELETE /api/v1/chat/conversations/{id}/ - Delete conversation
    - GET /api/v1/chat/conversations/{id}/messages/ - Get messages
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    serializer_class = ConversationSerializer

    def get_queryset(self):
        """Get queryset filtered by user."""
        return Conversation.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """Get serializer class based on action."""
        if self.action == "create":
            return ConversationCreateSerializer
        return ConversationSerializer

    def perform_create(self, serializer):
        """Create conversation for current user."""
        service = ConversationService()
        conversation = service.create_conversation(
            user_id=self.request.user.id,
            agent_type=serializer.validated_data.get(
                "agent_type", AgentType.TEXT_RAG.value
            ),
            title=serializer.validated_data.get("title", ""),
        )
        return conversation

    def create(self, request, *args, **kwargs):
        """Create a new conversation."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = ConversationService()
        conversation = service.create_conversation(
            user_id=request.user.id,
            agent_type=serializer.validated_data.get(
                "agent_type", AgentType.TEXT_RAG.value
            ),
            title=serializer.validated_data.get("title", ""),
        )

        output_serializer = ConversationSerializer(conversation)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        """Get conversation details."""
        service = ConversationService()
        try:
            conversation = service.get_conversation(
                conversation_id=kwargs["pk"],
                user_id=request.user.id,
            )
            serializer = ConversationSerializer(conversation)
            return Response(serializer.data)
        except ConversationNotFoundError:
            return Response(
                {"error": "Conversation not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except UnauthorizedAccessError:
            return Response(
                {"error": "Unauthorized"},
                status=status.HTTP_403_FORBIDDEN,
            )

    def destroy(self, request, *args, **kwargs):
        """Delete conversation."""
        service = ConversationService()
        try:
            service.delete_conversation(
                conversation_id=kwargs["pk"],
                user_id=request.user.id,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ConversationNotFoundError:
            return Response(
                {"error": "Conversation not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except UnauthorizedAccessError:
            return Response(
                {"error": "Unauthorized"},
                status=status.HTTP_403_FORBIDDEN,
            )

    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        """Get messages for a conversation.

        Args:
            request: HTTP request.
            pk: Conversation ID.

        Returns:
            Paginated list of messages.
        """
        service = ConversationService()
        try:
            # Verify access
            service.get_conversation(
                conversation_id=pk,
                user_id=request.user.id,
            )

            # Get messages
            messages = Message.objects.filter(conversation_id=pk).order_by(
                "created_at"
            )

            # Paginate
            page = self.paginate_queryset(messages)
            if page is not None:
                serializer = MessageSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = MessageSerializer(messages, many=True)
            return Response(serializer.data)

        except ConversationNotFoundError:
            return Response(
                {"error": "Conversation not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except UnauthorizedAccessError:
            return Response(
                {"error": "Unauthorized"},
                status=status.HTTP_403_FORBIDDEN,
            )

    @action(detail=True, methods=["post"])
    def send_message(self, request, pk=None):
        """Send a message (HTTP fallback for non-WebSocket clients).

        This endpoint provides synchronous message sending for clients
        that cannot use WebSockets.

        Args:
            request: HTTP request with message content.
            pk: Conversation ID.

        Returns:
            Response with generated message.
        """
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        content = serializer.validated_data["content"]

        service = ConversationService()
        try:
            # Verify access
            conversation = service.get_conversation(
                conversation_id=pk,
                user_id=request.user.id,
            )

            # Import agents
            from apps.chat_agent.agents import GraphRAGAgent, TextRAGAgent

            # Select agent
            if conversation.agent_type == AgentType.GRAPH_RAG.value:
                agent = GraphRAGAgent()
            else:
                agent = TextRAGAgent()

            # Run agent synchronously
            import asyncio

            response_content = ""
            message_id = None
            sources = []
            token_count = 0

            async def run_agent():
                nonlocal response_content, message_id, sources, token_count
                async for event_type, data in agent.run_with_streaming(
                    conversation_id=pk,
                    query=content,
                    user_id=str(request.user.id),
                ):
                    if event_type == "chunk":
                        response_content += data
                    elif event_type == "complete":
                        message_id = data.get("message_id")
                        sources = data.get("sources", [])
                        token_count = data.get("token_count", 0)

            # Run async
            asyncio.run(run_agent())

            return Response(
                ChatResponseSerializer(
                    {
                        "message_id": message_id,
                        "content": response_content,
                        "sources": sources,
                        "token_count": token_count,
                    }
                ).data
            )

        except ConversationNotFoundError:
            return Response(
                {"error": "Conversation not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except UnauthorizedAccessError:
            return Response(
                {"error": "Unauthorized"},
                status=status.HTTP_403_FORBIDDEN,
            )
        except Exception as e:
            logger.exception(f"Send message failed: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Message read operations.

    Provides:
    - List messages (paginated)
    - Get message details

    Endpoints:
    - GET /api/v1/chat/messages/ - List all messages
    - GET /api/v1/chat/messages/{id}/ - Get message
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    serializer_class = MessageSerializer

    def get_queryset(self):
        """Get queryset filtered by user's conversations."""
        return Message.objects.filter(
            conversation__user=self.request.user
        ).order_by("-created_at")
