"""
Collection schema definitions for Milvus collections.

This module provides schema definitions and creation helpers for
Milvus collections used in the RAG system.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from pymilvus import DataType

from apps.milvus_database_controller.constants import (
    DEFAULT_DENSE_DIMENSION,
    FieldName,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FieldDefinition:
    """Definition of a single field in a collection schema.

    Attributes:
        name: Field name.
        dtype: Data type (DataType enum).
        is_primary: Whether this is the primary key.
        auto_id: Whether to auto-generate IDs.
        max_length: Maximum length for VARCHAR fields.
        dim: Dimension for vector fields.
        description: Field description.
        nullable: Whether the field can be null.
        enable_analyzer: Whether to enable text analyzer (for BM25).
        analyzer_params: Analyzer parameters (e.g., {"type": "chinese"}).
        enable_match: Whether to enable text matching (for keyword search).
    """

    name: str
    dtype: DataType
    is_primary: bool = False
    auto_id: bool = False
    max_length: int | None = None
    dim: int | None = None
    description: str = ""
    nullable: bool = False
    enable_analyzer: bool = False
    analyzer_params: dict | None = None
    enable_match: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for schema creation."""
        result: dict[str, Any] = {
            "name": self.name,
            "dtype": self.dtype,
        }
        if self.is_primary:
            result["is_primary"] = True
            result["auto_id"] = self.auto_id
        if self.max_length is not None:
            result["max_length"] = self.max_length
        if self.dim is not None:
            result["dim"] = self.dim
        if self.description:
            result["description"] = self.description
        if self.nullable:
            result["nullable"] = True
        if self.enable_analyzer:
            result["enable_analyzer"] = True
        if self.analyzer_params is not None:
            result["analyzer_params"] = self.analyzer_params
        if self.enable_match:
            result["enable_match"] = True
        return result


@dataclass(frozen=True)
class DocumentCollectionSchema:
    """Schema definition for the documents collection.

    This schema supports multi-vector search with:
    - summary_dense: Dense vector for document summary
    - text_dense: Dense vector for full text
    - text_sparse: Sparse vector for BM25 search

    Attributes:
        dimension: Dimension of dense vector fields.
        enable_dynamic_field: Whether to enable dynamic fields.
    """

    dimension: int = DEFAULT_DENSE_DIMENSION
    enable_dynamic_field: bool = True

    @property
    def fields(self) -> list[FieldDefinition]:
        """Get all field definitions."""
        return [
            # Primary key
            FieldDefinition(
                name=FieldName.PK.value,
                dtype=DataType.VARCHAR,
                is_primary=True,
                auto_id=False,
                max_length=256,
                description="Primary key (document hash)",
            ),
            # Text fields
            FieldDefinition(
                name=FieldName.TEXT.value,
                dtype=DataType.VARCHAR,
                max_length=65535,
                description="Full text content for BM25",
                enable_analyzer=True,
                analyzer_params={"type": "chinese"},
                enable_match=True,
            ),
            FieldDefinition(
                name=FieldName.SUMMARY.value,
                dtype=DataType.VARCHAR,
                max_length=65535,
                description="Document summary/abstract",
            ),
            FieldDefinition(
                name=FieldName.DOCUMENT.value,
                dtype=DataType.VARCHAR,
                max_length=65535,
                description="Original document content",
            ),
            # Source metadata
            FieldDefinition(
                name=FieldName.SOURCE.value,
                dtype=DataType.VARCHAR,
                max_length=64,
                description="Data source type",
            ),
            FieldDefinition(
                name=FieldName.SOURCE_NAME.value,
                dtype=DataType.VARCHAR,
                max_length=256,
                description="Data source name",
            ),
            # Link to PostgreSQL
            FieldDefinition(
                name=FieldName.LT_DOC_ID.value,
                dtype=DataType.VARCHAR,
                max_length=256,
                description="Link to document ID in PostgreSQL",
            ),
            # Chunk ID
            FieldDefinition(
                name=FieldName.CHUNK_ID.value,
                dtype=DataType.INT64,
                description="Chunk sequence number",
            ),
            # Dense vectors
            FieldDefinition(
                name=FieldName.SUMMARY_DENSE.value,
                dtype=DataType.FLOAT_VECTOR,
                dim=self.dimension,
                description="Summary embedding vector",
            ),
            FieldDefinition(
                name=FieldName.TEXT_DENSE.value,
                dtype=DataType.FLOAT_VECTOR,
                dim=self.dimension,
                description="Text embedding vector",
            ),
            # Sparse vector for BM25 (Milvus 2.5+ with BM25 Function)
            # Note: BM25 Function will auto-generate sparse vectors from text field
            FieldDefinition(
                name=FieldName.TEXT_SPARSE.value,
                dtype=DataType.SPARSE_FLOAT_VECTOR,
                description="BM25 sparse vector (auto-generated by Milvus Function)",
            ),
        ]

    def get_field_names(self) -> list[str]:
        """Get list of all field names."""
        return [field.name for field in self.fields]

    def get_vector_field_names(self) -> list[str]:
        """Get list of vector field names."""
        return [
            field.name
            for field in self.fields
            if field.dtype in (DataType.FLOAT_VECTOR, DataType.SPARSE_FLOAT_VECTOR)
        ]

    def get_dense_vector_field_names(self) -> list[str]:
        """Get list of dense vector field names."""
        return [
            field.name
            for field in self.fields
            if field.dtype == DataType.FLOAT_VECTOR
        ]

    def get_sparse_vector_field_names(self) -> list[str]:
        """Get list of sparse vector field names."""
        return [
            field.name
            for field in self.fields
            if field.dtype == DataType.SPARSE_FLOAT_VECTOR
        ]


