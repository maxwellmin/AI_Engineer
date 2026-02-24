"""
Custom permission classes for accounts app.
"""

from __future__ import annotations

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView


class IsSelf(permissions.BasePermission):
    """
    Permission that only allows users to access/modify their own data.

    Used for profile management where the user object IS the resource.
    This is different from IsOwner which checks if user owns another object.
    """

    message = "You can only access your own profile."

    def has_object_permission(
        self, request: Request, view: APIView, obj
    ) -> bool:
        """
        Check if the object being accessed is the request user themselves.

        Args:
            request: The HTTP request object.
            view: The view being accessed.
            obj: The object being accessed (should be a User instance).

        Returns:
            bool: True if the object is the request user, False otherwise.
        """
        return obj == request.user
