#!/usr/bin/env python3
"""Create indexes and load collection."""
from __future__ import annotations

from pymilvus import MilvusClient


def create_indexes_and_load() -> None:
    client = MilvusClient(uri="http://localhost:19530")

    # Create indexes for dense vector fields using MilvusClient API
    print("Creating index for summary_dense...")
    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="summary_dense",
        index_type="HNSW",
        metric_type="COSINE",
        params={"M": 16, "efConstruction": 200},
    )
    index_params.add_index(
        field_name="text_dense",
        index_type="HNSW",
        metric_type="COSINE",
        params={"M": 16, "efConstruction": 200},
    )
    client.create_index(
        collection_name="test_documents",
        index_params=index_params,
    )
    print("Created indexes for vector fields")

    # Load collection
    print("Loading collection...")
    client.load_collection("test_documents")
    print("Collection loaded successfully")

    # Verify load state
    state = client.get_load_state("test_documents")
    print(f"Load state: {state}")


if __name__ == "__main__":
    create_indexes_and_load()
