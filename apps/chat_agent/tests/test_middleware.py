"""
Tests for JWT WebSocket middleware.
"""

from __future__ import annotations

import pytest
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.chat_agent.middleware import JWTAuthMiddleware


@pytest.fixture
def test_user(db) -> User:
    """Create a test user."""
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )
    return user


@pytest.fixture
def jwt_token(test_user) -> str:
    """Generate a valid JWT access token for the test user."""
    refresh = RefreshToken.for_user(test_user)
    return str(refresh.access_token)


@pytest.fixture
def async_test_user(db):
    """Create a test user for async tests."""
    from asgiref.sync import sync_to_async
    
    @sync_to_async
    def create_user():
        return User.objects.create_user(
            username="async_testuser",
            email="async_test@example.com",
            password="testpass123",
        )
    
    return create_user()


@pytest.fixture
async def async_jwt_token(async_test_user):
    """Generate a valid JWT access token for the async test user."""
    user = await async_test_user
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


class TestJWTAuthMiddleware:
    """Tests for JWTAuthMiddleware."""

    @pytest.mark.asyncio
    @pytest.mark.django_db(transaction=True)
    async def test_valid_token_in_header(self, db):
        """Test authentication with valid token in Authorization header."""
        # Create user using sync_to_async to ensure test database is used
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def create_user_and_token():
            user = User.objects.create_user(
                username="testuser_header",
                email="test_header@example.com",
                password="testpass123",
            )
            refresh = RefreshToken.for_user(user)
            return user, str(refresh.access_token)
        
        test_user, jwt_token = await create_user_and_token()
        
        # Create a simple ASGI app that returns the scope
        captured_scope = {}

        async def test_app(scope, receive, send):
            captured_scope.update(scope)
            await send({"type": "websocket.accept"})

        # Create middleware-wrapped app
        middleware = JWTAuthMiddleware(test_app)

        # Create communicator with Authorization header
        communicator = WebsocketCommunicator(
            middleware,
            "/ws/test/",
            headers=[
                (b"authorization", f"Bearer {jwt_token}".encode()),
            ],
        )

        # Connect
        connected, _ = await communicator.connect()

        # Verify connection succeeded and user is authenticated
        assert connected is True
        result_user = captured_scope.get("user")
        assert result_user is not None
        assert result_user.id == test_user.id
        assert result_user.username == test_user.username

        # Clean up
        await communicator.disconnect()

    @pytest.mark.asyncio
    @pytest.mark.django_db(transaction=True)
    async def test_valid_token_in_query(self, db):
        """Test authentication with valid token in query string."""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def create_user_and_token():
            user = User.objects.create_user(
                username="testuser_query",
                email="test_query@example.com",
                password="testpass123",
            )
            refresh = RefreshToken.for_user(user)
            return user, str(refresh.access_token)
        
        test_user, jwt_token = await create_user_and_token()
        
        captured_scope = {}

        async def test_app(scope, receive, send):
            captured_scope.update(scope)
            await send({"type": "websocket.accept"})

        middleware = JWTAuthMiddleware(test_app)

        # Create communicator with token in query string
        communicator = WebsocketCommunicator(
            middleware,
            f"/ws/test/?token={jwt_token}",
        )

        connected, _ = await communicator.connect()

        assert connected is True
        result_user = captured_scope.get("user")
        assert result_user is not None
        assert result_user.id == test_user.id

        await communicator.disconnect()

    @pytest.mark.asyncio
    @pytest.mark.django_db
    async def test_no_token_anonymous_user(self):
        """Test that connection without token results in anonymous user."""
        captured_scope = {}

        async def test_app(scope, receive, send):
            captured_scope.update(scope)
            await send({"type": "websocket.accept"})

        middleware = JWTAuthMiddleware(test_app)

        communicator = WebsocketCommunicator(middleware, "/ws/test/")

        connected, _ = await communicator.connect()

        assert connected is True
        # The user should be AnonymousUser
        result_user = captured_scope.get("user")
        assert result_user.is_anonymous is True

        await communicator.disconnect()

    @pytest.mark.asyncio
    @pytest.mark.django_db
    async def test_invalid_token(self):
        """Test that invalid token results in anonymous user."""
        captured_scope = {}

        async def test_app(scope, receive, send):
            captured_scope.update(scope)
            await send({"type": "websocket.accept"})

        middleware = JWTAuthMiddleware(test_app)

        communicator = WebsocketCommunicator(
            middleware,
            "/ws/test/",
            headers=[
                (b"authorization", b"Bearer invalid_token"),
            ],
        )

        connected, _ = await communicator.connect()

        assert connected is True
        result_user = captured_scope.get("user")
        assert result_user.is_anonymous is True

        await communicator.disconnect()

    def test_token_extraction_from_header(self):
        """Test _get_token method extracts token from header."""
        middleware = JWTAuthMiddleware(lambda x: x)

        scope = {
            "type": "websocket",
            "headers": [
                (b"authorization", b"Bearer test_token_123"),
            ],
        }

        token = middleware._get_token(scope)

        assert token == "test_token_123"

    def test_token_extraction_from_query(self):
        """Test _get_token method extracts token from query string."""
        middleware = JWTAuthMiddleware(lambda x: x)

        scope = {
            "type": "websocket",
            "headers": [],
            "query_string": b"token=query_token_456",
        }

        token = middleware._get_token(scope)

        assert token == "query_token_456"

    def test_token_extraction_priority(self):
        """Test that header token takes priority over query string."""
        middleware = JWTAuthMiddleware(lambda x: x)

        scope = {
            "type": "websocket",
            "headers": [
                (b"authorization", b"Bearer header_token"),
            ],
            "query_string": b"token=query_token",
        }

        token = middleware._get_token(scope)

        assert token == "header_token"

    def test_no_token_returns_none(self):
        """Test that _get_token returns None when no token is present."""
        middleware = JWTAuthMiddleware(lambda x: x)

        scope = {
            "type": "websocket",
            "headers": [],
            "query_string": b"",
        }

        token = middleware._get_token(scope)

        assert token is None

    def test_token_extraction_case_insensitive(self):
        """Test that Bearer token extraction is case insensitive."""
        middleware = JWTAuthMiddleware(lambda x: x)

        # Test with lowercase 'bearer'
        scope = {
            "type": "websocket",
            "headers": [
                (b"authorization", b"bearer test_token_lower"),
            ],
        }

        token = middleware._get_token(scope)

        assert token == "test_token_lower"
