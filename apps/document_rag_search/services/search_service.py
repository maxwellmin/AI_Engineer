"""Search service for document RAG search module.

This module provides the SearchService class, which serves as the high-level
facade for all search operations in the document RAG search module.

The SearchService coordinates between multiple retrievers (Vector, Keyword, Graph)
and applies RRF fusion to produce unified search results.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from django.conf import settings

from apps.document_rag_search.constants import (
    DEFAULT_MIN_SCORE,
    DEFAULT_RRF_K,
    DEFAULT_TOP_K,
    MAX_QUERY_LENGTH,
    MIN_QUERY_LENGTH,
    RetrieverName,
)
from apps.document_rag_search.dto import (
    AdvancedSearchRequest,
    HybridSearchRequest,
    RankedResult,
    RetrieverResult,
    SearchConfig,
    SearchQuery,
    SearchResponse,
    SearchResultItem,
    SearchSuggestionsRequest,
    SearchSuggestionsResponse,
)
from apps.document_rag_search.exceptions import (
    EmptyQueryError,
    InvalidDateRangeError,
    NoResultsError,
    QueryTooLongError,
    QueryTooShortError,
    SearchServiceError,
)
from apps.document_rag_search.ranking import (
    ContextExpansionConfig,
    ContextExpander,
    RRFConfig,
    RRFFusion,
    expand_to_search_items,
)
from apps.document_rag_search.retrievers import (
    GraphRetriever,
    KeywordRetriever,
    VectorRetriever,
)
from apps.embedding_engine.services import EmbeddingService


logger = logging.getLogger(__name__)


# =============================================================================
# Search Service Implementation
# =============================================================================


class SearchService:
    """High-level facade service for RAG search operations.

    This service provides a unified interface for all search operations,
    coordinating between multiple retrievers and applying fusion ranking.

    The service supports three search modes:
    1. Simple search: Vector-only search for quick queries
    2. Hybrid search: Multi-retriever search with RRF fusion
    3. Advanced search: Hybrid search with filters and context expansion

    Example:
        >>> service = SearchService()
        >>> # Simple search
        >>> result = service.search("What is machine learning?")
        >>> # Hybrid search with all retrievers
        >>> request = HybridSearchRequest(
        ...     query="What is machine learning?",
        ...     use_vector=True,
        ...     use_keyword=True,
        ...     use_graph=True,
        ...     top_k=10,
        ... )
        >>> result = service.hybrid_search(request)
    """

    def __init__(self, config: SearchConfig | None = None) -> None:
        """Initialize service with retrievers and fusion.

        Args:
            config: Search configuration. If None, loads from Django settings.
        """
        self._config = config or self._load_config_from_settings()

        # Initialize retrievers lazily (only when needed)
        self._vector_retriever: VectorRetriever | None = None
        self._keyword_retriever: KeywordRetriever | None = None
        self._graph_retriever: GraphRetriever | None = None

        # Initialize embedding service
        self._embedding_service = EmbeddingService()

        # Initialize RRF fusion with default config
        rrf_config = RRFConfig(
            k=self._config.default_rrf_k,
            weights={
                RetrieverName.VECTOR.value: self._config.vector_weight,
                RetrieverName.KEYWORD.value: self._config.keyword_weight,
                RetrieverName.GRAPH.value: self._config.graph_weight,
            },
        )
        self._fusion = RRFFusion(rrf_config)

        logger.debug(
            f"SearchService initialized with config: "
            f"top_k={self._config.default_top_k}, "
            f"rrf_k={self._config.default_rrf_k}"
        )

    # =========================================================================
    # Properties for lazy retriever initialization
    # =========================================================================

    @property
    def vector_retriever(self) -> VectorRetriever:
        """Get or create vector retriever."""
        if self._vector_retriever is None:
            self._vector_retriever = VectorRetriever()
        return self._vector_retriever

    @property
    def keyword_retriever(self) -> KeywordRetriever:
        """Get or create keyword retriever."""
        if self._keyword_retriever is None:
            self._keyword_retriever = KeywordRetriever()
        return self._keyword_retriever

    @property
    def graph_retriever(self) -> GraphRetriever:
        """Get or create graph retriever."""
        if self._graph_retriever is None:
            self._graph_retriever = GraphRetriever()
        return self._graph_retriever

    # =========================================================================
    # Public Methods
    # =========================================================================

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        user_id: str | None = None,
    ) -> SearchResponse:
        """Simple search using vector retrieval.

        This is a convenience method for quick vector-only searches.
        For more control, use hybrid_search().

        Args:
            query: Search query text.
            top_k: Maximum number of results.
            user_id: Optional user filter for access control.

        Returns:
            SearchResponse with results.

        Raises:
            EmptyQueryError: If query is empty.
            QueryTooLongError: If query exceeds max length.
            QueryTooShortError: If query is too short.
            SearchServiceError: If search operation fails.
        """
        logger.info(f"Simple search: query='{query[:50]}...', top_k={top_k}")

        request = HybridSearchRequest(
            query=query,
            top_k=top_k,
            use_vector=True,
            use_keyword=False,
            use_graph=False,
            filters={"user_id": user_id} if user_id else {},
        )

        return self.hybrid_search(request)

    def hybrid_search(
        self,
        request: HybridSearchRequest,
    ) -> SearchResponse:
        """Hybrid search combining multiple retrievers with RRF.

        This method performs search using the configured retrievers,
        fuses the results using RRF, and returns unified results.

        Args:
            request: HybridSearchRequest with query and options.

        Returns:
            SearchResponse with fused results.

        Raises:
            EmptyQueryError: If query is empty.
            QueryTooLongError: If query exceeds max length.
            QueryTooShortError: If query is too short.
            NoResultsError: If no results found.
            SearchServiceError: If search operation fails.
        """
        start_time = time.time()

        logger.info(
            f"Hybrid search: query='{request.query[:50]}...', "
            f"vector={request.use_vector}, keyword={request.use_keyword}, "
            f"graph={request.use_graph}, top_k={request.top_k}"
        )

        try:
            # Validate query
            self._validate_query(request.query)

            # Generate query embedding (needed for vector retriever)
            embedding = self._get_query_embedding(request.query)

            # Build SearchQuery object
            search_query = SearchQuery(
                text=request.query,
                embedding=embedding,
                user_id=request.filters.get("user_id"),
            )

            # Collect results from all enabled retrievers
            retriever_results: dict[str, RetrieverResult] = {}
            retrievers_used: list[str] = []

            if request.use_vector:
                result = self._retrieve_with_vector(search_query, request.top_k)
                if result:
                    retriever_results[RetrieverName.VECTOR.value] = result
                    retrievers_used.append(RetrieverName.VECTOR.value)

            if request.use_keyword:
                result = self._retrieve_with_keyword(search_query, request.top_k)
                if result:
                    retriever_results[RetrieverName.KEYWORD.value] = result
                    retrievers_used.append(RetrieverName.KEYWORD.value)

            if request.use_graph:
                result = self._retrieve_with_graph(search_query, request.top_k)
                if result:
                    retriever_results[RetrieverName.GRAPH.value] = result
                    retrievers_used.append(RetrieverName.GRAPH.value)

            # Check if we have any results
            if not retriever_results:
                logger.warning("No retrievers returned results")
                return self._create_empty_response(0.0, [])

            # Apply RRF fusion
            ranked_results = self._apply_rrf_fusion(
                retriever_results=retriever_results,
                top_k=request.top_k,
                rrf_k=request.rrf_k,
                weights=request.weights,
            )

            # Convert to SearchResultItem
            search_items = self._convert_to_search_items(ranked_results)

            elapsed_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Hybrid search completed in {elapsed_ms:.2f}ms, "
                f"returned {len(search_items)} results"
            )

            return SearchResponse(
                results=search_items,
                total=len(search_items),
                query_time_ms=elapsed_ms,
                retrievers_used=retrievers_used,
            )

        except (EmptyQueryError, QueryTooLongError, QueryTooShortError, NoResultsError):
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during hybrid search: {e}")
            raise SearchServiceError("hybrid_search", str(e)) from e

    def advanced_search(
        self,
        request: AdvancedSearchRequest,
    ) -> SearchResponse:
        """Advanced search with filters and options.

        This method extends hybrid search with additional filtering
        capabilities and optional context expansion.

        Args:
            request: AdvancedSearchRequest with filters and options.

        Returns:
            SearchResponse with filtered (and optionally expanded) results.

        Raises:
            InvalidDateRangeError: If date_from > date_to.
            EmptyQueryError: If query is empty.
            QueryTooLongError: If query exceeds max length.
            QueryTooShortError: If query is too short.
            NoResultsError: If no results found.
            SearchServiceError: If search operation fails.
        """
        start_time = time.time()

        logger.info(
            f"Advanced search: query='{request.query[:50]}...', "
            f"filters=user_id={request.user_id}, "
            f"expand_context={request.expand_context}"
        )

        try:
            # Validate filters
            self._validate_filters(request)

            # Build hybrid search request
            filters: dict[str, Any] = {}
            if request.user_id:
                filters["user_id"] = request.user_id
            if request.document_ids:
                filters["document_ids"] = request.document_ids

            hybrid_request = HybridSearchRequest(
                query=request.query,
                top_k=request.top_k,
                use_vector=request.use_vector,
                use_keyword=request.use_keyword,
                use_graph=request.use_graph,
                filters=filters,
                rrf_k=request.rrf_k,
            )

            # Execute hybrid search
            response = self.hybrid_search(hybrid_request)

            # Apply context expansion if enabled
            if request.expand_context and response.results:
                response = self._apply_context_expansion(
                    response=response,
                    window_size=request.context_window,
                )

            elapsed_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Advanced search completed in {elapsed_ms:.2f}ms, "
                f"returned {len(response.results)} results"
            )

            return response

        except (InvalidDateRangeError, EmptyQueryError, QueryTooLongError,
                QueryTooShortError, NoResultsError):
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during advanced search: {e}")
            raise SearchServiceError("advanced_search", str(e)) from e

    def get_search_suggestions(
        self,
        request: SearchSuggestionsRequest,
    ) -> SearchSuggestionsResponse:
        """Get search suggestions based on query prefix.

        Uses PostgreSQL trigram similarity to find similar text
        from existing document chunks.

        Args:
            request: SearchSuggestionsRequest with prefix.

        Returns:
            SearchSuggestionsResponse with suggested terms.

        Raises:
            SearchServiceError: If suggestion operation fails.
        """
        start_time = time.time()

        logger.info(
            f"Getting search suggestions: prefix='{request.prefix[:20]}...', "
            f"limit={request.limit}"
        )

        try:
            from apps.documents_parser.models import DocumentChunk

            # Use trigram similarity for suggestions
            suggestions = list(
                DocumentChunk.objects.filter(
                    content__icontains=request.prefix,
                )
                .distinct()
                .order_by("?")[:request.limit * 2]  # Get extra for dedup
                .values_list("content", flat=True)
            )

            # Extract unique words/phrases starting with prefix
            unique_suggestions: set[str] = set()
            prefix_lower = request.prefix.lower()

            for content in suggestions:
                words = content.split()
                for i, word in enumerate(words):
                    if word.lower().startswith(prefix_lower):
                        # Include a few words for context
                        phrase = " ".join(words[i:i+3])
                        unique_suggestions.add(phrase)
                        if len(unique_suggestions) >= request.limit:
                            break
                if len(unique_suggestions) >= request.limit:
                    break

            final_suggestions = list(unique_suggestions)[:request.limit]

            elapsed_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Search suggestions completed in {elapsed_ms:.2f}ms, "
                f"returned {len(final_suggestions)} suggestions"
            )

            return SearchSuggestionsResponse(
                suggestions=final_suggestions,
                total=len(final_suggestions),
            )

        except Exception as e:
            logger.exception(f"Unexpected error during search suggestions: {e}")
            raise SearchServiceError("get_search_suggestions", str(e)) from e

    def health_check(self) -> dict[str, bool]:
        """Check health of all retrievers.

        Returns:
            Dictionary mapping retriever name to health status.
        """
        health_status: dict[str, bool] = {}

        try:
            health_status["vector"] = self.vector_retriever.health_check()
        except Exception as e:
            logger.warning(f"Vector retriever health check failed: {e}")
            health_status["vector"] = False

        try:
            health_status["keyword"] = self.keyword_retriever.health_check()
        except Exception as e:
            logger.warning(f"Keyword retriever health check failed: {e}")
            health_status["keyword"] = False

        try:
            health_status["graph"] = self.graph_retriever.health_check()
        except Exception as e:
            logger.warning(f"Graph retriever health check failed: {e}")
            health_status["graph"] = False

        # Overall health
        health_status["overall"] = any(health_status.values())

        return health_status

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _load_config_from_settings(self) -> SearchConfig:
        """Load search configuration from Django settings.

        Returns:
            SearchConfig instance from settings.
        """
        search_config = getattr(settings, "SEARCH_CONFIG", {})

        return SearchConfig(
            default_top_k=search_config.get("default_top_k", DEFAULT_TOP_K),
            default_rrf_k=search_config.get("default_rrf_k", DEFAULT_RRF_K),
            max_query_length=search_config.get("max_query_length", MAX_QUERY_LENGTH),
            min_query_length=search_config.get("min_query_length", MIN_QUERY_LENGTH),
            vector_weight=search_config.get("retriever_weights", {}).get(
                "vector", 0.4
            ),
            keyword_weight=search_config.get("retriever_weights", {}).get(
                "keyword", 0.3
            ),
            graph_weight=search_config.get("retriever_weights", {}).get(
                "graph", 0.3
            ),
            enable_suggestions=search_config.get("suggestions", {}).get(
                "enabled", True
            ),
            context_expansion_enabled=search_config.get("context_expansion", {}).get(
                "enabled", False
            ),
            context_window=search_config.get("context_expansion", {}).get(
                "window_size", 1
            ),
        )

    def _validate_query(self, query: str) -> None:
        """Validate search query.

        Args:
            query: Query text to validate.

        Raises:
            EmptyQueryError: If query is empty or whitespace only.
            QueryTooShortError: If query is shorter than minimum length.
            QueryTooLongError: If query exceeds maximum length.
        """
        if not query or not query.strip():
            raise EmptyQueryError()

        query_length = len(query.strip())

        if query_length < MIN_QUERY_LENGTH:
            raise QueryTooShortError(query_length, MIN_QUERY_LENGTH)

        if query_length > MAX_QUERY_LENGTH:
            raise QueryTooLongError(query_length, MAX_QUERY_LENGTH)

    def _validate_filters(self, request: AdvancedSearchRequest) -> None:
        """Validate search filters.

        Args:
            request: Advanced search request with filters.

        Raises:
            InvalidDateRangeError: If date_from is after date_to.
        """
        if request.date_from and request.date_to:
            if request.date_from > request.date_to:
                raise InvalidDateRangeError(
                    str(request.date_from),
                    str(request.date_to),
                )

    def _get_query_embedding(self, query: str) -> list[float]:
        """Generate embedding for query text.

        Args:
            query: Query text to embed.

        Returns:
            Embedding vector.
        """
        result = self._embedding_service.embed_query(query)
        return result.embedding

    def _retrieve_with_vector(
        self,
        query: SearchQuery,
        top_k: int,
    ) -> RetrieverResult | None:
        """Retrieve using vector search.

        Args:
            query: Search query with text and embedding.
            top_k: Maximum results to return.

        Returns:
            RetrieverResult or None if retrieval failed.
        """
        try:
            result = self.vector_retriever.retrieve(
                query=query,
                top_k=top_k,
            )
            logger.debug(
                f"Vector retriever returned {result.total} results "
                f"in {result.query_time_ms:.2f}ms"
            )
            return result
        except Exception as e:
            logger.warning(f"Vector retriever failed: {e}")
            return None

    def _retrieve_with_keyword(
        self,
        query: SearchQuery,
        top_k: int,
    ) -> RetrieverResult | None:
        """Retrieve using keyword (FTS) search.

        Args:
            query: Search query with text.
            top_k: Maximum results to return.

        Returns:
            RetrieverResult or None if retrieval failed.
        """
        try:
            result = self.keyword_retriever.retrieve(
                query=query,
                top_k=top_k,
            )
            logger.debug(
                f"Keyword retriever returned {result.total} results "
                f"in {result.query_time_ms:.2f}ms"
            )
            return result
        except Exception as e:
            logger.warning(f"Keyword retriever failed: {e}")
            return None

    def _retrieve_with_graph(
        self,
        query: SearchQuery,
        top_k: int,
    ) -> RetrieverResult | None:
        """Retrieve using graph (Neo4j) search.

        Args:
            query: Search query with text.
            top_k: Maximum results to return.

        Returns:
            RetrieverResult or None if retrieval failed.
        """
        try:
            result = self.graph_retriever.retrieve(
                query=query,
                top_k=top_k,
            )
            logger.debug(
                f"Graph retriever returned {result.total} results "
                f"in {result.query_time_ms:.2f}ms"
            )
            return result
        except Exception as e:
            logger.warning(f"Graph retriever failed: {e}")
            return None

    def _apply_rrf_fusion(
        self,
        retriever_results: dict[str, RetrieverResult],
        top_k: int,
        rrf_k: int | None = None,
        weights: dict[str, float] | None = None,
    ) -> list[RankedResult]:
        """Apply RRF fusion to retriever results.

        Args:
            retriever_results: Results from each retriever.
            top_k: Maximum results to return.
            rrf_k: RRF parameter (optional override).
            weights: Retriever weights (optional override).

        Returns:
            List of RankedResult sorted by fused score.
        """
        # Create fusion config with overrides if provided
        if rrf_k is not None or weights is not None:
            fusion_config = RRFConfig(
                k=rrf_k if rrf_k is not None else self._config.default_rrf_k,
                weights=weights if weights is not None else {
                    RetrieverName.VECTOR.value: self._config.vector_weight,
                    RetrieverName.KEYWORD.value: self._config.keyword_weight,
                    RetrieverName.GRAPH.value: self._config.graph_weight,
                },
            )
            fusion = RRFFusion(fusion_config)
        else:
            fusion = self._fusion

        return fusion.fuse(retriever_results, top_k)

    def _convert_to_search_items(
        self,
        ranked_results: list[RankedResult],
    ) -> list[SearchResultItem]:
        """Convert RankedResult list to SearchResultItem list.

        Args:
            ranked_results: List of RankedResult from fusion.

        Returns:
            List of SearchResultItem for API response.
        """
        return [
            SearchResultItem(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                text=r.text,
                score=r.score,
                source=r.source,
                metadata=r.metadata,
                retriever_scores=r.retriever_scores,
            )
            for r in ranked_results
        ]

    def _apply_context_expansion(
        self,
        response: SearchResponse,
        window_size: int,
    ) -> SearchResponse:
        """Apply context expansion to search results.

        Args:
            response: Original search response.
            window_size: Number of neighbor chunks to include.

        Returns:
            New SearchResponse with expanded context.
        """
        config = ContextExpansionConfig(
            enabled=True,
            window_size=window_size,
        )

        # Convert SearchResultItem back to RankedResult for expansion
        ranked_results = [
            RankedResult(
                chunk_id=item.chunk_id,
                document_id=item.document_id,
                text=item.text,
                score=item.score,
                source=item.source,
                metadata=item.metadata,
                retriever_scores=item.retriever_scores,
            )
            for item in response.results
        ]

        # Expand and convert back
        expanded_items = expand_to_search_items(ranked_results, config)

        return SearchResponse(
            results=expanded_items,
            total=len(expanded_items),
            query_time_ms=response.query_time_ms,
            retrievers_used=response.retrievers_used,
        )

    def _create_empty_response(
        self,
        query_time_ms: float,
        retrievers_used: list[str],
    ) -> SearchResponse:
        """Create an empty search response.

        Args:
            query_time_ms: Query time in milliseconds.
            retrievers_used: List of retrievers that were attempted.

        Returns:
            Empty SearchResponse.
        """
        return SearchResponse(
            results=[],
            total=0,
            query_time_ms=query_time_ms,
            retrievers_used=retrievers_used,
        )
