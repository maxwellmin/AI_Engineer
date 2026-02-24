"""
Django settings module selector.

This module selects the appropriate settings based on the DJANGO_SETTINGS_MODULE
environment variable. If not set, defaults to local settings for development.
"""

import os

# Default to local settings if not specified
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
