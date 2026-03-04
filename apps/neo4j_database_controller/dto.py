"""
Data Transfer Objects (DTOs) for Neo4j database controller.

This module defines all dataclasses used for request and response objects
in the Neo4j database controller API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# =============================================================================
# Request DTOs
# =============================================================================


@dataclass(frozen=True)
class CreateNodeRequest:
    """Request to create a new node.

    Attributes:
        label: Node label (Document, Chunk, Entity, Concept, User).
        properties: Dictionary of node properties.
            Must include 'id' as unique identifier.
    """

    label: str
    properties: dict[str, Any]


@dataclass(frozen=True)
class CreateNodesBatchRequest:
    """Request to batch create nodes.

    Attributes:
        label: Node label for all nodes in the batch.
        nodes: List of property dictionaries, one per node.
            Each dictionary must include 'id' as unique identifier.
    """

    label: str
    nodes: list[dict[str, Any]]


@dataclass(frozen=True)
class CreateRelationshipRequest:
    """Request to create a new relationship.

    Attributes:
        rel_type: Relationship type (CONTAINS, MENTIONS, RELATED_TO, etc.).
        from_node_id: ID of the source node.
        from_node_label: Label of the source node.
        to_node_id: ID of the target node.
        to_node_label: Label of the target node.
        properties: Optional dictionary of relationship properties.
    """

    rel_type: str
    from_node_id: str
    from_node_label: str
    to_node_id: str
    to_node_label: str
    properties: dict[str, Any] | None = None


@dataclass(frozen=True)
class CreateRelationshipsBatchRequest:
    """Request to batch create relationships.

    Attributes:
        relationships: List of CreateRelationshipRequest objects.
    """

    relationships: list[CreateRelationshipRequest]


@dataclass(frozen=True)
class FindPathRequest:
    """Request to find paths between nodes.

    Attributes:
        from_node_id: ID of the source node.
        from_node_label: Label of the source node.
        to_node_id: ID of the target node.
        to_node_label: Label of the target node.
        max_depth: Maximum traversal depth (default: 5).
        relationship_types: Optional list of relationship types to follow.
            If None, all relationship types are considered.
    """

    from_node_id: str
    from_node_label: str
    to_node_id: str
    to_node_label: str
    max_depth: int = 5
    relationship_types: list[str] | None = None


@dataclass(frozen=True)
class GetEntityContextRequest:
    """Request to get entity context for RAG.

    Attributes:
        entity_id: ID of the entity node.
        include_chunks: Whether to include chunks that mention the entity.
        include_related_entities: Whether to include related entities.
        max_depth: Maximum depth for entity relationship traversal.
    """

    entity_id: str
    include_chunks: bool = True
    include_related_entities: bool = True
    max_depth: int = 2


@dataclass(frozen=True)
class GetDocumentGraphRequest:
    """Request to get document subgraph.

    Attributes:
        document_id: ID of the document node.
        include_chunks: Whether to include chunk nodes.
        include_entities: Whether to include entity nodes.
        include_concepts: Whether to include concept nodes.
    """

    document_id: str
    include_chunks: bool = True
    include_entities: bool = True
    include_concepts: bool = True


@dataclass(frozen=True)
class SearchEntitiesRequest:
    """Request to search entities by name.

    Attributes:
        name: Entity name or partial name to search for.
        entity_type: Optional entity type filter.
        limit: Maximum number of results.
        case_sensitive: Whether search is case-sensitive.
    """

    name: str
    entity_type: str | None = None
    limit: int = 10
    case_sensitive: bool = False


@dataclass(frozen=True)
class UpdateNodeRequest:
    """Request to update node properties.

    Attributes:
        node_id: ID of the node to update.
        label: Label of the node.
        properties: Dictionary of properties to update.
            Only specified properties will be updated.
    """

    node_id: str
    label: str
    properties: dict[str, Any]


@dataclass(frozen=True)
class DeleteNodeRequest:
    """Request to delete a node.

    Attributes:
        node_id: ID of the node to delete.
        label: Label of the node.
        force: If True, delete connected relationships first.
    """

    node_id: str
    label: str
    force: bool = False


@dataclass(frozen=True)
class GetNodeNeighborsRequest:
    """Request to get node neighbors.

    Attributes:
        node_id: ID of the node.
        label: Label of the node.
        direction: Relationship direction (OUTGOING, INCOMING, BOTH).
        relationship_types: Optional list of relationship types to follow.
        limit: Maximum number of neighbors to return.
    """

    node_id: str
    label: str
    direction: str = "BOTH"
    relationship_types: list[str] | None = None
    limit: int = 100


# =============================================================================
# Response DTOs
# =============================================================================


@dataclass(frozen=True)
class NodeInfo:
    """Information about a node.

    Attributes:
        id: Unique identifier of the node.
        label: Node label.
        properties: Dictionary of all node properties.
    """

    id: str
    label: str
    properties: dict[str, Any]

    def get_property(self, key: str, default: Any = None) -> Any:
        """Get a property value by key.

        Args:
            key: Property name.
            default: Default value if property not found.

        Returns:
            Property value or default.
        """
        return self.properties.get(key, default)


@dataclass(frozen=True)
class RelationshipInfo:
    """Information about a relationship.

    Attributes:
        id: Neo4j internal relationship ID.
        rel_type: Relationship type.
        from_node_id: ID of the source node.
        from_node_label: Label of the source node.
        to_node_id: ID of the target node.
        to_node_label: Label of the target node.
        properties: Dictionary of relationship properties.
    """

    id: int
    rel_type: str
    from_node_id: str
    from_node_label: str
    to_node_id: str
    to_node_label: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PathInfo:
    """Information about a graph path.

    Attributes:
        nodes: List of nodes in the path, in order.
        relationships: List of relationships in the path, in order.
        length: Number of relationships (hops) in the path.
    """

    nodes: list[NodeInfo]
    relationships: list[RelationshipInfo]
    length: int


@dataclass(frozen=True)
class EntityContext:
    """Entity context for RAG.

    This provides comprehensive context about an entity for RAG queries.

    Attributes:
        entity: The entity node.
        mentioned_in: List of chunk nodes that mention this entity.
        related_entities: List of (entity, relation_type) tuples.
        concepts: List of related concept nodes.
    """

    entity: NodeInfo
    mentioned_in: list[NodeInfo] = field(default_factory=list)
    related_entities: list[tuple[NodeInfo, str]] = field(default_factory=list)
    concepts: list[NodeInfo] = field(default_factory=list)


@dataclass(frozen=True)
class DocumentGraph:
    """Document subgraph for RAG.

    Attributes:
        document: The document node.
        chunks: List of chunk nodes.
        entities: List of entity nodes mentioned in the document.
        concepts: List of concept nodes related to the document.
        relationships: List of all relationships in the subgraph.
    """

    document: NodeInfo
    chunks: list[NodeInfo] = field(default_factory=list)
    entities: list[NodeInfo] = field(default_factory=list)
    concepts: list[NodeInfo] = field(default_factory=list)
    relationships: list[RelationshipInfo] = field(default_factory=list)


@dataclass(frozen=True)
class NodeCreationResult:
    """Result of node creation.

    Attributes:
        node: The created node info.
        created: Whether the node was created (vs already existed).
    """

    node: NodeInfo
    created: bool = True


@dataclass(frozen=True)
class BatchNodeCreationResult:
    """Result of batch node creation.

    Attributes:
        nodes: List of created node info.
        created_count: Number of nodes created.
        failed_count: Number of nodes that failed to create.
    """

    nodes: list[NodeInfo]
    created_count: int
    failed_count: int = 0


@dataclass(frozen=True)
class RelationshipCreationResult:
    """Result of relationship creation.

    Attributes:
        relationship: The created relationship info.
        created: Whether the relationship was created (vs already existed).
    """

    relationship: RelationshipInfo
    created: bool = True


@dataclass(frozen=True)
class BatchRelationshipCreationResult:
    """Result of batch relationship creation.

    Attributes:
        relationships: List of created relationship info.
        created_count: Number of relationships created.
        failed_count: Number of relationships that failed to create.
    """

    relationships: list[RelationshipInfo]
    created_count: int
    failed_count: int = 0


@dataclass(frozen=True)
class DeleteResult:
    """Result of delete operation.

    Attributes:
        deleted: Whether the deletion was successful.
        deleted_count: Number of items deleted.
    """

    deleted: bool
    deleted_count: int = 0


@dataclass(frozen=True)
class HealthCheckResult:
    """Result of health check.

    Attributes:
        status: Health status ("healthy" or "unhealthy").
        connected: Whether connection is established.
        server_info: Server version and edition info.
        latency_ms: Connection latency in milliseconds.
        error: Error message if unhealthy.
    """

    status: str
    connected: bool
    server_info: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    error: str | None = None


# =============================================================================
# Helper Functions
# =============================================================================


def create_node_request(
    label: str,
    node_id: str,
    **properties: Any,
) -> CreateNodeRequest:
    """Create a CreateNodeRequest with ID included in properties.

    Args:
        label: Node label.
        node_id: Unique identifier for the node.
        **properties: Additional node properties.

    Returns:
        CreateNodeRequest instance.
    """
    props = {"id": node_id, **properties}
    return CreateNodeRequest(label=label, properties=props)


def create_relationship_request(
    rel_type: str,
    from_node_id: str,
    from_node_label: str,
    to_node_id: str,
    to_node_label: str,
    **properties: Any,
) -> CreateRelationshipRequest:
    """Create a CreateRelationshipRequest with optional properties.

    Args:
        rel_type: Relationship type.
        from_node_id: Source node ID.
        from_node_label: Source node label.
        to_node_id: Target node ID.
        to_node_label: Target node label.
        **properties: Relationship properties.

    Returns:
        CreateRelationshipRequest instance.
    """
    return CreateRelationshipRequest(
        rel_type=rel_type,
        from_node_id=from_node_id,
        from_node_label=from_node_label,
        to_node_id=to_node_id,
        to_node_label=to_node_label,
        properties=properties if properties else None,
    )


def node_info_from_record(
    record: dict[str, Any],
    label: str,
) -> NodeInfo:
    """Create NodeInfo from a Neo4j record.

    Args:
        record: Dictionary containing node properties.
        label: Node label.

    Returns:
        NodeInfo instance.
    """
    node_id = record.get("id", record.get("ID", ""))
    return NodeInfo(
        id=str(node_id),
        label=label,
        properties=record,
    )
