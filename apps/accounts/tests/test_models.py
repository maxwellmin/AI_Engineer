"""
Tests for User model.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.accounts.tests.factories import UserFactory

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestUserModel:
    """Tests for User model creation and constraints."""

    def test_create_user_success(self) -> None:
        """Test creating a user with all fields."""
        user = UserFactory.create_user(
            username="newuser",
            email="newuser@example.com",
            password="testpass123",
            phone="13812345678",
            bio="Test bio",
        )

        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.phone == "13812345678"
        assert user.bio == "Test bio"
        assert user.check_password("testpass123")
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.is_verified is False

    def test_create_superuser_success(self) -> None:
        """Test creating a superuser with correct flags."""
        admin = UserFactory.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
        )

        assert admin.username == "admin"
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.is_verified is True
        assert admin.check_password("adminpass123")

    def test_user_str_representation(self) -> None:
        """Test that __str__ returns username."""
        user = UserFactory.create_user(username="testuser")

        assert str(user) == "testuser"

    def test_email_unique_constraint(self) -> None:
        """Test that email can be duplicate (AbstractUser default behavior).

        Note: If unique email is required, add unique=True to email field
        in the User model and create a migration.
        """
        UserFactory.create_user(
            username="user1",
            email="same@example.com",
        )

        # Create another user with same email should succeed
        # (AbstractUser.email is not unique by default)
        user2 = UserFactory.create_user(
            username="user2",
            email="same@example.com",
        )

        assert user2.email == "same@example.com"

    def test_username_unique_constraint(self) -> None:
        """Test that duplicate username raises IntegrityError."""
        UserFactory.create_user(username="samename")

        # Create another user with same username should fail
        from django.db import IntegrityError

        user2 = User(username="samename")
        user2.set_password("testpass123")
        with pytest.raises(IntegrityError):
            user2.save()

    def test_created_at_auto_populated(self) -> None:
        """Test that created_at is automatically populated."""
        user = UserFactory.create_user(username="testuser")

        assert user.created_at is not None

    def test_updated_at_auto_updated(self) -> None:
        """Test that updated_at changes on save."""
        user = UserFactory.create_user(username="testuser")
        original_updated_at = user.updated_at

        # Update user
        user.bio = "Updated bio"
        user.save()

        assert user.updated_at > original_updated_at

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        # Create user directly to avoid Factory's sequence
        user = User(username="defaultuser")
        user.set_password("testpass123")
        user.save()

        assert user.phone == ""
        assert user.avatar == ""
        assert user.bio == ""
        assert user.is_verified is False
