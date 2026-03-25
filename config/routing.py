"""
WebSocket URL routing for melon project.
"""

from __future__ import annotations

from django.urls import re_path

from apps.chat_agent.consumers import ChatConsumer

websocket_urlpatterns = [
    # WebSocket endpoint for chat
    # URL pattern: /ws/chat/<conversation_id>/
    re_path(r"^ws/chat/(?P<conversation_id>[0-9a-f-]+)/$", ChatConsumer.as_asgi()),
]
