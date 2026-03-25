"""
Context service for assembling RAG context.

This service handles context assembly by:
1. Retrieving relevant documents using SearchService
2. Getting conversation history from ConversationService
3. Formatting context window for LLM prompt
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

from apps.chat_agent.constants import DEFAULT_HISTORY_LIMIT, DEFAULT_TOP_K, MAX_CONTEXT_TOKENS
from apps.chat_agent.exceptions import ContextAssemblyError

logger = logging.getLogger(__name__)

# Define ContextResult locally to avoid circular import
from typing import TypedDict


class ContextResult(TypedDict):
    """
    Result from context assembly.

    Attributes:
        context: Formatted context string for LLM.
        sources: List of source documents.
        retrieval_scores: Scores from each retriever.
        history: Recent conversation history.
    """

    context: str
    sources: list[dict]
    retrieval_scores: dict
    history: list[dict]


class ContextService:
    """Service for context assembly.

    This service assembles context for RAG generation by:
    - Retrieving relevant documents via SearchService
    - Getting conversation history via ConversationService
    - Formatting context window within token limits

    Example:
        >>> service = ContextService()
        >>> result = service.assemble_context(
        ...     query="What is machine learning?",
        ...     conversation_id="uuid",
        ... )
        >>> print(result["context"])
    """

    def __init__(
        self,
        search_service: SearchService | None = None,
        conversation_service: ConversationService | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        """Initialize the context service.

        Args:
            search_service: Optional SearchService instance.
            conversation_service: Optional ConversationService instance.
            embedding_service: Optional EmbeddingService instance.
        """
        self._search_service = search_service
        self._conversation_service = conversation_service
        self._embedding_service = embedding_service

    @property
    def search_service(self):
        """Get or create SearchService instance (lazy initialization)."""
        if self._search_service is None:
            from apps.document_rag_search.services import SearchService

            self._search_service = SearchService()
        return self._search_service

    @property
    def conversation_service(self):
        """Get or create ConversationService instance (lazy initialization)."""
        if self._conversation_service is None:
            from apps.chat_agent.services.conversation_service import ConversationService

            self._conversation_service = ConversationService()
        return self._conversation_service

    @property
    def embedding_service(self):
        """Get or create EmbeddingService instance (lazy initialization)."""
        if self._embedding_service is None:
            from apps.embedding_engine.services import EmbeddingService

            self._embedding_service = EmbeddingService()
        return self._embedding_service

    # =========================================================================
    # Main Methods
    # =========================================================================

    def assemble_context(
        self,
        query: str,
        conversation_id: str,
        user_id: str | None = None,
        use_graph: bool = False,
        top_k: int = DEFAULT_TOP_K,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
        max_tokens: int = MAX_CONTEXT_TOKENS,
    ) -> ContextResult:
        """Assemble context for RAG generation.

        This method:
        1. Gets conversation history (from PostgreSQL)
        2. Performs hybrid search via SearchService
        3. Formats context window respecting token limit

        Args:
            query: User query text.
            conversation_id: Conversation ID for history.
            user_id: Optional user ID for access control.
            use_graph: Whether to use graph retriever.
            top_k: Number of documents to retrieve.
            history_limit: Number of history messages to include.
            max_tokens: Maximum tokens for context window.

        Returns:
            ContextResult with context, sources, and metadata.

        Raises:
            ContextAssemblyError: If context assembly fails.
        """
        try:
            # Get conversation history
            history_messages = self._get_history(
                conversation_id=conversation_id,
                limit=history_limit,
            )

            # Perform hybrid search
            search_response = self._retrieve_documents(
                query=query,
                user_id=user_id,
                use_graph=use_graph,
                top_k=top_k,
            )

            # Format context window
            context = self._format_context_window(
                search_results=search_response,
                history_messages=history_messages,
                max_tokens=max_tokens,
            )

            # Build result
            sources = self._extract_sources(search_response)
            retrieval_scores = self._extract_scores(search_response)

            return ContextResult(
                context=context,
                sources=sources,
                retrieval_scores=retrieval_scores,
                history=[msg.to_llm_format() for msg in history_messages],
            )

        except Exception as e:
            logger.exception(f"Context assembly failed: {e}")
            raise ContextAssemblyError(str(e))

    def retrieve_documents_only(
        self,
        query: str,
        user_id: str | None = None,
        use_graph: bool = False,
        top_k: int = DEFAULT_TOP_K,
    ):
        """Retrieve documents without context formatting.

        Args:
            query: Query text.
            user_id: Optional user ID for access control.
            use_graph: Whether to use graph retriever.
            top_k: Number of documents to retrieve.

        Returns:
            SearchResponse with results.
        """
        return self._retrieve_documents(
            query=query,
            user_id=user_id,
            use_graph=use_graph,
            top_k=top_k,
        )

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _get_history(
        self,
        conversation_id: str,
        limit: int,
    ) -> list[Any]:
        """Get conversation history.

        Args:
            conversation_id: Conversation ID.
            limit: Maximum number of messages.

        Returns:
            List of Message instances.
        """
        try:
            return self.conversation_service.get_history(
                conversation_id=conversation_id,
                limit=limit,
            )
        except Exception as e:
            logger.warning(f"Failed to get history: {e}")
            return []

    def _retrieve_documents(
        self,
        query: str,
        user_id: str | None = None,
        use_graph: bool = False,
        top_k: int = DEFAULT_TOP_K,
    ):
        """Retrieve documents using hybrid search.

        Args:
            query: Query text.
            user_id: Optional user ID.
            use_graph: Whether to use graph retriever.
            top_k: Number of results.

        Returns:
            SearchResponse with results.
        """
        from apps.document_rag_search.dto import HybridSearchRequest

        request = HybridSearchRequest(
            query=query,
            top_k=top_k,
            use_vector=True,
            use_keyword=True,
            use_graph=use_graph,
            filters={"user_id": user_id} if user_id else {},
        )

        return self.search_service.hybrid_search(request)

    def _format_context_window(
        self,
        search_results,
        history_messages: list[Any],
        max_tokens: int,
    ) -> str:
        """Format context window for LLM prompt.

        Args:
            search_results: Search results from retrieval.
            history_messages: Conversation history messages.
            max_tokens: Maximum tokens for context.

        Returns:
            Formatted context string.
        """
        parts: list[str] = []

        # Add conversation history
        if history_messages:
            parts.append("=== Conversation History ===")
            for msg in history_messages:
                role = msg.role.capitalize()
                parts.append(f"{role}: {msg.content}")
            parts.append("")

        # Add retrieved documents
        if search_results.results:
            parts.append("=== Relevant Documents ===")
            for i, result in enumerate(search_results.results, 1):
                parts.append(f"[Document {i}]")
                parts.append(f"Content: {result.text}")
                parts.append(f"Score: {result.score:.3f}")
                parts.append("")
            parts.append("")

        context = "\n".join(parts)

        # Simple token estimation (roughly 4 chars per token)
        estimated_tokens = len(context) // 4

        if estimated_tokens > max_tokens:
            # Truncate context
            char_limit = max_tokens * 4
            context = context[:char_limit] + "\n...[truncated]"
            logger.warning(
                f"Context truncated from {estimated_tokens} to ~{max_tokens} tokens"
            )

        return context

    def _extract_sources(
        self,
        search_results,
    ) -> list[dict[str, Any]]:
        """Extract source information from search results.

        Args:
            search_results: Search results.

        Returns:
            List of source dictionaries.
        """
        return [
            {
                "chunk_id": result.chunk_id,
                "document_id": result.document_id,
                "text": result.text,
                "score": result.score,
                "source": result.source,
            }
            for result in search_results.results
        ]

    def _extract_scores(
        self,
        search_results,
    ) -> dict[str, Any]:
        """Extract retrieval scores from search results.

        Args:
            search_results: Search results.

        Returns:
            Dictionary of retrieval scores.
        """
        scores: dict[str, Any] = {
            "retrievers_used": search_results.retrievers_used,
            "query_time_ms": search_results.query_time_ms,
            "total_results": search_results.total,
        }
        return scores
