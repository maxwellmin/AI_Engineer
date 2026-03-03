#!/usr/bin/env python3
"""Generate test vectors for Milvus API testing."""
from __future__ import annotations

import json
import numpy as np


def generate_test_vectors() -> dict:
    """Generate 1536-dim test vectors."""
    np.random.seed(42)
    
    summary_dense = np.random.rand(1536).tolist()
    text_dense = np.random.rand(1536).tolist()
    
    # Use DocumentCollectionSchema fields
    test_data = {
        "collection_name": "test_documents",
        "data": [
            {
                "pk": "doc-001-chunk-001",
                "text": "This is the first test document about machine learning and artificial intelligence.",
                "summary": "Document about ML and AI",
                "document": "Full document content for the first test document...",
                "source": "upload",
                "source_name": "test_doc_001.pdf",
                "lt_doc_id": "550e8400-e29b-41d4-a716-446655440000",
                "chunk_id": 1,
                "summary_dense": summary_dense,
                "text_dense": text_dense
            }
        ]
    }
    
    return test_data


if __name__ == "__main__":
    data = generate_test_vectors()
    print(json.dumps(data))
