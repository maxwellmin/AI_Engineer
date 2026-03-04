"""
Query manager for Neo4j database controller.

This module provides specialized graph query operations for knowledge graph
retrieval, including path finding, entity context retrieval, and document
subgraph extraction.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from apps.neo4j_database_controller.client import Neo4jClient
from apps.neo4j_database_controller.constants import (
    DEFAULT_MAX_DEPTH,
    Direction,
    NodeLabel,
    PropName,
    RelType,
)
from apps.neo4j_database_controller.dto import (
    DocumentGraph,
    EntityContext,
    FindPathRequest,
    GetDocumentGraphRequest,
    GetEntityContextRequest,
    GetNodeNeighborsRequest,
    NodeInfo,
    PathInfo,
    RelationshipInfo,
    SearchEntitiesRequest,
)
from apps.neo4j_database_controller.exceptions import (
    NodeNotFoundError,
    PathNotFoundError,
    QueryError,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class QueryManager:
    """Manager for Neo4j graph query operations.

    This class handles specialized graph queries for knowledge graph:
    - Path finding (shortest, all paths)
    - Node neighbor retrieval
    - Entity context retrieval for RAG
    - Document subgraph extraction
    - Entity search

    Example:
        >>> manager = QueryManager()
        >>> path = manager.find_shortest_path("entity-1", "Entity", "entity-2", "Entity")
        >>> context = manager.get_entity_context("entity-1", include_chunks=True)
        >>> doc_graph = manager.get_document_graph("doc-1")
    """

    def __init__(self, client: Neo4jClient | None = None) -> None:
        """Initialize the query manager.

        Args:
            client: Optional Neo4jClient instance. If None, gets singleton.
        """
        self._client = client or Neo4jClient.get_instance()

    # =========================================================================
    # Path Finding Operations
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
        """Find the shortest path between two nodes.

        Args:
            from_node_id: Source node ID.
            from_node_label: Source node label.
            to_node_id: Target node ID.
            to_node_label: Target node label.
            max_depth: Maximum path length to search.
            relationship_types: Optional list of relationship types to follow.

        Returns:
            PathInfo if path found, None otherwise.
        """
        # Build relationship pattern
        if relationship_types:
            rel_pattern = "|".join(relationship_types)
            rel_pattern = f"[r:{rel_pattern}*]"
        else:
            rel_pattern = "[r*]"  # Match any relationship type

        query = f"""
        MATCH (from:{from_node_label} {{id: $from_id}}),
              (to:{to_node_label} {{id: $to_id}})
        MATCH path = shortestPath((from)-{rel_pattern}->(to))
        WHERE length(path) <= $max_depth
        RETURN path
        """

        try:
            results = self._client.execute_read(
                query,
                parameters={
                    "from_id": from_node_id,
                    "to_id": to_node_id,
                    "max_depth": max_depth,
                },
            )

            if not results:
                return None

            return self._parse_path_result(results[0].get("path", {}))

        except Exception as e:
            logger.error(f"Failed to find shortest path: {e}")
            raise

    def find_all_paths(
        self,
        from_node_id: str,
        from_node_label: str,
        to_node_id: str,
        to_node_label: str,
        max_depth: int = DEFAULT_MAX_DEPTH,
        relationship_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[PathInfo]:
        """Find all paths between two nodes up to a maximum depth.

        Args:
            from_node_id: Source node ID.
            from_node_label: Source node label.
            to_node_id: Target node ID.
            to_node_label: Target node label.
            max_depth: Maximum path length to search.
            relationship_types: Optional list of relationship types to follow.
            limit: Maximum number of paths to return.

        Returns:
            List of PathInfo objects.
        """
        # Build relationship pattern
        if relationship_types:
            rel_pattern = "|".join(relationship_types)
            rel_pattern = f"[r:{rel_pattern}*..{max_depth}]"
        else:
            rel_pattern = f"[r*..{max_depth}]"  # Match any relationship type

        query = f"""
        MATCH (from:{from_node_label} {{id: $from_id}}),
              (to:{to_node_label} {{id: $to_id}})
        MATCH path = (from)-{rel_pattern}->(to)
        RETURN path
        ORDER BY length(path)
        LIMIT $limit
        """

        try:
            results = self._client.execute_read(
                query,
                parameters={
                    "from_id": from_node_id,
                    "to_id": to_node_id,
                    "limit": limit,
                },
            )

            paths = []
            for record in results:
                path_info = self._parse_path_result(record.get("path", {}))
                if path_info:
                    paths.append(path_info)

            return paths

        except Exception as e:
            logger.error(f"Failed to find all paths: {e}")
            raise

    def _parse_path_result(self, path_data: Any) -> PathInfo | None:
        """Parse a Neo4j path result into PathInfo.

        Args:
            path_data: Path data from Neo4j result.
                Can be:
                1. neo4j.graph.Path object (with .nodes and .relationships)
                2. List representation from .data() serialization:
                   [node_dict, rel_type_str, node_dict, rel_type_str, ...]

        Returns:
            PathInfo or None if parsing fails.
        """
        if not path_data:
            return None

        try:
            # Case 1: Neo4j driver 5.x returns Path objects directly
            # The path object has .nodes and .relationships attributes
            if hasattr(path_data, "nodes") and hasattr(path_data, "relationships"):
                nodes: list[NodeInfo] = []
                relationships: list[RelationshipInfo] = []

                # Extract nodes from the path
                for node in path_data.nodes:
                    node_id = node.get("id", "")
                    node_labels = list(node.labels) if hasattr(node, "labels") else []
                    node_label = node_labels[0] if node_labels else ""

                    nodes.append(
                        NodeInfo(
                            id=str(node_id),
                            label=node_label,
                            properties=dict(node),
                        )
                    )

                # Extract relationships from the path
                for rel in path_data.relationships:
                    relationships.append(
                        RelationshipInfo(
                            id=rel.id,
                            rel_type=rel.type,
                            from_node_id=str(rel.start_node.get("id", "")) if rel.start_node else "",
                            from_node_label=list(rel.start_node.labels)[0] if rel.start_node and hasattr(rel.start_node, "labels") else "",
                            to_node_id=str(rel.end_node.get("id", "")) if rel.end_node else "",
                            to_node_label=list(rel.end_node.labels)[0] if rel.end_node and hasattr(rel.end_node, "labels") else "",
                            properties=dict(rel),
                        )
                    )

                return PathInfo(
                    nodes=nodes,
                    relationships=relationships,
                    length=len(relationships),
                )

            # Case 2: List representation from .data() serialization
            # Format: [node_dict, rel_type_str, node_dict, rel_type_str, ...]
            # - Odd indices (0, 2, 4, ...): node dictionaries
            # - Even indices (1, 3, 5, ...): relationship type strings
            if isinstance(path_data, list) and len(path_data) >= 1:
                nodes: list[NodeInfo] = []
                relationships: list[RelationshipInfo] = []

                # Extract nodes (odd indices: 0, 2, 4, ...)
                for i in range(0, len(path_data), 2):
                    node_dict = path_data[i]
                    if isinstance(node_dict, dict):
                        node_id = node_dict.get("id", "")
                        # Determine label from properties or default
                        node_label = node_dict.get("label", "")
                        if not node_label:
                            # Try to infer from common properties
                            if "entity_type" in node_dict:
                                node_label = "Entity"
                            elif "doc_type" in node_dict:
                                node_label = "Document"
                            elif "chunk_index" in node_dict:
                                node_label = "Chunk"
                            elif "category" in node_dict:
                                node_label = "Concept"

                        nodes.append(
                            NodeInfo(
                                id=str(node_id),
                                label=node_label,
                                properties=node_dict,
                            )
                        )

                # Extract relationships (even indices: 1, 3, 5, ...)
                for i in range(1, len(path_data), 2):
                    rel_type = path_data[i]
                    if isinstance(rel_type, str):
                        # Get the from and to nodes for this relationship
                        from_node_idx = (i - 1) // 2
                        to_node_idx = (i + 1) // 2

                        from_node_id = ""
                        from_node_label = ""
                        to_node_id = ""
                        to_node_label = ""

                        if from_node_idx < len(nodes):
                            from_node_id = nodes[from_node_idx].id
                            from_node_label = nodes[from_node_idx].label
                        if to_node_idx < len(nodes):
                            to_node_id = nodes[to_node_idx].id
                            to_node_label = nodes[to_node_idx].label

                        relationships.append(
                            RelationshipInfo(
                                id=0,  # No ID available in serialized format
                                rel_type=rel_type,
                                from_node_id=from_node_id,
                                from_node_label=from_node_label,
                                to_node_id=to_node_id,
                                to_node_label=to_node_label,
                                properties={},
                            )
                        )

                return PathInfo(
                    nodes=nodes,
                    relationships=relationships,
                    length=len(relationships),
                )

            # Case 3: Dict representation (older drivers or test mocks)
            if isinstance(path_data, dict):
                length = path_data.get("length", 0)
                return PathInfo(
                    nodes=[],
                    relationships=[],
                    length=length,
                )

            return None

        except Exception as e:
            logger.warning(f"Failed to parse path result: {e}")
            return None

    # =========================================================================
    # Node Neighbor Operations
    # =========================================================================

    def get_node_neighbors(
        self,
        node_id: str,
        node_label: str | None = None,
        direction: str = Direction.BOTH.value,
        relationship_types: list[str] | None = None,
        limit: int = 100,
    ) -> list[NodeInfo]:
        """Get neighboring nodes connected by relationships.

        Args:
            node_id: Node ID to get neighbors for.
            node_label: Optional node label for better query performance.
            direction: Relationship direction ("OUTGOING", "INCOMING", "BOTH").
            relationship_types: Optional list of relationship types to follow.
            limit: Maximum number of neighbors to return.

        Returns:
            List of neighboring NodeInfo objects.
        """
        # Build pattern based on direction
        node_pattern = f":{node_label}" if node_label else ""
        rel_type_clause = ""
        if relationship_types:
            rel_type_clause = ":" + "|".join(relationship_types)

        if direction.upper() == Direction.OUTGOING.value:
            pattern = f"(n{node_pattern} {{id: $node_id}})-[r{rel_type_clause}]->(neighbor)"
        elif direction.upper() == Direction.INCOMING.value:
            pattern = f"(neighbor)-[r{rel_type_clause}]->(n{node_pattern} {{id: $node_id}})"
        else:  # BOTH
            pattern = f"(n{node_pattern} {{id: $node_id}})-[r{rel_type_clause}]-(neighbor)"

        query = f"""
        MATCH {pattern}
        RETURN DISTINCT neighbor, labels(neighbor)[0] AS neighbor_label
        LIMIT $limit
        """

        try:
            results = self._client.execute_read(
                query,
                parameters={"node_id": node_id, "limit": limit},
            )

            neighbors = []
            for record in results:
                neighbor_data = record.get("neighbor", {})
                neighbor_label = record.get("neighbor_label", "")
                neighbor_id = neighbor_data.get(PropName.ID, "")

                neighbors.append(
                    NodeInfo(
                        id=str(neighbor_id),
                        label=neighbor_label,
                        properties=neighbor_data,
                    )
                )

            return neighbors

        except Exception as e:
            logger.error(f"Failed to get node neighbors: {e}")
            raise

    def get_node_neighbors_with_relationships(
        self,
        node_id: str,
        node_label: str | None = None,
        direction: str = Direction.BOTH.value,
        relationship_types: list[str] | None = None,
        limit: int = 100,
    ) -> list[tuple[NodeInfo, RelationshipInfo]]:
        """Get neighboring nodes with their connecting relationships.

        Args:
            node_id: Node ID.
            node_label: Optional node label.
            direction: Relationship direction.
            relationship_types: Optional list of relationship types.
            limit: Maximum number of results.

        Returns:
            List of (neighbor, relationship) tuples.
        """
        node_pattern = f":{node_label}" if node_label else ""
        rel_type_clause = ""
        if relationship_types:
            rel_type_clause = ":" + "|".join(relationship_types)

        if direction.upper() == Direction.OUTGOING.value:
            pattern = f"(n{node_pattern} {{id: $node_id}})-[r{rel_type_clause}]->(neighbor)"
        elif direction.upper() == Direction.INCOMING.value:
            pattern = f"(neighbor)-[r{rel_type_clause}]->(n{node_pattern} {{id: $node_id}})"
        else:
            pattern = f"(n{node_pattern} {{id: $node_id}})-[r{rel_type_clause}]-(neighbor)"

        query = f"""
        MATCH {pattern}
        RETURN DISTINCT neighbor, labels(neighbor)[0] AS neighbor_label,
               type(r) AS rel_type, id(r) AS rel_id, properties(r) AS rel_props,
               startNode(r).id AS from_id, endNode(r).id AS to_id,
               labels(startNode(r))[0] AS from_label, labels(endNode(r))[0] AS to_label
        LIMIT $limit
        """

        try:
            results = self._client.execute_read(
                query,
                parameters={"node_id": node_id, "limit": limit},
            )

            neighbors_with_rels = []
            for record in results:
                neighbor_data = record.get("neighbor", {})
                neighbor_label = record.get("neighbor_label", "")
                neighbor_id = neighbor_data.get(PropName.ID, "")

                neighbor_info = NodeInfo(
                    id=str(neighbor_id),
                    label=neighbor_label,
                    properties=neighbor_data,
                )

                rel_info = RelationshipInfo(
                    id=record.get("rel_id", 0),
                    rel_type=record.get("rel_type", ""),
                    from_node_id=record.get("from_id", ""),
                    from_node_label=record.get("from_label", ""),
                    to_node_id=record.get("to_id", ""),
                    to_node_label=record.get("to_label", ""),
                    properties=record.get("rel_props", {}),
                )

                neighbors_with_rels.append((neighbor_info, rel_info))

            return neighbors_with_rels

        except Exception as e:
            logger.error(f"Failed to get node neighbors with relationships: {e}")
            raise

    # =========================================================================
    # Entity Context Operations (RAG-focused)
    # =========================================================================

    def get_entity_context(
        self,
        entity_id: str,
        include_chunks: bool = True,
        include_related_entities: bool = True,
        include_concepts: bool = True,
        max_depth: int = 2,
        chunk_limit: int = 10,
        entity_limit: int = 10,
    ) -> EntityContext | None:
        """Get comprehensive context for an entity for RAG queries.

        This retrieves:
        - The entity itself
        - Chunks that mention this entity (via MENTIONS relationships)
        - Related entities (via RELATED_TO relationships)
        - Related concepts

        Args:
            entity_id: Entity node ID.
            include_chunks: Whether to include mentioning chunks.
            include_related_entities: Whether to include related entities.
            include_concepts: Whether to include related concepts.
            max_depth: Maximum depth for entity relationship traversal.
            chunk_limit: Maximum chunks to return.
            entity_limit: Maximum related entities to return.

        Returns:
            EntityContext or None if entity not found.
        """
        # First, get the entity node
        entity_query = """
        MATCH (e:Entity {id: $entity_id})
        RETURN e
        """

        try:
            entity_results = self._client.execute_read(
                entity_query,
                parameters={"entity_id": entity_id},
            )

            if not entity_results:
                return None

            entity_data = entity_results[0].get("e", {})
            entity_info = NodeInfo(
                id=entity_id,
                label=NodeLabel.ENTITY.value,
                properties=entity_data,
            )

            # Get chunks that mention this entity
            mentioned_in: list[NodeInfo] = []
            if include_chunks:
                chunks_query = """
                MATCH (c:Chunk)-[:MENTIONS]->(e:Entity {id: $entity_id})
                RETURN c
                ORDER BY c.chunk_index
                LIMIT $limit
                """
                chunk_results = self._client.execute_read(
                    chunks_query,
                    parameters={"entity_id": entity_id, "limit": chunk_limit},
                )
                for record in chunk_results:
                    chunk_data = record.get("c", {})
                    chunk_id = chunk_data.get(PropName.ID, "")
                    mentioned_in.append(
                        NodeInfo(
                            id=str(chunk_id),
                            label=NodeLabel.CHUNK.value,
                            properties=chunk_data,
                        )
                    )

            # Get related entities
            related_entities: list[tuple[NodeInfo, str]] = []
            if include_related_entities:
                entities_query = f"""
                MATCH (e:Entity {{id: $entity_id}})-[r:RELATED_TO*1..{max_depth}]-(related:Entity)
                RETURN DISTINCT related, type(last(r)) AS rel_type
                LIMIT $limit
                """
                entity_rel_results = self._client.execute_read(
                    entities_query,
                    parameters={"entity_id": entity_id, "limit": entity_limit},
                )
                for record in entity_rel_results:
                    related_data = record.get("related", {})
                    related_id = related_data.get(PropName.ID, "")
                    rel_type = record.get("rel_type", RelType.RELATED_TO.value)
                    related_entities.append(
                        (
                            NodeInfo(
                                id=str(related_id),
                                label=NodeLabel.ENTITY.value,
                                properties=related_data,
                            ),
                            rel_type,
                        )
                    )

            # Get related concepts
            concepts: list[NodeInfo] = []
            if include_concepts:
                # Concepts can be related through chunks or documents
                concepts_query = """
                MATCH (e:Entity {id: $entity_id})<-[:MENTIONS]-(c:Chunk)
                      <-[:CONTAINS]-(d:Document)-[:ABOUT]->(concept:Concept)
                RETURN DISTINCT concept
                LIMIT 10
                """
                concept_results = self._client.execute_read(
                    concepts_query,
                    parameters={"entity_id": entity_id},
                )
                for record in concept_results:
                    concept_data = record.get("concept", {})
                    concept_id = concept_data.get(PropName.ID, "")
                    concepts.append(
                        NodeInfo(
                            id=str(concept_id),
                            label=NodeLabel.CONCEPT.value,
                            properties=concept_data,
                        )
                    )

            return EntityContext(
                entity=entity_info,
                mentioned_in=mentioned_in,
                related_entities=related_entities,
                concepts=concepts,
            )

        except Exception as e:
            logger.error(f"Failed to get entity context: {e}")
            raise

    # =========================================================================
    # Document Graph Operations
    # =========================================================================

    def get_document_graph(
        self,
        document_id: str,
        include_chunks: bool = True,
        include_entities: bool = True,
        include_concepts: bool = True,
        chunk_limit: int = 100,
        entity_limit: int = 50,
    ) -> DocumentGraph | None:
        """Get a document's subgraph for RAG context.

        Retrieves:
        - Document node
        - Chunk nodes (via CONTAINS relationships)
        - Entity nodes (mentioned in chunks)
        - Concept nodes (document is about)
        - All relationships between them

        Args:
            document_id: Document node ID.
            include_chunks: Whether to include chunks.
            include_entities: Whether to include entities.
            include_concepts: Whether to include concepts.
            chunk_limit: Maximum chunks to return.
            entity_limit: Maximum entities to return.

        Returns:
            DocumentGraph or None if document not found.
        """
        # Get document node
        doc_query = """
        MATCH (d:Document {id: $document_id})
        RETURN d
        """

        try:
            doc_results = self._client.execute_read(
                doc_query,
                parameters={"document_id": document_id},
            )

            if not doc_results:
                return None

            doc_data = doc_results[0].get("d", {})
            doc_info = NodeInfo(
                id=document_id,
                label=NodeLabel.DOCUMENT.value,
                properties=doc_data,
            )

            chunks: list[NodeInfo] = []
            entities: list[NodeInfo] = []
            concepts: list[NodeInfo] = []
            relationships: list[RelationshipInfo] = []

            # Get chunks
            if include_chunks:
                chunks_query = """
                MATCH (d:Document {id: $document_id})-[r:CONTAINS]->(c:Chunk)
                RETURN c, id(r) AS rel_id
                ORDER BY c.chunk_index
                LIMIT $limit
                """
                chunk_results = self._client.execute_read(
                    chunks_query,
                    parameters={"document_id": document_id, "limit": chunk_limit},
                )
                for record in chunk_results:
                    chunk_data = record.get("c", {})
                    chunk_id = chunk_data.get(PropName.ID, "")
                    chunks.append(
                        NodeInfo(
                            id=str(chunk_id),
                            label=NodeLabel.CHUNK.value,
                            properties=chunk_data,
                        )
                    )

            # Get entities mentioned in chunks
            if include_entities and chunks:
                # Get entity IDs from chunks
                chunk_ids = [c.id for c in chunks]

                entities_query = """
                MATCH (c:Chunk)-[r:MENTIONS]->(e:Entity)
                WHERE c.id IN $chunk_ids
                RETURN DISTINCT e, id(r) AS rel_id, c.id AS chunk_id
                LIMIT $limit
                """
                entity_results = self._client.execute_read(
                    entities_query,
                    parameters={"chunk_ids": chunk_ids, "limit": entity_limit},
                )
                for record in entity_results:
                    entity_data = record.get("e", {})
                    entity_id = entity_data.get(PropName.ID, "")
                    entities.append(
                        NodeInfo(
                            id=str(entity_id),
                            label=NodeLabel.ENTITY.value,
                            properties=entity_data,
                        )
                    )

            # Get concepts
            if include_concepts:
                concepts_query = """
                MATCH (d:Document {id: $document_id})-[r:ABOUT]->(c:Concept)
                RETURN DISTINCT c
                """
                concept_results = self._client.execute_read(
                    concepts_query,
                    parameters={"document_id": document_id},
                )
                for record in concept_results:
                    concept_data = record.get("c", {})
                    concept_id = concept_data.get(PropName.ID, "")
                    concepts.append(
                        NodeInfo(
                            id=str(concept_id),
                            label=NodeLabel.CONCEPT.value,
                            properties=concept_data,
                        )
                    )

            return DocumentGraph(
                document=doc_info,
                chunks=chunks,
                entities=entities,
                concepts=concepts,
                relationships=relationships,
            )

        except Exception as e:
            logger.error(f"Failed to get document graph: {e}")
            raise

    # =========================================================================
    # Entity Search Operations
    # =========================================================================

    def find_entities_by_name(
        self,
        name: str,
        entity_type: str | None = None,
        limit: int = 10,
        case_sensitive: bool = False,
    ) -> list[NodeInfo]:
        """Find entities by name with optional type filter.

        Args:
            name: Entity name or partial name to search.
            entity_type: Optional entity type filter.
            limit: Maximum results to return.
            case_sensitive: Whether search is case-sensitive.

        Returns:
            List of matching Entity NodeInfo objects.
        """
        # Build WHERE clause
        if case_sensitive:
            name_condition = "e.name CONTAINS $name"
        else:
            name_condition = "toLower(e.name) CONTAINS toLower($name)"

        where_clause = f"WHERE {name_condition}"

        if entity_type:
            where_clause += " AND e.entity_type = $entity_type"

        query = f"""
        MATCH (e:Entity)
        {where_clause}
        RETURN e
        LIMIT $limit
        """

        try:
            results = self._client.execute_read(
                query,
                parameters={
                    "name": name,
                    "entity_type": entity_type,
                    "limit": limit,
                },
            )

            entities = []
            for record in results:
                entity_data = record.get("e", {})
                entity_id = entity_data.get(PropName.ID, "")
                entities.append(
                    NodeInfo(
                        id=str(entity_id),
                        label=NodeLabel.ENTITY.value,
                        properties=entity_data,
                    )
                )

            return entities

        except Exception as e:
            logger.error(f"Failed to find entities by name: {e}")
            raise

    def find_related_entities(
        self,
        entity_id: str,
        max_depth: int = 2,
        limit: int = 20,
    ) -> list[NodeInfo]:
        """Find entities related to a given entity via RELATED_TO relationships.

        Args:
            entity_id: Source entity ID.
            max_depth: Maximum traversal depth.
            limit: Maximum results.

        Returns:
            List of related Entity NodeInfo objects.
        """
        query = f"""
        MATCH (e:Entity {{id: $entity_id}})-[r:RELATED_TO*1..{max_depth}]-(related:Entity)
        RETURN DISTINCT related
        LIMIT $limit
        """

        try:
            results = self._client.execute_read(
                query,
                parameters={"entity_id": entity_id, "limit": limit},
            )

            entities = []
            for record in results:
                entity_data = record.get("related", {})
                related_id = entity_data.get(PropName.ID, "")
                entities.append(
                    NodeInfo(
                        id=str(related_id),
                        label=NodeLabel.ENTITY.value,
                        properties=entity_data,
                    )
                )

            return entities

        except Exception as e:
            logger.error(f"Failed to find related entities: {e}")
            raise

    def search_entities(
        self,
        request: SearchEntitiesRequest,
    ) -> list[NodeInfo]:
        """Search entities with SearchEntitiesRequest parameters.

        Args:
            request: SearchEntitiesRequest with search parameters.

        Returns:
            List of matching Entity NodeInfo objects.
        """
        return self.find_entities_by_name(
            name=request.name,
            entity_type=request.entity_type,
            limit=request.limit,
            case_sensitive=request.case_sensitive,
        )

    # =========================================================================
    # Graph Statistics
    # =========================================================================

    def get_node_degree(
        self,
        node_id: str,
        node_label: str | None = None,
        direction: str = Direction.BOTH.value,
        relationship_types: list[str] | None = None,
    ) -> int:
        """Get the degree (number of connections) of a node.

        Args:
            node_id: Node ID.
            node_label: Optional node label.
            direction: Relationship direction to count.
            relationship_types: Optional relationship types to count.

        Returns:
            Number of connections.
        """
        node_pattern = f":{node_label}" if node_label else ""
        rel_type_clause = ""
        if relationship_types:
            rel_type_clause = ":" + "|".join(relationship_types)

        if direction.upper() == Direction.OUTGOING.value:
            pattern = f"(n{node_pattern} {{id: $node_id}})-[r{rel_type_clause}]->()"
        elif direction.upper() == Direction.INCOMING.value:
            pattern = f"()-[r{rel_type_clause}]->(n{node_pattern} {{id: $node_id}})"
        else:
            pattern = f"(n{node_pattern} {{id: $node_id}})-[r{rel_type_clause}]-()"

        query = f"""
        MATCH {pattern}
        RETURN count(r) AS degree
        """

        try:
            results = self._client.execute_read(
                query,
                parameters={"node_id": node_id},
            )
            if results:
                return results[0].get("degree", 0)
            return 0

        except Exception as e:
            logger.error(f"Failed to get node degree: {e}")
            raise

    def get_graph_stats(self) -> dict[str, Any]:
        """Get overall graph statistics.

        Returns:
            Dictionary with node counts, relationship counts, etc.
        """
        query = """
        MATCH (n)
        RETURN labels(n)[0] AS label, count(n) AS count
        ORDER BY count DESC
        """

        rel_query = """
        MATCH ()-[r]->()
        RETURN type(r) AS type, count(r) AS count
        ORDER BY count DESC
        """

        try:
            node_results = self._client.execute_read(query)
            rel_results = self._client.execute_read(rel_query)

            node_counts = {}
            total_nodes = 0
            for record in node_results:
                label = record.get("label", "Unknown")
                count = record.get("count", 0)
                node_counts[label] = count
                total_nodes += count

            rel_counts = {}
            total_rels = 0
            for record in rel_results:
                rel_type = record.get("type", "Unknown")
                count = record.get("count", 0)
                rel_counts[rel_type] = count
                total_rels += count

            return {
                "total_nodes": total_nodes,
                "total_relationships": total_rels,
                "node_counts_by_label": node_counts,
                "relationship_counts_by_type": rel_counts,
            }

        except Exception as e:
            logger.error(f"Failed to get graph stats: {e}")
            raise
