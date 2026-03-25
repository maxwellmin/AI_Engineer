"""
Conversation service for managing conversations and messages.

This service handles CRUD operations for conversations and messages,
as well as integration with Milvus for conversation history embeddings.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from django.conf import settings

from apps.chat_agent.constants import AgentType, DEFAULT_HISTORY_LIMIT
from apps.chat_agent.exceptions import (
    ConversationNotFoundError,
    UnauthorizedAccessError,
)
from apps.chat_agent.models import Conversation, Message
from apps.embedding_engine.services import EmbeddingService
from apps.milvus_database_controller.constants import FieldName
from apps.milvus_database_controller.services import MilvusService

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for conversation management.

    This service provides methods for:
    - Creating, retrieving, and deleting conversations
    - Adding and retrieving messages
    - Storing and searching message embeddings in Milvus

    Example:
        >>> service = ConversationService()
        >>> conversation = service.create_conversation(user_id, "text_rag")
        >>> message = service.add_message(conversation.id, "user", "Hello")
    """

    def __init__(
        self,
        milvus_service: MilvusService | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        """Initialize the conversation service.

        Args:
            milvus_service: Optional MilvusService instance.
            embedding_service: Optional EmbeddingService instance.
        """
        self._milvus_service = milvus_service
        self._embedding_service = embedding_service
        self._chat_history_collection = (
            settings.MILVUS_CONFIG.get("chat_history_collection", "chat_history")
        )

    @property
    def milvus_service(self) -> MilvusService:
        """Get or create MilvusService instance (lazy initialization)."""
        if self._milvus_service is None:
            self._milvus_service = MilvusService()
        return self._milvus_service

    @property
    def embedding_service(self) -> EmbeddingService:
        """Get or create EmbeddingService instance (lazy initialization)."""
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    # =========================================================================
    # Conversation CRUD
    # =========================================================================

    def create_conversation(
        self,
        user_id: str | uuid.UUID,
        agent_type: str = AgentType.TEXT_RAG.value,
        title: str = "",
    ) -> Conversation:
        """Create a new conversation.

        Args:
            user_id: User ID who owns this conversation.
            agent_type: Type of RAG agent (text_rag or graph_rag).
            title: Optional title for the conversation.

        Returns:
            Created Conversation instance.
        """
        conversation = Conversation.objects.create(
            user_id=str(user_id),
            agent_type=agent_type,
            title=title,
        )

        logger.info(
            f"Created conversation {conversation.id} for user {user_id} "
            f"with agent_type={agent_type}"
        )

        return conversation

    def get_conversation(
        self,
        conversation_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
    ) -> Conversation:
        """Get conversation by ID with user authorization check.

        Args:
            conversation_id: Conversation ID to retrieve.
            user_id: User ID for authorization.

        Returns:
            Conversation instance.

        Raises:
            ConversationNotFoundError: If conversation not found.
            UnauthorizedAccessError: If user doesn't own the conversation.
        """
        try:
            conversation = Conversation.objects.get(id=str(conversation_id))
        except Conversation.DoesNotExist:
            raise ConversationNotFoundError(str(conversation_id))

        if str(conversation.user_id) != str(user_id):
            raise UnauthorizedAccessError()

        return conversation

    def list_conversations(
        self,
        user_id: str | uuid.UUID,
        agent_type: str | None = None,
        is_active: bool | None = True,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        """List conversations for a user.

        Args:
            user_id: User ID to list conversations for.
            agent_type: Optional filter by agent type.
            is_active: Optional filter by active status.
            limit: Maximum number of results.
            offset: Offset for pagination.

        Returns:
            List of Conversation instances.
        """
        queryset = Conversation.objects.filter(user_id=str(user_id))

        if agent_type:
            queryset = queryset.filter(agent_type=agent_type)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        return list(queryset[offset : offset + limit])

    def update_conversation(
        self,
        conversation_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
        title: str | None = None,
        is_active: bool | None = None,
    ) -> Conversation:
        """Update conversation properties.

        Args:
            conversation_id: Conversation ID to update.
            user_id: User ID for authorization.
            title: New title (optional).
            is_active: New active status (optional).

        Returns:
            Updated Conversation instance.
        """
        conversation = self.get_conversation(conversation_id, user_id)

        if title is not None:
            conversation.title = title

        if is_active is not None:
            conversation.is_active = is_active

        conversation.save()
        return conversation

    def delete_conversation(
        self,
        conversation_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
    ) -> bool:
        """Delete a conversation and its messages.

        Args:
            conversation_id: Conversation ID to delete.
            user_id: User ID for authorization.

        Returns:
            True if deleted successfully.
        """
        conversation = self.get_conversation(conversation_id, user_id)

        # Delete message embeddings from Milvus
        self._delete_conversation_embeddings(str(conversation_id))

        # Delete conversation (cascades to messages)
        conversation.delete()

        logger.info(f"Deleted conversation {conversation_id}")
        return True

    # =========================================================================
    # Message CRUD
    # =========================================================================

    def add_message(
        self,
        conversation_id: str | uuid.UUID,
        role: str,
        content: str,
        sources: list[str] | None = None,
        retrieval_scores: dict | None = None,
        token_count: int = 0,
        model_used: str = "",
    ) -> Message:
        """Add a message to a conversation.

        Args:
            conversation_id: Conversation ID.
            role: Message role (user, assistant, system).
            content: Message content.
            sources: List of source chunk IDs.
            retrieval_scores: Retrieval scores for each source.
            token_count: Number of tokens in the message.
            model_used: LLM model used for generation.

        Returns:
            Created Message instance.
        """
        message = Message.objects.create(
            conversation_id=str(conversation_id),
            role=role,
            content=content,
            sources=sources or [],
            retrieval_scores=retrieval_scores or {},
            token_count=token_count,
            model_used=model_used,
        )

        logger.debug(
            f"Added message {message.id} to conversation {conversation_id} "
            f"with role={role}"
        )

        return message

    def get_history(
        self,
        conversation_id: str | uuid.UUID,
        limit: int = DEFAULT_HISTORY_LIMIT,
    ) -> list[Message]:
        """Get recent conversation history.

        Args:
            conversation_id: Conversation ID.
            limit: Maximum number of messages to return.

        Returns:
            List of Message instances ordered by created_at.
        """
        messages = list(
            Message.objects.filter(conversation_id=str(conversation_id))
            .order_by("-created_at")[:limit]
        )
        # Return in chronological order
        return list(reversed(messages))

    def get_message(
        self,
        message_id: str | uuid.UUID,
    ) -> Message | None:
        """Get a message by ID.

        Args:
            message_id: Message ID.

        Returns:
            Message instance or None if not found.
        """
        try:
            return Message.objects.get(id=str(message_id))
        except Message.DoesNotExist:
            return None

    # =========================================================================
    # Milvus Integration
    # =========================================================================

    def store_message_embedding(
        self,
        message: Message,
    ) -> str:
        """Store message embedding in Milvus chat_history collection.

        Args:
            message: Message instance to store.

        Returns:
            Embedding ID in Milvus.
        """
        # Ensure collection exists
        self._ensure_chat_history_collection()

        # Generate embedding
        result = self.embedding_service.embed_query(message.content)

        # Prepare data for Milvus (using field names from schema)
        from apps.milvus_database_controller.constants import FieldName

        data = [
            {
                FieldName.PK.value: str(message.id),
                FieldName.MESSAGE.value: message.content,
                FieldName.ROLE.value: message.role,
                FieldName.CONVERSATION_ID.value: str(message.conversation_id),
                FieldName.USER_ID.value: str(message.conversation.user_id),
                FieldName.TIMESTAMP.value: int(message.created_at.timestamp()),
                FieldName.EMBEDDING.value: result.embedding,
            }
        ]

        # Insert into Milvus
        insert_result = self.milvus_service.insert_vectors(
            collection_name=self._chat_history_collection,
            data=data,
        )

        # Update message with embedding ID
        message.embedding_id = str(message.id)
        message.save()

        logger.debug(
            f"Stored embedding for message {message.id} in Milvus"
        )

        return str(message.id)

    def search_similar_messages(
        self,
        query_embedding: list[float],
        conversation_id: str | None = None,
        user_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search similar messages from conversation history.

        Args:
            query_embedding: Query embedding vector.
            conversation_id: Optional filter by conversation.
            user_id: Optional filter by user.
            top_k: Number of results.

        Returns:
            List of similar messages with scores.
        """
        # Ensure collection exists
        self._ensure_chat_history_collection()

        # Build filter expression
        filter_parts: list[str] = []

        if conversation_id:
            filter_parts.append(f'{FieldName.CONVERSATION_ID.value} == "{conversation_id}"')

        if user_id:
            filter_parts.append(f'{FieldName.USER_ID.value} == "{user_id}"')

        filter_expr = " && ".join(filter_parts) if filter_parts else ""

        # Search in Milvus
        result = self.milvus_service.search(
            collection_name=self._chat_history_collection,
            query_vector=query_embedding,
            anns_field=FieldName.EMBEDDING.value,
            top_k=top_k,
            filter_expr=filter_expr,
            output_fields=[
                FieldName.MESSAGE.value,
                FieldName.ROLE.value,
                FieldName.CONVERSATION_ID.value,
                FieldName.TIMESTAMP.value,
            ],
        )

        return [
            {
                "message_id": item.id,
                "score": item.score,
                "message": item.entity.get(FieldName.MESSAGE.value, ""),
                "role": item.entity.get(FieldName.ROLE.value, ""),
                "conversation_id": item.entity.get(FieldName.CONVERSATION_ID.value, ""),
                "timestamp": item.entity.get(FieldName.TIMESTAMP.value, 0),
            }
            for item in result.items
        ]

    def _delete_conversation_embeddings(
        self,
        conversation_id: str,
    ) -> int:
        """Delete all message embeddings for a conversation.

        Args:
            conversation_id: Conversation ID.

        Returns:
            Number of deleted embeddings.
        """
        filter_expr = f'{FieldName.CONVERSATION_ID.value} == "{conversation_id}"'

        try:
            result = self.milvus_service.delete_vectors_by_filter(
                collection_name=self._chat_history_collection,
                filter_expr=filter_expr,
            )
            logger.debug(
                f"Deleted {result.count} embeddings for conversation {conversation_id}"
            )
            return result.count
        except Exception as e:
            logger.warning(
                f"Failed to delete embeddings for conversation {conversation_id}: {e}"
            )
            return 0

    def _ensure_chat_history_collection(self) -> bool:
        """Ensure chat_history collection exists in Milvus.

        Returns:
            True if collection exists or was created.
        """
        try:
            if not self.milvus_service.has_collection(self._chat_history_collection):
                from apps.milvus_database_controller.schemas.collection_schema import (
                    get_chat_history_collection_schema,
                )

                schema = get_chat_history_collection_schema(
                    dimension=self.embedding_service.dimension,
                )
                self.milvus_service._collection_manager.create_collection_with_schema(
                    collection_name=self._chat_history_collection,
                    schema=schema,
                    description="Chat message embeddings for conversation history",
                )
                # Create index and load collection
                self.milvus_service.load_collection(self._chat_history_collection)
                logger.info(f"Created chat_history collection in Milvus")
            return True
        except Exception as e:
            logger.warning(f"Failed to ensure chat_history collection: {e}")
            return False

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def count_conversations(
        self,
        user_id: str | uuid.UUID,
        is_active: bool | None = None,
    ) -> int:
        """Count conversations for a user.

        Args:
            user_id: User ID.
            is_active: Optional filter by active status.

        Returns:
            Number of conversations.
        """
        queryset = Conversation.objects.filter(user_id=str(user_id))

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        return queryset.count()

    def count_messages(
        self,
        conversation_id: str | uuid.UUID,
    ) -> int:
        """Count messages in a conversation.

        Args:
            conversation_id: Conversation ID.

        Returns:
            Number of messages.
        """
        return Message.objects.filter(conversation_id=str(conversation_id)).count()
