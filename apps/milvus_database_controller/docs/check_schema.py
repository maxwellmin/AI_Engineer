#!/usr/bin/env python3
"""Check Milvus collection schema."""
from __future__ import annotations

from pymilvus import MilvusClient


def main() -> None:
    client = MilvusClient(uri="http://localhost:19530")
    info = client.describe_collection("test_documents")
    print("Collection Schema:")
    for field in info.get("fields", []):
        print(
            f"  {field.get('name')}: {field.get('type')} "
            f"(primary={field.get('is_primary', False)}, auto_id={field.get('auto_id', False)})"
        )


if __name__ == "__main__":
    main()
