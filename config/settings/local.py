"""
Local development settings for melon project.

Override base settings for local development environment.
"""

from __future__ import annotations

from .base import *  # noqa: F401, F403

# =============================================================================
# Debug Settings
# =============================================================================

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

# =============================================================================
# Debug Toolbar
# =============================================================================

INSTALLED_APPS.append("debug_toolbar")  # noqa: F405

MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405

INTERNAL_IPS = ["127.0.0.1"]

# =============================================================================
# CORS Settings (Development)
# =============================================================================

CORS_ALLOW_ALL_ORIGINS = True

# =============================================================================
# REST Framework Settings (Development)
# =============================================================================

REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = [  # noqa: F405
    "rest_framework.permissions.AllowAny",
]

# =============================================================================
# Logging Settings (Development)
# =============================================================================

LOGGING["loggers"]["apps"]["level"] = "DEBUG"  # noqa: F405

# =============================================================================
# Email Backend (Development - print to console)
# =============================================================================

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# =============================================================================
# Static Files (Development)
# =============================================================================

STATICFILES_DIRS = [
    BASE_DIR / "static",  # noqa: F405
]

# =============================================================================
# Media Files (Development)
# =============================================================================

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"  # noqa: F405
