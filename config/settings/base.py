"""
Base Django settings for melon project.

This file contains all common settings shared across environments.
Environment-specific settings should be defined in local.py or production.py.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env file
# Priority: environment variables > .env file
env_file = BASE_DIR / "env" / ".env.local"
if env_file.exists():
    load_dotenv(env_file)

# =============================================================================
# Core Settings
# =============================================================================

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-change-me-in-production")

DEBUG = False

ALLOWED_HOSTS: list[str] = []

# =============================================================================
# Application Definition
# =============================================================================

INSTALLED_APPS = [
    # Django built-in apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_filters",
    "drf_yasg",
    # Local apps
    "apps.accounts",
    "apps.documents_parser",
    "apps.document_pipeline_manager",
    "apps.milvus_database_controller",
    "apps.neo4j_database_controller",
    "apps.embedding_engine",
    "apps.rag_processing",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.RequestLoggingMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# =============================================================================
# Database Configuration
# =============================================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "Melon"),
        "USER": os.environ.get("DB_USER", "maxmelonmind"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "melonmind123"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# =============================================================================
# Redis Configuration
# =============================================================================

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# =============================================================================
# Celery Configuration
# =============================================================================

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# =============================================================================
# Milvus Configuration
# =============================================================================

MILVUS_HOST = os.environ.get("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.environ.get("MILVUS_PORT", "19530"))

MILVUS_CONFIG = {
    "host": MILVUS_HOST,
    "port": MILVUS_PORT,
    # Collection names
    "documents_collection": "documents",
    "chat_history_collection": "chat_history",
    # Index settings
    "index_type": "IVF_FLAT",
    "metric_type": "COSINE",
    "nlist": 128,
    "nprobe": 10,
}

# =============================================================================
# Neo4j Configuration
# =============================================================================

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")

NEO4J_CONFIG = {
    "uri": NEO4J_URI,
    "user": NEO4J_USER,
    "password": NEO4J_PASSWORD,
}

# =============================================================================
# Qwen API Configuration
# =============================================================================

QWEN_API_KEY = os.environ.get("QWEN_API_KEY", "")
QWEN_BASE_URL = os.environ.get(
    "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
QWEN_EMBEDDING_MODEL = os.environ.get("QWEN_EMBEDDING_MODEL", "text-embedding-v1")
QWEN_CHAT_MODEL = os.environ.get("QWEN_CHAT_MODEL", "qwen-2-7b")

QWEN_CONFIG = {
    "api_key": QWEN_API_KEY,
    "base_url": QWEN_BASE_URL,
    "embedding_model": QWEN_EMBEDDING_MODEL,
    "chat_model": QWEN_CHAT_MODEL,
    "embedding_dimension": 1536,  # text-embedding-v1 dimension
}

# =============================================================================
# Password Validation
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# =============================================================================
# Internationalization
# =============================================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# =============================================================================
# Static Files
# =============================================================================

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# =============================================================================
# Default Primary Key Field Type
# =============================================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# REST Framework Configuration
# =============================================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_yasg.generators.OpenAPISchemaGenerator",
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}

# =============================================================================
# CORS Configuration
# =============================================================================

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS: list[str] = []

# =============================================================================
# Logging Configuration
# =============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
