"""
Tests for account serializers.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.test import APIRequestFactory

from apps.accounts.serializers import (
    PasswordChangeSerializer,
    UserLoginSerializer,
    UserRegistrationSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.accounts.tests.factories import UserFactory

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestUserRegistrationSerializer:
    """Tests for UserRegistrationSerializer."""

    def test_valid_registration(self) -> None:
        """Test successful user registration with valid data."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123",
        }
        serializer = UserRegistrationSerializer(data=data)

        assert serializer.is_valid()
        user = serializer.save()

        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.check_password("testpass123")

    def test_duplicate_username(self) -> None:
        """Test that duplicate username raises validation error."""
        UserFactory.create_user(username="existinguser")

        data = {
            "username": "existinguser",
            "email": "new@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123",
        }
        serializer = UserRegistrationSerializer(data=data)

        assert not serializer.is_valid()
        assert "username" in serializer.errors
        # Django default error message for unique constraint
        assert "already exists" in str(serializer.errors["username"]).lower()

    def test_duplicate_email(self) -> None:
        """Test that duplicate email raises validation error."""
        UserFactory.create_user(email="existing@example.com")

        data = {
            "username": "newuser",
            "email": "existing@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123",
        }
        serializer = UserRegistrationSerializer(data=data)

        assert not serializer.is_valid()
        assert "email" in serializer.errors
        assert "该邮箱已被注册" in str(serializer.errors["email"])

    def test_password_mismatch(self) -> None:
        """Test that password mismatch raises validation error."""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "testpass123",
            "password_confirm": "differentpass",
        }
        serializer = UserRegistrationSerializer(data=data)

        assert not serializer.is_valid()
        assert "password_confirm" in serializer.errors
        assert "两次输入的密码不一致" in str(serializer.errors["password_confirm"])

    def test_password_too_short(self) -> None:
        """Test that short password raises validation error."""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "short7",  # 7 chars, less than 8
            "password_confirm": "short7",
        }
        serializer = UserRegistrationSerializer(data=data)

        assert not serializer.is_valid()
        assert "password" in serializer.errors
        assert "密码长度至少为8个字符" in str(serializer.errors["password"])

    def test_optional_phone_field(self) -> None:
        """Test that phone field is optional."""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123",
            "phone": "13812345678",
        }
        serializer = UserRegistrationSerializer(data=data)

        assert serializer.is_valid()
        user = serializer.save()
        assert user.phone == "13812345678"


@pytest.mark.django_db
@pytest.mark.unit
class TestUserLoginSerializer:
    """Tests for UserLoginSerializer."""

    def test_login_with_username(self) -> None:
        """Test login with username."""
        UserFactory.create_user(
            username="testuser",
            password="testpass123",
        )

        data = {
            "username": "testuser",
            "password": "testpass123",
        }
        serializer = UserLoginSerializer(data=data)

        assert serializer.is_valid()
        assert serializer.validated_data["user"].username == "testuser"

    def test_login_with_email(self) -> None:
        """Test login with email instead of username."""
        UserFactory.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

        data = {
            "username": "test@example.com",  # Using email as username
            "password": "testpass123",
        }
        serializer = UserLoginSerializer(data=data)

        assert serializer.is_valid()
        assert serializer.validated_data["user"].email == "test@example.com"

    def test_invalid_username(self) -> None:
        """Test login with non-existent username."""
        data = {
            "username": "nonexistent",
            "password": "testpass123",
        }
        serializer = UserLoginSerializer(data=data)

        assert not serializer.is_valid()
        assert "username" in serializer.errors
        assert "用户名或邮箱不存在" in str(serializer.errors["username"])

    def test_invalid_password(self) -> None:
        """Test login with wrong password."""
        UserFactory.create_user(
            username="testuser",
            password="correctpass",
        )

        data = {
            "username": "testuser",
            "password": "wrongpass",
        }
        serializer = UserLoginSerializer(data=data)

        assert not serializer.is_valid()
        assert "password" in serializer.errors
        assert "密码错误" in str(serializer.errors["password"])

    def test_disabled_user(self) -> None:
        """Test login with disabled user account."""
        UserFactory.create_user(
            username="disableduser",
            password="testpass123",
            is_active=False,
        )

        data = {
            "username": "disableduser",
            "password": "testpass123",
        }
        serializer = UserLoginSerializer(data=data)

        assert not serializer.is_valid()
        assert "username" in serializer.errors
        assert "该账户已被禁用" in str(serializer.errors["username"])


@pytest.mark.django_db
@pytest.mark.unit
class TestUserSerializer:
    """Tests for UserSerializer (read-only)."""

    def test_user_serializer_output(self) -> None:
        """Test that UserSerializer outputs correct fields."""
        user = UserFactory.create_user(
            username="testuser",
            email="test@example.com",
            phone="13812345678",
            bio="Test bio",
        )

        serializer = UserSerializer(user)

        assert serializer.data["id"] == user.id
        assert serializer.data["username"] == "testuser"
        assert serializer.data["email"] == "test@example.com"
        assert serializer.data["phone"] == "13812345678"
        assert serializer.data["bio"] == "Test bio"
        assert "password" not in serializer.data

    def test_all_fields_read_only(self) -> None:
        """Test that all fields in UserSerializer are read-only."""
        serializer = UserSerializer()

        for field in serializer.Meta.read_only_fields:
            assert field in serializer.fields


