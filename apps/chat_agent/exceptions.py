"""
Custom exceptions for chat_agent application.
"""

from __future__ import annotations


class ChatAgentError(Exception):
    """Base exception for chat agent errors."""

    def __init__(self, message: str = "Chat agent error") -> None:
        self.message = message
        super().__init__(self.message)


class ConversationNotFoundError(ChatAgentError):
    """Conversation not found."""

    def __init__(self, conversation_id: str) -> None:
        super().__init__(f"Conversation not found: {conversation_id}")


class UnauthorizedAccessError(ChatAgentError):
    """Unauthorized access to conversation."""

    def __init__(self) -> None:
        super().__init__("Unauthorized access to conversation")


class AgentError(ChatAgentError):
    """Error during agent execution."""

    def __init__(self, agent_type: str, reason: str = "") -> None:
        super().__init__(f"Agent '{agent_type}' error: {reason}")


class LLMError(ChatAgentError):
    """Error during LLM generation."""

    def __init__(self, reason: str = "") -> None:
        super().__init__(f"LLM error: {reason}")


class ContextAssemblyError(ChatAgentError):
    """Error during context assembly."""

    def __init__(self, reason: str = "") -> None:
        super().__init__(f"Context assembly error: {reason}")


class RateLimitError(ChatAgentError):
    """Rate limit exceeded."""

    def __init__(self, limit_type: str = "messages") -> None:
        super().__init__(f"Rate limit exceeded for {limit_type}")


class TimeoutError(ChatAgentError):
    """Operation timeout."""

    def __init__(self, operation: str = "operation") -> None:
        super().__init__(f"Timeout during {operation}")
