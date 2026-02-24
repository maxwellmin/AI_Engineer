"""
Tests for account views (API endpoints).
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.tests.factories import UserFactory

User = get_user_model()


class NoThrottleAPIClient(APIClient):
    """API client that bypasses throttling for testing."""

    def request(self, **kwargs):
        # Add REMOTE_ADDR to bypass rate limiting
        kwargs.setdefault("REMOTE_ADDR", f"127.0.0.{id(self) % 255}")
        return super().request(**kwargs)


@pytest.mark.django_db
@pytest.mark.integration
class TestRegisterView:
    """Tests for RegisterView (POST /api/v1/accounts/auth/register/)."""

    def test_register_success(self, api_client) -> None:
        """Test successful user registration."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123",
        }
        response = api_client.post("/api/v1/accounts/auth/register/", data)

        assert response.status_code == status.HTTP_201_CREATED
        assert "user" in response.data
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["username"] == "newuser"
        assert response.data["user"]["email"] == "newuser@example.com"

    def test_register_duplicate_username(self, api_client) -> None:
        """Test registration with existing username."""
        UserFactory.create_user(username="existinguser")

        data = {
            "username": "existinguser",
            "email": "new@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123",
        }
        response = api_client.post("/api/v1/accounts/auth/register/", data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "username" in response.data

    def test_register_password_mismatch(self, api_client) -> None:
        """Test registration with mismatched passwords."""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "testpass123",
            "password_confirm": "differentpass",
        }
        response = api_client.post("/api/v1/accounts/auth/register/", data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password_confirm" in response.data

    def test_register_missing_fields(self, api_client) -> None:
        """Test registration with missing required fields."""
        data = {
            "username": "newuser",
            # Missing email, password, password_confirm
        }
        response = api_client.post("/api/v1/accounts/auth/register/", data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.integration
class TestLoginView:
    """Tests for LoginView (POST /api/v1/accounts/auth/login/)."""

    def test_login_success_username(self, test_user) -> None:
        """Test successful login with username."""
        client = NoThrottleAPIClient()  # New client to avoid throttling
        data = {
            "username": "testuser",
            "password": "testpass123",
        }
        response = client.post("/api/v1/accounts/auth/login/", data)

        assert response.status_code == status.HTTP_200_OK
        assert "user" in response.data
        assert "access" in response.data
        assert "refresh" in response.data
        assert "knox_token" in response.data
        assert response.data["user"]["username"] == "testuser"

    def test_login_success_email(self) -> None:
        """Test successful login with email."""
        client = NoThrottleAPIClient()  # New client to avoid throttling
        UserFactory.create_user(
            username="emailuser",
            email="emailuser@example.com",
            password="testpass123",
        )

        data = {
            "username": "emailuser@example.com",  # Using email
            "password": "testpass123",
        }
        response = client.post("/api/v1/accounts/auth/login/", data)

        assert response.status_code == status.HTTP_200_OK
        assert "user" in response.data
        assert response.data["user"]["email"] == "emailuser@example.com"

    def test_login_invalid_credentials(self, test_user) -> None:
        """Test login with wrong password."""
        client = NoThrottleAPIClient()  # New client to avoid throttling
        data = {
            "username": "testuser",
            "password": "wrongpassword",
        }
        response = client.post("/api/v1/accounts/auth/login/", data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data

    def test_login_disabled_user(self) -> None:
        """Test login with disabled user account."""
        client = NoThrottleAPIClient()  # New client to avoid throttling
        UserFactory.create_user(
            username="disableduser",
            password="testpass123",
            is_active=False,
        )

        data = {
            "username": "disableduser",
            "password": "testpass123",
        }
        response = client.post("/api/v1/accounts/auth/login/", data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.integration
class TestLogoutView:
    """Tests for LogoutView (POST /api/v1/accounts/auth/logout/)."""

    def test_logout_success(self, authenticated_client, test_user) -> None:
        """Test successful logout with JWT token."""
        refresh = RefreshToken.for_user(test_user)

        data = {"refresh": str(refresh)}
        response = authenticated_client.post("/api/v1/accounts/auth/logout/", data)

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

    def test_logout_unauthenticated(self, api_client) -> None:
        """Test logout without authentication."""
        response = api_client.post("/api/v1/accounts/auth/logout/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
@pytest.mark.integration
class TestProfileView:
    """Tests for ProfileView (GET/PATCH /api/v1/accounts/profile/)."""

    def test_get_profile_success(self, authenticated_client, test_user) -> None:
        """Test getting user profile."""
        response = authenticated_client.get("/api/v1/accounts/profile/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == test_user.username
        assert response.data["email"] == test_user.email

    def test_update_profile_success(self, authenticated_client) -> None:
        """Test updating user profile."""
        data = {
            "bio": "New bio",
            "phone": "13812345678",
        }
        response = authenticated_client.patch("/api/v1/accounts/profile/", data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["bio"] == "New bio"
        assert response.data["phone"] == "13812345678"

    def test_get_profile_unauthenticated(self, api_client) -> None:
        """Test getting profile without authentication."""
        response = api_client.get("/api/v1/accounts/profile/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_profile_duplicate_email(
        self, authenticated_client, another_user
    ) -> None:
        """Test updating profile to existing email."""
        data = {"email": another_user.email}
        response = authenticated_client.patch("/api/v1/accounts/profile/", data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data


@pytest.mark.django_db
@pytest.mark.integration
class TestPasswordChangeView:
    """Tests for PasswordChangeView (POST /api/v1/accounts/password/change/)."""

    def test_change_password_success(self, authenticated_client) -> None:
        """Test successful password change."""
        data = {
            "old_password": "testpass123",
            "new_password": "newpass123",
            "new_password_confirm": "newpass123",
        }
        response = authenticated_client.post(
            "/api/v1/accounts/password/change/", data
        )

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

    def test_change_password_wrong_old(self, authenticated_client) -> None:
        """Test password change with wrong old password."""
        data = {
            "old_password": "wrongpassword",
            "new_password": "newpass123",
            "new_password_confirm": "newpass123",
        }
        response = authenticated_client.post(
            "/api/v1/accounts/password/change/", data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "old_password" in response.data

    def test_change_password_unauthenticated(self, api_client) -> None:
        """Test password change without authentication."""
        data = {
            "old_password": "oldpass123",
            "new_password": "newpass123",
            "new_password_confirm": "newpass123",
        }
        response = api_client.post("/api/v1/accounts/password/change/", data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
@pytest.mark.integration
class TestTokenRefreshView:
    """Tests for TokenRefreshView (POST /api/v1/accounts/auth/refresh/)."""

    def test_refresh_success(self, api_client, test_user) -> None:
        """Test successful token refresh."""
        refresh = RefreshToken.for_user(test_user)

        data = {"refresh": str(refresh)}
        response = api_client.post("/api/v1/accounts/auth/refresh/", data)

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_refresh_invalid_token(self, api_client) -> None:
        """Test token refresh with invalid token."""
        data = {"refresh": "invalid_token"}
        response = api_client.post("/api/v1/accounts/auth/refresh/", data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
