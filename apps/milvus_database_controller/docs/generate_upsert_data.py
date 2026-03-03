#!/usr/bin/env python3
"""Generate upsert test data."""
from __future__ import annotations

import json
import numpy as np


def generate_upsert_data() -> dict:
    """Generate 1536-dim test vectors for upsert."""
    np.random.seed(43)
    
    return {
        "collection_name": "test_documents",
        "data": [
            {
                "pk": "doc-001-chunk-001",
                "text": "Updated: This is the updated test document about machine learning.",
                "summary": "Updated document about ML",
                "document": "Updated full document content...",
                "source": "upload",
                "source_name": "test_doc_001_v2.pdf",
                "lt_doc_id": "550e8400-e29b-41d4-a716-446655440000",
                "chunk_id": 1,
                "summary_dense": np.random.rand(1536).tolist(),
                "text_dense": np.random.rand(1536).tolist(),
            }
        ],
    }


if __name__ == "__main__":
    print(json.dumps(generate_upsert_data()))
