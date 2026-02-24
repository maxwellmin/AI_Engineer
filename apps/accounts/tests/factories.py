"""
Factory Boy factories for accounts app tests.
"""
from __future__ import annotations

import factory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating User instances in tests.

    Usage:
        # Create basic user (without hashed password)
        user = UserFactory()

        # Create user with hashed password
        user = UserFactory.create_user(username="myuser", password="mypass")

        # Create superuser
        admin = UserFactory.create_superuser(username="admin")
    """

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    phone = factory.Sequence(lambda n: f"138{str(n).zfill(8)}")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True

    @classmethod
    def create_user(cls, password: str = "testpass123", **kwargs) -> User:
        """
        Create a user with hashed password.

        Args:
            password: Plain text password to be hashed.
            **kwargs: Additional user attributes.

        Returns:
            User instance with hashed password.
        """
        user = cls(**kwargs)
        user.set_password(password)
        user.save()
        return user

    @classmethod
    def create_superuser(cls, password: str = "adminpass123", **kwargs) -> User:
        """
        Create a superuser with staff and superuser flags.

        Args:
            password: Plain text password to be hashed.
            **kwargs: Additional user attributes.

        Returns:
            User instance with superuser privileges.
        """
        kwargs.setdefault("is_staff", True)
        kwargs.setdefault("is_superuser", True)
        kwargs.setdefault("is_verified", True)
        return cls.create_user(password=password, **kwargs)
