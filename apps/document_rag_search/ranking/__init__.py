"""Ranking algorithms for document RAG search module.

This module provides ranking and fusion algorithms for combining
results from multiple retrievers.

Available Classes:
    RRFConfig: Configuration for RRF fusion.
    RRFFusion: Reciprocal Rank Fusion implementation.
    DeduplicationConfig: Configuration for result deduplication.
    DeduplicationStrategy: Strategy enum for deduplication.
    ContextExpansionConfig: Configuration for context expansion.
    ContextExpander: Expand results with neighboring chunks.
    ExpandedResult: Search result with expanded context.

Available Functions:
    deduplicate_results: Deduplicate ranked results.
    deduplicate_retriever_results: Deduplicate items within retriever results.
    count_duplicates: Count duplicate occurrences in results.
    get_unique_count: Get count of unique results.
    expand_results: Expand results with neighboring chunks.
    expand_to_search_items: Expand and convert to SearchResultItem.
"""

from apps.document_rag_search.ranking.context_expansion import (
    ContextExpansionConfig,
    ContextExpander,
    ExpandedResult,
    expand_results,
    expand_to_search_items,
)
from apps.document_rag_search.ranking.deduplication import (
    DeduplicationConfig,
    DeduplicationStrategy,
    count_duplicates,
    deduplicate_results,
    deduplicate_retriever_results,
    get_unique_count,
)
from apps.document_rag_search.ranking.rrf_fusion import RRFConfig, RRFFusion

__all__ = [
    # RRF Fusion
    "RRFConfig",
    "RRFFusion",
    # Deduplication
    "DeduplicationConfig",
    "DeduplicationStrategy",
    "deduplicate_results",
    "deduplicate_retriever_results",
    "count_duplicates",
    "get_unique_count",
    # Context Expansion
    "ContextExpansionConfig",
    "ContextExpander",
    "ExpandedResult",
    "expand_results",
    "expand_to_search_items",
]
