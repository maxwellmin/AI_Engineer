"""
Tests for permission classes.
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIRequestFactory

from apps.accounts.permissions import IsSelf
from apps.accounts.tests.factories import UserFactory


@pytest.mark.django_db
@pytest.mark.unit
class TestIsSelfPermission:
    """Tests for IsSelf permission class."""

    def test_has_permission_self(self) -> None:
        """Test that user has permission for their own object."""
        user = UserFactory.create_user(username="testuser")

        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = user

        permission = IsSelf()
        result = permission.has_object_permission(request, None, user)

        assert result is True

    def test_has_permission_other(self) -> None:
        """Test that user does not have permission for others' objects."""
        user1 = UserFactory.create_user(username="user1")
        user2 = UserFactory.create_user(username="user2")

        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = user1

        permission = IsSelf()
        result = permission.has_object_permission(request, None, user2)

        assert result is False

    def test_has_permission_message(self) -> None:
        """Test that IsSelf has the correct message."""
        permission = IsSelf()

        assert permission.message == "You can only access your own profile."
