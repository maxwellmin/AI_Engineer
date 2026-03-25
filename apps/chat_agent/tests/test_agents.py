"""
Tests for Agent classes.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.chat_agent.agents.base import BaseRAGAgent
from apps.chat_agent.agents.state import AgentState
from apps.chat_agent.agents.text_rag_agent import TextRAGAgent


class TestAgentState:
    """Tests for AgentState TypedDict."""

    def test_agent_state_creation(self):
        """Test creating an AgentState."""
        state: AgentState = {
            "conversation_id": "test-conv",
            "user_id": "user-1",
            "query": "Hello",
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

        assert state["conversation_id"] == "test-conv"
        assert state["query"] == "Hello"


class TestTextRAGAgent:
    """Tests for TextRAGAgent."""

    def test_agent_initialization(self):
        """Test agent can be initialized."""
        agent = TextRAGAgent()
        assert agent is not None

    def test_build_graph(self):
        """Test building the agent graph."""
        agent = TextRAGAgent()

        # Build the graph (this is synchronous)
        graph = agent.build_graph()

        assert graph is not None

    def test_lazy_service_initialization(self):
        """Test services are lazily initialized."""
        agent = TextRAGAgent()

        # Services should not be initialized yet
        assert agent._context_service is None
        assert agent._llm_service is None
        assert agent._conversation_service is None


class TestBaseRAGAgent:
    """Tests for BaseRAGAgent."""

    def test_cannot_instantiate_base_class(self):
        """Test that BaseRAGAgent cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseRAGAgent()

    def test_subclass_must_implement_build_graph(self):
        """Test that subclasses must implement build_graph."""

        class IncompleteAgent(BaseRAGAgent):
            pass

        with pytest.raises(TypeError):
            IncompleteAgent()
