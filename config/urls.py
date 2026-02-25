"""
Root URL configuration for melon project.
"""

from __future__ import annotations

from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Melon API",
        default_version="v1",
        description="Django REST API for RAG-based document knowledge base",
        contact=openapi.Contact(email="stttt2003pk@gmail.com"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # API documentation
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    # API endpoints
    path("api/v1/accounts/", include("apps.accounts.urls")),
    path("api/v1/documents/", include("apps.documents_parser.urls")),
    path("api/v1/storage/", include("apps.object_storage_controller.urls")),
]

# Debug toolbar URLs (only in debug mode)
import os
if os.environ.get("DEBUG", "False").lower() == "true":
    import debug_toolbar
    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns

# Serve media files in development
from django.conf import settings
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
