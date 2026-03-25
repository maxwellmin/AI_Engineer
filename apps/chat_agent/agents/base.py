"""
Base RAG agent implementation using LangGraph.

This module provides the base class for all RAG agents, implementing
the core workflow of retrieve -> generate -> save.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from langgraph.graph import StateGraph

from apps.chat_agent.agents.state import AgentState
from apps.chat_agent.services import ContextService, ConversationService, LLMService

logger = logging.getLogger(__name__)


class BaseRAGAgent(ABC):
    """Base class for RAG agents.

    This abstract class defines the core workflow for RAG agents:
    1. Retrieve: Get relevant context from search service
    2. Generate: Stream response from LLM
    3. Save: Store conversation turn

    Subclasses should implement:
    - build_graph(): Define the agent's state graph

    Example:
        >>> class TextRAGAgent(BaseRAGAgent):
        ...     def build_graph(self) -> StateGraph:
        ...         graph = StateGraph(AgentState)
        ...         # Add nodes and edges
        ...         return graph.compile()
    """

    def __init__(
        self,
        context_service: ContextService | None = None,
        llm_service: LLMService | None = None,
        conversation_service: ConversationService | None = None,
    ) -> None:
        """Initialize the base RAG agent.

        Args:
            context_service: Optional ContextService instance.
            llm_service: Optional LLMService instance.
            conversation_service: Optional ConversationService instance.
        """
        self._context_service = context_service
        self._llm_service = llm_service
        self._conversation_service = conversation_service

    @property
    def context_service(self) -> ContextService:
        """Get or create ContextService instance (lazy initialization)."""
        if self._context_service is None:
            self._context_service = ContextService()
        return self._context_service

    @property
    def llm_service(self) -> LLMService:
        """Get or create LLMService instance (lazy initialization)."""
        if self._llm_service is None:
            self._llm_service = LLMService()
        return self._llm_service

    @property
    def conversation_service(self) -> ConversationService:
        """Get or create ConversationService instance (lazy initialization)."""
        if self._conversation_service is None:
            self._conversation_service = ConversationService()
        return self._conversation_service

    @abstractmethod
    def build_graph(self) -> StateGraph:
        """Build the agent's state graph.

        Subclasses must implement this method to define the
        workflow graph with nodes and edges.

        Returns:
            Compiled StateGraph ready for execution.
        """
        pass

    async def run(
        self,
        conversation_id: str,
        query: str,
        user_id: str,
    ) -> AsyncIterator[AgentState]:
        """Run the agent and yield state updates.

        This method executes the agent's graph and yields
        intermediate states for streaming.

        Args:
            conversation_id: Conversation ID.
            query: User query.
            user_id: User ID.

        Yields:
            AgentState updates as the graph executes.
        """
        # Build initial state
        initial_state: AgentState = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "query": query,
            "context": "",
            "sources": [],
            "history": [],
            "response": "",
            "response_chunks": [],
            "retrieval_scores": {},
            "token_count": 0,
            "error": None,
            "message_id": None,
        }

        # Get compiled graph
        graph = self.build_graph()

        try:
            # Execute graph and yield state updates
            async for event in graph.astream_events(initial_state, version="v2"):
                # Extract state updates from events
                if event.get("event") == "on_chain_end":
                    node_name = event.get("name", "")
                    if node_name and event.get("data", {}).get("output"):
                        state_update = event["data"]["output"]
                        yield state_update

        except Exception as e:
            logger.exception(f"Agent execution failed: {e}")
            yield {
                **initial_state,
                "error": str(e),
            }

    async def _retrieve_node(self, state: AgentState) -> dict:
        """Retrieve relevant context.

        This node retrieves relevant documents and conversation history.

        Args:
            state: Current agent state.

        Returns:
            State update with context and sources.
        """
        from asgiref.sync import sync_to_async

        @sync_to_async
        def assemble_context():
            return self.context_service.assemble_context(
                query=state["query"],
                conversation_id=state["conversation_id"],
                user_id=state["user_id"],
            )

        try:
            result = await assemble_context()

            return {
                "context": result["context"],
                "sources": result["sources"],
                "history": result["history"],
                "retrieval_scores": result["retrieval_scores"],
            }

        except Exception as e:
            logger.exception(f"Retrieval failed: {e}")
            return {"error": f"Retrieval error: {e}"}

    async def _generate_node(self, state: AgentState) -> dict:
        """Generate response with LLM.

        This node generates a response using the LLM service
        with the retrieved context.

        Args:
            state: Current agent state.

        Returns:
            State update with response.
        """
        try:
            # Build prompt with context
            messages = self.llm_service.build_rag_prompt(
                query=state["query"],
                context=state["context"],
                history=state["history"] if state["history"] else None,
            )

            # Stream generate response
            response_chunks: list[str] = []
            full_response = ""

            async for chunk in self.llm_service.stream_generate(messages):
                response_chunks.append(chunk)
                full_response += chunk

            # Estimate token count
            token_count = self.llm_service.estimate_tokens(full_response)

            return {
                "response": full_response,
                "response_chunks": response_chunks,
                "token_count": token_count,
            }

        except Exception as e:
            logger.exception(f"Generation failed: {e}")
            return {"error": f"Generation error: {e}"}

    async def _save_node(self, state: AgentState) -> dict:
        """Save conversation turn.

        This node saves the user message and assistant response
        to the database and optionally to Milvus.

        Args:
            state: Current agent state.

        Returns:
            State update with message ID.
        """
        from asgiref.sync import sync_to_async

        @sync_to_async
        def save_messages():
            # Save user message
            user_message = self.conversation_service.add_message(
                conversation_id=state["conversation_id"],
                role="user",
                content=state["query"],
            )

            # Save assistant message
            assistant_message = self.conversation_service.add_message(
                conversation_id=state["conversation_id"],
                role="assistant",
                content=state["response"],
                sources=[s.get("chunk_id", "") for s in state["sources"]],
                retrieval_scores=state["retrieval_scores"],
                token_count=state["token_count"],
                model_used=self.llm_service.model,
            )

            # Store message embeddings in Milvus (optional, non-blocking)
            try:
                self.conversation_service.store_message_embedding(user_message)
                self.conversation_service.store_message_embedding(assistant_message)
            except Exception as e:
                logger.warning(f"Failed to store message embeddings: {e}")

            return str(assistant_message.id)

        try:
            message_id = await save_messages()
            return {"message_id": message_id}
        except Exception as e:
            logger.exception(f"Save failed: {e}")
            return {"error": f"Save error: {e}"}
