# Phase 3: User Management Module Implementation Plan

## Overview

Implement user management module for melon RAG project, including custom User model, multiple authentication methods (JWT + Token + Knox), and permission management.

## Status: ✅ COMPLETED (2026-02-24)

## Completed Work Summary

### Task 1: Dependencies & Settings ✅
- Added `djangorestframework-simplejwt` and `django-rest-knox` to pyproject.toml
- Configured REST_FRAMEWORK authentication classes (JWT, Token, Knox, Session)
- Set AUTH_USER_MODEL = "accounts.User"
- Configured SIMPLE_JWT settings (access: 15min, refresh: 7 days)

### Task 2: Custom User Model ✅
Created `apps/accounts/models.py`:
- User model extending AbstractUser
- Fields: phone, avatar, bio, is_verified, created_at, updated_at
- db_table = "users"
- Indexes on email and phone

### Task 3: User Serializers ✅
Created `apps/accounts/serializers.py`:
- `UserRegistrationSerializer` - username, email, password, phone (optional)
- `UserLoginSerializer` - username/email + password
- `UserSerializer` - read-only user detail output
- `UserUpdateSerializer` - profile update (exclude password)
- `PasswordChangeSerializer` - old_password + new_password validation

### Task 4: Authentication Views ✅
Created `apps/accounts/views.py`:
- `RegisterView` - POST /api/v1/accounts/auth/register/
- `LoginView` - POST /api/v1/accounts/auth/login/ (returns JWT + Knox token)
- `LogoutView` - POST /api/v1/accounts/auth/logout/ (invalidate Knox token)
- `TokenRefreshView` - POST /api/v1/accounts/auth/refresh/ (JWT refresh)
- `ProfileView` - GET/PATCH /api/v1/accounts/profile/
- `PasswordChangeView` - POST /api/v1/accounts/password/change/

### Task 5: URL Configuration ✅
Created `apps/accounts/urls.py`:
- All 6 authentication endpoints configured
- Integrated with root urls.py under /api/v1/accounts/

### Task 6: Permission Classes ✅
Created `apps/accounts/permissions.py`:
- `IsOwnerOrReadOnly` - object-level permission for profile management

### Task 7: Admin Configuration ✅
Updated `apps/accounts/admin.py`:
- UserAdmin with list_display, list_filter, search_fields
- fieldsets for organization

### Task 8: Test Suite ✅
Created `apps/accounts/tests/`:
- `conftest.py` - shared fixtures (api_client, authenticated_user)
- `factories.py` - UserFactory with factory-boy
- `test_models.py` - User model tests
- `test_views.py` - API endpoint tests (register, login, logout, profile, password)
- `test_serializers.py` - serializer validation tests
- `test_permissions.py` - permission class tests

## Files Created/Modified

```
apps/accounts/
├── __init__.py          (exists)
├── models.py            ✅ User model created
├── serializers.py       ✅ 5 serializers created
├── views.py             ✅ 6 views created
├── urls.py              ✅ URL routing configured
├── permissions.py       ✅ IsOwnerOrReadOnly created
├── admin.py             ✅ UserAdmin registered
├── apps.py              (exists)
├── migrations/
│   └── 0001_initial.py  ✅ Migration created
└── tests/
    ├── __init__.py      ✅ created
    ├── conftest.py      ✅ created
    ├── factories.py     ✅ created
    ├── test_models.py   ✅ created
    ├── test_views.py    ✅ created
    ├── test_serializers.py ✅ created
    └── test_permissions.py ✅ created

config/settings/
└── base.py              ✅ AUTH_USER_MODEL, REST_FRAMEWORK, SIMPLE_JWT configured

config/urls.py           ✅ accounts URLs included

pyproject.toml           ✅ simplejwt, knox dependencies added
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

## Next Phase

Phase 4: Document Parser Module - Ready to start

See `.codebuddy/plans/phase4-document-parser.md` (to be created)
