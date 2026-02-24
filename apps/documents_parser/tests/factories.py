"""
Factory Boy factories for documents_parser tests.
"""

from __future__ import annotations

import factory
from apps.accounts.tests.factories import UserFactory


class DocumentFactory(factory.django.DjangoModelFactory):
    """Factory for creating Document instances in tests."""

    class Meta:
        model = "documents_parser.Document"

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"document_{n}")
    original_name = factory.Sequence(lambda n: f"original_{n}.pdf")
    file_path = factory.LazyAttribute(lambda obj: f"documents/2026/02/24/{obj.original_name}")
    file_size = factory.Faker("pyint", min_value=1000, max_value=10000000)
    file_type = factory.Iterator(["pdf", "docx", "txt"])
    file_hash = factory.Faker("sha256")
    status = "uploaded"
    title = factory.Faker("sentence", nb_words=4)
    description = factory.Faker("text", max_nb_chars=200)
    author = factory.Faker("name")


class DocumentChunkFactory(factory.django.DjangoModelFactory):
    """Factory for creating DocumentChunk instances in tests."""

    class Meta:
        model = "documents_parser.DocumentChunk"

    document = factory.SubFactory(DocumentFactory)
    chunk_index = factory.Sequence(lambda n: n)
    content = factory.Faker("text", max_nb_chars=500)
    content_hash = factory.Faker("sha256")
    char_count = factory.LazyAttribute(lambda obj: len(obj.content))
    token_count = factory.LazyAttribute(lambda obj: len(obj.content.split()))
