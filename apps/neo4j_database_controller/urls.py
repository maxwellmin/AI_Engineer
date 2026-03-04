"""
URL routing for Neo4j API endpoints.

This module defines URL patterns for all Neo4j REST API endpoints.

URL Structure:
    /api/v1/neo4j/
    ├── health/                           # GET - Health check
    ├── nodes/
    │   ├── create/                       # POST - Create node
    │   ├── batch-create/                 # POST - Batch create nodes
    │   ├── {label}/{id}/                 # GET - Get node by ID
    │   ├── {label}/                      # GET - List nodes by label
    │   ├── {label}/{id}/update/          # PATCH - Update node
    │   └── {label}/{id}/delete/          # DELETE - Delete node
    ├── relationships/
    │   ├── create/                       # POST - Create relationship
    │   ├── batch-create/                 # POST - Batch create relationships
    │   ├── {id}/                         # GET - Get relationship by ID
    │   ├── from/{node_id}/               # GET - Get relationships from node
    │   ├── {id}/update/                  # PATCH - Update relationship
    │   └── {id}/delete/                  # DELETE - Delete relationship
    └── query/
        ├── path/shortest/                # POST - Find shortest path
        ├── path/all/                     # POST - Find all paths
        ├── neighbors/{label}/{id}/       # GET - Get node neighbors
        ├── entity-context/{id}/          # GET - Get entity context for RAG
        ├── document-graph/{id}/          # GET - Get document subgraph
        ├── search-entities/              # POST - Search entities by name
        ├── related-entities/{id}/        # GET - Find related entities
        └── chunks-by-entities/           # POST - Get chunks by entity names
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.neo4j_database_controller.views import (
    HealthViewSet,
    NodeViewSet,
    QueryViewSet,
    RelationshipViewSet,
)

# Create routers
router = DefaultRouter()

# Register ViewSets with custom routes
# Note: We use custom action URLs instead of standard router patterns
# for more control over the URL structure

# Node endpoints
node_list = NodeViewSet.as_view({
    "get": "list_by_label",
})

node_detail = NodeViewSet.as_view({
    "get": "retrieve",
})

node_create = NodeViewSet.as_view({
    "post": "create_node",
})

node_batch_create = NodeViewSet.as_view({
    "post": "batch_create",
})

node_update = NodeViewSet.as_view({
    "patch": "update_node",
})

node_delete = NodeViewSet.as_view({
    "delete": "delete_node",
})

# Relationship endpoints
relationship_detail = RelationshipViewSet.as_view({
    "get": "retrieve",
})

relationship_create = RelationshipViewSet.as_view({
    "post": "create_relationship",
})

relationship_batch_create = RelationshipViewSet.as_view({
    "post": "batch_create",
})

relationship_from_node = RelationshipViewSet.as_view({
    "get": "get_from_node",
})

relationship_update = RelationshipViewSet.as_view({
    "patch": "update_relationship",
})

relationship_delete = RelationshipViewSet.as_view({
    "delete": "delete_relationship",
})

relationship_delete_by_filter = RelationshipViewSet.as_view({
    "delete": "delete_by_filter",
})

# Query endpoints
query_shortest_path = QueryViewSet.as_view({
    "post": "shortest_path",
})

query_all_paths = QueryViewSet.as_view({
    "post": "all_paths",
})

query_neighbors = QueryViewSet.as_view({
    "get": "neighbors",
})

query_entity_context = QueryViewSet.as_view({
    "get": "entity_context",
})

query_document_graph = QueryViewSet.as_view({
    "get": "document_graph",
})

query_search_entities = QueryViewSet.as_view({
    "post": "search_entities",
})

query_related_entities = QueryViewSet.as_view({
    "get": "related_entities",
})

query_chunks_by_entities = QueryViewSet.as_view({
    "post": "chunks_by_entities",
})

# Health endpoints
health_list = HealthViewSet.as_view({
    "get": "list",
})

health_stats = HealthViewSet.as_view({
    "get": "stats",
})

health_init_schema = HealthViewSet.as_view({
    "post": "init_schema",
})

# URL patterns
urlpatterns = [
    # Health check
    path("health/", health_list, name="neo4j-health"),
    path("health/stats/", health_stats, name="neo4j-health-stats"),
    path("health/init-schema/", health_init_schema, name="neo4j-init-schema"),

    # Node endpoints
    # Note: Order matters - more specific patterns first
    path("nodes/create/", node_create, name="neo4j-node-create"),
    path("nodes/batch-create/", node_batch_create, name="neo4j-node-batch-create"),
    # Node operations with separate label and node_id parameters
    path("nodes/<str:label>/<str:node_id>/", node_detail, name="neo4j-node-detail"),
    path("nodes/<str:label>/<str:node_id>/update/", node_update, name="neo4j-node-update"),
    path("nodes/<str:label>/<str:node_id>/delete/", node_delete, name="neo4j-node-delete"),
    # Node listing by label (must come after specific patterns)
    path("nodes/<str:label>/", node_list, name="neo4j-node-list"),

    # Relationship endpoints
    path("relationships/create/", relationship_create, name="neo4j-relationship-create"),
    path("relationships/batch-create/", relationship_batch_create, name="neo4j-relationship-batch-create"),
    path("relationships/<int:pk>/", relationship_detail, name="neo4j-relationship-detail"),
    path("relationships/<int:pk>/update/", relationship_update, name="neo4j-relationship-update"),
    path("relationships/<int:pk>/delete/", relationship_delete, name="neo4j-relationship-delete"),
    path("relationships/from/<str:node_id>/", relationship_from_node, name="neo4j-relationship-from-node"),
    path("relationships/delete-by-filter/", relationship_delete_by_filter, name="neo4j-relationship-delete-by-filter"),

    # Query endpoints
    path("query/path/shortest/", query_shortest_path, name="neo4j-query-shortest-path"),
    path("query/path/all/", query_all_paths, name="neo4j-query-all-paths"),
    path("query/neighbors/<str:label>/<str:node_id>/", query_neighbors, name="neo4j-query-neighbors"),
    path("query/entity-context/<str:entity_id>/", query_entity_context, name="neo4j-query-entity-context"),
    path("query/document-graph/<str:document_id>/", query_document_graph, name="neo4j-query-document-graph"),
    path("query/search-entities/", query_search_entities, name="neo4j-query-search-entities"),
    path("query/related-entities/<str:entity_id>/", query_related_entities, name="neo4j-query-related-entities"),
    path("query/chunks-by-entities/", query_chunks_by_entities, name="neo4j-query-chunks-by-entities"),
]
