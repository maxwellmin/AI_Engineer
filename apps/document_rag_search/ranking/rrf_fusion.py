"""
Reciprocal Rank Fusion (RRF) implementation for combining multiple retriever results.

RRF is a simple yet effective method for combining ranked lists from multiple
retrievers. The algorithm assigns a score to each document based on its ranks
across all input lists.

Reference: https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf

Formula: score(d) = sum(w_i / (k + rank(d, i)))
where:
    - d is a document
    - w_i is the weight for retriever i
    - k is the RRF parameter (default: 60)
    - rank(d, i) is the rank of document d in retriever i's result list
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from apps.document_rag_search.constants import DEFAULT_RRF_K, DEFAULT_VECTOR_WEIGHT, DEFAULT_KEYWORD_WEIGHT, DEFAULT_GRAPH_WEIGHT, RetrieverName
from apps.document_rag_search.dto import RankedResult, RetrieverResult
from apps.document_rag_search.exceptions import FusionConfigError, FusionError, NoResultsError


logger = logging.getLogger(__name__)


# =============================================================================
# Configuration DTOs
# =============================================================================


@dataclass(frozen=True)
class RRFConfig:
    """Configuration for RRF fusion.

    Attributes:
        k: RRF parameter (default: 60). Higher values give more weight to
           lower-ranked documents.
        weights: Optional weights for each retriever. If not provided,
                 default weights are used.
        min_score_threshold: Minimum score threshold for including results.
                            Results with scores below this threshold are excluded.
        normalize_scores: Whether to normalize final scores to [0, 1] range.
                         Uses min-max normalization based on actual score range.
    """

    k: int = DEFAULT_RRF_K
    weights: dict[str, float] | None = None
    min_score_threshold: float = 0.0
    normalize_scores: bool = True

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.k <= 0:
            raise FusionConfigError("k", f"k must be positive, got {self.k}")

        if self.weights is not None:
            for retriever_name, weight in self.weights.items():
                if weight < 0:
                    raise FusionConfigError(
                        "weights",
                        f"weight for '{retriever_name}' must be non-negative, got {weight}",
                    )

        if self.min_score_threshold < 0:
            raise FusionConfigError(
                "min_score_threshold",
                f"min_score_threshold must be non-negative, got {self.min_score_threshold}",
            )

        if self.min_score_threshold > 1.0:
            raise FusionConfigError(
                "min_score_threshold",
                f"min_score_threshold cannot exceed 1.0 when normalize_scores is True, got {self.min_score_threshold}",
            )


# =============================================================================
# RRF Fusion Implementation
# =============================================================================


class RRFFusion:
    """Reciprocal Rank Fusion for combining multiple rankings.

    RRF combines ranked lists from multiple retrievers into a single ranked list.
    It's particularly effective for hybrid search where different retrievers
    may have complementary strengths.

    The algorithm works by:
    1. Converting each retriever's results into rank-based scores
    2. Summing the scores across all retrievers (with optional weights)
    3. Sorting by the final fused score

    Example:
        >>> config = RRFConfig(k=60, weights={"vector": 0.5, "keyword": 0.5})
        >>> fusion = RRFFusion(config)
        >>> retriever_results = {
        ...     "vector": RetrieverResult(retriever_name="vector", items=[...], ...),
        ...     "keyword": RetrieverResult(retriever_name="keyword", items=[...], ...),
        ... }
        >>> ranked_results = fusion.fuse(retriever_results, top_k=10)

    Attributes:
        _config: RRF configuration.
        _default_weights: Default weights used when not specified in config.
    """

    # Default weights for each retriever type
    _DEFAULT_WEIGHTS: dict[str, float] = {
        RetrieverName.VECTOR.value: DEFAULT_VECTOR_WEIGHT,
        RetrieverName.KEYWORD.value: DEFAULT_KEYWORD_WEIGHT,
        RetrieverName.GRAPH.value: DEFAULT_GRAPH_WEIGHT,
    }

    def __init__(self, config: RRFConfig | None = None) -> None:
        """Initialize RRF fusion with configuration.

        Args:
            config: RRF configuration. If None, default configuration is used.
        """
        self._config = config or RRFConfig()
        self._default_weights = self._DEFAULT_WEIGHTS.copy()

        # Merge config weights with defaults if provided
        if self._config.weights:
            self._default_weights.update(self._config.weights)

        logger.debug(
            f"RRFFusion initialized with k={self._config.k}, "
            f"weights={self._default_weights}, "
            f"min_score_threshold={self._config.min_score_threshold}, "
            f"normalize_scores={self._config.normalize_scores}"
        )

    @property
    def config(self) -> RRFConfig:
        """Return the RRF configuration."""
        return self._config

    @property
    def weights(self) -> dict[str, float]:
        """Return the effective weights for each retriever."""
        return self._default_weights.copy()

    def fuse(
        self,
        retriever_results: dict[str, RetrieverResult],
        top_k: int = 10,
    ) -> list[RankedResult]:
        """Fuse multiple retriever results using RRF algorithm.

        This is the main entry point for RRF fusion. It takes results from
        multiple retrievers and returns a unified ranked list.

        Args:
            retriever_results: Dictionary mapping retriever name to RetrieverResult.
                              Each RetrieverResult contains items from that retriever.
            top_k: Maximum number of results to return after fusion.

        Returns:
            List of RankedResult sorted by fused score (descending).

        Raises:
            NoResultsError: If all retrievers returned empty results.
            FusionError: If fusion operation fails unexpectedly.

        Note:
            - Results with errors are still included in the fusion if they have items.
            - Documents not found in a retriever's results get no contribution from
              that retriever (not a penalty).
            - Chunk IDs are used for deduplication across retrievers.
        """
        start_time = time.time()
        logger.info(
            f"Starting RRF fusion with {len(retriever_results)} retrievers, "
            f"top_k={top_k}"
        )

        try:
            # Validate inputs
            self._validate_retriever_results(retriever_results)

            # Filter out empty results and results with errors
            valid_results = self._filter_valid_results(retriever_results)

            if not valid_results:
                logger.warning("No valid results from any retriever")
                raise NoResultsError()

            # Compute RRF scores
            chunk_scores: dict[str, dict[str, Any]] = {}
            for retriever_name, result in valid_results.items():
                self._process_retriever_results(
                    retriever_name=retriever_name,
                    result=result,
                    chunk_scores=chunk_scores,
                )

            if not chunk_scores:
                logger.warning("No chunks found after processing retriever results")
                raise NoResultsError()

            # Build final ranked results
            ranked_results = self._build_ranked_results(chunk_scores, top_k)

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                f"RRF fusion completed in {elapsed_ms:.2f}ms, "
                f"returned {len(ranked_results)} results"
            )

            return ranked_results

        except NoResultsError:
            raise
        except FusionConfigError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during RRF fusion: {e}")
            raise FusionError(str(e)) from e

    def _validate_retriever_results(
        self,
        retriever_results: dict[str, RetrieverResult],
    ) -> None:
        """Validate retriever results input.

        Args:
            retriever_results: Dictionary of retriever results to validate.

        Raises:
            FusionConfigError: If no retriever results provided.
        """
        if not retriever_results:
            raise FusionConfigError(
                "retriever_results",
                "No retriever results provided for fusion",
            )

    def _filter_valid_results(
        self,
        retriever_results: dict[str, RetrieverResult],
    ) -> dict[str, RetrieverResult]:
        """Filter out invalid retriever results.

        A result is considered invalid if:
        - It has no items
        - It has an error and no items

        Args:
            retriever_results: Dictionary of retriever results to filter.

        Returns:
            Dictionary of valid retriever results.
        """
        valid_results: dict[str, RetrieverResult] = {}

        for retriever_name, result in retriever_results.items():
            # Skip if no items
            if not result.items:
                if result.error:
                    logger.warning(
                        f"Retriever '{retriever_name}' returned error: {result.error}"
                    )
                else:
                    logger.debug(f"Retriever '{retriever_name}' returned no items")
                continue

            # Include results even if there was an error (partial results)
            if result.error:
                logger.warning(
                    f"Retriever '{retriever_name}' had error but returned "
                    f"{len(result.items)} items: {result.error}"
                )

            valid_results[retriever_name] = result

        return valid_results

    def _process_retriever_results(
        self,
        retriever_name: str,
        result: RetrieverResult,
        chunk_scores: dict[str, dict[str, Any]],
    ) -> None:
        """Process results from a single retriever and update chunk scores.

        Args:
            retriever_name: Name of the retriever.
            result: RetrieverResult from this retriever.
            chunk_scores: Dictionary to store/accumulate chunk scores.
                         Maps chunk_id to score and metadata.
        """
        weight = self._default_weights.get(retriever_name, 1.0)
        k = self._config.k

        for rank, item in enumerate(result.items, start=1):
            chunk_id = item.get("chunk_id")
            if not chunk_id:
                logger.warning(
                    f"Item from '{retriever_name}' missing chunk_id, skipping"
                )
                continue

            # Calculate RRF score contribution from this retriever
            # Formula: score = weight / (k + rank)
            rrf_contribution = weight / (k + rank)

            # Get the original score from the retriever (for tracking)
            original_score = item.get("score", 0.0)

            if chunk_id not in chunk_scores:
                # Initialize new chunk entry
                chunk_scores[chunk_id] = {
                    "chunk_id": chunk_id,
                    "document_id": item.get("document_id", ""),
                    "text": item.get("text", ""),
                    "source": item.get("source", ""),
                    "metadata": item.get("metadata", {}),
                    "fused_score": 0.0,
                    "retriever_scores": {},
                    "rrf_contributions": {},
                }

            # Accumulate RRF score
            chunk_scores[chunk_id]["fused_score"] += rrf_contribution

            # Track individual retriever scores
            chunk_scores[chunk_id]["retriever_scores"][retriever_name] = original_score

            # Track RRF contributions for debugging
            chunk_scores[chunk_id]["rrf_contributions"][retriever_name] = rrf_contribution

    def _build_ranked_results(
        self,
        chunk_scores: dict[str, dict[str, Any]],
        top_k: int,
    ) -> list[RankedResult]:
        """Build final ranked results from accumulated chunk scores.

        Args:
            chunk_scores: Dictionary of chunk scores and metadata.
            top_k: Maximum number of results to return.

        Returns:
            List of RankedResult sorted by fused score (descending).
        """
        # Sort chunks by fused score (descending)
        sorted_chunks = sorted(
            chunk_scores.values(),
            key=lambda x: x["fused_score"],
            reverse=True,
        )

        # Normalize scores if enabled
        if self._config.normalize_scores and sorted_chunks:
            sorted_chunks = self._normalize_scores(sorted_chunks)

        # Apply minimum score threshold (after normalization if enabled)
        filtered_chunks = [
            chunk
            for chunk in sorted_chunks
            if chunk["fused_score"] >= self._config.min_score_threshold
        ]

        # Limit to top_k
        final_chunks = filtered_chunks[:top_k]

        # Build RankedResult objects
        ranked_results: list[RankedResult] = []
        for chunk in final_chunks:
            ranked_result = RankedResult(
                chunk_id=chunk["chunk_id"],
                document_id=chunk["document_id"],
                text=chunk["text"],
                score=chunk["fused_score"],
                source=chunk["source"],
                metadata=chunk["metadata"],
                retriever_scores=chunk["retriever_scores"],
            )
            ranked_results.append(ranked_result)

        # Log detailed scoring for debugging
        if logger.isEnabledFor(logging.DEBUG):
            for i, result in enumerate(ranked_results[:5], start=1):
                contributions = chunk_scores[result.chunk_id].get("rrf_contributions", {})
                logger.debug(
                    f"Rank {i}: chunk_id={result.chunk_id[:8]}..., "
                    f"score={result.score:.4f}, "
                    f"contributions={contributions}"
                )

        return ranked_results

    def _normalize_scores(
        self,
        chunks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Normalize scores to [0, 1] range using min-max normalization.

        Uses min-max normalization: normalized = (score - min) / (max - min)
        This preserves the relative ranking while scaling to [0, 1].

        Edge cases:
        - If all scores are the same, all normalized scores are set to 1.0
        - The top result always gets score 1.0
        - The lowest result gets score close to 0.0 (but not necessarily 0.0
          if min score is not the lowest in the entire set)

        Args:
            chunks: List of chunk dictionaries with "fused_score" key.
                   Must be non-empty and already sorted by score (descending).

        Returns:
            List of chunk dictionaries with normalized "fused_score".
        """
        if not chunks:
            return chunks

        scores = [chunk["fused_score"] for chunk in chunks]
        max_score = scores[0]  # Already sorted descending
        min_score = scores[-1]

        # Handle edge case: all scores are the same
        if max_score == min_score:
            logger.debug(
                "All RRF scores are identical, setting all normalized scores to 1.0"
            )
            for chunk in chunks:
                chunk["fused_score"] = 1.0
            return chunks

        # Apply min-max normalization
        score_range = max_score - min_score
        logger.debug(
            f"Normalizing RRF scores: min={min_score:.6f}, max={max_score:.6f}, "
            f"range={score_range:.6f}"
        )

        for chunk in chunks:
            original_score = chunk["fused_score"]
            normalized_score = (original_score - min_score) / score_range
            # Round to 6 decimal places to avoid floating point precision issues
            chunk["fused_score"] = round(normalized_score, 6)

        return chunks

    def get_score_breakdown(
        self,
        retriever_results: dict[str, RetrieverResult],
        chunk_id: str,
    ) -> dict[str, float] | None:
        """Get detailed score breakdown for a specific chunk.

        This is a utility method for debugging and analysis.

        Args:
            retriever_results: Dictionary of retriever results.
            chunk_id: The chunk ID to get score breakdown for.

        Returns:
            Dictionary mapping retriever name to RRF contribution,
            or None if chunk not found.
        """
        chunk_scores: dict[str, dict[str, Any]] = {}

        for retriever_name, result in retriever_results.items():
            self._process_retriever_results(
                retriever_name=retriever_name,
                result=result,
                chunk_scores=chunk_scores,
            )

        if chunk_id in chunk_scores:
            return chunk_scores[chunk_id].get("rrf_contributions")

        return None
