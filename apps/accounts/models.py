from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.

    Additional fields:
    - phone: User's phone number (optional)
    - avatar: URL to user's avatar image (optional)
    - bio: User's biography/description (optional)
    - is_verified: Whether the user has verified their email
    """

    phone = models.CharField(max_length=20, blank=True, default="")
    avatar = models.URLField(max_length=500, blank=True, default="")
    bio = models.TextField(blank=True, default="")
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["phone"]),
        ]

    def __str__(self) -> str:
        return self.username
