#!/usr/bin/env python3
"""Create collection with correct schema."""
from __future__ import annotations

from pymilvus import DataType, MilvusClient


def create_collection_with_full_schema() -> None:
    """Create collection with DocumentCollectionSchema."""
    client = MilvusClient(uri="http://localhost:19530")

    # Drop existing collection
    if client.has_collection("test_documents"):
        client.drop_collection("test_documents")
        print("Dropped existing collection")

    # Create schema with all required fields
    from pymilvus import CollectionSchema, FieldSchema

    fields = [
        FieldSchema(name="pk", dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=256),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="summary", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="document", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="source_name", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="lt_doc_id", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="chunk_id", dtype=DataType.INT64),
        FieldSchema(name="summary_dense", dtype=DataType.FLOAT_VECTOR, dim=1536),
        FieldSchema(name="text_dense", dtype=DataType.FLOAT_VECTOR, dim=1536),
    ]

    schema = CollectionSchema(
        fields=fields,
        description="Test collection for manual testing",
        enable_dynamic_field=True,
    )

    # Create collection
    client.create_collection(
        collection_name="test_documents",
        schema=schema,
    )
    print("Created collection with full schema")

    # Verify schema
    info = client.describe_collection("test_documents")
    print("\nCollection Schema:")
    for field in info.get("fields", []):
        print(f"  {field.get('name')}: {field.get('type')} (primary={field.get('is_primary', False)})")


if __name__ == "__main__":
    create_collection_with_full_schema()
