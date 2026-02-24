"""
Custom middleware for melon project.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """
    Middleware to log all HTTP requests with timing information.

    Logs method, path, status code, and response time for each request.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Record start time
        start_time = time.perf_counter()

        # Process request
        response = self.get_response(request)

        # Calculate duration
        duration = time.perf_counter() - start_time
        duration_ms = round(duration * 1000, 2)

        # Log request info
        log_data = {
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user_id": self._get_user_id(request),
            "ip": self._get_client_ip(request),
        }

        # Choose log level based on status code
        if response.status_code >= 500:
            logger.error("HTTP request", extra=log_data)
        elif response.status_code >= 400:
            logger.warning("HTTP request", extra=log_data)
        else:
            logger.info("HTTP request", extra=log_data)

        # Add timing header
        response["X-Response-Time"] = f"{duration_ms}ms"

        return response

    def _get_user_id(self, request: HttpRequest) -> str | None:
        """Get user ID from request if authenticated."""
        if hasattr(request, "user") and request.user.is_authenticated:
            return str(request.user.pk)
        return None

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")


class CorrelationIdMiddleware:
    """
    Middleware to add correlation ID to requests for tracing.

    If X-Correlation-ID header is present, uses it. Otherwise, generates a new one.
    """

    _HEADER_NAME = "X-Correlation-ID"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Get or generate correlation ID
        correlation_id = request.META.get(
            f"HTTP_{self._HEADER_NAME.replace('-', '_')}",
            self._generate_correlation_id(),
        )

        # Store in request for use in views
        request.correlation_id = correlation_id  # type: ignore[attr-defined]

        # Process request
        response = self.get_response(request)

        # Add correlation ID to response headers
        response[self._HEADER_NAME] = correlation_id

        return response

    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID."""
        import uuid

        return str(uuid.uuid4())
