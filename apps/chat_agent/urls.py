"""
URL routing for chat_agent application.
"""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.chat_agent.views.chat_views import ConversationViewSet, MessageViewSet

router = DefaultRouter()
router.register(r"conversations", ConversationViewSet, basename="conversation")
router.register(r"messages", MessageViewSet, basename="message")

urlpatterns = [
    path("", include(router.urls)),
]
