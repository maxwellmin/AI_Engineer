from __future__ import annotations

from django.urls import path

from apps.accounts.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    ProfileView,
    RegisterView,
    TokenRefreshView,
)

app_name = "accounts"

urlpatterns = [
    # Authentication endpoints
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Profile endpoints
    path("profile/", ProfileView.as_view(), name="profile"),
    path("password/change/", PasswordChangeView.as_view(), name="password_change"),
]
