"""
Relationship manager for Neo4j database controller.

This module provides relationship CRUD operations including
creation, retrieval, update, and deletion of relationships.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from apps.neo4j_database_controller.client import Neo4jClient
from apps.neo4j_database_controller.constants import (
    DEFAULT_BATCH_SIZE,
    Direction,
    PropName,
    RelType,
    VALID_REL_TYPES,
)
from apps.neo4j_database_controller.dto import (
    BatchRelationshipCreationResult,
    CreateRelationshipRequest,
    CreateRelationshipsBatchRequest,
    DeleteResult,
    RelationshipCreationResult,
    RelationshipInfo,
)
from apps.neo4j_database_controller.exceptions import (
    InvalidRelationshipTypeError,
    NodeNotFoundError,
    RelationshipCreationError,
    RelationshipDeletionError,
    RelationshipNotFoundError,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class RelationshipManager:
    """Manager for Neo4j relationship CRUD operations.

    This class handles:
    - Single relationship creation between nodes
    - Batch relationship creation
    - Relationship retrieval by ID or filters
    - Relationship updates and deletion

    Example:
        >>> manager = RelationshipManager()
        >>> rel = manager.create_relationship(
        ...     "MENTIONS", "chunk-1", "Chunk", "entity-1", "Entity"
        ... )
        >>> rels = manager.get_relationships("chunk-1", direction="OUTGOING")
        >>> manager.delete_relationship(rel.id)
    """

    def __init__(self, client: Neo4jClient | None = None) -> None:
        """Initialize the relationship manager.

        Args:
            client: Optional Neo4jClient instance. If None, gets singleton.
        """
        self._client = client or Neo4jClient.get_instance()

    def _validate_rel_type(self, rel_type: str) -> None:
        """Validate that relationship type is valid.

        Args:
            rel_type: Relationship type to validate.

        Raises:
            InvalidRelationshipTypeError: If relationship type is invalid.
        """
        if rel_type not in VALID_REL_TYPES:
            raise InvalidRelationshipTypeError(rel_type)

    def _prepare_properties(
        self,
        properties: dict[str, Any] | None,
        include_timestamp: bool = True,
    ) -> dict[str, Any]:
        """Prepare relationship properties with timestamps.

        Args:
            properties: Original properties dictionary.
            include_timestamp: Whether to add created_at.

        Returns:
            Properties dictionary with timestamps.
        """
        props = (properties or {}).copy()
        if include_timestamp:
            now = datetime.utcnow().isoformat()
            if PropName.CREATED_AT not in props:
                props[PropName.CREATED_AT] = now
        return props

    # =========================================================================
    # Create Operations
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
            rel_type: Relationship type (CONTAINS, MENTIONS, RELATED_TO, etc.).
            from_node_id: Source node ID.
            from_node_label: Source node label.
            to_node_id: Target node ID.
            to_node_label: Target node label.
            properties: Optional relationship properties.
            merge: If True, use MERGE instead of CREATE (upsert behavior).

        Returns:
            RelationshipCreationResult with created relationship info.

        Raises:
            InvalidRelationshipTypeError: If relationship type is invalid.
            NodeNotFoundError: If source or target node does not exist.
            RelationshipCreationError: If creation fails.
        """
        self._validate_rel_type(rel_type)

        props = self._prepare_properties(properties)

        # Build Cypher query
        if merge:
            query = f"""
            MATCH (from:{from_node_label} {{id: $from_id}})
            MATCH (to:{to_node_label} {{id: $to_id}})
            MERGE (from)-[r:{rel_type}]->(to)
            SET r += $properties
            RETURN from.id AS from_id, to.id AS to_id, type(r) AS rel_type,
                   id(r) AS rel_id, properties(r) AS properties,
                   labels(from)[0] AS from_label, labels(to)[0] AS to_label
            """
        else:
            query = f"""
            MATCH (from:{from_node_label} {{id: $from_id}})
            MATCH (to:{to_node_label} {{id: $to_id}})
            CREATE (from)-[r:{rel_type}]->(to)
            SET r = $properties
            RETURN from.id AS from_id, to.id AS to_id, type(r) AS rel_type,
                   id(r) AS rel_id, properties(r) AS properties,
                   labels(from)[0] AS from_label, labels(to)[0] AS to_label
            """

        try:
            logger.info(
                f"Creating {rel_type} relationship: {from_node_label}({from_node_id}) -> "
                f"{to_node_label}({to_node_id})"
            )

            results = self._client.execute_write(
                query,
                parameters={
                    "from_id": from_node_id,
                    "to_id": to_node_id,
                    "properties": props,
                },
            )

            if not results:
                raise RelationshipCreationError(
                    rel_type=rel_type,
                    from_node_id=from_node_id,
                    to_node_id=to_node_id,
                    reason="No result returned - nodes may not exist",
                )

            record = results[0]
            rel_info = RelationshipInfo(
                id=record.get("rel_id", 0),
                rel_type=record.get("rel_type", rel_type),
                from_node_id=record.get("from_id", from_node_id),
                from_node_label=record.get("from_label", from_node_label),
                to_node_id=record.get("to_id", to_node_id),
                to_node_label=record.get("to_label", to_node_label),
                properties=record.get("properties", {}),
            )

            logger.info(
                f"Successfully created {rel_type} relationship "
                f"({from_node_id} -> {to_node_id})"
            )

            return RelationshipCreationResult(
                relationship=rel_info,
                created=True,
            )

        except Exception as e:
            error_msg = str(e)
            if "not found" in error_msg.lower() or "no rows" in error_msg.lower():
                raise NodeNotFoundError(
                    node_id=from_node_id if "from" in error_msg.lower() else to_node_id,
                    label=from_node_label if "from" in error_msg.lower() else to_node_label,
                )
            logger.error(f"Failed to create {rel_type} relationship: {e}")
            raise RelationshipCreationError(
                rel_type=rel_type,
                from_node_id=from_node_id,
                to_node_id=to_node_id,
                reason=error_msg,
            )

    def create_relationships_batch(
        self,
        relationships: list[CreateRelationshipRequest],
        batch_size: int = DEFAULT_BATCH_SIZE,
        merge: bool = False,
    ) -> BatchRelationshipCreationResult:
        """Create multiple relationships in batches.

        Uses UNWIND for efficient batch operations.

        Args:
            relationships: List of CreateRelationshipRequest objects.
            batch_size: Number of relationships per batch.
            merge: If True, use MERGE instead of CREATE.

        Returns:
            BatchRelationshipCreationResult with created relationships and counts.

        Raises:
            InvalidRelationshipTypeError: If any relationship type is invalid.
            RelationshipCreationError: If batch creation fails.
        """
        if not relationships:
            return BatchRelationshipCreationResult(
                relationships=[],
                created_count=0,
                failed_count=0,
            )

        # Validate all relationship types first
        for rel in relationships:
            self._validate_rel_type(rel.rel_type)

        all_created_rels: list[RelationshipInfo] = []
        total_created = 0
        total_failed = 0

        # Process in batches
        for i in range(0, len(relationships), batch_size):
            batch = relationships[i : i + batch_size]

            # Prepare batch data
            batch_data = []
            for rel in batch:
                props = self._prepare_properties(rel.properties)
                batch_data.append(
                    {
                        "from_id": rel.from_node_id,
                        "from_label": rel.from_node_label,
                        "to_id": rel.to_node_id,
                        "to_label": rel.to_node_label,
                        "rel_type": rel.rel_type,
                        "properties": props,
                    }
                )

            # Build Cypher query with UNWIND
            # Note: We can't parameterize relationship types in Cypher,
            # so we need to use a different approach - process by relationship type
            rel_types_in_batch = set(rel.rel_type for rel in batch)

            for rel_type in rel_types_in_batch:
                rel_type_data = [d for d in batch_data if d["rel_type"] == rel_type]

                if merge:
                    query = f"""
                    UNWIND $rels AS rel_data
                    MATCH (from {{id: rel_data.from_id}})
                    WHERE rel_data.from_label IN labels(from)
                    MATCH (to {{id: rel_data.to_id}})
                    WHERE rel_data.to_label IN labels(to)
                    MERGE (from)-[r:{rel_type}]->(to)
                    SET r += rel_data.properties
                    RETURN from.id AS from_id, to.id AS to_id, type(r) AS rel_type,
                           id(r) AS rel_id, properties(r) AS properties,
                           labels(from)[0] AS from_label, labels(to)[0] AS to_label
                    """
                else:
                    query = f"""
                    UNWIND $rels AS rel_data
                    MATCH (from {{id: rel_data.from_id}})
                    WHERE rel_data.from_label IN labels(from)
                    MATCH (to {{id: rel_data.to_id}})
                    WHERE rel_data.to_label IN labels(to)
                    CREATE (from)-[r:{rel_type}]->(to)
                    SET r = rel_data.properties
                    RETURN from.id AS from_id, to.id AS to_id, type(r) AS rel_type,
                           id(r) AS rel_id, properties(r) AS properties,
                           labels(from)[0] AS from_label, labels(to)[0] AS to_label
                    """

                try:
                    logger.info(
                        f"Creating batch of {len(rel_type_data)} {rel_type} relationships"
                    )

                    results = self._client.execute_write(
                        query,
                        parameters={
                            "rels": rel_type_data,
                        },
                    )

                    # Parse results
                    for record in results:
                        rel_info = RelationshipInfo(
                            id=record.get("rel_id", 0),
                            rel_type=record.get("rel_type", rel_type),
                            from_node_id=record.get("from_id", ""),
                            from_node_label=record.get("from_label", ""),
                            to_node_id=record.get("to_id", ""),
                            to_node_label=record.get("to_label", ""),
                            properties=record.get("properties", {}),
                        )
                        all_created_rels.append(rel_info)

                    total_created += len(rel_type_data)
                    logger.info(f"Successfully created {len(rel_type_data)} {rel_type} relationships")

                except Exception as e:
                    logger.error(f"Failed to create {rel_type} batch: {e}")
                    total_failed += len(rel_type_data)

        return BatchRelationshipCreationResult(
            relationships=all_created_rels,
            created_count=total_created,
            failed_count=total_failed,
        )

    # =========================================================================
    # Read Operations
    # =========================================================================

    def get_relationship_by_id(
        self,
        rel_id: int,
    ) -> RelationshipInfo | None:
        """Retrieve a relationship by its Neo4j internal ID.

        Args:
            rel_id: Neo4j internal relationship ID.

        Returns:
            RelationshipInfo if found, None otherwise.
        """
        query = """
        MATCH ()-[r]->()
        WHERE id(r) = $rel_id
        RETURN type(r) AS rel_type, id(r) AS rel_id, properties(r) AS properties,
               startNode(r).id AS from_id, endNode(r).id AS to_id,
               labels(startNode(r))[0] AS from_label,
               labels(endNode(r))[0] AS to_label
        """

        try:
            results = self._client.execute_read(
                query,
                parameters={"rel_id": rel_id},
            )

            if not results:
                return None

            record = results[0]
            return RelationshipInfo(
                id=record.get("rel_id", rel_id),
                rel_type=record.get("rel_type", ""),
                from_node_id=record.get("from_id", ""),
                from_node_label=record.get("from_label", ""),
                to_node_id=record.get("to_id", ""),
                to_node_label=record.get("to_label", ""),
                properties=record.get("properties", {}),
            )

        except Exception as e:
            logger.error(f"Failed to get relationship {rel_id}: {e}")
            raise

    def get_relationship_by_id_or_raise(
        self,
        rel_id: int,
    ) -> RelationshipInfo:
        """Retrieve a relationship by ID, raising error if not found.

        Args:
            rel_id: Neo4j internal relationship ID.

        Returns:
            RelationshipInfo if found.

        Raises:
            RelationshipNotFoundError: If relationship does not exist.
        """
        rel = self.get_relationship_by_id(rel_id)
        if rel is None:
            raise RelationshipNotFoundError(rel_id=rel_id)
        return rel

    def get_relationships(
        self,
        node_id: str,
        node_label: str | None = None,
        direction: str = Direction.BOTH.value,
        rel_type: str | None = None,
        limit: int = 100,
    ) -> list[RelationshipInfo]:
        """Get relationships connected to a node.

        Args:
            node_id: Node ID to get relationships for.
            node_label: Optional node label for better query performance.
            direction: Relationship direction ("OUTGOING", "INCOMING", "BOTH").
            rel_type: Optional filter by relationship type.
            limit: Maximum number of relationships to return.

        Returns:
            List of RelationshipInfo objects.

        Raises:
            InvalidRelationshipTypeError: If rel_type is invalid and provided.
        """
        # Validate relationship type if provided
        if rel_type:
            self._validate_rel_type(rel_type)

        # Build pattern based on direction
        rel_type_clause = f":{rel_type}" if rel_type else ""
        node_pattern = f":{node_label}" if node_label else ""

        if direction.upper() == Direction.OUTGOING.value:
            pattern = f"(n{node_pattern} {{id: $node_id}})-[r{rel_type_clause}]->()"
        elif direction.upper() == Direction.INCOMING.value:
            pattern = f"()-[r{rel_type_clause}]->(n{node_pattern} {{id: $node_id}})"
        else:  # BOTH
            pattern = f"(n{node_pattern} {{id: $node_id}})-[r{rel_type_clause}]-()"

        query = f"""
        MATCH {pattern}
        RETURN type(r) AS rel_type, id(r) AS rel_id, properties(r) AS properties,
               startNode(r).id AS from_id, endNode(r).id AS to_id,
               labels(startNode(r))[0] AS from_label,
               labels(endNode(r))[0] AS to_label
        LIMIT $limit
        """

        try:
            results = self._client.execute_read(
                query,
                parameters={"node_id": node_id, "limit": limit},
            )

            relationships = []
            for record in results:
                rel_info = RelationshipInfo(
                    id=record.get("rel_id", 0),
                    rel_type=record.get("rel_type", ""),
                    from_node_id=record.get("from_id", ""),
                    from_node_label=record.get("from_label", ""),
                    to_node_id=record.get("to_id", ""),
                    to_node_label=record.get("to_label", ""),
                    properties=record.get("properties", {}),
                )
                relationships.append(rel_info)

            return relationships

        except Exception as e:
            logger.error(f"Failed to get relationships for node '{node_id}': {e}")
            raise

    def get_outgoing_relationships(
        self,
        node_id: str,
        node_label: str | None = None,
        rel_type: str | None = None,
        limit: int = 100,
    ) -> list[RelationshipInfo]:
        """Get outgoing relationships from a node.

        Args:
            node_id: Node ID.
            node_label: Optional node label.
            rel_type: Optional filter by relationship type.
            limit: Maximum number of relationships.

        Returns:
            List of outgoing RelationshipInfo objects.
        """
        return self.get_relationships(
            node_id=node_id,
            node_label=node_label,
            direction=Direction.OUTGOING.value,
            rel_type=rel_type,
            limit=limit,
        )

    def get_incoming_relationships(
        self,
        node_id: str,
        node_label: str | None = None,
        rel_type: str | None = None,
        limit: int = 100,
    ) -> list[RelationshipInfo]:
        """Get incoming relationships to a node.

        Args:
            node_id: Node ID.
            node_label: Optional node label.
            rel_type: Optional filter by relationship type.
            limit: Maximum number of relationships.

        Returns:
            List of incoming RelationshipInfo objects.
        """
        return self.get_relationships(
            node_id=node_id,
            node_label=node_label,
            direction=Direction.INCOMING.value,
            rel_type=rel_type,
            limit=limit,
        )

    def count_relationships(
        self,
        node_id: str,
        node_label: str | None = None,
        direction: str = Direction.BOTH.value,
        rel_type: str | None = None,
    ) -> int:
        """Count relationships connected to a node.

        Args:
            node_id: Node ID.
            node_label: Optional node label.
            direction: Relationship direction.
            rel_type: Optional filter by relationship type.

        Returns:
            Number of relationships.
        """
        if rel_type:
            self._validate_rel_type(rel_type)

        rel_type_clause = f":{rel_type}" if rel_type else ""
        node_pattern = f":{node_label}" if node_label else ""

        if direction.upper() == Direction.OUTGOING.value:
            pattern = f"(n{node_pattern} {{id: $node_id}})-[r{rel_type_clause}]->()"
        elif direction.upper() == Direction.INCOMING.value:
            pattern = f"()-[r{rel_type_clause}]->(n{node_pattern} {{id: $node_id}})"
        else:  # BOTH
            pattern = f"(n{node_pattern} {{id: $node_id}})-[r{rel_type_clause}]-()"

        query = f"""
        MATCH {pattern}
        RETURN count(r) AS count
        """

        try:
            results = self._client.execute_read(
                query,
                parameters={"node_id": node_id},
            )
            if results:
                return results[0].get("count", 0)
            return 0

        except Exception as e:
            logger.error(f"Failed to count relationships for node '{node_id}': {e}")
            raise

    def relationship_exists(
        self,
        rel_type: str,
        from_node_id: str,
        to_node_id: str,
    ) -> bool:
        """Check if a relationship exists between two nodes.

        Args:
            rel_type: Relationship type.
            from_node_id: Source node ID.
            to_node_id: Target node ID.

        Returns:
            True if relationship exists.
        """
        self._validate_rel_type(rel_type)

        query = f"""
        MATCH ()-[r:{rel_type}]->()
        WHERE startNode(r).id = $from_id AND endNode(r).id = $to_id
        RETURN count(r) > 0 AS exists
        """

        try:
            results = self._client.execute_read(
                query,
                parameters={"from_id": from_node_id, "to_id": to_node_id},
            )
            if results:
                return results[0].get("exists", False)
            return False

        except Exception as e:
            logger.error(f"Failed to check relationship existence: {e}")
            raise

    # =========================================================================
    # Update Operations
    # =========================================================================

    def update_relationship(
        self,
        rel_id: int,
        properties: dict[str, Any],
        merge: bool = True,
    ) -> RelationshipInfo:
        """Update relationship properties.

        Args:
            rel_id: Neo4j internal relationship ID.
            properties: Properties to update.
            merge: If True, merge with existing properties. If False, replace all.

        Returns:
            Updated RelationshipInfo.

        Raises:
            RelationshipNotFoundError: If relationship does not exist.
        """
        # Add updated_at timestamp
        props = properties.copy()
        props[PropName.UPDATED_AT] = datetime.utcnow().isoformat()

        set_clause = "SET r += $properties" if merge else "SET r = $properties"

        query = f"""
        MATCH ()-[r]->()
        WHERE id(r) = $rel_id
        {set_clause}
        RETURN type(r) AS rel_type, id(r) AS rel_id, properties(r) AS properties,
               startNode(r).id AS from_id, endNode(r).id AS to_id,
               labels(startNode(r))[0] AS from_label,
               labels(endNode(r))[0] AS to_label
        """

        try:
            results = self._client.execute_write(
                query,
                parameters={"rel_id": rel_id, "properties": props},
            )

            if not results:
                raise RelationshipNotFoundError(rel_id=rel_id)

            record = results[0]

            logger.info(f"Updated relationship {rel_id}")

            return RelationshipInfo(
                id=record.get("rel_id", rel_id),
                rel_type=record.get("rel_type", ""),
                from_node_id=record.get("from_id", ""),
                from_node_label=record.get("from_label", ""),
                to_node_id=record.get("to_id", ""),
                to_node_label=record.get("to_label", ""),
                properties=record.get("properties", {}),
            )

        except RelationshipNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update relationship {rel_id}: {e}")
            raise

    # =========================================================================
    # Delete Operations
    # =========================================================================

    def delete_relationship(
        self,
        rel_id: int,
    ) -> DeleteResult:
        """Delete a relationship by ID.

        Args:
            rel_id: Neo4j internal relationship ID.

        Returns:
            DeleteResult with deletion status.

        Raises:
            RelationshipNotFoundError: If relationship does not exist.
            RelationshipDeletionError: If deletion fails.
        """
        # Check if relationship exists first
        if not self.get_relationship_by_id(rel_id):
            raise RelationshipNotFoundError(rel_id=rel_id)

        query = """
        MATCH ()-[r]->()
        WHERE id(r) = $rel_id
        DELETE r
        RETURN count(r) AS deleted_count
        """

        try:
            logger.info(f"Deleting relationship {rel_id}")

            self._client.execute_write(
                query,
                parameters={"rel_id": rel_id},
            )

            logger.info(f"Successfully deleted relationship {rel_id}")

            return DeleteResult(deleted=True, deleted_count=1)

        except Exception as e:
            logger.error(f"Failed to delete relationship {rel_id}: {e}")
            raise RelationshipDeletionError(rel_id=rel_id, reason=str(e))

    def delete_relationships_by_filter(
        self,
        node_id: str,
        node_label: str | None = None,
        direction: str = Direction.BOTH.value,
        rel_type: str | None = None,
    ) -> DeleteResult:
        """Delete relationships matching filter conditions.

        Args:
            node_id: Node ID to delete relationships for.
            node_label: Optional node label.
            direction: Relationship direction to delete.
            rel_type: Optional filter by relationship type.

        Returns:
            DeleteResult with deletion count.

        Raises:
            InvalidRelationshipTypeError: If rel_type is invalid and provided.
            RelationshipDeletionError: If deletion fails.
        """
        if rel_type:
            self._validate_rel_type(rel_type)

        rel_type_clause = f":{rel_type}" if rel_type else ""
        node_pattern = f":{node_label}" if node_label else ""

        if direction.upper() == Direction.OUTGOING.value:
            pattern = f"(n{node_pattern} {{id: $node_id}})-[r{rel_type_clause}]->()"
        elif direction.upper() == Direction.INCOMING.value:
            pattern = f"()-[r{rel_type_clause}]->(n{node_pattern} {{id: $node_id}})"
        else:  # BOTH
            pattern = f"(n{node_pattern} {{id: $node_id}})-[r{rel_type_clause}]-()"

        query = f"""
        MATCH {pattern}
        WITH n, r, count(r) AS rel_count
        DELETE r
        RETURN rel_count
        """

        try:
            logger.info(
                f"Deleting relationships for node '{node_id}' "
                f"(direction={direction}, type={rel_type})"
            )

            results = self._client.execute_write(
                query,
                parameters={"node_id": node_id},
            )

            deleted_count = 0
            if results:
                deleted_count = results[0].get("rel_count", 0)

            logger.info(f"Successfully deleted {deleted_count} relationships")

            return DeleteResult(deleted=True, deleted_count=deleted_count)

        except Exception as e:
            logger.error(f"Failed to delete relationships by filter: {e}")
            raise RelationshipDeletionError(rel_id=0, reason=str(e))

    def delete_all_relationships_of_type(
        self,
        rel_type: str,
    ) -> DeleteResult:
        """Delete all relationships of a given type.

        WARNING: This is a destructive operation. Use with caution.

        Args:
            rel_type: Relationship type to delete.

        Returns:
            DeleteResult with deletion count.
        """
        self._validate_rel_type(rel_type)

        query = f"""
        MATCH ()-[r:{rel_type}]->()
        WITH r, count(r) AS rel_count
        DELETE r
        RETURN rel_count
        """

        try:
            logger.warning(f"Deleting ALL {rel_type} relationships")

            results = self._client.execute_write(query)

            deleted_count = 0
            if results:
                deleted_count = results[0].get("rel_count", 0)

            logger.info(f"Successfully deleted {deleted_count} {rel_type} relationships")

            return DeleteResult(deleted=True, deleted_count=deleted_count)

        except Exception as e:
            logger.error(f"Failed to delete all {rel_type} relationships: {e}")
            raise RelationshipDeletionError(rel_id=0, reason=str(e))

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def create_contains_relationship(
        self,
        document_id: str,
        chunk_id: str,
        order: int = 0,
    ) -> RelationshipCreationResult:
        """Create a CONTAINS relationship (Document -> Chunk).

        Args:
            document_id: Document node ID.
            chunk_id: Chunk node ID.
            order: Order of chunk in document.

        Returns:
            RelationshipCreationResult.
        """
        return self.create_relationship(
            rel_type=RelType.CONTAINS.value,
            from_node_id=document_id,
            from_node_label="Document",
            to_node_id=chunk_id,
            to_node_label="Chunk",
            properties={PropName.ORDER: order},
        )

    def create_mentions_relationship(
        self,
        chunk_id: str,
        entity_id: str,
        confidence: float = 1.0,
        count: int = 1,
    ) -> RelationshipCreationResult:
        """Create a MENTIONS relationship (Chunk -> Entity).

        Args:
            chunk_id: Chunk node ID.
            entity_id: Entity node ID.
            confidence: Extraction confidence.
            count: Number of times entity is mentioned.

        Returns:
            RelationshipCreationResult.
        """
        return self.create_relationship(
            rel_type=RelType.MENTIONS.value,
            from_node_id=chunk_id,
            from_node_label="Chunk",
            to_node_id=entity_id,
            to_node_label="Entity",
            properties={
                PropName.CONFIDENCE: confidence,
                PropName.COUNT: count,
            },
        )

    def create_related_to_relationship(
        self,
        from_entity_id: str,
        to_entity_id: str,
        relation_type: str = "",
        confidence: float = 1.0,
    ) -> RelationshipCreationResult:
        """Create a RELATED_TO relationship (Entity -> Entity).

        Args:
            from_entity_id: Source entity ID.
            to_entity_id: Target entity ID.
            relation_type: Type of relationship (semantic).
            confidence: Relationship confidence.

        Returns:
            RelationshipCreationResult.
        """
        return self.create_relationship(
            rel_type=RelType.RELATED_TO.value,
            from_node_id=from_entity_id,
            from_node_label="Entity",
            to_node_id=to_entity_id,
            to_node_label="Entity",
            properties={
                PropName.RELATION_TYPE: relation_type,
                PropName.CONFIDENCE: confidence,
            },
        )

    def create_about_relationship(
        self,
        document_id: str,
        concept_id: str,
        confidence: float = 1.0,
    ) -> RelationshipCreationResult:
        """Create an ABOUT relationship (Document -> Concept).

        Args:
            document_id: Document node ID.
            concept_id: Concept node ID.
            confidence: Relevance confidence.

        Returns:
            RelationshipCreationResult.
        """
        return self.create_relationship(
            rel_type=RelType.ABOUT.value,
            from_node_id=document_id,
            from_node_label="Document",
            to_node_id=concept_id,
            to_node_label="Concept",
            properties={PropName.CONFIDENCE: confidence},
        )
