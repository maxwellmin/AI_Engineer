"""
Constants for document RAG search module.

This module defines all constant values used across the document RAG search module,
including search types, ranking methods, retriever names, and configuration defaults.
"""

from __future__ import annotations

from enum import Enum


# =============================================================================
# Search Types
# =============================================================================


class SearchType(str, Enum):
    """Search type for hybrid search operations.

    Defines the available search strategies that can be combined
    in hybrid search queries.
    """

    VECTOR = "vector"
    KEYWORD = "keyword"
    GRAPH = "graph"


# =============================================================================
# Ranking Methods
# =============================================================================


class RankingMethod(str, Enum):
    """Ranking method for result fusion.

    Defines the algorithms available for combining and ranking
    results from multiple retrievers.
    """

    RRF = "rrf"  # Reciprocal Rank Fusion
    WEIGHTED = "weighted"  # Weighted average of scores
    MAX = "max"  # Maximum score from all retrievers


# =============================================================================
# Retriever Names
# =============================================================================


class RetrieverName(str, Enum):
    """Retriever names for identification.

    Standard names used to identify retrievers in logs, metrics,
    and result metadata.
    """

    VECTOR = "vector"
    KEYWORD = "keyword"
    GRAPH = "graph"


# =============================================================================
# Default Configuration Values
# =============================================================================

DEFAULT_TOP_K = 10
DEFAULT_RRF_K = 60
DEFAULT_VECTOR_WEIGHT = 0.4
DEFAULT_KEYWORD_WEIGHT = 0.3
DEFAULT_GRAPH_WEIGHT = 0.3

MAX_QUERY_LENGTH = 500
MIN_QUERY_LENGTH = 2

DEFAULT_SUGGESTIONS_LIMIT = 5
MIN_PREFIX_LENGTH = 2

DEFAULT_FTS_CONFIG = "simple"  # PostgreSQL FTS config for mixed Chinese/English

# =============================================================================
# Context Expansion Defaults
# =============================================================================

DEFAULT_CONTEXT_WINDOW = 1  # Number of neighbor chunks to include

# =============================================================================
# Timeout Defaults
# =============================================================================

DEFAULT_SEARCH_TIMEOUT = 30  # seconds
DEFAULT_RETRIEVER_TIMEOUT = 10  # seconds per retriever

# =============================================================================
# Score Thresholds
# =============================================================================

MIN_SCORE_THRESHOLD = 0.0
MAX_SCORE_THRESHOLD = 1.0
DEFAULT_MIN_SCORE = 0.1  # Minimum score to include in results
