"""
Agent state definitions for LangGraph-based RAG agents.

This module defines the state structure that flows through the agent graph.
"""

from __future__ import annotations

from typing import Annotated

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """
    State for RAG agent.

    This TypedDict defines the state that flows through the agent graph.
    The state is updated at each node in the graph.

    Attributes:
        conversation_id: UUID of the conversation.
        user_id: UUID of the user.
        query: User's query text.
        context: Assembled context from retrieval.
        sources: List of source documents used.
        history: Conversation history messages.
        response: Complete response text.
        response_chunks: Streaming response chunks (accumulated).
        retrieval_scores: Scores from retrieval.
        token_count: Total tokens used.
        error: Error message if any.
        message_id: ID of the saved message.
    """

    # Conversation context
    conversation_id: str
    user_id: str
    query: str

    # Retrieval context
    context: str
    sources: list[dict]
    history: list[dict]

    # Generation
    response: str
    response_chunks: Annotated[list[str], add_messages]

    # Metadata
    retrieval_scores: dict
    token_count: int
    error: str | None
    message_id: str | None


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
