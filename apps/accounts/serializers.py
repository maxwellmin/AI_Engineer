from __future__ import annotations

import logging
import re

from django.contrib.auth import get_user_model
from rest_framework import serializers

logger = logging.getLogger(__name__)

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.

    Fields:
        - username: Required, unique
        - email: Required, unique, validated as email
        - password: Required, write-only, min 8 chars
        - password_confirm: Required, write-only, must match password
        - phone: Optional

    Validates:
        - Password confirmation match
        - Unique username
        - Unique email
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={"min_length": "密码长度至少为8个字符"},
    )
    password_confirm = serializers.CharField(write_only=True)
    phone = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "password_confirm", "phone"]
        read_only_fields = ["id"]

    def validate_username(self, value: str) -> str:
        """Validate username uniqueness."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("该用户名已被注册")
        return value

    def validate_email(self, value: str) -> str:
        """Validate email uniqueness."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("该邮箱已被注册")
        return value

    def validate(self, attrs: dict) -> dict:
        """Validate password confirmation match."""
        password = attrs.get("password")
        password_confirm = attrs.get("password_confirm")

        if password != password_confirm:
            raise serializers.ValidationError(
                {"password_confirm": "两次输入的密码不一致"}
            )

        return attrs

    def create(self, validated_data: dict) -> User:
        """Create user with hashed password."""
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        logger.info(f"User registered: {user.username}")
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login.

    Fields:
        - username: Can be username or email
        - password: Required, write-only

    Validates:
        - User exists with given username/email
        - Password is correct
        - User is active
    """

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        """Validate credentials and return user if valid."""
        username = attrs.get("username")
        password = attrs.get("password")

        # Try to find user by username or email
        user = User.objects.filter(username=username).first()
        if not user:
            user = User.objects.filter(email=username).first()

        if not user:
            raise serializers.ValidationError(
                {"username": "用户名或邮箱不存在"}
            )

        if not user.check_password(password):
            raise serializers.ValidationError(
                {"password": "密码错误"}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"username": "该账户已被禁用"}
            )

        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for user detail output.

    Fields:
        - id: User ID
        - username: Username
        - email: Email address
        - phone: Phone number
        - avatar: Avatar URL
        - bio: Biography
        - is_verified: Email verification status
        - created_at: Account creation time
        - updated_at: Last update time
    """

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone",
            "avatar",
            "bio",
            "is_verified",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile update.

    Fields:
        - email: Optional, validated for uniqueness
        - phone: Optional
        - avatar: Optional, validated as URL
        - bio: Optional

    Validates:
        - Email uniqueness (excluding current user)
    """

    class Meta:
        model = User
        fields = ["email", "phone", "avatar", "bio"]

    def validate_email(self, value: str) -> str:
        """Validate email uniqueness excluding current user."""
        user = self.instance
        if User.objects.filter(email=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("该邮箱已被其他用户使用")
        return value

    def update(self, instance: User, validated_data: dict) -> User:
        """Update user profile."""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        logger.info(f"User profile updated: {instance.username}")
        return instance


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change.

    Fields:
        - old_password: Required, write-only
        - new_password: Required, write-only, min 8 chars
        - new_password_confirm: Required, write-only, must match new_password

    Validates:
        - old_password matches current password
        - new_password matches new_password_confirm
    """

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={"min_length": "新密码长度至少为8个字符"},
    )
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_old_password(self, value: str) -> str:
        """Validate that old_password matches current password."""
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("原密码错误")
        return value

    def validate(self, attrs: dict) -> dict:
        """Validate new password confirmation match."""
        new_password = attrs.get("new_password")
        new_password_confirm = attrs.get("new_password_confirm")

        if new_password != new_password_confirm:
            raise serializers.ValidationError(
                {"new_password_confirm": "两次输入的新密码不一致"}
            )

        return attrs

    def save(self) -> None:
        """Save new password."""
        user = self.context["request"].user
        new_password = self.validated_data["new_password"]
        user.set_password(new_password)
        user.save()
        logger.info(f"User password changed: {user.username}")
