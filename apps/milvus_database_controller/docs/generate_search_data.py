#!/usr/bin/env python3
"""Generate search query vector."""
from __future__ import annotations

import json
import numpy as np


def generate_search_data() -> dict:
    """Generate 1536-dim search query vector."""
    np.random.seed(44)
    
    return {
        "collection_name": "test_documents",
        "query_vector": np.random.rand(1536).tolist(),
        "anns_field": "text_dense",
        "top_k": 10,
        "filter_expr": "",
        "output_fields": ["pk", "text", "summary", "source", "lt_doc_id"],
    }


if __name__ == "__main__":
    print(json.dumps(generate_search_data()))