@pytest.mark.django_db
@pytest.mark.unit
class TestUserUpdateSerializer:
    """Tests for UserUpdateSerializer."""

    def test_update_email_success(self) -> None:
        """Test successful email update."""
        user = UserFactory.create_user(
            username="testuser",
            email="old@example.com",
        )

        data = {"email": "new@example.com"}
        serializer = UserUpdateSerializer(user, data=data, partial=True)

        assert serializer.is_valid()
        updated_user = serializer.save()

        assert updated_user.email == "new@example.com"

    def test_update_email_duplicate(self) -> None:
        """Test that updating to existing email raises error."""
        user1 = UserFactory.create_user(
            username="user1",
            email="user1@example.com",
        )
        UserFactory.create_user(
            username="user2",
            email="user2@example.com",
        )

        data = {"email": "user2@example.com"}
        serializer = UserUpdateSerializer(user1, data=data, partial=True)

        assert not serializer.is_valid()
        assert "email" in serializer.errors
        assert "该邮箱已被其他用户使用" in str(serializer.errors["email"])

    def test_update_phone(self) -> None:
        """Test successful phone update."""
        user = UserFactory.create_user(
            username="testuser",
            phone="13800000000",
        )

        data = {"phone": "13812345678"}
        serializer = UserUpdateSerializer(user, data=data, partial=True)

        assert serializer.is_valid()
        updated_user = serializer.save()

        assert updated_user.phone == "13812345678"

    def test_update_bio(self) -> None:
        """Test successful bio update."""
        user = UserFactory.create_user(username="testuser")

        data = {"bio": "New biography"}
        serializer = UserUpdateSerializer(user, data=data, partial=True)

        assert serializer.is_valid()
        updated_user = serializer.save()

        assert updated_user.bio == "New biography"

    def test_update_avatar(self) -> None:
        """Test successful avatar URL update."""
        user = UserFactory.create_user(username="testuser")

        data = {"avatar": "https://example.com/avatar.jpg"}
        serializer = UserUpdateSerializer(user, data=data, partial=True)

        assert serializer.is_valid()
        updated_user = serializer.save()

        assert updated_user.avatar == "https://example.com/avatar.jpg"


@pytest.mark.django_db
@pytest.mark.unit
class TestPasswordChangeSerializer:
    """Tests for PasswordChangeSerializer."""

    def test_valid_password_change(self) -> None:
        """Test successful password change with correct data."""
        user = UserFactory.create_user(
            username="testuser",
            password="oldpass123",
        )

        # Create mock request with user
        factory = APIRequestFactory()
        request = factory.post("/")
        request.user = user

        data = {
            "old_password": "oldpass123",
            "new_password": "newpass123",
            "new_password_confirm": "newpass123",
        }
        serializer = PasswordChangeSerializer(data=data, context={"request": request})

        assert serializer.is_valid()
        serializer.save()

        user.refresh_from_db()
        assert user.check_password("newpass123")

    def test_wrong_old_password(self) -> None:
        """Test that wrong old password raises error."""
        user = UserFactory.create_user(
            username="testuser",
            password="correctpass",
        )

        factory = APIRequestFactory()
        request = factory.post("/")
        request.user = user

        data = {
            "old_password": "wrongpass",
            "new_password": "newpass123",
            "new_password_confirm": "newpass123",
        }
        serializer = PasswordChangeSerializer(data=data, context={"request": request})

        assert not serializer.is_valid()
        assert "old_password" in serializer.errors
        assert "原密码错误" in str(serializer.errors["old_password"])

    def test_new_password_mismatch(self) -> None:
        """Test that new password mismatch raises error."""
        user = UserFactory.create_user(
            username="testuser",
            password="oldpass123",
        )

        factory = APIRequestFactory()
        request = factory.post("/")
        request.user = user

        data = {
            "old_password": "oldpass123",
            "new_password": "newpass123",
            "new_password_confirm": "differentpass",
        }
        serializer = PasswordChangeSerializer(data=data, context={"request": request})

        assert not serializer.is_valid()
        assert "new_password_confirm" in serializer.errors
        assert "两次输入的新密码不一致" in str(serializer.errors["new_password_confirm"])

    def test_new_password_too_short(self) -> None:
        """Test that short new password raises error."""
        user = UserFactory.create_user(
            username="testuser",
            password="oldpass123",
        )

        factory = APIRequestFactory()
        request = factory.post("/")
        request.user = user

        data = {
            "old_password": "oldpass123",
            "new_password": "short7",  # 7 chars
            "new_password_confirm": "short7",
        }
        serializer = PasswordChangeSerializer(data=data, context={"request": request})

        assert not serializer.is_valid()
        assert "new_password" in serializer.errors
        assert "新密码长度至少为8个字符" in str(serializer.errors["new_password"])
