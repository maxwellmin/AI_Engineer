"""
WebSocket consumer for real-time chat.

This module provides the ChatConsumer class that handles WebSocket
connections for the chat agent module.
"""

from __future__ import annotations

import logging
import uuid

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.chat_agent.agents import GraphRAGAgent, TextRAGAgent
from apps.chat_agent.constants import AgentType, ErrorCode, MessageType
from apps.chat_agent.exceptions import (
    ConversationNotFoundError,
    RateLimitError,
    UnauthorizedAccessError,
)
from apps.chat_agent.services import ConversationService

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for chat.

    This consumer handles real-time chat communication:
    - Connection management (connect, disconnect)
    - Message routing (chat.message, chat.stop)
    - Agent orchestration (Text RAG, Graph RAG)
    - Response streaming

    WebSocket URL: /ws/chat/<conversation_id>/

    Message Format (Client -> Server):
        {
            "type": "chat.message",
            "content": "User question"
        }

    Message Format (Server -> Client):
        {
            "type": "chat.response.chunk",
            "content": "AI response chunk",
            "is_final": false
        }

    Example:
        >>> # Connect to WebSocket
        >>> ws = websocket.connect("/ws/chat/uuid/")
        >>> # Send message
        >>> ws.send_json({"type": "chat.message", "content": "Hello"})
        >>> # Receive chunks
        >>> for msg in ws:
        ...     print(msg["content"])
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the consumer."""
        super().__init__(*args, **kwargs)
        self.conversation_id: str = ""
        self.user_id: str = ""
        self._conversation_service: ConversationService | None = None

    @property
    def conversation_service(self) -> ConversationService:
        """Get or create ConversationService instance."""
        if self._conversation_service is None:
            self._conversation_service = ConversationService()
        return self._conversation_service

    # =========================================================================
    # Connection Handlers
    # =========================================================================

    async def connect(self) -> None:
        """Handle WebSocket connection.

        This method:
        1. Extracts conversation_id from URL
        2. Authenticates user
        3. Joins conversation group
        """
        # Get conversation_id from URL
        self.conversation_id = self.scope["url_route"]["kwargs"].get(
            "conversation_id", ""
        )

        # Authenticate user
        if self.scope.get("user") is None or self.scope["user"].is_anonymous:
            logger.warning("WebSocket connection rejected: anonymous user")
            await self.close()
            return

        self.user_id = str(self.scope["user"].id)

        # Accept connection first so we can send error messages
        await self.accept()

        # Validate conversation_id format
        try:
            uuid.UUID(self.conversation_id)
        except ValueError:
            logger.warning(f"Invalid conversation_id format: {self.conversation_id}")
            await self._send_error(
                ErrorCode.CONVERSATION_NOT_FOUND,
                "Invalid conversation ID format",
            )
            await self.close()
            return

        # Verify user has access to conversation
        try:
            await self._verify_conversation_access()
        except (ConversationNotFoundError, UnauthorizedAccessError) as e:
            logger.warning(f"Access denied: {e}")
            await self._send_error(str(e.__class__.__name__).upper(), str(e))
            await self.close()
            return

        # Join conversation group
        await self.channel_layer.group_add(
            f"chat_{self.conversation_id}",
            self.channel_name,
        )

        logger.info(
            f"WebSocket connected: user={self.user_id}, "
            f"conversation={self.conversation_id}"
        )

    async def disconnect(self, code: int) -> None:
        """Handle WebSocket disconnection.

        Args:
            code: Close code.
        """
        # Leave conversation group
        if self.conversation_id:
            await self.channel_layer.group_discard(
                f"chat_{self.conversation_id}",
                self.channel_name,
            )

        logger.info(
            f"WebSocket disconnected: user={self.user_id}, "
            f"conversation={self.conversation_id}, code={code}"
        )

    # =========================================================================
    # Message Handlers
    # =========================================================================

    async def receive_json(self, content: dict) -> None:
        """Handle incoming WebSocket message.

        Args:
            content: Parsed JSON message.
        """
        message_type = content.get("type", "")

        if message_type == MessageType.CHAT_MESSAGE.value:
            await self._handle_chat_message(content)
        elif message_type == MessageType.CHAT_STOP.value:
            await self._handle_stop_generation()
        else:
            logger.warning(f"Unknown message type: {message_type}")
            await self._send_error(
                ErrorCode.AGENT_ERROR,
                f"Unknown message type: {message_type}",
            )

    async def _handle_chat_message(self, content: dict) -> None:
        """Handle chat message.

        Args:
            content: Message content with 'content' field.
        """
        query = content.get("content", "").strip()

        if not query:
            await self._send_error(ErrorCode.AGENT_ERROR, "Empty message")
            return

        logger.debug(
            f"Chat message: user={self.user_id}, "
            f"conversation={self.conversation_id}, query={query[:50]}..."
        )

        try:
            # Get or create conversation
            conversation = await self._get_or_create_conversation()

            # Select agent based on conversation type
            agent = self._get_agent(conversation.agent_type)

            # Run agent with streaming
            async for event_type, data in agent.run_with_streaming(
                conversation_id=self.conversation_id,
                query=query,
                user_id=self.user_id,
            ):
                if event_type == "status":
                    # Send status update
                    await self.send_json({
                        "type": "chat.status",
                        "status": data,
                    })
                elif event_type == "chunk":
                    # Send response chunk
                    await self.send_json({
                        "type": MessageType.CHAT_RESPONSE_CHUNK.value,
                        "content": data,
                        "is_final": False,
                    })
                elif event_type == "complete":
                    # Send completion message
                    await self.send_json({
                        "type": MessageType.CHAT_RESPONSE_COMPLETE.value,
                        "message_id": data.get("message_id"),
                        "sources": data.get("sources", []),
                        "token_count": data.get("token_count", 0),
                    })
                elif event_type == "error":
                    # Send error message
                    await self._send_error(ErrorCode.AGENT_ERROR, data)

        except RateLimitError:
            await self._send_error(
                ErrorCode.RATE_LIMIT,
                "Rate limit exceeded. Please wait before sending more messages.",
            )
        except Exception as e:
            logger.exception(f"Chat message handling failed: {e}")
            await self._send_error(ErrorCode.AGENT_ERROR, str(e))

    async def _handle_stop_generation(self) -> None:
        """Handle stop generation request."""
        # TODO: Implement generation cancellation
        logger.info(f"Stop generation requested: {self.conversation_id}")
        await self.send_json({
            "type": "chat.stopped",
            "message": "Generation stopped",
        })

    # =========================================================================
    # Channel Layer Handlers
    # =========================================================================

    async def chat_message(self, event: dict) -> None:
        """Handle messages from channel layer.

        Args:
            event: Event data with 'message' field.
        """
        await self.send_json(event.get("message", {}))

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _verify_conversation_access(self) -> None:
        """Verify user has access to conversation.

        Raises:
            ConversationNotFoundError: If conversation not found.
            UnauthorizedAccessError: If user doesn't own the conversation.
        """
        # Use sync_to_async for database operations
        from asgiref.sync import sync_to_async

        @sync_to_async
        def get_conversation():
            return self.conversation_service.get_conversation(
                conversation_id=self.conversation_id,
                user_id=self.user_id,
            )

        await get_conversation()

    async def _get_or_create_conversation(self):
        """Get or create conversation.

        Returns:
            Conversation instance.
        """
        from asgiref.sync import sync_to_async

        @sync_to_async
        def get_or_create():
            try:
                return self.conversation_service.get_conversation(
                    conversation_id=self.conversation_id,
                    user_id=self.user_id,
                )
            except ConversationNotFoundError:
                # Create new conversation
                return self.conversation_service.create_conversation(
                    user_id=self.user_id,
                    agent_type=AgentType.TEXT_RAG.value,
                )

        return await get_or_create()

    def _get_agent(self, agent_type: str):
        """Get agent instance by type.

        Args:
            agent_type: Agent type (text_rag or graph_rag).

        Returns:
            Agent instance.
        """
        if agent_type == AgentType.GRAPH_RAG.value:
            return GraphRAGAgent()
        return TextRAGAgent()

    async def _send_error(self, error_code: str, message: str) -> None:
        """Send error message to client.

        Args:
            error_code: Error code.
            message: Error message.
        """
        await self.send_json({
            "type": MessageType.CHAT_ERROR.value,
            "error_code": error_code,
            "message": message,
        })
