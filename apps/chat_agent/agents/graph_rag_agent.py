"""
Graph RAG Agent implementation.

This module provides a RAG agent with entity context enrichment,
using Neo4j for graph traversal to enhance context.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import StateGraph

from apps.chat_agent.agents.base import BaseRAGAgent
from apps.chat_agent.agents.state import AgentState

logger = logging.getLogger(__name__)


class GraphRAGAgent(BaseRAGAgent):
    """Graph RAG agent for relationship-aware queries.

    This agent extends the base RAG workflow with entity context:
    1. Retrieve relevant documents and context
    2. Extract entities and enrich context from Neo4j
    3. Generate response using LLM
    4. Save conversation turn

    Graph structure:
        ┌──────────┐    ┌─────────────┐    ┌──────────┐    ┌──────────┐
        │ retrieve │ -> │ entity_ctx  │ -> │ generate │ -> │   save   │
        └──────────┘    └─────────────┘    └──────────┘    └──────────┘

    The entity_context node extracts entities from the query and
    retrieves related information from the Neo4j knowledge graph.

    Example:
        >>> agent = GraphRAGAgent()
        >>> async for state in agent.run(conversation_id, query, user_id):
        ...     print(state.get("response", ""))
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the Graph RAG agent."""
        super().__init__(*args, **kwargs)
        self._neo4j_service = None

    @property
    def neo4j_service(self):
        """Get or create Neo4j service instance (lazy initialization)."""
        if self._neo4j_service is None:
            from apps.neo4j_database_controller.services import Neo4jQueryService

            self._neo4j_service = Neo4jQueryService()
        return self._neo4j_service

    def build_graph(self) -> StateGraph:
        """Build the Graph RAG graph with entity context.

        The graph has four nodes:
        - retrieve: Get relevant context
        - entity_context: Enrich with Neo4j graph data
        - generate: Generate response with LLM
        - save: Save conversation turn

        Returns:
            Compiled StateGraph.
        """
        # Create graph with AgentState
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("retrieve", self._retrieve_node)
        graph.add_node("entity_context", self._entity_context_node)
        graph.add_node("generate", self._generate_node)
        graph.add_node("save", self._save_node)

        # Set entry point
        graph.set_entry_point("retrieve")

        # Add edges
        graph.add_edge("retrieve", "entity_context")
        graph.add_edge("entity_context", "generate")
        graph.add_edge("generate", "save")

        # Set finish point
        graph.set_finish_point("save")

        # Compile and return
        return graph.compile()

    async def _entity_context_node(self, state: AgentState) -> dict:
        """Extract entities and enrich context from Neo4j.

        This node extracts entities from the query and retrieves
        related information from the knowledge graph to enhance
        the context.

        Args:
            state: Current agent state.

        Returns:
            State update with enriched context.
        """
        try:
            # Extract entities from query (simple keyword extraction)
            entities = await self._extract_entities(state["query"])

            if not entities:
                # No entities found, skip enrichment
                return {}

            # Get entity relationships from Neo4j
            graph_context = await self._get_entity_context(entities)

            if not graph_context:
                return {}

            # Append graph context to existing context
            enriched_context = state["context"]
            if enriched_context:
                enriched_context += "\n\n"
            enriched_context += "=== Knowledge Graph Context ===\n"
            enriched_context += graph_context

            # Update sources with graph sources
            sources = state.get("sources", [])
            sources.append({
                "chunk_id": "graph",
                "document_id": "neo4j",
                "text": graph_context,
                "score": 1.0,
                "source": "graph",
            })

            return {
                "context": enriched_context,
                "sources": sources,
            }

        except Exception as e:
            logger.warning(f"Entity context extraction failed: {e}")
            # Don't fail the whole pipeline, just skip enrichment
            return {}

    async def _extract_entities(self, query: str) -> list[str]:
        """Extract entities from the query.

        This is a simple implementation that extracts capitalized
        words and potential named entities. For production, consider
        using an NER model or entity extraction service.

        Args:
            query: Query text.

        Returns:
            List of extracted entity names.
        """
        # Simple entity extraction: capitalized words and quoted phrases
        import re

        entities: list[str] = []

        # Find quoted phrases
        quoted = re.findall(r'"([^"]+)"', query)
        entities.extend(quoted)

        # Find capitalized words (potential named entities)
        capitalized = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", query)
        entities.extend(capitalized)

        # Remove duplicates while preserving order
        seen = set()
        unique_entities = []
        for e in entities:
            if e.lower() not in seen:
                seen.add(e.lower())
                unique_entities.append(e)

        return unique_entities[:5]  # Limit to top 5 entities

    async def _get_entity_context(self, entities: list[str]) -> str:
        """Get context from Neo4j for entities.

        Args:
            entities: List of entity names.

        Returns:
            Formatted graph context string.
        """
        context_parts: list[str] = []

        for entity in entities:
            try:
                # Query Neo4j for entity relationships
                result = await self._query_entity_relationships(entity)
                if result:
                    context_parts.append(f"Entity: {entity}")
                    context_parts.extend(result)
                    context_parts.append("")

            except Exception as e:
                logger.warning(f"Failed to query entity {entity}: {e}")
                continue

        return "\n".join(context_parts)

    async def _query_entity_relationships(self, entity: str) -> list[str]:
        """Query Neo4j for entity relationships.

        Args:
            entity: Entity name to query.

        Returns:
            List of relationship descriptions.
        """
        try:
            # Use Neo4jQueryService to find related entities
            # This assumes the Neo4j service has a method for this
            # Adjust based on actual Neo4j service API

            # Query pattern: Find entity and its relationships
            query = """
                MATCH (e:Entity {name: $entity_name})
                OPTIONAL MATCH (e)-[r]->(related)
                RETURN e.name as entity,
                       type(r) as relationship,
                       related.name as related_entity,
                       labels(related) as related_labels
                LIMIT 10
            """

            results = self.neo4j_service.execute_query(
                query,
                {"entity_name": entity},
            )

            relationships: list[str] = []
            for record in results:
                rel_type = record.get("relationship", "")
                related = record.get("related_entity", "")
                if rel_type and related:
                    relationships.append(f"  - {rel_type} -> {related}")

            return relationships

        except Exception as e:
            logger.warning(f"Neo4j query failed for {entity}: {e}")
            return []

    async def run_with_streaming(
        self,
        conversation_id: str,
        query: str,
        user_id: str,
    ):
        """Run with real-time streaming of response chunks.

        This method yields response chunks as they are generated,
        suitable for WebSocket streaming.

        Args:
            conversation_id: Conversation ID.
            query: User query.
            user_id: User ID.

        Yields:
            Tuple of (event_type, data) for streaming.
        """
        # Build initial state
        state: AgentState = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "query": query,
            "context": "",
            "sources": [],
            "history": [],
            "response": "",
            "response_chunks": [],
            "retrieval_scores": {},
            "token_count": 0,
            "error": None,
            "message_id": None,
        }

        try:
            # Step 1: Retrieve
            yield ("status", "retrieving")
            retrieve_result = await self._retrieve_node(state)
            state.update(retrieve_result)

            if state.get("error"):
                yield ("error", state["error"])
                return

            # Step 2: Entity context enrichment
            yield ("status", "analyzing_entities")
            entity_result = await self._entity_context_node(state)
            state.update(entity_result)

            # Step 3: Generate with streaming
            yield ("status", "generating")

            messages = self.llm_service.build_rag_prompt(
                query=state["query"],
                context=state["context"],
                history=state["history"] if state["history"] else None,
            )

            response_chunks: list[str] = []
            full_response = ""

            async for chunk in self.llm_service.stream_generate(messages):
                response_chunks.append(chunk)
                full_response += chunk
                yield ("chunk", chunk)

            state["response"] = full_response
            state["response_chunks"] = response_chunks
            state["token_count"] = self.llm_service.estimate_tokens(full_response)

            # Step 4: Save
            yield ("status", "saving")
            save_result = await self._save_node(state)
            state.update(save_result)

            if state.get("error"):
                yield ("error", state["error"])
                return

            # Final result
            yield ("complete", {
                "message_id": state["message_id"],
                "sources": state["sources"],
                "token_count": state["token_count"],
            })

        except Exception as e:
            logger.exception(f"Agent execution failed: {e}")
            yield ("error", str(e))
