"""
Chat Agent Application Configuration.
"""

from __future__ import annotations

from django.apps import AppConfig


class ChatAgentConfig(AppConfig):
    """Configuration for chat_agent application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.chat_agent"
    verbose_name = "Chat Agent"

    def ready(self) -> None:
        """Initialize application when ready."""
        # Import signals if any
        pass
