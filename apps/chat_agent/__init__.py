"""
Chat Agent Application

This module provides real-time conversational AI capabilities based on RAG
(Retrieval-Augmented Generation) technology with WebSocket streaming support.

Key Features:
- Real-time chat via WebSocket
- RAG-based response generation
- Conversation history management
- Multiple agent types (Text RAG, Graph RAG)
"""

from __future__ import annotations

default_app_config = "apps.chat_agent.apps.ChatAgentConfig"
