# Phase 3: User Management Module Implementation Plan

## Overview

Implement user management module for melon RAG project, including custom User model, multiple authentication methods (JWT + Token + Knox), and permission management.

## Current State (Phase 2 Completed)

- Django project structure established
- 7 apps created under `/apps/` (all empty skeletons)
- PostgreSQL, Redis, Milvus, Neo4j, Qwen API configured in `config/settings/base.py`
- Core infrastructure ready: `core/exceptions.py`, `core/middleware.py`, `core/pagination.py`
- Test framework configured: pytest, pytest-django, factory-boy

## Confirmed Decisions

1. **Authentication**: Support both `simplejwt` and `rest_framework.authtoken` - dual compatibility
2. **Knox Integration**: Required for API gateway token auth
3. **Docker Compose**: Manual management, no updates needed

## Implementation Tasks

### Task 1: Dependencies & Settings

Add dependencies to `pyproject.toml`:
```toml
djangorestframework-simplejwt = "^5.3.0"
django-rest-knox = "^5.0.0"
```

Update `config/settings/base.py`:
- Add `knox` to INSTALLED_APPS
- Configure REST_FRAMEWORK authentication classes (JWT, Token, Knox, Session)
- Set AUTH_USER_MODEL = "accounts.User"
- Configure SIMPLE_JWT settings (access: 15min, refresh: 7 days)

### Task 2: Custom User Model

Create `apps/accounts/models.py`:
```python
class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        indexes = [models.Index(fields=["email"]), models.Index(fields=["phone"])]
```

### Task 3: User Serializers

Create `apps/accounts/serializers.py`:
- `UserRegistrationSerializer` - username, email, password, phone (optional)
- `UserLoginSerializer` - username/email + password
- `UserSerializer` - read-only user detail output
- `UserUpdateSerializer` - profile update (exclude password)
- `PasswordChangeSerializer` - old_password + new_password validation

### Task 4: Authentication Views

Create `apps/accounts/views.py`:
- `RegisterView` - POST /api/v1/accounts/auth/register/
- `LoginView` - POST /api/v1/accounts/auth/login/ (returns JWT + Knox token)
- `LogoutView` - POST /api/v1/accounts/auth/logout/ (invalidate Knox token)
- `TokenRefreshView` - POST /api/v1/accounts/auth/refresh/ (JWT refresh)
- `ProfileView` - GET/PATCH /api/v1/accounts/profile/
- `PasswordChangeView` - POST /api/v1/accounts/password/change/

### Task 5: URL Configuration

Create `apps/accounts/urls.py`:
```python
urlpatterns = [
    path("auth/register/", RegisterView.as_view()),
    path("auth/login/", LoginView.as_view()),
    path("auth/logout/", LogoutView.as_view()),
    path("auth/refresh/", TokenRefreshView.as_view()),
    path("profile/", ProfileView.as_view()),
    path("password/change/", PasswordChangeView.as_view()),
]
```

### Task 6: Permission Classes

Create `apps/accounts/permissions.py`:
- `IsOwnerOrReadOnly` - object-level permission for profile management

### Task 7: Admin Configuration

Update `apps/accounts/admin.py`:
- Register User model with custom admin

### Task 8: Test Suite (TDD)

Create `apps/accounts/tests/`:
- `conftest.py` - shared fixtures (api_client, authenticated_user)
- `factories.py` - UserFactory with factory-boy
- `test_models.py` - User model tests
- `test_views.py` - API endpoint tests (register, login, logout, profile, password)
- `test_serializers.py` - serializer validation tests

Target: 80%+ coverage

## Files to Create/Modify

```
apps/accounts/
├── __init__.py          (exists)
├── models.py            (modify - add User model)
├── serializers.py       (create)
├── views.py             (create)
├── urls.py              (create)
├── permissions.py       (create)
├── admin.py             (modify - register User)
├── apps.py              (exists)
├── migrations/
│   └── __init__.py      (exists)
└── tests/
    ├── __init__.py      (create)
    ├── conftest.py      (create)
    ├── factories.py     (create)
    ├── test_models.py   (create)
    ├── test_views.py    (create)
    └── test_serializers.py (create)

config/settings/
└── base.py              (modify - AUTH_USER_MODEL, REST_FRAMEWORK, SIMPLE_JWT)

config/urls.py           (modify - include accounts URLs)

pyproject.toml           (modify - add simplejwt, knox)
```

## Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Request                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  DRF Authentication                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ JWT Auth    │  │ Knox Auth   │  │ Token Auth  │         │
│  │ (SPA/Web)   │  │ (API GW)    │  │ (Service)   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    User Model                                │
│  PostgreSQL: users table                                     │
└─────────────────────────────────────────────────────────────┘
```

## Execution Order

1. Add dependencies to pyproject.toml, run `poetry install`
2. Create User model in models.py
3. Update settings (AUTH_USER_MODEL, REST_FRAMEWORK, SIMPLE_JWT)
4. Run `python manage.py makemigrations accounts`
5. Run `python manage.py migrate`
6. Create serializers, views, urls, permissions, admin
7. Update root urls.py
8. Create test suite
9. Run tests, verify 80%+ coverage
