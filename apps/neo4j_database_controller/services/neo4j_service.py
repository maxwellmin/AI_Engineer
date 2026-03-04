"""
Neo4j service layer for knowledge graph operations.

This module provides a high-level facade service that coordinates
all Neo4j operations through a unified interface, making it easy
for other modules to interact with the knowledge graph.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

from apps.neo4j_database_controller.client import Neo4jClient
from apps.neo4j_database_controller.constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_DEPTH,
    Direction,
    NodeLabel,
    PropName,
    RelType,
)
from apps.neo4j_database_controller.dto import (
    BatchNodeCreationResult,
    BatchRelationshipCreationResult,
    CreateRelationshipRequest,
    DeleteResult,
    DocumentGraph,
    EntityContext,
    NodeCreationResult,
    NodeInfo,
    PathInfo,
    RelationshipCreationResult,
    RelationshipInfo,
)
from apps.neo4j_database_controller.managers import (
    NodeManager,
    QueryManager,
    RelationshipManager,
)
from apps.neo4j_database_controller.schemas.graph_schema import (
    GraphSchemaManager,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# Entity Extraction Interface (Reserved for LLM Integration)
# =============================================================================


class EntityExtractorInterface(ABC):
    """Abstract interface for entity extraction.

    This interface is reserved for future LLM integration.
    Implementations should extract entities and relationships from text.
    """

    @abstractmethod
    def extract_entities(self, text: str) -> list[dict[str, Any]]:
        """Extract entities from text.

        Args:
            text: Input text to extract entities from.

        Returns:
            List of entity dictionaries with:
            - name: Entity name
            - entity_type: Entity type (person, org, location, etc.)
            - confidence: Extraction confidence (0.0-1.0)
            - description: Optional entity description
        """
        pass

    @abstractmethod
    def extract_relationships(
        self, text: str, entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Extract relationships between entities.

        Args:
            text: Input text.
            entities: List of extracted entities.

        Returns:
            List of relationship dictionaries with:
            - from_entity: Source entity name
            - to_entity: Target entity name
            - relation_type: Relationship type
            - confidence: Extraction confidence (0.0-1.0)
        """
        pass


