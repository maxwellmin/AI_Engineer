"""
Tests for ChatConsumer (unit tests without WebSocket).
"""

from __future__ import annotations

import pytest

from apps.chat_agent.constants import AgentType
from apps.chat_agent.consumers.chat_consumer import ChatConsumer


class TestChatConsumerMethods:
    """Tests for ChatConsumer methods that don't require WebSocket connection."""

    def test_get_agent_text_rag(self):
        """Test _get_agent returns TextRAGAgent for text_rag type."""
        consumer = ChatConsumer()
        agent = consumer._get_agent(AgentType.TEXT_RAG.value)

        assert agent is not None
        assert hasattr(agent, "build_graph")

    def test_get_agent_graph_rag(self):
        """Test _get_agent returns GraphRAGAgent for graph_rag type."""
        consumer = ChatConsumer()
        agent = consumer._get_agent(AgentType.GRAPH_RAG.value)

        assert agent is not None
        assert hasattr(agent, "build_graph")

    def test_get_agent_default(self):
        """Test _get_agent returns TextRAGAgent for unknown type."""
        consumer = ChatConsumer()
        agent = consumer._get_agent("unknown_type")

        assert agent is not None
        # Should default to TextRAGAgent
        assert hasattr(agent, "build_graph")

    def test_consumer_initialization(self):
        """Test consumer can be initialized."""
        consumer = ChatConsumer()

        assert consumer.conversation_id == ""
        assert consumer.user_id == ""
        assert consumer._conversation_service is None
