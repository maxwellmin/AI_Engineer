"""
WebSocket middleware for Chat Agent module.

This module provides custom authentication middleware for WebSocket connections
that supports JWT token authentication instead of session-based authentication.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)

# Get the custom User model
User = get_user_model()


class JWTAuthMiddleware:
    """JWT authentication middleware for Django Channels WebSocket.

    This middleware extracts JWT token from the Authorization header and
    authenticates the user for WebSocket connections.

    Unlike Django's AuthMiddlewareStack which uses session-based authentication,
    this middleware uses JWT tokens sent in the Authorization header.

    Usage:
        # In asgi.py
        application = ProtocolTypeRouter({
            "websocket": AllowedHostsOriginValidator(
                JWTAuthMiddleware(URLRouter(websocket_urlpatterns))
            ),
        })

    WebSocket Connection Examples:

        # Using wscat with Bearer token
        wscat -c "ws://localhost:8000/ws/chat/<conversation_id>/" \\
            -H "Authorization: Bearer <jwt_token>"

        # Using JavaScript WebSocket
        const ws = new WebSocket(
            'ws://localhost:8000/ws/chat/<conversation_id>/',
            [],
            { headers: { 'Authorization': 'Bearer <jwt_token>' } }
        );

    Token Extraction Priority:
        1. Authorization header (Bearer token)
        2. Query parameter (for browser compatibility): ?token=<jwt_token>

    Note:
        - Token must be a valid AccessToken from rest_framework_simplejwt
        - Expired tokens will be rejected
        - Blacklisted tokens will be rejected (if token blacklist is enabled)
    """

    # Header name for JWT token
    AUTH_HEADER_NAME = "Authorization"
    AUTH_HEADER_TYPE = "Bearer"

    def __init__(self, inner: Callable[[dict], Awaitable[Any]]) -> None:
        """Initialize the middleware.

        Args:
            inner: The inner ASGI application to wrap.
        """
        self.inner = inner

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> Any:
        """Process the WebSocket connection.

        Args:
            scope: The ASGI scope dictionary.
            receive: The ASGI receive callable.
            send: The ASGI send callable.

        Returns:
            The result of the inner ASGI application.
        """
        # Only handle WebSocket connections
        if scope["type"] != "websocket":
            return await self.inner(scope, receive, send)

        # Get token from headers or query string
        token = self._get_token(scope)

        if token:
            # Validate token and get user
            user = await self._get_user_from_token(token)
            scope["user"] = user

            if user and not isinstance(user, AnonymousUser):
                logger.debug(
                    f"WebSocket authenticated via JWT: user_id={user.id}, "
                    f"username={user.username}"
                )
            else:
                logger.warning("WebSocket authentication failed: invalid token")
        else:
            # No token provided, set anonymous user
            scope["user"] = AnonymousUser()
            logger.debug("WebSocket connection without token: using anonymous user")

        return await self.inner(scope, receive, send)

    def _get_token(self, scope: dict) -> str | None:
        """Extract JWT token from the scope.

        Tries to get token from:
        1. Authorization header (Bearer token)
        2. Query string parameter (token)

        Args:
            scope: The ASGI scope dictionary.

        Returns:
            The JWT token string or None if not found.
        """
        # Try to get token from Authorization header
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(
            self.AUTH_HEADER_NAME.lower().encode(), b""
        ).decode()

        if auth_header:
            # Parse Bearer token
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == self.AUTH_HEADER_TYPE.lower():
                return parts[1]

        # Try to get token from query string
        query_string = scope.get("query_string", b"").decode()
        if query_string:
            params = dict(
                pair.split("=", 1) if "=" in pair else (pair, "")
                for pair in query_string.split("&")
            )
            if "token" in params:
                return params["token"]

        return None

    def _get_user_from_token_sync(self, token: str) -> User | AnonymousUser:
        """Validate JWT token and get the user (synchronous version).

        Args:
            token: The JWT token string.

        Returns:
            The authenticated User or AnonymousUser if invalid.
        """
        try:
            # Validate and decode the token
            access_token = AccessToken(token)

            # Get user ID from token payload
            user_id = access_token.get("user_id")

            if not user_id:
                logger.warning("Token does not contain user_id")
                return AnonymousUser()

            # Get user from database
            try:
                user = User.objects.get(id=user_id)
                return user
            except User.DoesNotExist:
                logger.warning(f"User not found: user_id={user_id}")
                return AnonymousUser()

        except InvalidToken as e:
            logger.warning(f"Invalid token: {e}")
            return AnonymousUser()
        except TokenError as e:
            logger.warning(f"Token error: {e}")
            return AnonymousUser()
        except Exception as e:
            logger.exception(f"Unexpected error during token validation: {e}")
            return AnonymousUser()

    # Async wrapper for use in __call__
    _get_user_from_token = database_sync_to_async(_get_user_from_token_sync)
