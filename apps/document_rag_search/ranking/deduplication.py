"""
Result deduplication utilities for document RAG search.

This module provides deduplication strategies for combining results from
multiple retrievers or for post-processing search results.

Deduplication Strategies:
    - HIGHEST_SCORE: Keep the result with the highest score
    - FIRST_SEEN: Keep the first occurrence (stable)
    - MERGE: Merge metadata from all occurrences
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from apps.document_rag_search.dto import RankedResult, RetrieverResult


logger = logging.getLogger(__name__)


# =============================================================================
# Deduplication Strategies
# =============================================================================


class DeduplicationStrategy(str, Enum):
    """Strategy for deduplicating search results.

    Attributes:
        HIGHEST_SCORE: Keep the result with the highest score (default).
        FIRST_SEEN: Keep the first occurrence of each chunk.
        MERGE: Keep first occurrence but merge metadata from all.
    """

    HIGHEST_SCORE = "highest_score"
    FIRST_SEEN = "first_seen"
    MERGE = "merge"


# =============================================================================
# Configuration
# =============================================================================


@dataclass(frozen=True)
class DeduplicationConfig:
    """Configuration for result deduplication.

    Attributes:
        strategy: Deduplication strategy to use.
        key_field: Field to use as deduplication key (default: "chunk_id").
        score_field: Field to use for score comparison (default: "score").
    """

    strategy: DeduplicationStrategy = DeduplicationStrategy.HIGHEST_SCORE
    key_field: str = "chunk_id"
    score_field: str = "score"


# =============================================================================
# Deduplication Functions
# =============================================================================


def deduplicate_results(
    results: list[RankedResult],
    config: DeduplicationConfig | None = None,
) -> list[RankedResult]:
    """Deduplicate ranked results based on configuration.

    Args:
        results: List of RankedResult to deduplicate.
        config: Deduplication configuration. If None, uses defaults.

    Returns:
        Deduplicated list of RankedResult, preserving order by score.

    Example:
        >>> results = [
        ...     RankedResult(chunk_id="a", score=0.9, ...),
        ...     RankedResult(chunk_id="b", score=0.8, ...),
        ...     RankedResult(chunk_id="a", score=0.7, ...),  # duplicate
        ... ]
        >>> deduped = deduplicate_results(results)
        >>> len(deduped)  # 2, not 3
    """
    if not results:
        return results

    config = config or DeduplicationConfig()

    if config.strategy == DeduplicationStrategy.HIGHEST_SCORE:
        return _dedupe_highest_score(results, config)
    elif config.strategy == DeduplicationStrategy.FIRST_SEEN:
        return _dedupe_first_seen(results, config)
    elif config.strategy == DeduplicationStrategy.MERGE:
        return _dedupe_merge(results, config)
    else:
        logger.warning(
            f"Unknown deduplication strategy '{config.strategy}', "
            f"falling back to HIGHEST_SCORE"
        )
        return _dedupe_highest_score(results, config)


def deduplicate_retriever_results(
    retriever_results: dict[str, RetrieverResult],
    config: DeduplicationConfig | None = None,
) -> dict[str, RetrieverResult]:
    """Deduplicate items within each retriever's results.

    This is useful when a single retriever might return duplicate items
    for the same chunk.

    Args:
        retriever_results: Dictionary of retriever name to RetrieverResult.
        config: Deduplication configuration.

    Returns:
        Dictionary with deduplicated RetrieverResult objects.
    """
    if not retriever_results:
        return retriever_results

    config = config or DeduplicationConfig()
    deduped_results: dict[str, RetrieverResult] = {}

    for retriever_name, result in retriever_results.items():
        deduped_items = _deduplicate_items(
            items=result.items,
            config=config,
        )

        deduped_results[retriever_name] = RetrieverResult(
            retriever_name=result.retriever_name,
            items=deduped_items,
            query_time_ms=result.query_time_ms,
            total=len(deduped_items),
            error=result.error,
        )

    return deduped_results


def _dedupe_highest_score(
    results: list[RankedResult],
    config: DeduplicationConfig,
) -> list[RankedResult]:
    """Deduplicate by keeping the result with the highest score.

    Args:
        results: List of RankedResult to deduplicate.
        config: Deduplication configuration.

    Returns:
        Deduplicated list preserving original order.
    """
    seen: dict[str, RankedResult] = {}

    for result in results:
        key = getattr(result, config.key_field, None)
        if key is None:
            logger.warning(
                f"Result missing key field '{config.key_field}', keeping anyway"
            )
            # Use object id as fallback key to avoid dropping
            key = f"__no_key_{id(result)}"

        if key not in seen:
            seen[key] = result
        else:
            # Keep the one with higher score
            current_score = getattr(result, config.score_field, 0)
            existing_score = getattr(seen[key], config.score_field, 0)
            if current_score > existing_score:
                seen[key] = result

    # Return in original order (by score, descending)
    return list(seen.values())


def _dedupe_first_seen(
    results: list[RankedResult],
    config: DeduplicationConfig,
) -> list[RankedResult]:
    """Deduplicate by keeping the first occurrence.

    Args:
        results: List of RankedResult to deduplicate.
        config: Deduplication configuration.

    Returns:
        Deduplicated list preserving first occurrence order.
    """
    seen: dict[str, bool] = {}
    deduped: list[RankedResult] = []

    for result in results:
        key = getattr(result, config.key_field, None)
        if key is None:
            key = f"__no_key_{id(result)}"

        if key not in seen:
            seen[key] = True
            deduped.append(result)

    return deduped


def _dedupe_merge(
    results: list[RankedResult],
    config: DeduplicationConfig,
) -> list[RankedResult]:
    """Deduplicate by keeping first occurrence and merging metadata.

    Args:
        results: List of RankedResult to deduplicate.
        config: Deduplication configuration.

    Returns:
        Deduplicated list with merged metadata.
    """
    seen: dict[str, RankedResult] = {}

    for result in results:
        key = getattr(result, config.key_field, None)
        if key is None:
            key = f"__no_key_{id(result)}"

        if key not in seen:
            seen[key] = result
        else:
            # Merge metadata and retriever_scores
            existing = seen[key]
            merged_metadata = {**existing.metadata, **result.metadata}
            merged_scores = {**existing.retriever_scores, **result.retriever_scores}

            # Create new RankedResult with merged data
            seen[key] = RankedResult(
                chunk_id=existing.chunk_id,
                document_id=existing.document_id,
                text=existing.text,
                score=existing.score,  # Keep first score
                source=existing.source,
                metadata=merged_metadata,
                retriever_scores=merged_scores,
            )

    return list(seen.values())


def _deduplicate_items(
    items: list[dict[str, Any]],
    config: DeduplicationConfig,
) -> list[dict[str, Any]]:
    """Deduplicate a list of item dictionaries.

    Args:
        items: List of item dictionaries.
        config: Deduplication configuration.

    Returns:
        Deduplicated list of items.
    """
    if not items:
        return items

    seen: dict[str, dict[str, Any]] = {}

    for item in items:
        key = item.get(config.key_field)
        if key is None:
            key = f"__no_key_{id(item)}"

        if key not in seen:
            seen[key] = item
        elif config.strategy == DeduplicationStrategy.HIGHEST_SCORE:
            # Keep the one with higher score
            current_score = item.get(config.score_field, 0)
            existing_score = seen[key].get(config.score_field, 0)
            if current_score > existing_score:
                seen[key] = item
        elif config.strategy == DeduplicationStrategy.MERGE:
            # Merge metadata
            existing = seen[key]
            existing_metadata = existing.get("metadata", {})
            new_metadata = item.get("metadata", {})
            merged_metadata = {**existing_metadata, **new_metadata}
            existing["metadata"] = merged_metadata

    return list(seen.values())


# =============================================================================
# Utility Functions
# =============================================================================


def count_duplicates(
    results: list[RankedResult],
    key_field: str = "chunk_id",
) -> dict[str, int]:
    """Count how many times each chunk appears in results.

    Useful for debugging and analysis.

    Args:
        results: List of RankedResult to analyze.
        key_field: Field to use as key.

    Returns:
        Dictionary mapping chunk_id to count (only includes duplicates).
    """
    counts: dict[str, int] = {}

    for result in results:
        key = getattr(result, key_field, None)
        if key:
            counts[key] = counts.get(key, 0) + 1

    # Filter to only duplicates
    return {k: v for k, v in counts.items() if v > 1}


def get_unique_count(
    results: list[RankedResult],
    key_field: str = "chunk_id",
) -> int:
    """Get count of unique results.

    Args:
        results: List of RankedResult.
        key_field: Field to use as key.

    Returns:
        Number of unique results.
    """
    keys = set()
    for result in results:
        key = getattr(result, key_field, None)
        if key:
            keys.add(key)
    return len(keys)
