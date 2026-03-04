"""
DRF Serializers for Neo4j API.

This module contains serializers for validating requests and
formatting responses for Neo4j operations.
"""

from rest_framework import serializers

from apps.neo4j_database_controller.constants import (
    VALID_NODE_LABELS,
    VALID_REL_TYPES,
)


# =============================================================================
# Node Serializers
# =============================================================================


class NodePropertiesSerializer(serializers.Serializer):
    """Serializer for node properties (flexible)."""

    id = serializers.CharField(required=True, max_length=100)
    created_at = serializers.DateTimeField(required=False, read_only=True)
    updated_at = serializers.DateTimeField(required=False, read_only=True)

    def validate(self, attrs):
        """Allow additional properties."""
        return attrs


class CreateNodeSerializer(serializers.Serializer):
    """Serializer for creating a node."""

    label = serializers.ChoiceField(
        choices=list(VALID_NODE_LABELS),
        help_text="Node label (Document, Chunk, Entity, Concept, User)",
    )
    properties = serializers.DictField(
        help_text="Node properties",
        required=True,
    )
    merge = serializers.BooleanField(
        default=False,
        help_text="If True, use MERGE for upsert behavior",
    )


class NodeResponseSerializer(serializers.Serializer):
    """Serializer for node response."""

    id = serializers.CharField()
    label = serializers.CharField()
    properties = serializers.DictField()


class BatchCreateNodesSerializer(serializers.Serializer):
    """Serializer for batch creating nodes."""

    label = serializers.ChoiceField(choices=list(VALID_NODE_LABELS))
    nodes = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
        help_text="List of node property dictionaries",
    )
    batch_size = serializers.IntegerField(default=1000, min_value=1)


class BatchNodeResponseSerializer(serializers.Serializer):
    """Serializer for batch node creation response."""

    nodes = NodeResponseSerializer(many=True)
    created_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()


class UpdateNodeSerializer(serializers.Serializer):
    """Serializer for updating a node."""

    properties = serializers.DictField(required=True)
    merge = serializers.BooleanField(
        default=True,
        help_text="If True, merge with existing properties",
    )


class NodeFilterSerializer(serializers.Serializer):
    """Serializer for node query filters."""

    filters = serializers.DictField(required=False, default=dict)
    order_by = serializers.CharField(required=False, default="")
    order_desc = serializers.BooleanField(default=False)
    skip = serializers.IntegerField(default=0, min_value=0)
    limit = serializers.IntegerField(default=100, min_value=1, max_value=1000)


class NodeListResponseSerializer(serializers.Serializer):
    """Serializer for node list response."""

    nodes = NodeResponseSerializer(many=True)
    count = serializers.IntegerField()
    total = serializers.IntegerField(required=False)


# =============================================================================
# Relationship Serializers
# =============================================================================


class CreateRelationshipSerializer(serializers.Serializer):
    """Serializer for creating a relationship."""

    rel_type = serializers.ChoiceField(
        choices=list(VALID_REL_TYPES),
        help_text="Relationship type (CONTAINS, MENTIONS, RELATED_TO, etc.)",
    )
    from_node_id = serializers.CharField(help_text="Source node ID")
    from_node_label = serializers.ChoiceField(
        choices=list(VALID_NODE_LABELS),
        help_text="Source node label",
    )
    to_node_id = serializers.CharField(help_text="Target node ID")
    to_node_label = serializers.ChoiceField(
        choices=list(VALID_NODE_LABELS),
        help_text="Target node label",
    )
    properties = serializers.DictField(required=False, default=dict)
    merge = serializers.BooleanField(
        default=False,
        help_text="If True, use MERGE for upsert behavior",
    )


class RelationshipResponseSerializer(serializers.Serializer):
    """Serializer for relationship response."""

    id = serializers.IntegerField()
    rel_type = serializers.CharField()
    from_node_id = serializers.CharField()
    from_node_label = serializers.CharField()
    to_node_id = serializers.CharField()
    to_node_label = serializers.CharField()
    properties = serializers.DictField()


class BatchCreateRelationshipsSerializer(serializers.Serializer):
    """Serializer for batch creating relationships."""

    relationships = CreateRelationshipSerializer(many=True, allow_empty=False)
    batch_size = serializers.IntegerField(default=1000, min_value=1)


class BatchRelationshipResponseSerializer(serializers.Serializer):
    """Serializer for batch relationship creation response."""

    relationships = RelationshipResponseSerializer(many=True)
    created_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()


class UpdateRelationshipSerializer(serializers.Serializer):
    """Serializer for updating a relationship."""

    properties = serializers.DictField(required=True)
    merge = serializers.BooleanField(default=True)


class RelationshipFilterSerializer(serializers.Serializer):
    """Serializer for relationship query filters."""

    node_id = serializers.CharField(required=False)
    node_label = serializers.ChoiceField(
        choices=list(VALID_NODE_LABELS),
        required=False,
    )
    direction = serializers.ChoiceField(
        choices=["OUTGOING", "INCOMING", "BOTH"],
        default="BOTH",
    )
    rel_type = serializers.ChoiceField(
        choices=list(VALID_REL_TYPES),
        required=False,
    )
    limit = serializers.IntegerField(default=100, min_value=1, max_value=1000)


# =============================================================================
# Query Serializers
# =============================================================================


