"""
Custom API exceptions for melon project.

This module defines custom exception classes and a custom exception handler
to ensure consistent error response format across the API.
"""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


class APIErrorResponse:
    """Standard API error response format."""

    @staticmethod
    def format(
        error_code: str,
        message: str,
        details: dict[str, Any] | None = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> dict[str, Any]:
        """
        Format a standard error response.

        Args:
            error_code: Machine-readable error code (e.g., "VALIDATION_ERROR")
            message: Human-readable error message
            details: Additional error details (field errors, etc.)
            status_code: HTTP status code

        Returns:
            Dict with standard error response format
        """
        response: dict[str, Any] = {
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
            },
            "data": None,
        }
        if details:
            response["error"]["details"] = details
        return response


# =============================================================================
# Custom Exception Classes
# =============================================================================


class ValidationError(APIException):
    """Custom validation error with field-level details."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Validation error."
    default_code = "VALIDATION_ERROR"


class ResourceNotFoundError(APIException):
    """Raised when a requested resource is not found."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Resource not found."
    default_code = "RESOURCE_NOT_FOUND"


class AuthenticationFailedError(APIException):
    """Raised when authentication fails."""

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication failed."
    default_code = "AUTHENTICATION_FAILED"


class PermissionDeniedError(APIException):
    """Raised when user lacks permission for an action."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Permission denied."
    default_code = "PERMISSION_DENIED"


class ExternalServiceError(APIException):
    """Raised when an external service (LLM, Milvus, etc.) fails."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "External service unavailable."
    default_code = "EXTERNAL_SERVICE_ERROR"


class RateLimitExceededError(APIException):
    """Raised when rate limit is exceeded."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Rate limit exceeded."
    default_code = "RATE_LIMIT_EXCEEDED"


class DocumentProcessingError(APIException):
    """Raised when document processing fails."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Document processing failed."
    default_code = "DOCUMENT_PROCESSING_ERROR"


class EmbeddingError(APIException):
    """Raised when embedding generation fails."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Embedding generation failed."
    default_code = "EMBEDDING_ERROR"


# =============================================================================
# Custom Exception Handler
# =============================================================================


def custom_exception_handler(
    exc: Exception, context: dict[str, Any]
) -> Response | None:
    """
    Custom exception handler that returns consistent error responses.

    Args:
        exc: The exception that was raised
        context: The context in which the exception was raised

    Returns:
        Response with standard error format, or None if not handled
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Get error details
        error_code = getattr(exc, "code", getattr(exc, "default_code", "ERROR"))
        message = str(exc.detail) if hasattr(exc, "detail") else str(exc)

        # Handle validation errors with field details
        details = None
        if hasattr(exc, "detail") and isinstance(exc.detail, dict):
            details = exc.detail
            message = "Validation error. Check details for field errors."

        # Format response
        response.data = APIErrorResponse.format(
            error_code=str(error_code).upper(),
            message=message,
            details=details,
            status_code=response.status_code,
        )

    return response
