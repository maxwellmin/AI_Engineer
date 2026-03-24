"""
Context expansion utilities for document RAG search.

Context expansion enhances search results by including neighboring chunks
to provide more complete context around the matched chunk.

This is useful when:
- A matched chunk is part of a longer passage
- The answer spans multiple chunks
- Users need surrounding context to understand the match
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from apps.document_rag_search.dto import RankedResult, SearchResultItem
from apps.document_rag_search.constants import DEFAULT_CONTEXT_WINDOW


if TYPE_CHECKING:
    from apps.documents_parser.models import DocumentChunk


logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass(frozen=True)
class ContextExpansionConfig:
    """Configuration for context expansion.

    Attributes:
        enabled: Whether context expansion is enabled.
        window_size: Number of neighbor chunks to include on each side.
                    For example, window_size=1 includes 1 prev + 1 next chunk.
        max_total_chunks: Maximum total chunks per result after expansion.
                         This limits memory usage for very long documents.
        include_self: Whether to include the original matched chunk.
                     Usually True, but can be False if only context is needed.
    """

    enabled: bool = True
    window_size: int = DEFAULT_CONTEXT_WINDOW
    max_total_chunks: int = 10  # Prevent explosion
    include_self: bool = True


# =============================================================================
# Result Types
# =============================================================================


@dataclass(frozen=True)
class ExpandedResult:
    """A search result with expanded context.

    Attributes:
        chunk_id: ID of the primary (matched) chunk.
        document_id: ID of the parent document.
        primary_text: Text of the primary matched chunk.
        primary_score: Score of the primary chunk.
        context_before: List of chunks before the primary chunk.
        context_after: List of chunks after the primary chunk.
        source: Source file name.
        metadata: Metadata from the primary chunk.
        retriever_scores: Scores from individual retrievers.
    """

    chunk_id: str
    document_id: str
    primary_text: str
    primary_score: float
    context_before: list[dict[str, Any]] = field(default_factory=list)
    context_after: list[dict[str, Any]] = field(default_factory=list)
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    retriever_scores: dict[str, float] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        """Get full text including context."""
        parts = []

        for chunk in self.context_before:
            parts.append(chunk.get("content", chunk.get("text", "")))

        if self.include_self:
            parts.append(self.primary_text)

        for chunk in self.context_after:
            parts.append(chunk.get("content", chunk.get("text", "")))

        return "\n\n".join(parts)

    @property
    def include_self(self) -> bool:
        """Whether primary chunk is included in full_text."""
        return True  # Always include in expanded result

    @property
    def total_chunks(self) -> int:
        """Get total number of chunks in this result."""
        return len(self.context_before) + 1 + len(self.context_after)

    def to_search_result_item(self) -> SearchResultItem:
        """Convert to SearchResultItem with full text."""
        return SearchResultItem(
            chunk_id=self.chunk_id,
            document_id=self.document_id,
            text=self.full_text,
            score=self.primary_score,
            source=self.source,
            metadata={
                **self.metadata,
                "context_expanded": True,
                "context_chunks": self.total_chunks,
                "context_before_count": len(self.context_before),
                "context_after_count": len(self.context_after),
            },
            retriever_scores=self.retriever_scores,
        )


# =============================================================================
# Context Expansion Implementation
# =============================================================================


class ContextExpander:
    """Expand search results with neighboring chunks.

    This class fetches neighboring chunks from the database to provide
    more context around matched chunks.

    Example:
        >>> config = ContextExpansionConfig(window_size=1)
        >>> expander = ContextExpander(config)
        >>> results = [RankedResult(chunk_id="...", ...)]
        >>> expanded = expander.expand(results)
    """

    def __init__(self, config: ContextExpansionConfig | None = None) -> None:
        """Initialize context expander.

        Args:
            config: Context expansion configuration.
        """
        self._config = config or ContextExpansionConfig()

    @property
    def config(self) -> ContextExpansionConfig:
        """Return the configuration."""
        return self._config

    def expand(
        self,
        results: list[RankedResult],
    ) -> list[ExpandedResult]:
        """Expand results with neighboring chunks.

        Args:
            results: List of RankedResult to expand.

        Returns:
            List of ExpandedResult with context.
        """
        if not results or not self._config.enabled:
            return self._convert_without_expansion(results)

        logger.info(
            f"Expanding context for {len(results)} results, "
            f"window_size={self._config.window_size}"
        )

        # Group results by document for efficient querying
        document_chunks: dict[str, list[tuple[int, RankedResult]]] = {}
        chunk_id_to_result: dict[str, RankedResult] = {}

        for result in results:
            chunk_id_to_result[result.chunk_id] = result
            # We need to get chunk_index from database
            # Store result for later lookup
            if result.document_id not in document_chunks:
                document_chunks[result.document_id] = []
            # We'll populate chunk_index after DB query

        # Fetch chunk indices and neighbor chunks
        expanded_results: list[ExpandedResult] = []

        for result in results:
            expanded = self._expand_single_result(result)
            if expanded:
                expanded_results.append(expanded)
            else:
                # Fallback: create ExpandedResult without context
                expanded_results.append(
                    ExpandedResult(
                        chunk_id=result.chunk_id,
                        document_id=result.document_id,
                        primary_text=result.text,
                        primary_score=result.score,
                        source=result.source,
                        metadata=result.metadata,
                        retriever_scores=result.retriever_scores,
                    )
                )

        logger.info(f"Expanded {len(expanded_results)} results with context")
        return expanded_results

    def _expand_single_result(
        self,
        result: RankedResult,
    ) -> ExpandedResult | None:
        """Expand a single result with context.

        Args:
            result: The result to expand.

        Returns:
            ExpandedResult with context, or None if chunk not found.
        """
        from apps.documents_parser.models import DocumentChunk

        try:
            # Get the primary chunk to find its index
            primary_chunk = DocumentChunk.objects.filter(
                id=result.chunk_id,
            ).only("id", "chunk_index", "content", "document_id").first()

            if not primary_chunk:
                logger.warning(f"Chunk {result.chunk_id} not found in database")
                return None

            chunk_index = primary_chunk.chunk_index
            document_id = str(primary_chunk.document_id)

            # Calculate range for context
            window = self._config.window_size
            start_index = max(0, chunk_index - window)
            end_index = chunk_index + window + 1

            # Fetch neighbor chunks
            neighbor_chunks = list(
                DocumentChunk.objects.filter(
                    document_id=document_id,
                    chunk_index__gte=start_index,
                    chunk_index__lt=end_index,
                )
                .only("id", "chunk_index", "content", "page_number")
                .order_by("chunk_index")
            )

            # Separate into before and after
            context_before: list[dict[str, Any]] = []
            context_after: list[dict[str, Any]] = []

            for chunk in neighbor_chunks:
                chunk_data = {
                    "chunk_id": str(chunk.id),
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                }

                if chunk.chunk_index < chunk_index:
                    context_before.append(chunk_data)
                elif chunk.chunk_index > chunk_index:
                    context_after.append(chunk_data)

            # Limit total chunks
            if len(context_before) + 1 + len(context_after) > self._config.max_total_chunks:
                # Trim from ends
                excess = len(context_before) + 1 + len(context_after) - self._config.max_total_chunks
                # Remove from the farther end
                while excess > 0 and len(context_after) > len(context_before):
                    context_after.pop()
                    excess -= 1
                while excess > 0 and context_before:
                    context_before.pop(0)
                    excess -= 1

            return ExpandedResult(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                primary_text=result.text,
                primary_score=result.score,
                context_before=context_before,
                context_after=context_after,
                source=result.source,
                metadata=result.metadata,
                retriever_scores=result.retriever_scores,
            )

        except Exception as e:
            logger.exception(f"Error expanding context for chunk {result.chunk_id}: {e}")
            return None

    def _convert_without_expansion(
        self,
        results: list[RankedResult],
    ) -> list[ExpandedResult]:
        """Convert results without expanding context.

        Args:
            results: List of RankedResult.

        Returns:
            List of ExpandedResult without context.
        """
        return [
            ExpandedResult(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                primary_text=r.text,
                primary_score=r.score,
                source=r.source,
                metadata=r.metadata,
                retriever_scores=r.retriever_scores,
            )
            for r in results
        ]


# =============================================================================
# Utility Functions
# =============================================================================


def expand_results(
    results: list[RankedResult],
    config: ContextExpansionConfig | None = None,
) -> list[ExpandedResult]:
    """Convenience function to expand results with context.

    Args:
        results: List of RankedResult to expand.
        config: Context expansion configuration.

    Returns:
        List of ExpandedResult with context.
    """
    expander = ContextExpander(config)
    return expander.expand(results)


def expand_to_search_items(
    results: list[RankedResult],
    config: ContextExpansionConfig | None = None,
) -> list[SearchResultItem]:
    """Expand results and convert to SearchResultItem.

    Args:
        results: List of RankedResult to expand.
        config: Context expansion configuration.

    Returns:
        List of SearchResultItem with expanded context.
    """
    expanded = expand_results(results, config)
    return [e.to_search_result_item() for e in expanded]
