"""
Constants and enums for chat_agent application.
"""

from __future__ import annotations

from enum import Enum


class AgentType(str, Enum):
    """Agent type for conversation."""

    TEXT_RAG = "text_rag"
    GRAPH_RAG = "graph_rag"


class MessageRole(str, Enum):
    """Message role in conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, Enum):
    """WebSocket message type."""

    CHAT_MESSAGE = "chat.message"
    CHAT_RESPONSE_CHUNK = "chat.response.chunk"
    CHAT_RESPONSE_COMPLETE = "chat.response.complete"
    CHAT_ERROR = "chat.error"
    CHAT_STOP = "chat.stop"


class ErrorCode(str, Enum):
    """Error codes for WebSocket messages."""

    UNAUTHORIZED = "UNAUTHORIZED"
    CONVERSATION_NOT_FOUND = "CONVERSATION_NOT_FOUND"
    RATE_LIMIT = "RATE_LIMIT"
    AGENT_ERROR = "AGENT_ERROR"
    LLM_ERROR = "LLM_ERROR"
    CONTEXT_ERROR = "CONTEXT_ERROR"
    TIMEOUT = "TIMEOUT"


# Default settings
DEFAULT_HISTORY_LIMIT = 10
DEFAULT_TOP_K = 5
DEFAULT_MAX_TOKENS = 2000
DEFAULT_TEMPERATURE = 0.7
MAX_CONTEXT_TOKENS = 4000
MAX_MESSAGE_LENGTH = 4000

# Rate limiting
MESSAGES_PER_MINUTE = 20
TOKENS_PER_MINUTE = 10000

# WebSocket settings
WEBSOCKET_HEARTBEAT = 30  # seconds
CONNECTION_TIMEOUT = 300  # seconds
