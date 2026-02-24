from __future__ import annotations

import logging

from knox.models import AuthToken
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as JWTTokenRefreshView

from apps.accounts.serializers import (
    PasswordChangeSerializer,
    UserLoginSerializer,
    UserRegistrationSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

logger = logging.getLogger(__name__)


def get_client_ip(request) -> str:
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


class AuthRateThrottle(AnonRateThrottle):
    """Rate throttle for authentication endpoints."""

    rate = "5/min"


class RegisterView(APIView):
    """
    User registration endpoint.

    POST /api/v1/accounts/auth/register/

    Request body:
        - username: Required, unique
        - email: Required, unique
        - password: Required, min 8 chars
        - password_confirm: Required, must match password
        - phone: Optional

    Returns:
        - User data (without password)
        - JWT access and refresh tokens
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request) -> Response:
        """Handle user registration."""
        serializer = UserRegistrationSerializer(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                f"Registration failed for username '{request.data.get('username', 'unknown')}': "
                f"{serializer.errors}"
            )
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        logger.info(
            f"User registered successfully: {user.username} "
            f"from IP: {get_client_ip(request)}"
        )

        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    User login endpoint.

    POST /api/v1/accounts/auth/login/

    Request body:
        - username: Can be username or email
        - password: Required

    Returns:
        - User data
        - JWT access and refresh tokens
        - Knox token (for API gateway compatibility)
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request) -> Response:
        """Handle user login."""
        serializer = UserLoginSerializer(data=request.data)

        if not serializer.is_valid():
            username = request.data.get("username", "unknown")
            logger.warning(
                f"Login failed for '{username}' from IP: {get_client_ip(request)}. "
                f"Errors: {serializer.errors}"
            )
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.validated_data["user"]

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Generate Knox token (returns tuple: (instance, token_string))
        _, knox_token = AuthToken.objects.create(user)

        logger.info(
            f"User logged in successfully: {user.username} "
            f"from IP: {get_client_ip(request)}"
        )

        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "knox_token": knox_token,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    User logout endpoint.

    POST /api/v1/accounts/auth/logout/

    Invalidates the Knox token and blacklists the JWT refresh token.

    Headers:
        - Authorization: Bearer <access_token>

    Request body (optional):
        - refresh: JWT refresh token to blacklist

    Returns:
        - Success message
    """

    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        """Handle user logout."""
        user = request.user
        username = user.username

        # Delete Knox token if present
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Token "):
            token_str = auth_header.split(" ")[1]
            # Knox stores only first 8 chars as token_key
            token_key = token_str[:8]
            try:
                deleted_count, _ = AuthToken.objects.filter(
                    token_key=token_key, user=user
                ).delete()
                if deleted_count > 0:
                    logger.info(f"Knox token deleted for user: {username}")
            except Exception as e:
                logger.warning(f"Failed to delete Knox token: {e}")

        # Blacklist JWT refresh token if provided
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.info(f"JWT refresh token blacklisted for user: {username}")
            except (TokenError, AttributeError, KeyError) as e:
                logger.warning(f"Failed to blacklist refresh token: {e}")

        logger.info(
            f"User logged out: {username} from IP: {get_client_ip(request)}"
        )

        return Response(
            {"message": "Successfully logged out"},
            status=status.HTTP_200_OK,
        )


class TokenRefreshView(JWTTokenRefreshView):
    """
    JWT token refresh endpoint.

    POST /api/v1/accounts/auth/refresh/

    Request body:
        - refresh: JWT refresh token

    Returns:
        - access: New JWT access token
    """

    pass


class ProfileView(APIView):
    """
    User profile endpoint.

    GET /api/v1/accounts/profile/
        - Returns current user's profile

    PATCH /api/v1/accounts/profile/
        - Updates current user's profile

    Headers:
        - Authorization: Bearer <access_token>

    Request body (PATCH):
        - email: Optional
        - phone: Optional
        - avatar: Optional
        - bio: Optional
    """

    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        """Get current user's profile."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request) -> Response:
        """Update current user's profile."""
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        logger.info(f"User profile updated: {request.user.username}")

        return Response(serializer.data, status=status.HTTP_200_OK)


class PasswordChangeView(APIView):
    """
    Password change endpoint.

    POST /api/v1/accounts/password/change/

    Headers:
        - Authorization: Bearer <access_token>

    Request body:
        - old_password: Required
        - new_password: Required, min 8 chars
        - new_password_confirm: Required, must match new_password

    Returns:
        - Success message
    """

    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        """Handle password change."""
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={"request": request},
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        logger.info(f"User password changed: {request.user.username}")

        return Response(
            {"message": "Password changed successfully"},
            status=status.HTTP_200_OK,
        )
