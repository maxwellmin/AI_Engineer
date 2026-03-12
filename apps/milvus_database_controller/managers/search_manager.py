"""
Search manager for Milvus database controller.

This module provides search operations including single vector search,
hybrid search, and BM25 text search.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from apps.milvus_database_controller.client import MilvusClientWrapper
from apps.milvus_database_controller.client import AnnSearchRequest, RRFRanker
from apps.milvus_database_controller.constants import (
    DEFAULT_TOP_K,
    FieldName,
    HNSW_SEARCH_PARAMS,
    SPARSE_SEARCH_PARAMS,
)
from apps.milvus_database_controller.dto import (
    BM25SearchRequest,
    HybridSearchRequest,
    HybridSearchResult,
    SearchRequest,
    SearchResult,
    SearchResultItem,
)
from apps.milvus_database_controller.exceptions import (
    CollectionNotFoundError,
    HybridSearchError,
    InvalidFilterError,
    SearchError,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SearchManager:
    """Manager for Milvus search operations.

    This class handles:
    - Single vector field search
    - Hybrid search across multiple vector fields
    - BM25 sparse vector search
    - Search with metadata filters

    Example:
        >>> manager = SearchManager()
        >>> result = manager.search("documents", query_vector, top_k=10)
    """

    def __init__(self, client: MilvusClientWrapper | None = None) -> None:
        """Initialize the search manager.

        Args:
            client: Optional MilvusClientWrapper instance.
        """
        self._client = client or MilvusClientWrapper.get_instance()

    def _validate_collection(self, collection_name: str) -> None:
        """Validate that collection exists.

        Args:
            collection_name: Name of the collection.

        Raises:
            CollectionNotFoundError: If collection does not exist.
        """
        if not self._client.has_collection(collection_name):
            raise CollectionNotFoundError(collection_name)

    def _parse_search_results(
        self,
        results: list[list[dict[str, Any]]],
        top_k: int,
    ) -> list[SearchResultItem]:
        """Parse search results into SearchResultItem objects.

        Args:
            results: Raw search results from Milvus.
            top_k: Maximum number of results.

        Returns:
            List of SearchResultItem objects.
        """
        items: list[SearchResultItem] = []

        # Results are organized by query (list of lists)
        # We typically have one query, so take the first list
        if results and len(results) > 0:
            for hit in results[0]:
                item = SearchResultItem(
                    id=str(hit.get("id", hit.get("pk", ""))),
                    distance=hit.get("distance", 0.0),
                    text=hit.get(FieldName.TEXT.value, ""),
                    summary=hit.get(FieldName.SUMMARY.value, ""),
                    document=hit.get(FieldName.DOCUMENT.value, ""),
                    source=hit.get(FieldName.SOURCE.value, ""),
                    source_name=hit.get(FieldName.SOURCE_NAME.value, ""),
                    lt_doc_id=hit.get(FieldName.LT_DOC_ID.value, ""),
                    chunk_id=hit.get(FieldName.CHUNK_ID.value, 0),
                )
                items.append(item)

        return items[:top_k]

    def search(self, request: SearchRequest) -> SearchResult:
        """Perform a single vector field search.

        Args:
            request: Search request with query vector and parameters.

        Returns:
            SearchResult with matching items.

        Raises:
            CollectionNotFoundError: If collection does not exist.
            SearchError: If search fails.
        """
        self._validate_collection(request.collection_name)

        start_time = time.time()

        try:
            output_fields = request.output_fields or [
                FieldName.PK.value,
                FieldName.TEXT.value,
                FieldName.SUMMARY.value,
                FieldName.DOCUMENT.value,
                FieldName.SOURCE.value,
                FieldName.SOURCE_NAME.value,
                FieldName.LT_DOC_ID.value,
                FieldName.CHUNK_ID.value,
            ]

            search_params = request.search_params or HNSW_SEARCH_PARAMS.copy()

            logger.debug(
                f"Searching in '{request.collection_name}' on field '{request.anns_field}' "
                f"with top_k={request.top_k}"
            )

            results = self._client.search(
                collection_name=request.collection_name,
                data=[request.query_vector],
                anns_field=request.anns_field,
                limit=request.top_k,
                filter_expr=request.filter_expr if request.filter_expr else None,
                output_fields=output_fields,
                search_params=search_params,
            )

            items = self._parse_search_results(results, request.top_k)
            query_time_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"Search completed in {query_time_ms:.2f}ms, found {len(items)} results"
            )

            return SearchResult(
                items=items,
                total=len(items),
                query_time_ms=query_time_ms,
            )

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise SearchError(
                reason=str(e),
                collection_name=request.collection_name,
            )

    def hybrid_search(self, request: HybridSearchRequest) -> HybridSearchResult:
        """Perform hybrid search across multiple vector fields.

        This method supports:
        1. Multi-dense-vector fusion (summary_dense + text_dense)
        2. Dense + sparse (BM25) fusion

        For dense + sparse fusion, pass query_text and enable_sparse=True.

        Args:
            request: Hybrid search request with query vectors and optional query_text.

        Returns:
            HybridSearchResult with combined and reranked items.

        Raises:
            HybridSearchError: If hybrid search fails.
        """
        self._validate_collection(request.collection_name)

        start_time = time.time()

        try:
            output_fields = request.output_fields or [
                FieldName.PK.value,
                FieldName.TEXT.value,
                FieldName.SUMMARY.value,
                FieldName.DOCUMENT.value,
                FieldName.SOURCE.value,
                FieldName.SOURCE_NAME.value,
                FieldName.LT_DOC_ID.value,
                FieldName.CHUNK_ID.value,
            ]

            # Check if we should include BM25 sparse search
            include_sparse = (
                hasattr(request, "include_sparse")
                and request.include_sparse
                and request.query_text
            )

            if include_sparse:
                # Use Milvus hybrid_search API for dense + sparse fusion
                return self._hybrid_search_with_sparse(
                    request=request,
                    output_fields=output_fields,
                    start_time=start_time,
                )
            else:
                # Use application-level fusion for multi-dense-vector search
                return self._hybrid_search_dense_only(
                    request=request,
                    output_fields=output_fields,
                    start_time=start_time,
                )

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise HybridSearchError(
                reason=str(e),
                collection_name=request.collection_name,
            )

    def _hybrid_search_with_sparse(
        self,
        request: HybridSearchRequest,
        output_fields: list[str],
        start_time: float,
    ) -> HybridSearchResult:
        """Perform dense + sparse hybrid search using Milvus API.

        Uses Milvus 2.5+ hybrid_search with AnnSearchRequest and RRFRanker.
        """
        # Build search requests for each vector field
        reqs: list[AnnSearchRequest] = []

        # Dense vector search requests
        for field_name, query_vector in request.query_vectors.items():
            dense_req = AnnSearchRequest(
                data=[query_vector],
                anns_field=field_name,
                param=HNSW_SEARCH_PARAMS,
                limit=request.top_k * 2,  # Get more for better fusion
                expr=request.filter_expr if request.filter_expr else None,
            )
            reqs.append(dense_req)

        # BM25 sparse search request
        sparse_req = AnnSearchRequest(
            data=[request.query_text],  # Pass query text directly
            anns_field=FieldName.TEXT_SPARSE.value,
            param=SPARSE_SEARCH_PARAMS,
            limit=request.top_k * 2,
            expr=request.filter_expr if request.filter_expr else None,
        )
        reqs.append(sparse_req)

        # Create ranker (RRF by default)
        ranker = RRFRanker(k=request.rrf_k)

        # Execute hybrid search
        results = self._client.hybrid_search(
            collection_name=request.collection_name,
            reqs=reqs,
            ranker=ranker,
            limit=request.top_k,
            output_fields=output_fields,
        )

        # Parse results
        items = self._parse_search_results(results, request.top_k)
        query_time_ms = (time.time() - start_time) * 1000

        logger.debug(
            f"Dense+sparse hybrid search completed in {query_time_ms:.2f}ms, "
            f"found {len(items)} results"
        )

        return HybridSearchResult(
            items=items,
            total=len(items),
            query_time_ms=query_time_ms,
            search_details={
                "method": "milvus_hybrid_rrf",
                "rrf_k": request.rrf_k,
                "include_sparse": True,
            },
        )

    def _hybrid_search_dense_only(
        self,
        request: HybridSearchRequest,
        output_fields: list[str],
        start_time: float,
    ) -> HybridSearchResult:
        """Perform multi-dense-vector hybrid search with application-level fusion.

        This is the original implementation for dense-only fusion.
        """
        # Store results from each search
        all_results: dict[str, list[dict[str, Any]]] = {}

        # Perform individual searches for each vector field
        for field_name, query_vector in request.query_vectors.items():
            search_req = SearchRequest(
                collection_name=request.collection_name,
                query_vector=query_vector,
                anns_field=field_name,
                top_k=request.top_k * 2,  # Get more for better fusion
                filter_expr=request.filter_expr,
                output_fields=output_fields,
            )

            result = self.search(search_req)
            all_results[field_name] = [
                {
                    "id": item.id,
                    "distance": item.distance,
                    "text": item.text,
                    "summary": item.summary,
                    "document": item.document,
                    "source": item.source,
                    "source_name": item.source_name,
                    "lt_doc_id": item.lt_doc_id,
                    "chunk_id": item.chunk_id,
                }
                for item in result.items
            ]

        # Combine results using RRF or weighted scoring
        if request.rerank_method == "rrf":
            combined = self._reciprocal_rank_fusion(
                all_results,
                k=request.rrf_k,
                top_k=request.top_k,
            )
        else:
            combined = self._weighted_fusion(
                all_results,
                weights=request.weights,
                top_k=request.top_k,
            )

        query_time_ms = (time.time() - start_time) * 1000

        logger.debug(
            f"Dense-only hybrid search completed in {query_time_ms:.2f}ms, "
            f"found {len(combined)} results"
        )

        return HybridSearchResult(
            items=combined,
            total=len(combined),
            query_time_ms=query_time_ms,
            search_details={
                "method": request.rerank_method,
                "include_sparse": False,
            },
        )

    def _reciprocal_rank_fusion(
        self,
        all_results: dict[str, list[dict[str, Any]]],
        k: int = 60,
        top_k: int = 10,
    ) -> list[SearchResultItem]:
        """Combine results using Reciprocal Rank Fusion.

        RRF score = sum(1 / (k + rank)) for each result list

        Args:
            all_results: Results from each vector field search.
            k: RRF parameter (default 60).
            top_k: Number of results to return.

        Returns:
            Combined and ranked results.
        """
        scores: dict[str, float] = {}
        item_data: dict[str, dict[str, Any]] = {}

        for field_name, results in all_results.items():
            for rank, item in enumerate(results, start=1):
                item_id = item["id"]
                if item_id not in scores:
                    scores[item_id] = 0.0
                    item_data[item_id] = item

                # Add RRF score contribution
                scores[item_id] += 1.0 / (k + rank)

        # Sort by combined score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # Build result items
        combined: list[SearchResultItem] = []
        for item_id in sorted_ids[:top_k]:
            data = item_data[item_id]
            combined.append(
                SearchResultItem(
                    id=item_id,
                    distance=scores[item_id],  # RRF score as distance
                    text=data.get("text", ""),
                    summary=data.get("summary", ""),
                    document=data.get("document", ""),
                    source=data.get("source", ""),
                    source_name=data.get("source_name", ""),
                    lt_doc_id=data.get("lt_doc_id", ""),
                    chunk_id=data.get("chunk_id", 0),
                )
            )

        return combined

    def _weighted_fusion(
        self,
        all_results: dict[str, list[dict[str, Any]]],
        weights: list[float] | None,
        top_k: int = 10,
    ) -> list[SearchResultItem]:
        """Combine results using weighted scoring.

        Args:
            all_results: Results from each vector field search.
            weights: Weight for each field (should sum to 1.0).
            top_k: Number of results to return.

        Returns:
            Combined and ranked results.
        """
        if weights is None:
            # Equal weights if not specified
            weights = [1.0 / len(all_results)] * len(all_results)

        scores: dict[str, float] = {}
        item_data: dict[str, dict[str, Any]] = {}

        for (field_name, results), weight in zip(all_results.items(), weights):
            for item in results:
                item_id = item["id"]
                if item_id not in scores:
                    scores[item_id] = 0.0
                    item_data[item_id] = item

                # Add weighted distance score
                # Note: Lower distance is better, so we invert
                distance = item.get("distance", 1.0)
                scores[item_id] += weight * (1.0 - distance)

        # Sort by combined score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # Build result items
        combined: list[SearchResultItem] = []
        for item_id in sorted_ids[:top_k]:
            data = item_data[item_id]
            combined.append(
                SearchResultItem(
                    id=item_id,
                    distance=scores[item_id],
                    text=data.get("text", ""),
                    summary=data.get("summary", ""),
                    document=data.get("document", ""),
                    source=data.get("source", ""),
                    source_name=data.get("source_name", ""),
                    lt_doc_id=data.get("lt_doc_id", ""),
                    chunk_id=data.get("chunk_id", 0),
                )
            )

        return combined

    def bm25_search(self, request: BM25SearchRequest) -> SearchResult:
        """Perform BM25 sparse vector search.

        This method uses Milvus built-in BM25 function for text search.
        The query text is passed directly to Milvus, which handles the
        sparse vector generation automatically.

        Args:
            request: BM25 search request with query text.

        Returns:
            SearchResult with matching items.

        Raises:
            CollectionNotFoundError: If collection does not exist.
            SearchError: If search fails.
        """
        self._validate_collection(request.collection_name)

        start_time = time.time()

        try:
            output_fields = request.output_fields or [
                FieldName.PK.value,
                FieldName.TEXT.value,
                FieldName.SUMMARY.value,
                FieldName.DOCUMENT.value,
                FieldName.SOURCE.value,
                FieldName.SOURCE_NAME.value,
                FieldName.LT_DOC_ID.value,
                FieldName.CHUNK_ID.value,
            ]

            # BM25 search: pass query text directly
            # Milvus 2.5+ BM25 Function handles text -> sparse vector conversion
            search_params = SPARSE_SEARCH_PARAMS.copy()

            logger.debug(
                f"BM25 search in '{request.collection_name}' with query: "
                f"'{request.query_text[:50]}...' top_k={request.top_k}"
            )

            results = self._client.search(
                collection_name=request.collection_name,
                data=[request.query_text],  # Pass query text directly
                anns_field=FieldName.TEXT_SPARSE.value,
                limit=request.top_k,
                filter_expr=request.filter_expr if request.filter_expr else None,
                output_fields=output_fields,
                search_params=search_params,
            )

            items = self._parse_search_results(results, request.top_k)
            query_time_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"BM25 search completed in {query_time_ms:.2f}ms, "
                f"found {len(items)} results"
            )

            return SearchResult(
                items=items,
                total=len(items),
                query_time_ms=query_time_ms,
            )

        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            raise SearchError(
                reason=str(e),
                collection_name=request.collection_name,
            )

    def search_by_document(
        self,
        collection_name: str,
        document_id: str,
        query_vector: list[float],
        top_k: int = 5,
        anns_field: str = FieldName.TEXT_DENSE.value,
    ) -> SearchResult:
        """Search within a specific document's chunks.

        Args:
            collection_name: Name of the collection.
            document_id: PostgreSQL document ID.
            query_vector: Query embedding vector.
            top_k: Number of results.
            anns_field: Vector field to search.

        Returns:
            SearchResult with matching chunks.
        """
        filter_expr = f'{FieldName.LT_DOC_ID.value} == "{document_id}"'

        request = SearchRequest(
            collection_name=collection_name,
            query_vector=query_vector,
            anns_field=anns_field,
            top_k=top_k,
            filter_expr=filter_expr,
        )

        return self.search(request)

    def search_by_source(
        self,
        collection_name: str,
        source_type: str,
        query_vector: list[float],
        top_k: int = 10,
        anns_field: str = FieldName.TEXT_DENSE.value,
    ) -> SearchResult:
        """Search within a specific source type.

        Args:
            collection_name: Name of the collection.
            source_type: Source type to filter by.
            query_vector: Query embedding vector.
            top_k: Number of results.
            anns_field: Vector field to search.

        Returns:
            SearchResult with matching items.
        """
        filter_expr = f'{FieldName.SOURCE.value} == "{source_type}"'

        request = SearchRequest(
            collection_name=collection_name,
            query_vector=query_vector,
            anns_field=anns_field,
            top_k=top_k,
            filter_expr=filter_expr,
        )

        return self.search(request)