class MockEntityExtractor(EntityExtractorInterface):
    """Mock entity extractor for testing.

    Returns empty lists, used as placeholder until LLM integration.
    """

    def extract_entities(self, text: str) -> list[dict[str, Any]]:
        """Return empty list (no entities extracted)."""
        return []

    def extract_relationships(
        self, text: str, entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Return empty list (no relationships extracted)."""
        return []


# =============================================================================
# Neo4j Service
# =============================================================================


class Neo4jService:
    """High-level facade service for Neo4j operations.

    This service provides a unified interface for all Neo4j operations,
    coordinating NodeManager, RelationshipManager, and QueryManager.
    It offers high-level methods optimized for common use cases in the
    RAG pipeline.

    Example:
        >>> service = Neo4jService()
        >>> # Create a document with chunks
        >>> doc = service.create_document("doc-1", "My Document", "source.pdf")
        >>> service.add_chunk_to_document("doc-1", "chunk-1", "Some text...")
        >>>
        >>> # Get context for RAG
        >>> context = service.get_entity_context("entity-1")
        >>> doc_graph = service.get_document_graph("doc-1")
    """

    def __init__(
        self,
        client: Neo4jClient | None = None,
        entity_extractor: EntityExtractorInterface | None = None,
    ) -> None:
        """Initialize the Neo4j service.

        Args:
            client: Optional Neo4jClient instance. If None, gets singleton.
            entity_extractor: Optional entity extractor for LLM integration.
        """
        self._client = client or Neo4jClient.get_instance()
        self._node_manager = NodeManager(self._client)
        self._relationship_manager = RelationshipManager(self._client)
        self._query_manager = QueryManager(self._client)
        self._entity_extractor = entity_extractor or MockEntityExtractor()

    # =========================================================================
    # Node Management (Low-level)
    # =========================================================================

    def create_node(
        self,
        label: str,
        properties: dict[str, Any],
        merge: bool = False,
    ) -> NodeCreationResult:
        """Create a node with the given label and properties.

        Args:
            label: Node label (Document, Chunk, Entity, Concept, User).
            properties: Node properties.
            merge: If True, use MERGE for upsert behavior.

        Returns:
            NodeCreationResult with created node info.
        """
        return self._node_manager.create_node(label, properties, merge)

    def create_nodes_batch(
        self,
        label: str,
        nodes: list[dict[str, Any]],
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> BatchNodeCreationResult:
        """Create multiple nodes in batches.

        Args:
            label: Node label.
            nodes: List of node property dictionaries.
            batch_size: Batch size for operations.

        Returns:
            BatchNodeCreationResult with created nodes.
        """
        return self._node_manager.create_nodes_batch(label, nodes, batch_size)

    def get_node_by_id(
        self,
        node_id: str,
        label: str | None = None,
    ) -> NodeInfo | None:
        """Get a node by ID.

        Args:
            node_id: Node ID.
            label: Optional node label for better performance.

        Returns:
            NodeInfo or None if not found.
        """
        if label:
            return self._node_manager.get_node_by_id(node_id, label)
        # Try all labels
        for node_label in NodeLabel:
            result = self._node_manager.get_node_by_id(
                node_id, node_label.value
            )
            if result:
                return result
        return None

    def get_node_by_id_or_raise(
        self,
        node_id: str,
        label: str,
    ) -> NodeInfo:
        """Get a node by ID, raising error if not found.

        Args:
            node_id: Node ID.
            label: Node label.

        Returns:
            NodeInfo.

        Raises:
            NodeNotFoundError: If node doesn't exist.
        """
        return self._node_manager.get_node_by_id_or_raise(node_id, label)

    def update_node(
        self,
        node_id: str,
        label: str,
        properties: dict[str, Any],
        merge: bool = True,
    ) -> NodeInfo:
        """Update a node's properties.

        Args:
            node_id: Node ID.
            label: Node label.
            properties: Properties to update.
            merge: If True, merge with existing. If False, replace all.

        Returns:
            Updated NodeInfo.
        """
        return self._node_manager.update_node(node_id, label, properties, merge)

    def delete_node(
        self,
        node_id: str,
        label: str,
        force: bool = False,
    ) -> DeleteResult:
        """Delete a node.

        Args:
            node_id: Node ID.
            label: Node label.
            force: If True, delete connected relationships first.

        Returns:
            DeleteResult.
        """
        return self._node_manager.delete_node(node_id, label, force)

    # =========================================================================
    # Document Operations (High-level)
    # =========================================================================

    def create_document(
        self,
        document_id: str,
        title: str,
        source: str,
        doc_type: str = "unknown",
        status: str = "active",
        extra_properties: dict[str, Any] | None = None,
    ) -> NodeCreationResult:
        """Create a document node with standard properties.

        Args:
            document_id: Unique document ID.
            title: Document title.
            source: Document source (file path, URL, etc.).
            doc_type: Document type (pdf, txt, html, etc.).
            status: Document status (active, archived, etc.).
            extra_properties: Additional properties.

        Returns:
            NodeCreationResult with created document info.
        """
        properties = {
            PropName.ID: document_id,
            PropName.TITLE: title,
            PropName.SOURCE: source,
            PropName.DOC_TYPE: doc_type,
            PropName.STATUS: status,
        }
        if extra_properties:
            properties.update(extra_properties)

        return self._node_manager.create_document_node(**properties)

    def get_document(self, document_id: str) -> NodeInfo | None:
        """Get a document by ID.

        Args:
            document_id: Document ID.

        Returns:
            NodeInfo or None.
        """
        return self._node_manager.get_node_by_id(
            document_id, NodeLabel.DOCUMENT.value
        )

    def delete_document(
        self,
        document_id: str,
        delete_chunks: bool = True,
    ) -> DeleteResult:
        """Delete a document and optionally its chunks.

        Args:
            document_id: Document ID.
            delete_chunks: If True, delete all chunks belonging to document.

        Returns:
            DeleteResult.
        """
        if delete_chunks:
            # Delete all chunks first
            self._node_manager.delete_nodes_by_filter(
                NodeLabel.CHUNK.value,
                filters={PropName.DOCUMENT_ID: document_id},
            )

        return self._node_manager.delete_node(
            document_id, NodeLabel.DOCUMENT.value, force=True
        )

    def add_chunk_to_document(
        self,
        document_id: str,
        chunk_id: str,
        text: str,
        chunk_index: int = 0,
        page_number: int | None = None,
        start_char: int | None = None,
        end_char: int | None = None,
        extra_properties: dict[str, Any] | None = None,
    ) -> tuple[NodeCreationResult, RelationshipCreationResult]:
        """Add a chunk to a document with CONTAINS relationship.

        Args:
            document_id: Parent document ID.
            chunk_id: Unique chunk ID.
            text: Chunk text content.
            chunk_index: Index of chunk in document.
            page_number: Optional page number.
            start_char: Optional start character position.
            end_char: Optional end character position.
            extra_properties: Additional properties.

        Returns:
            Tuple of (NodeCreationResult, RelationshipCreationResult).

        Raises:
            NodeNotFoundError: If document doesn't exist.
        """
        # Create chunk node
        properties = {
            PropName.ID: chunk_id,
            PropName.TEXT: text,
            PropName.CHUNK_INDEX: chunk_index,
            PropName.DOCUMENT_ID: document_id,
        }
        if page_number is not None:
            properties[PropName.PAGE_NUMBER] = page_number
        if start_char is not None:
            properties[PropName.START_CHAR] = start_char
        if end_char is not None:
            properties[PropName.END_CHAR] = end_char
        if extra_properties:
            properties.update(extra_properties)

        chunk_result = self._node_manager.create_chunk_node(**properties)

        # Create CONTAINS relationship
        rel_result = self._relationship_manager.create_contains_relationship(
            document_id=document_id,
            chunk_id=chunk_id,
            order=chunk_index,
        )

        return (chunk_result, rel_result)

    def get_document_chunks(
        self,
        document_id: str,
        limit: int = 100,
    ) -> list[NodeInfo]:
        """Get all chunks of a document.

        Args:
            document_id: Document ID.
            limit: Maximum chunks to return.

        Returns:
            List of chunk NodeInfo objects.
        """
        return self._node_manager.get_nodes_by_label(
            NodeLabel.CHUNK.value,
            filters={PropName.DOCUMENT_ID: document_id},
            order_by=PropName.CHUNK_INDEX,
            limit=limit,
        )

    # =========================================================================
    # Entity Operations (High-level)
    # =========================================================================

    def create_entity(
        self,
        entity_id: str,
        name: str,
        entity_type: str,
        description: str = "",
        confidence: float = 1.0,
        extra_properties: dict[str, Any] | None = None,
    ) -> NodeCreationResult:
        """Create an entity node.

        Args:
            entity_id: Unique entity ID.
            name: Entity name.
            entity_type: Entity type (person, organization, location, etc.).
            description: Entity description.
            confidence: Extraction confidence (0.0-1.0).
            extra_properties: Additional properties.

        Returns:
            NodeCreationResult.
        """
        properties = {
            PropName.ID: entity_id,
            PropName.NAME: name,
            PropName.ENTITY_TYPE: entity_type,
            PropName.DESCRIPTION: description,
            PropName.CONFIDENCE: confidence,
        }
        if extra_properties:
            properties.update(extra_properties)

        return self._node_manager.create_entity_node(**properties)

    def get_entity(self, entity_id: str) -> NodeInfo | None:
        """Get an entity by ID.

        Args:
            entity_id: Entity ID.

        Returns:
            NodeInfo or None.
        """
        return self._node_manager.get_node_by_id(
            entity_id, NodeLabel.ENTITY.value
        )

    def find_entity_by_name(
        self,
        name: str,
        entity_type: str | None = None,
    ) -> NodeInfo | None:
        """Find an entity by name.

        Args:
            name: Entity name.
            entity_type: Optional entity type filter.

        Returns:
            NodeInfo or None.
        """
        entities = self._query_manager.find_entities_by_name(
            name=name,
            entity_type=entity_type,
            limit=1,
        )
        return entities[0] if entities else None

    def link_chunk_to_entity(
        self,
        chunk_id: str,
        entity_id: str,
        confidence: float = 1.0,
        count: int = 1,
    ) -> RelationshipCreationResult:
        """Create a MENTIONS relationship from chunk to entity.

        Args:
            chunk_id: Chunk ID.
            entity_id: Entity ID.
            confidence: Mention confidence.
            count: Number of times entity is mentioned.

        Returns:
            RelationshipCreationResult.
        """
        return self._relationship_manager.create_mentions_relationship(
            chunk_id=chunk_id,
            entity_id=entity_id,
            confidence=confidence,
            count=count,
        )

    def get_entities_in_chunk(
        self,
        chunk_id: str,
    ) -> list[NodeInfo]:
        """Get all entities mentioned in a chunk.

        Args:
            chunk_id: Chunk ID.

        Returns:
            List of entity NodeInfo objects.
        """
        rels = self._relationship_manager.get_outgoing_relationships(
            node_id=chunk_id,
            node_label=NodeLabel.CHUNK.value,
            rel_type=RelType.MENTIONS.value,
        )

        entities = []
        for rel in rels:
            entity = self._node_manager.get_node_by_id(
                rel.to_node_id, NodeLabel.ENTITY.value
            )
            if entity:
                entities.append(entity)

        return entities

    # =========================================================================
    # Concept Operations (High-level)
    # =========================================================================

    def create_concept(
        self,
        concept_id: str,
        name: str,
        description: str = "",
        category: str = "",
        extra_properties: dict[str, Any] | None = None,
    ) -> NodeCreationResult:
        """Create a concept node.

        Args:
            concept_id: Unique concept ID.
            name: Concept name.
            description: Concept description.
            category: Concept category.
            extra_properties: Additional properties.

        Returns:
            NodeCreationResult.
        """
        properties = {
            PropName.ID: concept_id,
            PropName.NAME: name,
            PropName.DESCRIPTION: description,
            PropName.CATEGORY: category,
        }
        if extra_properties:
            properties.update(extra_properties)

        return self._node_manager.create_concept_node(**properties)

    def get_concept(self, concept_id: str) -> NodeInfo | None:
        """Get a concept by ID.

        Args:
            concept_id: Concept ID.

        Returns:
            NodeInfo or None.
        """
        return self._node_manager.get_node_by_id(
            concept_id, NodeLabel.CONCEPT.value
        )

    def link_document_to_concept(
        self,
        document_id: str,
        concept_id: str,
        confidence: float = 1.0,
    ) -> RelationshipCreationResult:
        """Create an ABOUT relationship from document to concept.

        Args:
            document_id: Document ID.
            concept_id: Concept ID.
            confidence: Relevance confidence.

        Returns:
            RelationshipCreationResult.
        """
        return self._relationship_manager.create_about_relationship(
            document_id=document_id,
            concept_id=concept_id,
            confidence=confidence,
        )

    # =========================================================================
    # Entity-to-Entity Relationships
    # =========================================================================

    def link_entities(
        self,
        from_entity_id: str,
        to_entity_id: str,
        relation_type: str = "",
        confidence: float = 1.0,
    ) -> RelationshipCreationResult:
        """Create a RELATED_TO relationship between two entities.

        Args:
            from_entity_id: Source entity ID.
            to_entity_id: Target entity ID.
            relation_type: Semantic relationship type.
            confidence: Relationship confidence.

        Returns:
            RelationshipCreationResult.
        """
        return self._relationship_manager.create_related_to_relationship(
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            relation_type=relation_type,
            confidence=confidence,
        )

    # =========================================================================
    # Knowledge Graph Retrieval for RAG
    # =========================================================================

    def get_entity_context(
        self,
        entity_id: str,
        include_chunks: bool = True,
        include_related_entities: bool = True,
        include_concepts: bool = True,
        max_depth: int = 2,
    ) -> EntityContext | None:
        """Get comprehensive context for an entity for RAG queries.

        This retrieves:
        - The entity itself
        - Chunks that mention this entity
        - Related entities
        - Related concepts

        Args:
            entity_id: Entity ID.
            include_chunks: Include mentioning chunks.
            include_related_entities: Include related entities.
            include_concepts: Include related concepts.
            max_depth: Max depth for entity traversal.

        Returns:
            EntityContext or None if entity not found.
        """
        return self._query_manager.get_entity_context(
            entity_id=entity_id,
            include_chunks=include_chunks,
            include_related_entities=include_related_entities,
            include_concepts=include_concepts,
            max_depth=max_depth,
        )

    def get_document_graph(
        self,
        document_id: str,
        include_chunks: bool = True,
        include_entities: bool = True,
        include_concepts: bool = True,
    ) -> DocumentGraph | None:
        """Get a document's subgraph for RAG context.

        Retrieves:
        - Document node
        - Chunk nodes
        - Entity nodes mentioned in chunks
        - Concept nodes (document is about)

        Args:
            document_id: Document ID.
            include_chunks: Include chunks.
            include_entities: Include entities.
            include_concepts: Include concepts.

        Returns:
            DocumentGraph or None if document not found.
        """
        return self._query_manager.get_document_graph(
            document_id=document_id,
            include_chunks=include_chunks,
            include_entities=include_entities,
            include_concepts=include_concepts,
        )

    def find_related_entities(
        self,
        entity_id: str,
        max_depth: int = 2,
        limit: int = 20,
    ) -> list[NodeInfo]:
        """Find entities related to a given entity.

        Args:
            entity_id: Source entity ID.
            max_depth: Max traversal depth.
            limit: Max results.

        Returns:
            List of related entity NodeInfo objects.
        """
        return self._query_manager.find_related_entities(
            entity_id=entity_id,
            max_depth=max_depth,
            limit=limit,
        )

    def search_entities(
        self,
        name: str,
        entity_type: str | None = None,
        limit: int = 10,
    ) -> list[NodeInfo]:
        """Search entities by name.

        Args:
            name: Entity name or partial name.
            entity_type: Optional type filter.
            limit: Max results.

        Returns:
            List of matching entity NodeInfo objects.
        """
        return self._query_manager.find_entities_by_name(
            name=name,
            entity_type=entity_type,
            limit=limit,
        )

    def get_chunks_by_entities(
        self,
        entity_names: list[str],
        limit: int = 20,
    ) -> list[NodeInfo]:
        """Get chunks that mention any of the given entities.

        Args:
            entity_names: List of entity names to search for.
            limit: Max chunks to return.

        Returns:
            List of chunk NodeInfo objects.
        """
        if not entity_names:
            return []

        # Find entities by names
        all_entities = []
        for name in entity_names:
            entities = self._query_manager.find_entities_by_name(name=name, limit=5)
            all_entities.extend(entities)

        if not all_entities:
            return []

        # Get chunks that mention these entities
        chunk_ids = set()
        for entity in all_entities:
            rels = self._relationship_manager.get_incoming_relationships(
                node_id=entity.id,
                node_label=NodeLabel.ENTITY.value,
                rel_type=RelType.MENTIONS.value,
            )
            for rel in rels:
                chunk_ids.add(rel.from_node_id)

        # Fetch chunk nodes
        chunks = []
        for chunk_id in list(chunk_ids)[:limit]:
            chunk = self._node_manager.get_node_by_id(
                chunk_id, NodeLabel.CHUNK.value
            )
            if chunk:
                chunks.append(chunk)

        return chunks

    # =========================================================================
    # Graph Queries
    # =========================================================================

    def find_shortest_path(
        self,
        from_node_id: str,
        from_node_label: str,
        to_node_id: str,
        to_node_label: str,
        max_depth: int = DEFAULT_MAX_DEPTH,
        relationship_types: list[str] | None = None,
    ) -> PathInfo | None:
        """Find shortest path between two nodes.

        Args:
            from_node_id: Source node ID.
            from_node_label: Source node label.
            to_node_id: Target node ID.
            to_node_label: Target node label.
            max_depth: Max search depth.
            relationship_types: Optional relationship type filter.

        Returns:
            PathInfo or None if no path found.
        """
        return self._query_manager.find_shortest_path(
            from_node_id=from_node_id,
            from_node_label=from_node_label,
            to_node_id=to_node_id,
            to_node_label=to_node_label,
            max_depth=max_depth,
            relationship_types=relationship_types,
        )

    def get_node_neighbors(
        self,
        node_id: str,
        node_label: str | None = None,
        direction: str = Direction.BOTH.value,
        relationship_types: list[str] | None = None,
        limit: int = 100,
    ) -> list[NodeInfo]:
        """Get neighboring nodes.

        Args:
            node_id: Node ID.
            node_label: Optional node label.
            direction: Relationship direction.
            relationship_types: Optional relationship type filter.
            limit: Max results.

        Returns:
            List of neighbor NodeInfo objects.
        """
        return self._query_manager.get_node_neighbors(
            node_id=node_id,
            node_label=node_label,
            direction=direction,
            relationship_types=relationship_types,
            limit=limit,
        )

    # =========================================================================
    # Health Check & Statistics
    # =========================================================================

    def health_check(self) -> dict[str, Any]:
        """Check Neo4j connection health.

        Returns:
            Dictionary with health status and server info.
        """
        try:
            # Use Neo4jClient's health_check method
            client_health = self._client.health_check()
            is_connected = client_health.get("connected", False)

            result = {
                "status": "healthy" if is_connected else "unhealthy",
                "connected": is_connected,
            }

            if is_connected:
                # Include server info from client health check
                server_info = client_health.get("server_info", {})
                if server_info:
                    result["server_info"] = server_info

                # Get graph stats
                try:
                    stats = self._query_manager.get_graph_stats()
                    result["graph_stats"] = stats
                except Exception as e:
                    result["graph_stats"] = {"error": str(e)}

            return result

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
            }

    def get_graph_stats(self) -> dict[str, Any]:
        """Get graph statistics.

        Returns:
            Dictionary with node counts, relationship counts, etc.
        """
        return self._query_manager.get_graph_stats()

    # =========================================================================
    # Schema Management
    # =========================================================================

    def initialize_schema(self) -> dict[str, Any]:
        """Initialize Neo4j schema (indexes and constraints).

        Returns:
            Dictionary with creation results.
        """
        schema_manager = GraphSchemaManager(self._client)
        return schema_manager.initialize_schema()

    # =========================================================================
    # Relationship Management
    # =========================================================================

    def create_relationship(
        self,
        rel_type: str,
        from_node_id: str,
        from_node_label: str,
        to_node_id: str,
        to_node_label: str,
        properties: dict[str, Any] | None = None,
        merge: bool = False,
    ) -> RelationshipCreationResult:
        """Create a relationship between two nodes.

        Args:
            rel_type: Relationship type.
            from_node_id: Source node ID.
            from_node_label: Source node label.
            to_node_id: Target node ID.
            to_node_label: Target node label.
            properties: Optional relationship properties.
            merge: Use MERGE for upsert.

        Returns:
            RelationshipCreationResult.
        """
        return self._relationship_manager.create_relationship(
            rel_type=rel_type,
            from_node_id=from_node_id,
            from_node_label=from_node_label,
            to_node_id=to_node_id,
            to_node_label=to_node_label,
            properties=properties,
            merge=merge,
        )

    def delete_relationship(self, rel_id: int) -> DeleteResult:
        """Delete a relationship by ID.

        Args:
            rel_id: Neo4j internal relationship ID.

        Returns:
            DeleteResult.
        """
        return self._relationship_manager.delete_relationship(rel_id)

    # =========================================================================
    # Entity Extraction (Reserved for LLM Integration)
    # =========================================================================

    def set_entity_extractor(self, extractor: EntityExtractorInterface) -> None:
        """Set the entity extractor implementation.

        This allows for LLM-based entity extraction integration.

        Args:
            extractor: EntityExtractorInterface implementation.
        """
        self._entity_extractor = extractor

    def extract_and_store_entities(
        self,
        text: str,
        chunk_id: str,
        confidence_threshold: float = 0.7,
    ) -> list[NodeInfo]:
        """Extract entities from text and store in Neo4j.

        Uses the configured entity extractor (default: MockEntityExtractor).
        This method is reserved for LLM integration.

        Args:
            text: Text to extract entities from.
            chunk_id: Chunk ID to link entities to.
            confidence_threshold: Minimum confidence to store entity.

        Returns:
            List of created entity NodeInfo objects.
        """
        # Extract entities
        extracted = self._entity_extractor.extract_entities(text)

        created_entities = []
        for entity_data in extracted:
            confidence = entity_data.get("confidence", 1.0)
            if confidence < confidence_threshold:
                continue

            # Generate entity ID (in production, use proper UUID)
            import uuid
            entity_id = str(uuid.uuid4())

            # Create entity node
            result = self.create_entity(
                entity_id=entity_id,
                name=entity_data.get("name", ""),
                entity_type=entity_data.get("entity_type", "unknown"),
                description=entity_data.get("description", ""),
                confidence=confidence,
            )

            if result.created:
                # Create MENTIONS relationship
                self.link_chunk_to_entity(
                    chunk_id=chunk_id,
                    entity_id=entity_id,
                    confidence=confidence,
                )
                created_entities.append(result.node)

        return created_entities


# =============================================================================
# Service Singleton (Optional)
# =============================================================================

_service_instance: Neo4jService | None = None


def get_neo4j_service() -> Neo4jService:
    """Get the Neo4jService singleton instance.

    Returns:
        Neo4jService instance.
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = Neo4jService()
    return _service_instance
