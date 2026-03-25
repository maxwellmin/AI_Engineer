"""
Text RAG Agent implementation.

This module provides a simple RAG agent with a linear workflow:
retrieve -> generate -> save
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph

from apps.chat_agent.agents.base import BaseRAGAgent
from apps.chat_agent.agents.state import AgentState

logger = logging.getLogger(__name__)


class TextRAGAgent(BaseRAGAgent):
    """Text RAG agent for basic Q&A.

    This agent implements a simple linear workflow:
    1. Retrieve relevant documents and context
    2. Generate response using LLM
    3. Save conversation turn

    Graph structure:
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ retrieve │ -> │ generate │ -> │   save   │
        └──────────┘    └──────────┘    └──────────┘

    Example:
        >>> agent = TextRAGAgent()
        >>> async for state in agent.run(conversation_id, query, user_id):
        ...     print(state.get("response", ""))
    """

    def build_graph(self) -> StateGraph:
        """Build the linear RAG graph.

        The graph has three nodes:
        - retrieve: Get relevant context
        - generate: Generate response with LLM
        - save: Save conversation turn

        Returns:
            Compiled StateGraph.
        """
        # Create graph with AgentState
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("retrieve", self._retrieve_node)
        graph.add_node("generate", self._generate_node)
        graph.add_node("save", self._save_node)

        # Set entry point
        graph.set_entry_point("retrieve")

        # Add edges
        graph.add_edge("retrieve", "generate")
        graph.add_edge("generate", "save")

        # Set finish point
        graph.set_finish_point("save")

        # Compile and return
        return graph.compile()

    async def run_with_streaming(
        self,
        conversation_id: str,
        query: str,
        user_id: str,
    ):
        """Run with real-time streaming of response chunks.

        This method yields response chunks as they are generated,
        suitable for WebSocket streaming.

        Args:
            conversation_id: Conversation ID.
            query: User query.
            user_id: User ID.

        Yields:
            Tuple of (event_type, data) for streaming.
        """
        import asyncio

        # Build initial state
        state: AgentState = {
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

        try:
            # Step 1: Retrieve
            yield ("status", "retrieving")
            retrieve_result = await self._retrieve_node(state)
            state.update(retrieve_result)

            if state.get("error"):
                yield ("error", state["error"])
                return

            # Step 2: Generate with streaming
            yield ("status", "generating")

            messages = self.llm_service.build_rag_prompt(
                query=state["query"],
                context=state["context"],
                history=state["history"] if state["history"] else None,
            )

            response_chunks: list[str] = []
            full_response = ""

            async for chunk in self.llm_service.stream_generate(messages):
                response_chunks.append(chunk)
                full_response += chunk
                yield ("chunk", chunk)

            state["response"] = full_response
            state["response_chunks"] = response_chunks
            state["token_count"] = self.llm_service.estimate_tokens(full_response)

            # Step 3: Save
            yield ("status", "saving")
            save_result = await self._save_node(state)
            state.update(save_result)

            if state.get("error"):
                yield ("error", state["error"])
                return

            # Final result
            yield ("complete", {
                "message_id": state["message_id"],
                "sources": state["sources"],
                "token_count": state["token_count"],
            })

        except Exception as e:
            logger.exception(f"Agent execution failed: {e}")
            yield ("error", str(e))
