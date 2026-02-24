"""
Shared pytest fixtures for accounts app tests.
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.tests.factories import UserFactory


@pytest.fixture
def api_client() -> APIClient:
    """
    Unauthenticated DRF API client.

    Use this for testing endpoints that don't require authentication
    or for manually adding authentication headers.
    """
    return APIClient()


@pytest.fixture
def test_user():
    """
    Regular user for testing.

    Creates a user with known credentials:
    - username: testuser
    - email: testuser@example.com
    - password: testpass123
    """
    return UserFactory.create_user(
        username="testuser",
        email="testuser@example.com",
        password="testpass123",
    )


@pytest.fixture
def admin_user():
    """
    Superuser for admin testing.

    Creates a superuser with known credentials:
    - username: adminuser
    - email: admin@example.com
    - password: adminpass123
    """
    return UserFactory.create_superuser(
        username="adminuser",
        email="admin@example.com",
        password="adminpass123",
    )


@pytest.fixture
def authenticated_client(api_client: APIClient, test_user) -> APIClient:
    """
    API client authenticated as test_user via JWT.

    The client has Authorization header set with Bearer token.
    Use this for testing endpoints that require authentication.
    """
    refresh = RefreshToken.for_user(test_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def knox_authenticated_client(api_client: APIClient, test_user) -> APIClient:
    """
    API client authenticated via Knox token.

    Use this for testing Knox token authentication.
    """
    from knox.models import AuthToken

    token = AuthToken.objects.create(test_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return api_client


@pytest.fixture
def another_user():
    """
    Another regular user for testing multi-user scenarios.

    Creates a user with known credentials:
    - username: anotheruser
    - email: anotheruser@example.com
    - password: anotherpass123
    """
    return UserFactory.create_user(
        username="anotheruser",
        email="anotheruser@example.com",
        password="anotherpass123",
    )
