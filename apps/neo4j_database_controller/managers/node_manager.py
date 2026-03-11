"""
Node manager for Neo4j database controller.

This module provides node CRUD operations including
creation, retrieval, update, and deletion of nodes.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from apps.neo4j_database_controller.client import Neo4jClient
from apps.neo4j_database_controller.constants import (
    DEFAULT_BATCH_SIZE,
    NodeLabel,
    PropName,
    VALID_NODE_LABELS,
)
from apps.neo4j_database_controller.dto import (
    BatchNodeCreationResult,
    CreateNodeRequest,
    CreateNodesBatchRequest,
    DeleteNodeRequest,
    DeleteResult,
    GetNodeNeighborsRequest,
    NodeCreationResult,
    NodeInfo,
    UpdateNodeRequest,
    node_info_from_record,
)
from apps.neo4j_database_controller.exceptions import (
    InvalidNodeLabelError,
    NodeAlreadyExistsError,
    NodeCreationError,
    NodeDeletionError,
    NodeNotFoundError,
    QueryError,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class NodeManager:
    """Manager for Neo4j node CRUD operations.

    This class handles:
    - Single node creation and retrieval
    - Batch node creation
    - Node updates and deletion
    - Node queries by label and filters

    Example:
        >>> manager = NodeManager()
        >>> node = manager.create_node("Entity", {"id": "123", "name": "Python"})
        >>> retrieved = manager.get_node_by_id("123", "Entity")
        >>> manager.delete_node("123", "Entity")
    """

    def __init__(self, client: Neo4jClient | None = None) -> None:
        """Initialize the node manager.

        Args:
            client: Optional Neo4jClient instance. If None, gets singleton.
        """
        self._client = client or Neo4jClient.get_instance()

    def _validate_label(self, label: str) -> None:
        """Validate that label is a valid node label.

        Args:
            label: Node label to validate.

        Raises:
            InvalidNodeLabelError: If label is invalid.
        """
        if label not in VALID_NODE_LABELS:
            raise InvalidNodeLabelError(label)

    def _prepare_properties(
        self,
        properties: dict[str, Any],
        include_timestamp: bool = True,
    ) -> dict[str, Any]:
        """Prepare node properties with timestamps.

        Args:
            properties: Original properties dictionary.
            include_timestamp: Whether to add created_at/updated_at.

        Returns:
            Properties dictionary with timestamps.
        """
        props = properties.copy()
        if include_timestamp:
            now = datetime.utcnow().isoformat()
            if PropName.CREATED_AT not in props:
                props[PropName.CREATED_AT] = now
            props[PropName.UPDATED_AT] = now
        return props

    # =========================================================================
    # Create Operations
    # =========================================================================

    def create_node(
        self,
        label: str,
        properties: dict[str, Any],
        merge: bool = False,
    ) -> NodeCreationResult:
        """Create a single node with properties.

        Args:
            label: Node label (Document, Chunk, Entity, Concept, User).
            properties: Node properties. Must include 'id' as unique identifier.
            merge: If True, use MERGE instead of CREATE (upsert behavior).

        Returns:
            NodeCreationResult with created node info.

        Raises:
            InvalidNodeLabelError: If label is invalid.
            NodeCreationError: If creation fails.
            NodeAlreadyExistsError: If node with same ID exists and merge=False.
        """
        self._validate_label(label)

        # Validate required properties
        if PropName.ID not in properties:
            raise NodeCreationError(
                label=label,
                reason="Missing required property 'id'",
            )

        node_id = properties[PropName.ID]
        props = self._prepare_properties(properties)

        # Build Cypher query
        if merge:
            query = f"""
            MERGE (n:{label} {{id: $id}})
            SET n += $properties
            RETURN n
            """
        else:
            query = f"""
            CREATE (n:{label} $properties)
            RETURN n
            """

        try:
            logger.info(f"Creating {label} node with id='{node_id}'")

            results = self._client.execute_write(
                query,
                parameters={"id": node_id, "properties": props},
            )

            if not results:
                raise NodeCreationError(
                    label=label,
                    reason="No result returned from query",
                )

            # Extract node from result
            record = results[0]
            node_data = record.get("n", {})

            node_info = NodeInfo(
                id=node_id,
                label=label,
                properties=node_data,
            )

            logger.info(f"Successfully created {label} node '{node_id}'")

            return NodeCreationResult(
                node=node_info,
                created=True,
            )

        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower() or "constraint" in error_msg.lower():
                raise NodeAlreadyExistsError(node_id=node_id, label=label)
            logger.error(f"Failed to create {label} node: {e}")
            raise NodeCreationError(label=label, reason=error_msg)

    def create_nodes_batch(
        self,
        label: str,
        nodes: list[dict[str, Any]],
        batch_size: int = DEFAULT_BATCH_SIZE,
        merge: bool = False,
    ) -> BatchNodeCreationResult:
        """Create multiple nodes in batches.

        Uses UNWIND for efficient batch operations.

        Args:
            label: Node label for all nodes.
            nodes: List of property dictionaries. Each must include 'id'.
            batch_size: Number of nodes per batch.
            merge: If True, use MERGE instead of CREATE.

        Returns:
            BatchNodeCreationResult with created nodes and counts.

        Raises:
            InvalidNodeLabelError: If label is invalid.
            NodeCreationError: If batch creation fails.
        """
        self._validate_label(label)

        if not nodes:
            return BatchNodeCreationResult(
                nodes=[],
                created_count=0,
                failed_count=0,
            )

        # Validate all nodes have id
        for i, node in enumerate(nodes):
            if PropName.ID not in node:
                raise NodeCreationError(
                    label=label,
                    reason=f"Node at index {i} missing required property 'id'",
                )

        all_created_nodes: list[NodeInfo] = []
        total_created = 0
        total_failed = 0

        # Process in batches
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i : i + batch_size]

            # Prepare properties with timestamps
            prepared_batch = [
                self._prepare_properties(props) for props in batch
            ]

            # Build Cypher query with UNWIND
            if merge:
                query = f"""
                UNWIND $nodes AS node_data
                MERGE (n:{label} {{id: node_data.id}})
                SET n += node_data
                RETURN n.id AS id, n AS properties
                """
            else:
                query = f"""
                UNWIND $nodes AS node_data
                CREATE (n:{label})
                SET n = node_data
                RETURN n.id AS id, n AS properties
                """

            try:
                logger.info(
                    f"Creating batch of {len(batch)} {label} nodes "
                    f"(batch {i // batch_size + 1})"
                )

                results = self._client.execute_write(
                    query,
                    parameters={"nodes": prepared_batch},
                )

                # Parse results
                for record in results:
                    node_id = record.get("id", "")
                    node_props = record.get("properties", {})
                    all_created_nodes.append(
                        NodeInfo(
                            id=str(node_id),
                            label=label,
                            properties=node_props,
                        )
                    )

                total_created += len(batch)
                logger.info(f"Successfully created {len(batch)} {label} nodes in batch")

            except Exception as e:
                logger.error(f"Failed to create batch at index {i}: {e}")
                total_failed += len(batch)
                # Continue with next batch instead of failing entirely

        return BatchNodeCreationResult(
            nodes=all_created_nodes,
            created_count=total_created,
            failed_count=total_failed,
        )

    # =========================================================================
    # Read Operations
    # =========================================================================

    def get_node_by_id(
        self,
        node_id: str,
        label: str,
    ) -> NodeInfo | None:
        """Retrieve a node by its ID.

        Args:
            node_id: Unique identifier of the node.
            label: Node label.

        Returns:
            NodeInfo if found, None otherwise.

        Raises:
            InvalidNodeLabelError: If label is invalid.
        """
        self._validate_label(label)

        query = f"""
        MATCH (n:{label} {{id: $id}})
        RETURN n
        LIMIT 1
        """

        try:
            results = self._client.execute_read(
                query,
                parameters={"id": node_id},
            )

            if not results:
                return None

            node_data = results[0].get("n", {})
            return NodeInfo(
                id=node_id,
                label=label,
                properties=node_data,
            )

        except Exception as e:
            logger.error(f"Failed to get {label} node '{node_id}': {e}")
            raise

    def get_node_by_id_or_raise(
        self,
        node_id: str,
        label: str,
    ) -> NodeInfo:
        """Retrieve a node by ID, raising error if not found.

        Args:
            node_id: Unique identifier of the node.
            label: Node label.

        Returns:
            NodeInfo if found.

        Raises:
            NodeNotFoundError: If node does not exist.
            InvalidNodeLabelError: If label is invalid.
        """
        node = self.get_node_by_id(node_id, label)
        if node is None:
            raise NodeNotFoundError(node_id=node_id, label=label)
        return node

    def get_nodes_by_label(
        self,
        label: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str | None = None,
        order_direction: str = "DESC",
    ) -> list[NodeInfo]:
        """Query nodes by label with optional filters.

        Args:
            label: Node label.
            filters: Optional property filters (key-value pairs).
            limit: Maximum number of results.
            offset: Offset for pagination.
            order_by: Property to order by.
            order_direction: "ASC" or "DESC".

        Returns:
            List of NodeInfo objects.

        Raises:
            InvalidNodeLabelError: If label is invalid.
        """
        self._validate_label(label)

        # Build WHERE clause from filters
        where_clause = ""
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if filters:
            conditions = []
            for key, value in filters.items():
                param_key = f"filter_{key}"
                conditions.append(f"n.{key} = ${param_key}")
                params[param_key] = value
            where_clause = f"WHERE {' AND '.join(conditions)}"

        # Build ORDER BY clause
        order_clause = ""
        if order_by:
            direction = "DESC" if order_direction.upper() == "DESC" else "ASC"
            order_clause = f"ORDER BY n.{order_by} {direction}"

        query = f"""
        MATCH (n:{label})
        {where_clause}
        RETURN n
        {order_clause}
        SKIP $offset
        LIMIT $limit
        """

        try:
            results = self._client.execute_read(query, parameters=params)

            nodes = []
            for record in results:
                node_data = record.get("n", {})
                node_id = node_data.get(PropName.ID, "")
                nodes.append(
                    NodeInfo(
                        id=str(node_id),
                        label=label,
                        properties=node_data,
                    )
                )

            return nodes

        except Exception as e:
            logger.error(f"Failed to query {label} nodes: {e}")
            raise

    def count_nodes(
        self,
        label: str,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """Count nodes by label with optional filters.

        Args:
            label: Node label.
            filters: Optional property filters.

        Returns:
            Number of matching nodes.
        """
        self._validate_label(label)

        where_clause = ""
        params: dict[str, Any] = {}

        if filters:
            conditions = []
            for key, value in filters.items():
                param_key = f"filter_{key}"
                conditions.append(f"n.{key} = ${param_key}")
                params[param_key] = value
            where_clause = f"WHERE {' AND '.join(conditions)}"

        query = f"""
        MATCH (n:{label})
        {where_clause}
        RETURN count(n) AS count
        """

        try:
            results = self._client.execute_read(query, parameters=params)
            if results:
                return results[0].get("count", 0)
            return 0

        except Exception as e:
            logger.error(f"Failed to count {label} nodes: {e}")
            raise

    def node_exists(
        self,
        node_id: str,
        label: str,
    ) -> bool:
        """Check if a node exists.

        Args:
            node_id: Unique identifier of the node.
            label: Node label.

        Returns:
            True if node exists.
        """
        self._validate_label(label)

        query = f"""
        MATCH (n:{label} {{id: $id}})
        RETURN count(n) > 0 AS exists
        """

        try:
            results = self._client.execute_read(
                query,
                parameters={"id": node_id},
            )
            if results:
                return results[0].get("exists", False)
            return False

        except Exception as e:
            logger.error(f"Failed to check node existence: {e}")
            raise

    # =========================================================================
    # Update Operations
    # =========================================================================

    def update_node(
        self,
        node_id: str,
        label: str,
        properties: dict[str, Any],
        merge: bool = True,
    ) -> NodeInfo:
        """Update node properties.

        Args:
            node_id: Unique identifier of the node.
            label: Node label.
            properties: Properties to update.
            merge: If True, merge with existing properties. If False, replace all.

        Returns:
            Updated NodeInfo.

        Raises:
            NodeNotFoundError: If node does not exist.
            InvalidNodeLabelError: If label is invalid.
        """
        self._validate_label(label)

        # Add updated_at timestamp
        props = properties.copy()
        props[PropName.UPDATED_AT] = datetime.utcnow().isoformat()

        # Build SET clause
        if merge:
            set_clause = "SET n += $properties"
        else:
            set_clause = "SET n = $properties"

        query = f"""
        MATCH (n:{label} {{id: $id}})
        {set_clause}
        RETURN n
        """

        try:
            results = self._client.execute_write(
                query,
                parameters={"id": node_id, "properties": props},
            )

            if not results:
                raise NodeNotFoundError(node_id=node_id, label=label)

            node_data = results[0].get("n", {})

            logger.info(f"Updated {label} node '{node_id}'")

            return NodeInfo(
                id=node_id,
                label=label,
                properties=node_data,
            )

        except NodeNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update {label} node '{node_id}': {e}")
            raise

    # =========================================================================
    # Delete Operations
    # =========================================================================

    def delete_node(
        self,
        node_id: str,
        label: str,
        force: bool = False,
    ) -> DeleteResult:
        """Delete a node by ID.

        Args:
            node_id: Unique identifier of the node.
            label: Node label.
            force: If True, delete connected relationships first.

        Returns:
            DeleteResult with deletion status.

        Raises:
            NodeNotFoundError: If node does not exist.
            NodeDeletionError: If deletion fails.
            InvalidNodeLabelError: If label is invalid.
        """
        self._validate_label(label)

        # Check if node exists first
        if not self.node_exists(node_id, label):
            raise NodeNotFoundError(node_id=node_id, label=label)

        if force:
            # Delete relationships first, then node
            query = f"""
            MATCH (n:{label} {{id: $id}})
            DETACH DELETE n
            """
        else:
            # Just delete the node (will fail if relationships exist)
            query = f"""
            MATCH (n:{label} {{id: $id}})
            DELETE n
            """

        try:
            logger.info(f"Deleting {label} node '{node_id}' (force={force})")

            self._client.execute_write(
                query,
                parameters={"id": node_id},
            )

            logger.info(f"Successfully deleted {label} node '{node_id}'")

            return DeleteResult(deleted=True, deleted_count=1)

        except Exception as e:
            error_msg = str(e)
            if "still has relationships" in error_msg.lower():
                raise NodeDeletionError(
                    node_id=node_id,
                    label=label,
                    reason="Node has connected relationships. Use force=True to delete.",
                )
            logger.error(f"Failed to delete {label} node '{node_id}': {e}")
            raise NodeDeletionError(node_id=node_id, label=label, reason=error_msg)

    def delete_nodes_by_filter(
        self,
        label: str,
        filters: dict[str, Any],
        force: bool = False,
    ) -> DeleteResult:
        """Delete nodes matching filter conditions.

        Args:
            label: Node label.
            filters: Property filters to match nodes.
            force: If True, delete connected relationships first.

        Returns:
            DeleteResult with deletion count.

        Raises:
            InvalidNodeLabelError: If label is invalid.
            NodeDeletionError: If deletion fails.
        """
        self._validate_label(label)

        # Build WHERE clause from filters
        conditions = []
        params: dict[str, Any] = {}
        for key, value in filters.items():
            param_key = f"filter_{key}"
            conditions.append(f"n.{key} = ${param_key}")
            params[param_key] = value

        where_clause = f"WHERE {' AND '.join(conditions)}"

        if force:
            query = f"""
            MATCH (n:{label})
            {where_clause}
            WITH n, count(n) AS node_count
            DETACH DELETE n
            RETURN node_count
            """
        else:
            query = f"""
            MATCH (n:{label})
            {where_clause}
            WITH n, count(n) AS node_count
            DELETE n
            RETURN node_count
            """

        try:
            logger.info(
                f"Deleting {label} nodes with filters: {filters} (force={force})"
            )

            results = self._client.execute_write(query, parameters=params)

            deleted_count = 0
            if results:
                deleted_count = results[0].get("node_count", 0)

            logger.info(f"Successfully deleted {deleted_count} {label} nodes")

            return DeleteResult(deleted=True, deleted_count=deleted_count)

        except Exception as e:
            logger.error(f"Failed to delete {label} nodes by filter: {e}")
            raise NodeDeletionError(
                node_id="",
                label=label,
                reason=str(e),
            )

    def delete_all_nodes(
        self,
        label: str,
        force: bool = True,
    ) -> DeleteResult:
        """Delete all nodes of a given label.

        WARNING: This is a destructive operation. Use with caution.

        Args:
            label: Node label.
            force: If True, delete connected relationships first.

        Returns:
            DeleteResult with deletion count.
        """
        self._validate_label(label)

        if force:
            query = f"""
            MATCH (n:{label})
            WITH n, count(n) AS node_count
            DETACH DELETE n
            RETURN node_count
            """
        else:
            query = f"""
            MATCH (n:{label})
            WITH n, count(n) AS node_count
            DELETE n
            RETURN node_count
            """

        try:
            logger.warning(f"Deleting ALL {label} nodes (force={force})")

            results = self._client.execute_write(query)

            deleted_count = 0
            if results:
                deleted_count = results[0].get("node_count", 0)

            logger.info(f"Successfully deleted {deleted_count} {label} nodes")

            return DeleteResult(deleted=True, deleted_count=deleted_count)

        except Exception as e:
            logger.error(f"Failed to delete all {label} nodes: {e}")
            raise NodeDeletionError(
                node_id="",
                label=label,
                reason=str(e),
            )

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def create_document_node(
        self,
        document_id: str,
        title: str,
        source: str = "",
        doc_type: str = "",
        status: str = "active",
        **extra_properties: Any,
    ) -> NodeCreationResult:
        """Create a Document node with standard properties.

        Args:
            document_id: Unique document identifier.
            title: Document title.
            source: Document source.
            doc_type: Document type.
            status: Document status.
            **extra_properties: Additional properties.

        Returns:
            NodeCreationResult with created node.
        """
        properties = {
            PropName.ID: document_id,
            PropName.TITLE: title,
            PropName.SOURCE: source,
            PropName.DOC_TYPE: doc_type,
            PropName.STATUS: status,
            **extra_properties,
        }
        return self.create_node(NodeLabel.DOCUMENT.value, properties, merge=True)

    def create_chunk_node(
        self,
        chunk_id: str,
        text: str,
        document_id: str,
        chunk_index: int,
        page_number: int | None = None,
        start_char: int | None = None,
        end_char: int | None = None,
        **extra_properties: Any,
    ) -> NodeCreationResult:
        """Create a Chunk node with standard properties.

        Args:
            chunk_id: Unique chunk identifier.
            text: Chunk text content.
            document_id: Parent document ID.
            chunk_index: Index of chunk in document.
            page_number: Page number (optional).
            start_char: Start character position (optional).
            end_char: End character position (optional).
            **extra_properties: Additional properties.

        Returns:
            NodeCreationResult with created node.
        """
        properties = {
            PropName.ID: chunk_id,
            PropName.TEXT: text,
            PropName.DOCUMENT_ID: document_id,
            PropName.CHUNK_INDEX: chunk_index,
            **extra_properties,
        }
        if page_number is not None:
            properties[PropName.PAGE_NUMBER] = page_number
        if start_char is not None:
            properties[PropName.START_CHAR] = start_char
        if end_char is not None:
            properties[PropName.END_CHAR] = end_char
        return self.create_node(NodeLabel.CHUNK.value, properties, merge=True)

    def create_entity_node(
        self,
        entity_id: str,
        name: str,
        entity_type: str,
        description: str = "",
        confidence: float = 1.0,
        **extra_properties: Any,
    ) -> NodeCreationResult:
        """Create an Entity node with standard properties.

        Args:
            entity_id: Unique entity identifier.
            name: Entity name.
            entity_type: Entity type (person, organization, etc.).
            description: Entity description.
            confidence: Extraction confidence (0.0 to 1.0).
            **extra_properties: Additional properties.

        Returns:
            NodeCreationResult with created node.
        """
        properties = {
            PropName.ID: entity_id,
            PropName.NAME: name,
            PropName.ENTITY_TYPE: entity_type,
            PropName.DESCRIPTION: description,
            PropName.CONFIDENCE: confidence,
            **extra_properties,
        }
        return self.create_node(NodeLabel.ENTITY.value, properties)

    def create_concept_node(
        self,
        concept_id: str,
        name: str,
        description: str = "",
        category: str = "",
        **extra_properties: Any,
    ) -> NodeCreationResult:
        """Create a Concept node with standard properties.

        Args:
            concept_id: Unique concept identifier.
            name: Concept name.
            description: Concept description.
            category: Concept category.
            **extra_properties: Additional properties.

        Returns:
            NodeCreationResult with created node.
        """
        properties = {
            PropName.ID: concept_id,
            PropName.NAME: name,
            PropName.DESCRIPTION: description,
            PropName.CATEGORY: category,
            **extra_properties,
        }
        return self.create_node(NodeLabel.CONCEPT.value, properties)

    def create_user_node(
        self,
        user_id: str,
        username: str,
        email: str = "",
        **extra_properties: Any,
    ) -> NodeCreationResult:
        """Create a User node with standard properties.

        Args:
            user_id: Unique user identifier (should match PostgreSQL user ID).
            username: Username.
            email: User email.
            **extra_properties: Additional properties.

        Returns:
            NodeCreationResult with created node.
        """
        properties = {
            PropName.ID: user_id,
            "username": username,
            "email": email,
            **extra_properties,
        }
        return self.create_node(NodeLabel.USER.value, properties)
