"""
Schemas module for Milvus database controller.

This module contains schema definitions for Milvus collections.
"""

from apps.milvus_database_controller.schemas.collection_schema import (
    DocumentCollectionSchema,
    get_document_collection_schema,
)

__all__ = [
    "DocumentCollectionSchema",
    "get_document_collection_schema",
]
