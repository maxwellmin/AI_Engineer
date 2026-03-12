"""
Constants for Milvus database controller.

This module defines all constant values used across the Milvus database controller,
including collection names, field names, index names, and configuration defaults.
"""

from __future__ import annotations

from enum import Enum


# =============================================================================
# Collection Names
# =============================================================================

COLLECTION_DOCUMENTS = "documents"
COLLECTION_CHAT_HISTORY = "chat_history"

DEFAULT_COLLECTIONS: list[str] = [COLLECTION_DOCUMENTS, COLLECTION_CHAT_HISTORY]


# =============================================================================
# Field Names
# =============================================================================


class FieldName(str, Enum):
    """Field names for Milvus collections."""

    # Primary key
    PK = "pk"

    # Text fields
    TEXT = "text"
    SUMMARY = "summary"
    DOCUMENT = "document"

    # Source metadata
    SOURCE = "source"
    SOURCE_NAME = "source_name"

    # Link to PostgreSQL document ID
    LT_DOC_ID = "lt_doc_id"

    # Chunk sequence number
    CHUNK_ID = "chunk_id"

    # Dense vector fields
    SUMMARY_DENSE = "summary_dense"
    TEXT_DENSE = "text_dense"

    # Sparse vector field (BM25)
    TEXT_SPARSE = "text_sparse"


# =============================================================================
# Index Names
# =============================================================================


class IndexName(str, Enum):
    """Index names for vector fields."""

    SUMMARY_DENSE = "summary_dense_index"
    TEXT_DENSE = "text_dense_index"
    TEXT_SPARSE = "text_sparse_index"


# =============================================================================
# Metric Types
# =============================================================================


class MetricType(str, Enum):
    """Metric types for vector search."""

    COSINE = "COSINE"
    IP = "IP"  # Inner Product
    L2 = "L2"
    BM25 = "BM25"


# =============================================================================
# Index Types
# =============================================================================


class IndexType(str, Enum):
    """Index types for vector fields."""

    # Dense vector indexes
    HNSW = "HNSW"
    IVF_FLAT = "IVF_FLAT"
    IVF_SQ8 = "IVF_SQ8"
    IVF_PQ = "IVF_PQ"
    FLAT = "FLAT"

    # Sparse vector indexes
    SPARSE_INVERTED_INDEX = "SPARSE_INVERTED_INDEX"
    SPARSE_WAND = "SPARSE_WAND"


# =============================================================================
# Default Configuration Values
# =============================================================================

# Vector dimensions
DEFAULT_DENSE_DIMENSION = 1536  # OpenAI/Qwen embedding dimension

# HNSW index parameters
DEFAULT_HNSW_M = 32
DEFAULT_HNSW_EF_CONSTRUCTION = 200
DEFAULT_HNSW_EF = 100

# IVF_FLAT index parameters
DEFAULT_IVF_NLIST = 128
DEFAULT_IVF_NPROBE = 10

# BM25 parameters
# k1: Term frequency saturation parameter (1.2-2.0 typical, 1.5 for mixed corpus)
# b: Document length normalization (0.75 typical, 0.8 for strong normalization)
DEFAULT_BM25_K1 = 1.5
DEFAULT_BM25_B = 0.8

# Search defaults
DEFAULT_TOP_K = 10
DEFAULT_SEARCH_TIMEOUT = 30  # seconds

# Batch operation defaults
DEFAULT_BATCH_SIZE = 1000
MAX_BATCH_SIZE = 10000

# Field lengths
MAX_TEXT_LENGTH = 65535  # VARCHAR max length in Milvus
MAX_PK_LENGTH = 256


# =============================================================================
# HNSW Index Parameters
# =============================================================================

HNSW_INDEX_PARAMS: dict = {
    "metric_type": MetricType.COSINE.value,
    "index_type": IndexType.HNSW.value,
    "params": {
        "M": DEFAULT_HNSW_M,
        "efConstruction": DEFAULT_HNSW_EF_CONSTRUCTION,
    },
}

HNSW_SEARCH_PARAMS: dict = {
    "metric_type": MetricType.COSINE.value,
    "params": {
        "ef": DEFAULT_HNSW_EF,
    },
}


# =============================================================================
# Sparse Index Parameters
# =============================================================================

# BM25 sparse index parameters for Milvus 2.5+
# Note: For BM25 search, use metric_type="BM25" and index_type="SPARSE_WAND"
# The k1 and b parameters are configured at index creation time
SPARSE_INDEX_PARAMS: dict = {
    "index_type": IndexType.SPARSE_WAND.value,
    "metric_type": MetricType.BM25.value,
    "params": {
        "bm25_k1": DEFAULT_BM25_K1,  # Term frequency saturation
        "bm25_b": DEFAULT_BM25_B,    # Document length normalization
    },
}

SPARSE_SEARCH_PARAMS: dict = {
    "metric_type": MetricType.BM25.value,
    "params": {
        "drop_ratio_search": 0.2,
    },
}


# =============================================================================
# Collection Schema Fields Configuration
# =============================================================================

DENSE_VECTOR_FIELD_CONFIG: dict = {
    "dtype": "FLOAT_VECTOR",
    "dim": DEFAULT_DENSE_DIMENSION,
}

SPARSE_VECTOR_FIELD_CONFIG: dict = {
    "dtype": "SPARSE_FLOAT_VECTOR",
}

VARCHAR_FIELD_CONFIG: dict = {
    "dtype": "VARCHAR",
    "max_length": MAX_TEXT_LENGTH,
}

PK_FIELD_CONFIG: dict = {
    "dtype": "VARCHAR",
    "max_length": MAX_PK_LENGTH,
    "is_primary": True,
    "auto_id": False,
}

INT64_FIELD_CONFIG: dict = {
    "dtype": "INT64",
}


# =============================================================================
# Source Types
# =============================================================================


class SourceType(str, Enum):
    """Source types for document origin."""

    UPLOAD = "upload"
    WEB_CRAWL = "web_crawl"
    API_IMPORT = "api_import"
    MANUAL = "manual"
    SYNC = "sync"


# =============================================================================
# Error Messages
# =============================================================================

ERROR_COLLECTION_NOT_FOUND = "Collection '{collection_name}' not found"
ERROR_COLLECTION_ALREADY_EXISTS = "Collection '{collection_name}' already exists"
ERROR_INVALID_VECTOR_DIMENSION = "Invalid vector dimension: expected {expected}, got {actual}"
ERROR_INSERT_FAILED = "Failed to insert vectors: {reason}"
ERROR_SEARCH_FAILED = "Search operation failed: {reason}"
ERROR_CONNECTION_FAILED = "Failed to connect to Milvus server: {reason}"
ERROR_INDEX_CREATION_FAILED = "Failed to create index '{index_name}': {reason}"
ERROR_INVALID_FILTER = "Invalid filter expression: {filter_expr}"
