"""
Graph retriever for document RAG search module.

This retriever uses Neo4j knowledge graph for entity-based context retrieval,
supporting entity extraction, graph traversal, and chunk recommendation.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from apps.document_rag_search.constants import (
    DEFAULT_TOP_K,
    RetrieverName,
)
from apps.document_rag_search.dto import (
    RetrieverResult,
    SearchQuery,
)
from apps.document_rag_search.exceptions import GraphRetrieverError
from apps.document_rag_search.retrievers.base import BaseRetriever
from apps.documents_parser.models import DocumentChunk
from apps.neo4j_database_controller.dto import NodeInfo
from apps.neo4j_database_controller.services.neo4j_service import Neo4jService

logger = logging.getLogger(__name__)


class GraphRetriever(BaseRetriever):
    """Retriever that uses Neo4j knowledge graph for context retrieval.

    This retriever performs entity-based retrieval using Neo4j's graph
    capabilities. It supports:
    - Entity extraction from query (simple keyword-based for MVP)
    - Finding chunks that mention relevant entities
    - Graph traversal for related context
    - Multi-hop relationship expansion

    Note:
        For MVP, entity extraction uses simple keyword matching.
        Future versions should integrate LLM-based entity extraction.

    Example:
        >>> retriever = GraphRetriever()
        >>> result = retriever.retrieve(
        ...     query=SearchQuery(text="What is the relationship between AI and machine learning?"),
        ...     top_k=10,
        ... )
        >>> print(len(result.items))
        5
    """

    # Common stop words to filter out during entity extraction
    STOP_WORDS = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "dare",
        "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
        "from", "as", "into", "through", "during", "before", "after",
        "above", "below", "between", "under", "again", "further", "then",
        "once", "here", "there", "when", "where", "why", "how", "all", "each",
        "few", "more", "most", "other", "some", "such", "no", "nor", "not",
        "only", "own", "same", "so", "than", "too", "very", "just", "and",
        "but", "if", "or", "because", "until", "while", "although", "though",
        "what", "which", "who", "whom", "this", "that", "these", "those",
        "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you",
        "your", "yours", "yourself", "yourselves", "he", "him", "his",
        "himself", "she", "her", "hers", "herself", "it", "its", "itself",
        "they", "them", "their", "theirs", "themselves",
        # Chinese stop words
        "的", "是", "在", "有", "和", "与", "或", "了", "着", "过",
        "这", "那", "这", "那", "什么", "怎么", "如何", "为什么",
        "哪", "谁", "哪里", "哪个", "哪些", "多少", "几", "多",
        "可以", "能", "会", "要", "应", "应该", "必须", "需",
        "不", "没", "没有", "无", "非", "未",
    }

    def __init__(
        self,
        neo4j_service: Neo4jService | None = None,
        max_depth: int = 2,
        entity_limit: int = 10,
        min_entity_length: int = 2,
    ) -> None:
        """Initialize the graph retriever.

        Args:
            neo4j_service: Optional Neo4jService instance.
            max_depth: Maximum depth for graph traversal.
            entity_limit: Maximum number of entities to consider.
            min_entity_length: Minimum length for entity keywords.
        """
        self._neo4j_service = neo4j_service or Neo4jService()
        self._max_depth = max_depth
        self._entity_limit = entity_limit
        self._min_entity_length = min_entity_length

    @property
    def name(self) -> str:
        """Return retriever name."""
        return RetrieverName.GRAPH.value

    def retrieve(
        self,
        query: SearchQuery,
        top_k: int = DEFAULT_TOP_K,
        **kwargs: Any,
    ) -> RetrieverResult:
        """Retrieve documents using graph-based entity context.

        This method:
        1. Extracts potential entities from the query (simple keyword extraction)
        2. Searches for matching entities in the knowledge graph
        3. Finds chunks that mention these entities
        4. Expands context via graph traversal

        Args:
            query: Search query with text.
            top_k: Maximum number of results to return.
            **kwargs: Additional parameters:
                - max_depth: Override default traversal depth
                - entity_limit: Override default entity limit
                - user_id: Filter by user (not yet implemented in graph)

        Returns:
            RetrieverResult with matching documents.

        Raises:
            GraphRetrieverError: If retrieval fails.
        """
        start_time = time.time()

        try:
            # Extract potential entity keywords from query
            entity_keywords = self._extract_entity_keywords(query.text)
            logger.debug(f"Extracted entity keywords: {entity_keywords}")

            if not entity_keywords:
                # No entities found, return empty result
                return RetrieverResult(
                    retriever_name=self.name,
                    items=[],
                    query_time_ms=0.0,
                    total=0,
                )

            # Get parameters from kwargs
            max_depth = kwargs.get("max_depth", self._max_depth)
            entity_limit = kwargs.get("entity_limit", self._entity_limit)

            # Find chunks through entity-based retrieval
            chunk_data = self._find_chunks_by_entities(
                entity_keywords=entity_keywords,
                top_k=top_k,
                max_depth=max_depth,
                entity_limit=entity_limit,
                user_id=query.user_id,
            )

            query_time_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"Graph retrieval completed in {query_time_ms:.2f}ms, "
                f"found {len(chunk_data)} results"
            )

            return RetrieverResult(
                retriever_name=self.name,
                items=chunk_data,
                query_time_ms=query_time_ms,
                total=len(chunk_data),
            )

        except Exception as e:
            logger.error(f"Graph retriever failed: {e}")
            raise GraphRetrieverError(reason=str(e))

    def _extract_entity_keywords(self, query_text: str) -> list[str]:
        """Extract potential entity keywords from query text.

        This is a simple keyword extraction for MVP. Future versions
        should use NER (Named Entity Recognition) or LLM-based extraction.

        Args:
            query_text: Query text to extract entities from.

        Returns:
            List of potential entity keywords.
        """
        # Clean and normalize text
        text = query_text.strip()

        # Extract words/tokens
        # For English: split by whitespace and punctuation
        # For Chinese: split by characters (simple approach)
        tokens = []

        # Split by common delimiters
        words = re.split(r"[\s,，。.!！?？;；:：、""'「」【】()（）\[\]]+", text)

        for word in words:
            word = word.strip()
            if not word:
                continue

            # Skip stop words
            if word.lower() in self.STOP_WORDS:
                continue

            # Skip short words
            if len(word) < self._min_entity_length:
                continue

            # Check if it's Chinese (all characters are Chinese)
            if self._is_chinese(word):
                # For Chinese, also add individual characters as potential entities
                if len(word) >= 2:
                    tokens.append(word)
                # Optionally split long Chinese phrases
                if len(word) > 4:
                    # Add 2-4 character segments
                    for i in range(len(word) - 1):
                        tokens.append(word[i:i+2])
            else:
                # English word
                tokens.append(word)

        # Deduplicate and limit
        unique_tokens = list(dict.fromkeys(tokens))
        return unique_tokens[:self._entity_limit]

    def _is_chinese(self, text: str) -> bool:
        """Check if text contains Chinese characters.

        Args:
            text: Text to check.

        Returns:
            True if text contains Chinese characters.
        """
        for char in text:
            if "\u4e00" <= char <= "\u9fff":
                return True
        return False

    def _find_chunks_by_entities(
        self,
        entity_keywords: list[str],
        top_k: int,
        max_depth: int,
        entity_limit: int,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find chunks through entity-based graph traversal.

        Args:
            entity_keywords: List of entity keywords to search.
            top_k: Maximum results.
            max_depth: Graph traversal depth.
            entity_limit: Maximum entities to process.
            user_id: Optional user filter (not yet implemented).

        Returns:
            List of chunk data dictionaries.
        """
        # Find entities in Neo4j by name matching
        found_entities: list[NodeInfo] = []
        for keyword in entity_keywords[:entity_limit]:
            try:
                entities = self._neo4j_service.search_entities(
                    name=keyword,
                    limit=5,
                )
                found_entities.extend(entities)
            except Exception as e:
                logger.warning(f"Failed to search entities for '{keyword}': {e}")

        if not found_entities:
            return []

        logger.debug(f"Found {len(found_entities)} entities in graph")

        # Get chunk IDs from entity contexts
        chunk_data_map: dict[str, dict[str, Any]] = {}

        for entity in found_entities[:entity_limit]:
            try:
                # Get entity context (includes mentioning chunks)
                context = self._neo4j_service.get_entity_context(
                    entity_id=entity.id,
                    include_chunks=True,
                    include_related_entities=True,
                    include_concepts=False,
                    max_depth=max_depth,
                )

                if context and context.mentioned_in:
                    for chunk_node in context.mentioned_in:
                        chunk_id = chunk_node.id
                        if chunk_id not in chunk_data_map:
                            chunk_data_map[chunk_id] = {
                                "chunk_id": chunk_id,
                                "document_id": chunk_node.properties.get(
                                    "document_id", ""
                                ),
                                "text": chunk_node.properties.get("text", ""),
                                "score": 0.0,
                                "source": "",
                                "metadata": {
                                    "chunk_index": chunk_node.properties.get(
                                        "chunk_index", 0
                                    ),
                                    "page_number": chunk_node.properties.get(
                                        "page_number"
                                    ),
                                    "entity_match": entity.properties.get("name", ""),
                                },
                            }
                        # Increase score for each matching entity
                        chunk_data_map[chunk_id]["score"] += 1.0

            except Exception as e:
                logger.warning(f"Failed to get context for entity {entity.id}: {e}")

        # Sort by score and limit
        chunk_data = sorted(
            chunk_data_map.values(),
            key=lambda x: x["score"],
            reverse=True,
        )[:top_k]

        # Enrich with document source info from PostgreSQL
        self._enrich_chunk_sources(chunk_data)

        return chunk_data

    def _enrich_chunk_sources(self, chunk_data: list[dict[str, Any]]) -> None:
        """Enrich chunk data with document source information.

        Args:
            chunk_data: List of chunk data dictionaries to enrich in-place.
        """
        try:
            # Collect unique document IDs
            doc_ids = {
                cd["document_id"]
                for cd in chunk_data
                if cd.get("document_id")
            }

            if not doc_ids:
                return

            # Batch fetch documents from PostgreSQL
            documents = {
                str(doc.id): doc
                for doc in DocumentChunk.objects.filter(
                    id__in=list(doc_ids)[:50]  # Limit batch size
                ).select_related("document")
            }

            # Update chunk data with source info
            for cd in chunk_data:
                chunk_id = cd.get("chunk_id")
                if chunk_id and chunk_id in documents:
                    chunk = documents[chunk_id]
                    cd["text"] = cd.get("text") or chunk.content
                    cd["source"] = chunk.document.original_name
                    cd["document_id"] = str(chunk.document_id)
                    cd["metadata"]["char_count"] = chunk.char_count

        except Exception as e:
            logger.warning(f"Failed to enrich chunk sources: {e}")

    def health_check(self) -> bool:
        """Check if Neo4j is healthy and accessible.

        Returns:
            True if retriever is healthy, False otherwise.
        """
        try:
            health = self._neo4j_service.health_check()
            return health.get("connected", False)
        except Exception as e:
            logger.error(f"Graph retriever health check failed: {e}")
            return False
