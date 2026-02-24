"""
Custom permission classes for melon project.
"""

from __future__ import annotations

from typing import Any

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView


class IsAuthenticated(permissions.IsAuthenticated):
    """
    Extended IsAuthenticated permission with custom message.

    Returns a more descriptive message when authentication fails.
    """

    message = "Authentication required. Please provide valid credentials."


class IsAdminUser(permissions.IsAdminUser):
    """
    Extended IsAdminUser permission with custom message.

    Only allows access to admin users (is_staff=True).
    """

    message = "Admin access required."


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission that only allows owners to edit objects.

    Assumes the model instance has an 'owner' or 'user' attribute.
    """

    message = "You do not have permission to perform this action."

    def has_object_permission(
        self, request: Request, view: APIView, obj: Any
    ) -> bool:
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner
        owner = getattr(obj, "owner", None) or getattr(obj, "user", None)
        return owner == request.user


class IsOwner(permissions.BasePermission):
    """
    Object-level permission that only allows owners to access objects.

    More restrictive than IsOwnerOrReadOnly - no read access for non-owners.
    """

    message = "You do not have permission to access this resource."

    def has_object_permission(
        self, request: Request, view: APIView, obj: Any
    ) -> bool:
        owner = getattr(obj, "owner", None) or getattr(obj, "user", None)
        return owner == request.user


class IsAuthenticatedOrReadOnly(permissions.IsAuthenticatedOrReadOnly):
    """
    Extended IsAuthenticatedOrReadOnly with custom message.

    Allows read-only access to unauthenticated users.
    """

    message = "Authentication required for write operations."


class AllowAny(permissions.AllowAny):
    """
    Explicit AllowAny permission for clarity in view definitions.
    """

    pass