class FindPathSerializer(serializers.Serializer):
    """Serializer for path finding queries."""

    from_node_id = serializers.CharField()
    from_node_label = serializers.ChoiceField(choices=list(VALID_NODE_LABELS))
    to_node_id = serializers.CharField()
    to_node_label = serializers.ChoiceField(choices=list(VALID_NODE_LABELS))
    max_depth = serializers.IntegerField(default=5, min_value=1, max_value=10)
    relationship_types = serializers.ListField(
        child=serializers.ChoiceField(choices=list(VALID_REL_TYPES)),
        required=False,
        allow_empty=True,
    )
    limit = serializers.IntegerField(default=10, min_value=1, max_value=100)


class PathNodeSerializer(serializers.Serializer):
    """Serializer for a node in a path."""

    id = serializers.CharField()
    label = serializers.CharField()
    properties = serializers.DictField()


class PathRelationshipSerializer(serializers.Serializer):
    """Serializer for a relationship in a path."""

    id = serializers.IntegerField()
    rel_type = serializers.CharField()
    from_node_id = serializers.CharField()
    to_node_id = serializers.CharField()
    properties = serializers.DictField()


class PathResponseSerializer(serializers.Serializer):
    """Serializer for a path response."""

    nodes = PathNodeSerializer(many=True)
    relationships = PathRelationshipSerializer(many=True)
    length = serializers.IntegerField()


class NeighborQuerySerializer(serializers.Serializer):
    """Serializer for neighbor query parameters."""

    direction = serializers.ChoiceField(
        choices=["OUTGOING", "INCOMING", "BOTH"],
        default="BOTH",
    )
    relationship_types = serializers.ListField(
        child=serializers.ChoiceField(choices=list(VALID_REL_TYPES)),
        required=False,
        allow_empty=True,
    )
    limit = serializers.IntegerField(default=100, min_value=1, max_value=1000)


class EntityContextQuerySerializer(serializers.Serializer):
    """Serializer for entity context query parameters."""

    include_chunks = serializers.BooleanField(default=True)
    include_related_entities = serializers.BooleanField(default=True)
    include_concepts = serializers.BooleanField(default=True)
    max_depth = serializers.IntegerField(default=2, min_value=1, max_value=5)
    chunk_limit = serializers.IntegerField(default=10, min_value=1, max_value=100)
    entity_limit = serializers.IntegerField(default=10, min_value=1, max_value=50)


class EntityContextResponseSerializer(serializers.Serializer):
    """Serializer for entity context response."""

    entity = NodeResponseSerializer()
    mentioned_in = NodeResponseSerializer(many=True)
    related_entities = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of {entity: NodeInfo, relation_type: str}",
    )
    concepts = NodeResponseSerializer(many=True)


class DocumentGraphQuerySerializer(serializers.Serializer):
    """Serializer for document graph query parameters."""

    include_chunks = serializers.BooleanField(default=True)
    include_entities = serializers.BooleanField(default=True)
    include_concepts = serializers.BooleanField(default=True)
    chunk_limit = serializers.IntegerField(default=100, min_value=1, max_value=500)
    entity_limit = serializers.IntegerField(default=50, min_value=1, max_value=200)


class DocumentGraphResponseSerializer(serializers.Serializer):
    """Serializer for document graph response."""

    document = NodeResponseSerializer()
    chunks = NodeResponseSerializer(many=True)
    entities = NodeResponseSerializer(many=True)
    concepts = NodeResponseSerializer(many=True)
    relationships = RelationshipResponseSerializer(many=True)


class SearchEntitiesSerializer(serializers.Serializer):
    """Serializer for entity search."""

    name = serializers.CharField(
        max_length=200,
        help_text="Entity name or partial name to search",
    )
    entity_type = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional entity type filter",
    )
    limit = serializers.IntegerField(default=10, min_value=1, max_value=100)
    case_sensitive = serializers.BooleanField(default=False)


# =============================================================================
# Health Check Serializers
# =============================================================================


class HealthCheckResponseSerializer(serializers.Serializer):
    """Serializer for health check response."""

    status = serializers.CharField()
    connected = serializers.BooleanField()
    server_info = serializers.DictField(required=False)
    graph_stats = serializers.DictField(required=False)
    error = serializers.CharField(required=False)


# =============================================================================
# Delete Serializers
# =============================================================================


class DeleteResponseSerializer(serializers.Serializer):
    """Serializer for delete response."""

    deleted = serializers.BooleanField()
    deleted_count = serializers.IntegerField()


class DeleteNodeQuerySerializer(serializers.Serializer):
    """Serializer for delete node query parameters."""

    force = serializers.BooleanField(
        default=False,
        help_text="If True, delete connected relationships first",
    )


class DeleteRelationshipsQuerySerializer(serializers.Serializer):
    """Serializer for delete relationships by filter query parameters."""

    node_id = serializers.CharField(required=False)
    node_label = serializers.ChoiceField(
        choices=list(VALID_NODE_LABELS),
        required=False,
    )
    direction = serializers.ChoiceField(
        choices=["OUTGOING", "INCOMING", "BOTH"],
        default="BOTH",
    )
    rel_type = serializers.ChoiceField(
        choices=list(VALID_REL_TYPES),
        required=False,
    )