def get_document_collection_schema(
    dimension: int = DEFAULT_DENSE_DIMENSION,
    enable_dynamic_field: bool = True,
) -> DocumentCollectionSchema:
    """Get the document collection schema.

    Args:
        dimension: Dimension of dense vector fields.
        enable_dynamic_field: Whether to enable dynamic fields.

    Returns:
        DocumentCollectionSchema instance.
    """
    return DocumentCollectionSchema(
        dimension=dimension,
        enable_dynamic_field=enable_dynamic_field,
    )


def create_schema_from_definition(
    schema_def: DocumentCollectionSchema,
) -> dict[str, Any]:
    """Create a Milvus schema dictionary from definition.

    This is used for compatibility with pymilvus MilvusClient.

    Args:
        schema_def: Schema definition.

    Returns:
        Dictionary containing schema information.
    """
    return {
        "fields": [field.to_dict() for field in schema_def.fields],
        "enable_dynamic_field": schema_def.enable_dynamic_field,
    }


# =============================================================================
# Chat History Collection Schema
# =============================================================================


@dataclass(frozen=True)
class ChatHistoryCollectionSchema:
    """Schema definition for the chat_history collection.

    This schema stores message embeddings for conversation history search.

    Attributes:
        dimension: Dimension of dense vector fields.
        enable_dynamic_field: Whether to enable dynamic fields.
    """

    dimension: int = DEFAULT_DENSE_DIMENSION
    enable_dynamic_field: bool = True

    @property
    def fields(self) -> list[FieldDefinition]:
        """Get all field definitions."""
        return [
            # Primary key (message ID)
            FieldDefinition(
                name=FieldName.PK.value,
                dtype=DataType.VARCHAR,
                is_primary=True,
                auto_id=False,
                max_length=256,
                description="Primary key (message ID)",
            ),
            # Message content
            FieldDefinition(
                name=FieldName.MESSAGE.value,
                dtype=DataType.VARCHAR,
                max_length=65535,
                description="Chat message content",
            ),
            # Message role
            FieldDefinition(
                name=FieldName.ROLE.value,
                dtype=DataType.VARCHAR,
                max_length=32,
                description="Message role (user/assistant/system)",
            ),
            # Conversation and user info
            FieldDefinition(
                name=FieldName.CONVERSATION_ID.value,
                dtype=DataType.VARCHAR,
                max_length=256,
                description="Conversation ID",
            ),
            FieldDefinition(
                name=FieldName.USER_ID.value,
                dtype=DataType.VARCHAR,
                max_length=256,
                description="User ID",
            ),
            # Timestamp
            FieldDefinition(
                name=FieldName.TIMESTAMP.value,
                dtype=DataType.INT64,
                description="Message timestamp (Unix timestamp)",
            ),
            # Dense vector (message embedding)
            FieldDefinition(
                name=FieldName.EMBEDDING.value,
                dtype=DataType.FLOAT_VECTOR,
                dim=self.dimension,
                description="Message embedding vector",
            ),
        ]

    def get_field_names(self) -> list[str]:
        """Get list of all field names."""
        return [field.name for field in self.fields]


def get_chat_history_collection_schema(
    dimension: int = DEFAULT_DENSE_DIMENSION,
    enable_dynamic_field: bool = True,
) -> ChatHistoryCollectionSchema:
    """Get the chat history collection schema.

    Args:
        dimension: Dimension of dense vector fields.
        enable_dynamic_field: Whether to enable dynamic fields.

    Returns:
        ChatHistoryCollectionSchema instance.
    """
    return ChatHistoryCollectionSchema(
        dimension=dimension,
        enable_dynamic_field=enable_dynamic_field,
    )
