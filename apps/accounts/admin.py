"""
Admin configuration for accounts app.
"""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin for User model.

    Provides comprehensive admin interface for managing users including:
    - Custom list display with verification status
    - Filtering by active, staff, and verification status
    - Search by username, email, phone, and name fields
    - Organized fieldsets for better UX
    """

    list_display = (
        "username",
        "email",
        "phone",
        "is_active",
        "is_staff",
        "is_verified",
        "created_at",
    )
    list_filter = ("is_active", "is_staff", "is_verified", "is_superuser")
    search_fields = ("username", "email", "phone", "first_name", "last_name")
    ordering = ("-created_at",)

    readonly_fields = ("created_at", "updated_at", "last_login", "date_joined")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            _("Personal Info"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "phone",
                    "avatar",
                    "bio",
                )
            },
        ),
        (
            _("Status"),
            {
                "fields": (
                    "is_active",
                    "is_verified",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("Important Dates"),
            {
                "fields": (
                    "last_login",
                    "date_joined",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "phone",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                    "is_verified",
                ),
            },
        ),
    )
