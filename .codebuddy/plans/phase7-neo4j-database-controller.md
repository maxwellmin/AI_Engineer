# Phase 7: Neo4j Database Controller Implementation Plan

## Overview

Implement Neo4j database controller module for melon RAG project, providing graph database operations including node management, relationship management, and knowledge graph query functionality.

## Status: COMPLETED

## Current Progress

- Submodule 7.1: Infrastructure Setup ✅ COMPLETED (2026-03-04)
- Submodule 7.2: Node Management ✅ COMPLETED (2026-03-04)
- Submodule 7.3: Relationship Management ✅ COMPLETED (2026-03-04)
- Submodule 7.4: Graph Query Operations ✅ COMPLETED (2026-03-04)
- Submodule 7.5: Service Layer & Integration ✅ COMPLETED (2026-03-04)
- Submodule 7.6: API Views Layer ✅ COMPLETED (2026-03-04)
- Submodule 7.7: Testing & Documentation ✅ COMPLETED (2026-03-04)
- Submodule 7.8: Manual Test Generation ✅ COMPLETED (2026-03-04)

## Dependencies

- Phase 2: Basic Setup ✅
- Phase 3: User Management Module ✅
- Phase 4: Document Parser Module ✅
- Phase 5: Object Storage Controller ✅
- Phase 6: Milvus Database Controller ✅ (Reference implementation)

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Neo4j SDK | neo4j-driver (Official Python Driver) | Official driver with async support, connection pooling |
| Connection Strategy | Singleton Driver | Consistent with Milvus implementation, connection reuse |
| Node Types | Document, Chunk, Entity, Concept, User | Core node types for knowledge graph |
| Relationship Types | CONTAINS, MENTIONS, RELATED_TO, ABOUT, ASKED, ANSWERED_BY | Core relationships for RAG context |
| Query Focus | Knowledge Graph Specialized | Entity relationship reasoning, context association queries |
| API Layer | REST API + Service Layer | Consistent with Milvus, support curl/Postman testing |
| Entity Extraction | Reserved Interface | Implement in future phases with LLM integration |

---

## Architecture Design

### Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    External Modules                          │
│  (documents_parser, embedding_engine, rag_processing)       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Neo4jService (Facade)                     │
│  - High-level API for all Neo4j operations                  │
│  - Business logic coordination                               │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┬───────────────┐
          ▼               ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│    Node      │ │ Relationship │ │   Graph      │ │    Query     │
│   Manager    │ │   Manager    │ │   Manager    │ │   Manager    │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │                │
       └────────────────┴────────────────┴────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    Neo4jClient (Singleton)                   │
│  - Connection management with driver                         │
│  - Session management                                        │
│  - Transaction support                                       │
└─────────────────────────────────────────────────────────────┘
```

### Graph Schema Design

Based on architecture.md reference:

#### Node Types

| Node Label | Properties | Description |
|------------|------------|-------------|
| **Document** | id (UUID), title, source, created_at, updated_at, doc_type, status | Document metadata |
| **Chunk** | id (UUID), text, chunk_index, page_number, start_char, end_char | Document chunk |
| **Entity** | id (UUID), name, entity_type, description, confidence | Extracted entity (person, org, location, etc.) |
| **Concept** | id (UUID), name, description, category | Concept/topic node |
| **User** | id (UUID), username, email | User node (link to PostgreSQL) |

#### Relationship Types

| Relationship | From → To | Properties | Description |
|--------------|-----------|------------|-------------|
| **CONTAINS** | Document → Chunk | order, created_at | Document contains chunks |
| **MENTIONS** | Chunk → Entity | confidence, count, created_at | Chunk mentions entity |
| **RELATED_TO** | Entity → Entity | relation_type, confidence, created_at | Entity relationships |
| **ABOUT** | Document → Concept | confidence, created_at | Document about concept |
| **ASKED** | User → Question | created_at | User asked question |
| **ANSWERED_BY** | Question → Chunk | confidence, created_at | Question answered by chunk |

#### Indexes and Constraints

```cypher
// Unique constraints (automatically create indexes)
CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT concept_id_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE;

// Additional indexes for common queries
CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.entity_type);
CREATE INDEX concept_name_index IF NOT EXISTS FOR (c:Concept) ON (c.name);
CREATE INDEX chunk_document_id_index IF NOT EXISTS FOR (c:Chunk) ON (c.document_id);
```

---

## Submodule Breakdown

### Submodule 7.1: Infrastructure Setup

**Goal**: Establish foundation for Neo4j operations

**Status**: ✅ COMPLETED (2026-03-04)

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 1.1 | Add neo4j-driver dependency | Add neo4j-driver to pyproject.toml | 0.5h | ✅ Completed |
| 1.2 | Create constants | Define node labels, relationship types, property names | 1h | ✅ Completed |
| 1.3 | Create exceptions | Custom exception classes for Neo4j operations | 1h | ✅ Completed |
| 1.4 | Create DTOs | Dataclasses for requests and responses | 2h | ✅ Completed |
| 1.5 | Implement Neo4jClient | Singleton client with driver management | 3h | ✅ Completed |
| 1.6 | Update settings | Verify NEO4J_CONFIG in settings | 0.5h | ✅ Completed |
| 1.7 | Update environment | Add NEO4J_* variables to .env file | 0.5h | ✅ Completed |

**Acceptance Criteria**:
- [x] neo4j-driver added to dependencies
- [x] Constants file with all node labels, relationship types
- [x] Exception classes for connection, query, constraint errors
- [x] DTOs for all request/response types
- [x] Neo4jClient singleton with connection management
- [x] Settings updated with Neo4j configuration
- [x] Environment variables documented

**Files Created**:
- `apps/neo4j_database_controller/constants.py`
- `apps/neo4j_database_controller/exceptions.py`
- `apps/neo4j_database_controller/dto.py`
- `apps/neo4j_database_controller/client/__init__.py`
- `apps/neo4j_database_controller/client/neo4j_client.py`
- `apps/neo4j_database_controller/managers/__init__.py`
- `apps/neo4j_database_controller/services/__init__.py`
- `apps/neo4j_database_controller/schemas/__init__.py`
- `apps/neo4j_database_controller/schemas/graph_schema.py`

**Files Modified**:
- `pyproject.toml` - Added neo4j dependency
- `config/settings/base.py` - Enhanced NEO4J_CONFIG
- `env/.env.local` - Added NEO4J_DATABASE and optional settings

---

### Submodule 7.2: Node Management

**Goal**: Implement node CRUD operations

**Status**: ✅ COMPLETED (2026-03-04)

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 2.1 | Create NodeManager class | Manager for all node operations | 1h | ✅ Completed |
| 2.2 | Implement create_node | Create single node with properties | 2h | ✅ Completed |
| 2.3 | Implement create_nodes_batch | Batch create nodes | 2h | ✅ Completed |
| 2.4 | Implement get_node_by_id | Retrieve node by ID | 1h | ✅ Completed |
| 2.5 | Implement get_nodes_by_label | Query nodes by label with filters | 2h | ✅ Completed |
| 2.6 | Implement update_node | Update node properties | 2h | ✅ Completed |
| 2.7 | Implement delete_node | Delete node by ID | 1h | ✅ Completed |
| 2.8 | Implement delete_nodes_by_filter | Delete nodes matching filter | 1.5h | ✅ Completed |

**Acceptance Criteria**:
- [x] NodeManager with all CRUD operations
- [x] Support for all 5 node types (Document, Chunk, Entity, Concept, User)
- [x] Batch operations for performance
- [x] Proper error handling and logging
- [ ] Unit tests for all operations (to be implemented in 7.7)

**Files Created**:
- `apps/neo4j_database_controller/managers/node_manager.py`

**Key Features**:
- `create_node()`: Create single node with merge option for upsert
- `create_nodes_batch()`: Batch creation using UNWIND for performance
- `get_node_by_id()`: Retrieve node by ID
- `get_node_by_id_or_raise()`: Retrieve or raise NodeNotFoundError
- `get_nodes_by_label()`: Query with filters, pagination, ordering
- `count_nodes()`: Count nodes with optional filters
- `node_exists()`: Check node existence
- `update_node()`: Update with merge/replace options
- `delete_node()`: Delete with force option for relationships
- `delete_nodes_by_filter()`: Delete by filter conditions
- `delete_all_nodes()`: Delete all nodes of a label (destructive)
- Convenience methods: `create_document_node()`, `create_chunk_node()`, `create_entity_node()`, `create_concept_node()`, `create_user_node()`

---

### Submodule 7.3: Relationship Management

**Goal**: Implement relationship CRUD operations

**Status**: ✅ COMPLETED (2026-03-04)

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 3.1 | Create RelationshipManager class | Manager for all relationship operations | 1h | ✅ Completed |
| 3.2 | Implement create_relationship | Create single relationship | 2h | ✅ Completed |
| 3.3 | Implement create_relationships_batch | Batch create relationships | 2h | ✅ Completed |
| 3.4 | Implement get_relationship_by_id | Retrieve relationship by ID | 1h | ✅ Completed |
| 3.5 | Implement get_relationships | Query relationships with filters | 2h | ✅ Completed |
| 3.6 | Implement update_relationship | Update relationship properties | 1.5h | ✅ Completed |
| 3.7 | Implement delete_relationship | Delete relationship by ID | 1h | ✅ Completed |
| 3.8 | Implement delete_relationships_by_filter | Delete relationships matching filter | 1.5h | ✅ Completed |

**Acceptance Criteria**:
- [x] RelationshipManager with all CRUD operations
- [x] Support for all 6 relationship types
- [x] Batch operations for performance
- [x] Proper error handling and logging
- [ ] Unit tests for all operations (to be implemented in 7.7)

**Files Created**:
- `apps/neo4j_database_controller/managers/relationship_manager.py`

**Key Features**:
- `create_relationship()`: Create relationship with merge option
- `create_relationships_batch()`: Batch creation using UNWIND
- `get_relationship_by_id()`: Retrieve by Neo4j internal ID
- `get_relationship_by_id_or_raise()`: Retrieve or raise error
- `get_relationships()`: Query by node, direction, type
- `get_outgoing_relationships()`: Get outgoing relationships
- `get_incoming_relationships()`: Get incoming relationships
- `count_relationships()`: Count with filters
- `relationship_exists()`: Check existence
- `update_relationship()`: Update properties
- `delete_relationship()`: Delete by ID
- `delete_relationships_by_filter()`: Delete by node/direction/type
- `delete_all_relationships_of_type()`: Delete all of type (destructive)
- Convenience methods: `create_contains_relationship()`, `create_mentions_relationship()`, `create_related_to_relationship()`, `create_about_relationship()`

---

### Submodule 7.4: Graph Query Operations

**Goal**: Implement knowledge graph specialized query functionality

**Status**: ✅ COMPLETED (2026-03-04)

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 4.1 | Create QueryManager class | Manager for graph queries | 1h | ✅ Completed |
| 4.2 | Implement find_shortest_path | Find shortest path between two nodes | 2h | ✅ Completed |
| 4.3 | Implement find_all_paths | Find all paths up to depth N | 2h | ✅ Completed |
| 4.4 | Implement get_node_neighbors | Get neighboring nodes with relationships | 1.5h | ✅ Completed |
| 4.5 | Implement get_entity_context | Get entity context for RAG (mentioned chunks, related entities) | 3h | ✅ Completed |
| 4.6 | Implement get_document_graph | Get document subgraph (chunks, entities, concepts) | 2.5h | ✅ Completed |
| 4.7 | Implement find_related_entities | Find entities related to given entity | 2h | ✅ Completed |
| 4.8 | Implement search_by_entity_name | Full-text search on entity names | 1.5h | ✅ Completed |

**Acceptance Criteria**:
- [x] QueryManager with specialized graph queries
- [x] Efficient path finding algorithms
- [x] RAG-optimized context retrieval
- [x] Support for graph traversal patterns
- [ ] Unit tests for all query operations (to be implemented in 7.7)

**Files Created**:
- `apps/neo4j_database_controller/managers/query_manager.py`

**Key Features**:
- `find_shortest_path()`: Find shortest path using Cypher shortestPath()
- `find_all_paths()`: Find all paths up to max depth
- `get_node_neighbors()`: Get neighboring nodes with direction/type filters
- `get_node_neighbors_with_relationships()`: Get neighbors with relationship info
- `get_entity_context()`: RAG-optimized entity context (chunks, entities, concepts)
- `get_document_graph()`: Complete document subgraph for RAG
- `find_entities_by_name()`: Search entities by name with type filter
- `find_related_entities()`: Find entities via RELATED_TO relationships
- `search_entities()`: Search with SearchEntitiesRequest DTO
- `get_node_degree()`: Get node connection count
- `get_graph_stats()`: Overall graph statistics

---

### Submodule 7.5: Service Layer & Integration

**Goal**: Provide unified service interface with business logic

**Status**: ✅ COMPLETED (2026-03-04)

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 5.1 | Create Neo4jService class | High-level facade service | 2h | ✅ Completed |
| 5.2 | Implement document operations | High-level document node operations | 2h | ✅ Completed |
| 5.3 | Implement chunk operations | High-level chunk node operations with CONTAINS relationship | 2h | ✅ Completed |
| 5.4 | Implement entity operations | High-level entity operations with MENTIONS relationship | 2.5h | ✅ Completed |
| 5.5 | Implement concept operations | High-level concept operations with ABOUT relationship | 1.5h | ✅ Completed |
| 5.6 | Implement knowledge graph retrieval | High-level KG retrieval for RAG pipeline | 3h | ✅ Completed |
| 5.7 | Implement health check | Connection health check and stats | 1h | ✅ Completed |
| 5.8 | Add entity extraction interface | Reserved interface for LLM integration | 1.5h | ✅ Completed |

**Acceptance Criteria**:
- [x] Neo4jService coordinating all managers
- [x] High-level API for common operations
- [x] Integration-ready for RAG pipeline
- [x] Reserved interface for entity extraction
- [ | Unit tests for service layer

---

### Submodule 7.6: API Views Layer

**Goal**: Expose Neo4j functionality through REST API endpoints

**Status**: ✅ COMPLETED (2026-03-04)

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 6.1 | Create serializers | Define request/response serializers | 2h | ✅ Completed |
| 6.2 | Implement NodeViews | Node CRUD endpoints | 3h | ✅ Completed |
| 6.3 | Implement RelationshipViews | Relationship CRUD endpoints | 2.5h | ✅ Completed |
| 6.4 | Implement QueryViews | Graph query endpoints | 3h | ✅ Completed |
| 6.5 | Implement HealthView | Health check endpoint | 1h | ✅ Completed |
| 6.6 | Create URL routing | URL patterns for all Neo4j endpoints | 1h | ✅ Completed |
| 6.7 | Register with main URL config | Include neo4j URLs in main api/urls.py | 0.5h | ✅ Completed |
| 6.8 | Write API tests | Test all API endpoints with pytest | 3h | Pending (to be implemented in 7.7) |

**Acceptance Criteria**:
- [x] REST API for all Neo4jService operations
- [x] Proper authentication (IsAuthenticated)
- [x] Request validation with DRF serializers
- [x] Consistent response format
- [x] OpenAPI documentation via drf-yasg
- [ ] API tests with >= 80% coverage

---

### Submodule 7.7: Testing & Documentation

**Goal**: Comprehensive testing and documentation

**Status**: ✅ COMPLETED (2026-03-04)

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 7.1 | Create test fixtures | Setup test Neo4j instance and sample data | 2h | ✅ Completed |
| 7.2 | Write client tests | Test Neo4jClient connection and basic ops | 1.5h | ✅ Completed |
| 7.3 | Write node manager tests | Test node CRUD operations | 2h | ✅ Completed |
| 7.4 | Write relationship manager tests | Test relationship CRUD operations | 2h | ✅ Completed |
| 7.5 | Write query manager tests | Test graph query operations | 2.5h | ✅ Completed |
| 7.6 | Write service tests | Test Neo4jService integration | 2h | ✅ Completed |
| 7.7 | Write integration tests | End-to-end tests with real Neo4j | 3h | ✅ Completed |
| 7.8 | Create module documentation | README and API usage examples | 2h | ✅ Completed |

**Acceptance Criteria**:
- [x] Test fixtures for Neo4j operations
- [x] Unit tests for all managers
- [x] Integration tests with real Neo4j
- [x] Module documentation with usage examples
- [x] API documentation in docs/

---

### Submodule 7.8: Manual Test Generation

**Goal**: Generate manual test cases for Neo4j operations

**Status**: ✅ COMPLETED (2026-03-04)

**Dependencies**: Submodule 7.7 (Testing & Documentation)

| # | Task | Description | Estimated Time | Status |
|---|------|-------------|----------------|--------|
| 8.1 | Invoke manual_test_generator agent | Generate manual test cases for Neo4j operations | 1h | ✅ Completed |
| 8.2 | Create manual test document | Create apps/neo4j_database_controller/docs/manual_test.md | 1h | ✅ Completed |
| 8.3 | Document test scenarios | Document node CRUD, relationship CRUD, graph query scenarios | 1.5h | ✅ Completed |

**Acceptance Criteria**:
- [x] Manual test document created
- [x] Test cases for all major operations
- [x] curl commands for API testing
- [x] Sample data for testing

---

## File Structure

```
apps/neo4j_database_controller/
├── __init__.py
├── apps.py                     # Django AppConfig
├── constants.py                # Node labels, relationship types, defaults
├── exceptions.py               # Custom exceptions
├── dto.py                      # Data Transfer Objects (dataclasses)
│
├── client/
│   ├── __init__.py
│   └── neo4j_client.py         # Neo4jClient singleton wrapper
│
├── managers/
│   ├── __init__.py
│   ├── node_manager.py         # Node CRUD operations
│   ├── relationship_manager.py # Relationship CRUD operations
│   └── query_manager.py        # Graph query operations
│
├── services/
│   ├── __init__.py
│   └── neo4j_service.py        # High-level facade service
│
├── schemas/
│   ├── __init__.py
│   └── graph_schema.py         # Graph schema definitions and constraints
│
├── views/                      # API Views Layer (Submodule 7.6)
│   ├── __init__.py
│   ├── node_views.py           # Node management endpoints
│   ├── relationship_views.py   # Relationship management endpoints
│   ├── query_views.py          # Graph query endpoints
│   └── health_views.py         # Health check endpoints
│
├── serializers.py              # DRF serializers for API requests/responses
├── urls.py                     # URL routing for Neo4j API
│
├── docs/                       # Documentation
│   ├── manual_test.md          # Manual test cases (Submodule 7.8)
│   └── README.md               # Module documentation
│
└── tests/
    ├── __init__.py
    ├── conftest.py             # Pytest fixtures
    ├── test_client.py          # Client tests
    ├── test_node_manager.py    # Node manager tests
    ├── test_relationship_manager.py
    ├── test_query_manager.py   # Query manager tests
    ├── test_neo4j_service.py   # Service tests
    ├── test_api_views.py       # API endpoint tests
    └── test_integration.py     # Integration tests
```

---

## Interface Design

### DTOs (Data Transfer Objects)

```python
from dataclasses import dataclass
from typing import Optional, Any
from datetime import datetime

# =============================================================================
# Request DTOs
# =============================================================================

@dataclass(frozen=True)
class CreateNodeRequest:
    """Request to create a new node."""
    label: str  # Document, Chunk, Entity, Concept, User
    properties: dict[str, Any]


@dataclass(frozen=True)
class CreateRelationshipRequest:
    """Request to create a new relationship."""
    rel_type: str  # CONTAINS, MENTIONS, RELATED_TO, etc.
    from_node_id: str
    from_node_label: str
    to_node_id: str
    to_node_label: str
    properties: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class FindPathRequest:
    """Request to find paths between nodes."""
    from_node_id: str
    from_node_label: str
    to_node_id: str
    to_node_label: str
    max_depth: int = 5
    relationship_types: Optional[list[str]] = None


@dataclass(frozen=True)
class GetEntityContextRequest:
    """Request to get entity context for RAG."""
    entity_id: str
    include_chunks: bool = True
    include_related_entities: bool = True
    max_depth: int = 2


# =============================================================================
# Response DTOs
# =============================================================================

@dataclass(frozen=True)
class NodeInfo:
    """Information about a node."""
    id: str
    label: str
    properties: dict[str, Any]


@dataclass(frozen=True)
class RelationshipInfo:
    """Information about a relationship."""
    id: int
    rel_type: str
    from_node_id: str
    from_node_label: str
    to_node_id: str
    to_node_label: str
    properties: dict[str, Any]


@dataclass(frozen=True)
class PathInfo:
    """Information about a graph path."""
    nodes: list[NodeInfo]
    relationships: list[RelationshipInfo]
    length: int


@dataclass(frozen=True)
class EntityContext:
    """Entity context for RAG."""
    entity: NodeInfo
    mentioned_in: list[NodeInfo]  # Chunks that mention this entity
    related_entities: list[tuple[NodeInfo, str]]  # (entity, relation_type)
    concepts: list[NodeInfo]  # Related concepts
```

### Neo4jService Interface

```python
class Neo4jService:
    """High-level facade service for Neo4j operations."""

    # Node Management
    def create_node(self, request: CreateNodeRequest) -> NodeInfo: ...
    def create_nodes_batch(self, label: str, nodes: list[dict]) -> list[NodeInfo]: ...
    def get_node_by_id(self, node_id: str, label: str) -> Optional[NodeInfo]: ...
    def get_nodes_by_label(self, label: str, filters: dict) -> list[NodeInfo]: ...
    def update_node(self, node_id: str, label: str, properties: dict) -> NodeInfo: ...
    def delete_node(self, node_id: str, label: str) -> bool: ...

    # Relationship Management
    def create_relationship(self, request: CreateRelationshipRequest) -> RelationshipInfo: ...
    def create_relationships_batch(self, relationships: list[CreateRelationshipRequest]) -> list[RelationshipInfo]: ...
    def get_relationships(self, from_node_id: str, rel_type: Optional[str] = None) -> list[RelationshipInfo]: ...
    def delete_relationship(self, rel_id: int) -> bool: ...

    # Graph Queries
    def find_shortest_path(self, request: FindPathRequest) -> Optional[PathInfo]: ...
    def find_all_paths(self, request: FindPathRequest) -> list[PathInfo]: ...
    def get_node_neighbors(self, node_id: str, label: str, direction: str = "both") -> list[NodeInfo]: ...
    def get_entity_context(self, request: GetEntityContextRequest) -> EntityContext: ...
    def get_document_graph(self, document_id: str) -> dict[str, Any]: ...
    def find_related_entities(self, entity_name: str, entity_type: Optional[str] = None) -> list[NodeInfo]: ...

    # Utility
    def health_check(self) -> dict[str, Any]: ...
    def create_indexes_and_constraints(self) -> bool: ...
```

---

## API Endpoints Design (Submodule 7.6)

### URL Structure

```
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
    └── search-entities/              # POST - Search entities by name
```

### Endpoint Details

#### Health Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/neo4j/health/` | Neo4j connection health check | IsAuthenticated |

**Response (200):**
```json
{
    "status": "healthy",
    "connected": true,
    "server_info": {
        "version": "5.x",
        "edition": "community"
    }
}
```

#### Node Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/neo4j/nodes/create/` | Create single node | IsAuthenticated |
| POST | `/api/v1/neo4j/nodes/batch-create/` | Batch create nodes | IsAuthenticated |
| GET | `/api/v1/neo4j/nodes/{label}/{id}/` | Get node by ID | IsAuthenticated |
| GET | `/api/v1/neo4j/nodes/{label}/` | List nodes by label | IsAuthenticated |
| PATCH | `/api/v1/neo4j/nodes/{label}/{id}/update/` | Update node | IsAuthenticated |
| DELETE | `/api/v1/neo4j/nodes/{label}/{id}/delete/` | Delete node | IsAuthenticated |

**Create Node Request (POST):**
```json
{
    "label": "Entity",
    "properties": {
        "id": "uuid-here",
        "name": "John Doe",
        "entity_type": "person",
        "description": "Software engineer",
        "confidence": 0.95
    }
}
```

**Node Response (200):**
```json
{
    "id": "uuid-here",
    "label": "Entity",
    "properties": {
        "id": "uuid-here",
        "name": "John Doe",
        "entity_type": "person",
        "description": "Software engineer",
        "confidence": 0.95,
        "created_at": "2026-03-04T10:00:00Z"
    }
}
```

#### Relationship Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/neo4j/relationships/create/` | Create relationship | IsAuthenticated |
| POST | `/api/v1/neo4j/relationships/batch-create/` | Batch create relationships | IsAuthenticated |
| GET | `/api/v1/neo4j/relationships/{id}/` | Get relationship by ID | IsAuthenticated |
| GET | `/api/v1/neo4j/relationships/from/{node_id}/` | Get relationships from node | IsAuthenticated |
| PATCH | `/api/v1/neo4j/relationships/{id}/update/` | Update relationship | IsAuthenticated |
| DELETE | `/api/v1/neo4j/relationships/{id}/delete/` | Delete relationship | IsAuthenticated |

**Create Relationship Request (POST):**
```json
{
    "rel_type": "MENTIONS",
    "from_node_id": "chunk-uuid",
    "from_node_label": "Chunk",
    "to_node_id": "entity-uuid",
    "to_node_label": "Entity",
    "properties": {
        "confidence": 0.9,
        "count": 3
    }
}
```

#### Query Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/neo4j/query/path/shortest/` | Find shortest path | IsAuthenticated |
| POST | `/api/v1/neo4j/query/path/all/` | Find all paths | IsAuthenticated |
| GET | `/api/v1/neo4j/query/neighbors/{label}/{id}/` | Get node neighbors | IsAuthenticated |
| GET | `/api/v1/neo4j/query/entity-context/{id}/` | Get entity context | IsAuthenticated |
| GET | `/api/v1/neo4j/query/document-graph/{id}/` | Get document subgraph | IsAuthenticated |
| POST | `/api/v1/neo4j/query/search-entities/` | Search entities | IsAuthenticated |

**Find Shortest Path Request (POST):**
```json
{
    "from_node_id": "entity-uuid-1",
    "from_node_label": "Entity",
    "to_node_id": "entity-uuid-2",
    "to_node_label": "Entity",
    "max_depth": 5,
    "relationship_types": ["RELATED_TO", "MENTIONS"]
}
```

**Entity Context Response (200):**
```json
{
    "entity": {
        "id": "entity-uuid",
        "label": "Entity",
        "properties": {
            "name": "Python",
            "entity_type": "technology"
        }
    },
    "mentioned_in": [
        {
            "id": "chunk-uuid-1",
            "label": "Chunk",
            "properties": {
                "text": "Python is a programming language...",
                "chunk_index": 0
            }
        }
    ],
    "related_entities": [
        {
            "entity": {
                "id": "entity-uuid-2",
                "label": "Entity",
                "properties": {
                    "name": "Django",
                    "entity_type": "technology"
                }
            },
            "relation_type": "RELATED_TO"
        }
    ],
    "concepts": [
        {
            "id": "concept-uuid",
            "label": "Concept",
            "properties": {
                "name": "Web Development"
            }
        }
    ]
}
```

---

## Configuration Design

### Settings (base.py)

```python
# =============================================================================
# Neo4j Configuration
# =============================================================================

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")

NEO4J_CONFIG = {
    # Connection settings
    "uri": NEO4J_URI,
    "user": NEO4J_USER,
    "password": NEO4J_PASSWORD,
    "database": NEO4J_DATABASE,

    # Connection pool settings
    "max_connection_pool_size": 50,
    "connection_timeout": 30,  # seconds
    "max_transaction_retry_time": 30,  # seconds

    # Session settings
    "default_session_mode": "WRITE",  # WRITE or READ

    # Query settings
    "default_query_timeout": 60,  # seconds
    "default_batch_size": 1000,
}
```

### Environment Variables (.env)

```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password
NEO4J_DATABASE=neo4j
```

---

## Constants Design

```python
from enum import Enum

# =============================================================================
# Node Labels
# =============================================================================

class NodeLabel(str, Enum):
    """Node labels for Neo4j graph."""
    DOCUMENT = "Document"
    CHUNK = "Chunk"
    ENTITY = "Entity"
    CONCEPT = "Concept"
    USER = "User"


# =============================================================================
# Relationship Types
# =============================================================================

class RelType(str, Enum):
    """Relationship types for Neo4j graph."""
    CONTAINS = "CONTAINS"           # Document -> Chunk
    MENTIONS = "MENTIONS"           # Chunk -> Entity
    RELATED_TO = "RELATED_TO"       # Entity -> Entity
    ABOUT = "ABOUT"                 # Document -> Concept
    ASKED = "ASKED"                 # User -> Question
    ANSWERED_BY = "ANSWERED_BY"     # Question -> Chunk


# =============================================================================
# Property Names
# =============================================================================

class PropName:
    """Property names for nodes and relationships."""
    # Common properties
    ID = "id"
    NAME = "name"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"

    # Document properties
    TITLE = "title"
    SOURCE = "source"
    DOC_TYPE = "doc_type"
    STATUS = "status"

    # Chunk properties
    TEXT = "text"
    CHUNK_INDEX = "chunk_index"
    PAGE_NUMBER = "page_number"
    START_CHAR = "start_char"
    END_CHAR = "end_char"
    DOCUMENT_ID = "document_id"

    # Entity properties
    ENTITY_TYPE = "entity_type"
    DESCRIPTION = "description"
    CONFIDENCE = "confidence"

    # Concept properties
    CATEGORY = "category"

    # Relationship properties
    RELATION_TYPE = "relation_type"
    COUNT = "count"


# =============================================================================
# Entity Types
# =============================================================================

class EntityType(str, Enum):
    """Entity types for extraction."""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    TECHNOLOGY = "technology"
    EVENT = "event"
    DATE = "date"
    MONEY = "money"
    PRODUCT = "product"
    CONCEPT = "concept"


# =============================================================================
# Default Configuration Values
# =============================================================================

DEFAULT_MAX_DEPTH = 5
DEFAULT_BATCH_SIZE = 1000
DEFAULT_QUERY_TIMEOUT = 60  # seconds
DEFAULT_CONNECTION_TIMEOUT = 30  # seconds

# Relationship directions
class Direction(str, Enum):
    """Direction for relationship traversal."""
    OUTGOING = "OUTGOING"
    INCOMING = "INCOMING"
    BOTH = "BOTH"
```

---

## Exception Design

```python
class Neo4jError(Exception):
    """Base exception for Neo4j operations."""
    pass


class Neo4jConnectionError(Neo4jError):
    """Failed to connect to Neo4j server."""
    def __init__(self, reason: str = ""):
        self.reason = reason
        super().__init__(f"Failed to connect to Neo4j: {reason}")


class Neo4jQueryError(Neo4jError):
    """Failed to execute Cypher query."""
    def __init__(self, query: str = "", reason: str = ""):
        self.query = query
        self.reason = reason
        super().__init__(f"Query failed: {reason}")


class NodeNotFoundError(Neo4jError):
    """Node does not exist."""
    def __init__(self, node_id: str, label: str = ""):
        self.node_id = node_id
        self.label = label
        super().__init__(f"Node '{node_id}' (label: {label}) not found")


class RelationshipNotFoundError(Neo4jError):
    """Relationship does not exist."""
    def __init__(self, rel_id: int):
        self.rel_id = rel_id
        super().__init__(f"Relationship {rel_id} not found")


class ConstraintViolationError(Neo4jError):
    """Constraint violation error."""
    def __init__(self, constraint: str, reason: str = ""):
        self.constraint = constraint
        self.reason = reason
        super().__init__(f"Constraint violation '{constraint}': {reason}")


class InvalidNodeLabelError(Neo4jError):
    """Invalid node label."""
    def __init__(self, label: str):
        self.label = label
        valid_labels = [l.value for l in NodeLabel]
        super().__init__(
            f"Invalid node label '{label}'. Valid labels: {valid_labels}"
        )


class InvalidRelationshipTypeError(Neo4jError):
    """Invalid relationship type."""
    def __init__(self, rel_type: str):
        self.rel_type = rel_type
        valid_types = [t.value for t in RelType]
        super().__init__(
            f"Invalid relationship type '{rel_type}'. Valid types: {valid_types}"
        )
```

---

## Test Strategy

### Test Categories

1. **Unit Tests**: Mock Neo4j driver, test manager logic
2. **Integration Tests**: Real Neo4j instance (Docker)
3. **Performance Tests**: Benchmark query latency

### Test Fixtures

```python
# conftest.py
import pytest
from neo4j import GraphDatabase

@pytest.fixture
def neo4j_client():
    """Create Neo4j client for testing."""
    from apps.neo4j_database_controller.client import Neo4jClient
    client = Neo4jClient.get_instance()
    yield client
    # Cleanup: delete test nodes
    with client.session() as session:
        session.run("MATCH (n) WHERE n.id STARTS WITH 'test-' DETACH DELETE n")

@pytest.fixture
def test_document(neo4j_client):
    """Create test document node."""
    node_id = "test-doc-001"
    # ... create node
    yield node_id
    # Cleanup

@pytest.fixture
def sample_graph(neo4j_client):
    """Create sample knowledge graph for testing."""
    # Create Document -> Chunk -> Entity relationships
    # ...
    yield graph_data
    # Cleanup
```

### Test Commands

```bash
# Run all neo4j tests
pytest apps/neo4j_database_controller/tests/ -v

# Run with coverage
pytest apps/neo4j_database_controller/tests/ --cov=apps/neo4j_database_controller --cov-report=term-missing

# Run integration tests only (requires running Neo4j)
pytest apps/neo4j_database_controller/tests/test_integration.py -v

# Run unit tests with mocked driver
pytest apps/neo4j_database_controller/tests/ -v -m "not integration"
```

---

## Integration with Other Modules

### documents_parser Integration

```python
# After document parsing, create document and chunk nodes
from apps.neo4j_database_controller.services import Neo4jService
from apps.neo4j_database_controller.dto import CreateNodeRequest, CreateRelationshipRequest

neo4j_service = Neo4jService()

def store_document_graph(document_id: str, chunks: list[dict]) -> None:
    """Store document and chunks in Neo4j."""
    # Create document node
    neo4j_service.create_node(CreateNodeRequest(
        label="Document",
        properties={
            "id": document_id,
            "title": chunks[0].get("title", ""),
            "source": chunks[0].get("source", ""),
            "created_at": datetime.utcnow(),
        }
    ))

    # Create chunk nodes and CONTAINS relationships
    for idx, chunk in enumerate(chunks):
        chunk_id = f"{document_id}-chunk-{idx}"
        neo4j_service.create_node(CreateNodeRequest(
            label="Chunk",
            properties={
                "id": chunk_id,
                "text": chunk["text"],
                "chunk_index": idx,
                "document_id": document_id,
            }
        ))
        neo4j_service.create_relationship(CreateRelationshipRequest(
            rel_type="CONTAINS",
            from_node_id=document_id,
            from_node_label="Document",
            to_node_id=chunk_id,
            to_node_label="Chunk",
            properties={"order": idx}
        ))
```

### rag_processing Integration

```python
# Retrieve graph context for RAG query
from apps.neo4j_database_controller.services import Neo4jService
from apps.neo4j_database_controller.dto import GetEntityContextRequest

neo4j_service = Neo4jService()

def retrieve_graph_context(query_entities: list[str]) -> dict:
    """Retrieve graph context for RAG query."""
    contexts = []
    for entity_name in query_entities:
        # Find entity by name
        entities = neo4j_service.find_related_entities(
            entity_name=entity_name
        )
        if entities:
            # Get entity context (chunks, related entities, concepts)
            context = neo4j_service.get_entity_context(
                GetEntityContextRequest(
                    entity_id=entities[0].id,
                    include_chunks=True,
                    include_related_entities=True,
                    max_depth=2
                )
            )
            contexts.append(context)
    return contexts
```

### Entity Extraction Interface (Reserved)

```python
# Interface for future LLM integration
from abc import ABC, abstractmethod
from typing import List

class EntityExtractorInterface(ABC):
    """Abstract interface for entity extraction."""

    @abstractmethod
    def extract_entities(self, text: str) -> List[dict]:
        """
        Extract entities from text.

        Args:
            text: Input text to extract entities from.

        Returns:
            List of entity dictionaries with:
            - name: Entity name
            - entity_type: Entity type (person, org, location, etc.)
            - confidence: Extraction confidence
            - description: Optional entity description
        """
        pass

    @abstractmethod
    def extract_relationships(self, text: str, entities: List[dict]) -> List[dict]:
        """
        Extract relationships between entities.

        Args:
            text: Input text
            entities: List of extracted entities

        Returns:
            List of relationship dictionaries with:
            - from_entity: Source entity name
            - to_entity: Target entity name
            - relation_type: Relationship type
            - confidence: Extraction confidence
        """
        pass


# Placeholder implementation
class MockEntityExtractor(EntityExtractorInterface):
    """Mock entity extractor for testing."""

    def extract_entities(self, text: str) -> List[dict]:
        return []

    def extract_relationships(self, text: str, entities: List[dict]) -> List[dict]:
        return []
```

---

## Dependencies

```toml
# pyproject.toml additions
[tool.poetry.dependencies]
neo4j = "^5.0"  # Neo4j Python Driver

[tool.poetry.group.dev.dependencies]
# No additional dev dependencies needed for Neo4j testing
# Integration tests use existing local Neo4j instance
```

---

## Acceptance Criteria

### Core Functionality (Submodule 7.1-7.5)
- [ ] Neo4jClient singleton with connection management
- [ ] Node CRUD operations for all 5 node types
- [ ] Relationship CRUD operations for all 6 relationship types
- [ ] Graph query operations for knowledge graph retrieval
- [ ] Batch operations for performance
- [ ] Reserved interface for entity extraction
- [ ] Comprehensive error handling
- [ ] Test coverage >= 80%

### API Layer (Submodule 7.6)
- [ ] REST API endpoints for all Neo4jService operations
- [ ] Proper authentication (IsAuthenticated)
- [ ] Request validation with DRF serializers
- [ ] Consistent response format
- [ ] Clear error messages with appropriate HTTP status codes
- [ ] OpenAPI documentation via drf-yasg
- [ ] API tests with >= 80% coverage

### Testing & Documentation (Submodule 7.7)
- [ ] Unit tests for all managers
- [ ] Integration tests with real Neo4j
- [ ] Module documentation with usage examples
- [ ] Manual test cases for API testing

---

## Risks & Considerations

1. **Connection Management**: Neo4j driver connection pool size should be tuned for production workload
2. **Query Performance**: Complex graph traversals may need query optimization and proper indexing
3. **Transaction Management**: Batch operations should use transactions for data consistency
4. **Memory Usage**: Large graph query results may require pagination or streaming
5. **Data Synchronization**: Need to sync with PostgreSQL document metadata
6. **Entity Extraction**: LLM integration will be added in future phases, interface is reserved

---

## Execution Order

Recommended execution order:

1. **Submodule 7.1** (Tasks 1.1-1.7): Infrastructure setup
2. **Submodule 7.2** (Tasks 2.1-2.8): Node management
3. **Submodule 7.3** (Tasks 3.1-3.8): Relationship management
4. **Submodule 7.4** (Tasks 4.1-4.8): Graph query operations
5. **Submodule 7.5** (Tasks 5.1-5.8): Service layer and integration
6. **Submodule 7.6** (Tasks 6.1-6.8): API Views Layer
7. **Submodule 7.7** (Tasks 7.1-7.8): Testing and documentation
8. **Submodule 7.8** (Tasks 8.1-8.3): Manual test generation

---

## Files to Create/Modify

### New Files

| File | Purpose | Submodule |
|------|---------|-----------|
| `apps/neo4j_database_controller/constants.py` | Node labels, relationship types, defaults | 7.1 |
| `apps/neo4j_database_controller/exceptions.py` | Custom exceptions | 7.1 |
| `apps/neo4j_database_controller/dto.py` | Data transfer objects | 7.1 |
| `apps/neo4j_database_controller/client/__init__.py` | Client module init | 7.1 |
| `apps/neo4j_database_controller/client/neo4j_client.py` | Neo4jClient wrapper | 7.1 |
| `apps/neo4j_database_controller/managers/__init__.py` | Managers module init | 7.1 |
| `apps/neo4j_database_controller/managers/node_manager.py` | Node operations | 7.2 |
| `apps/neo4j_database_controller/managers/relationship_manager.py` | Relationship operations | 7.3 |
| `apps/neo4j_database_controller/managers/query_manager.py` | Graph query operations | 7.4 |
| `apps/neo4j_database_controller/services/__init__.py` | Services module init | 7.5 |
| `apps/neo4j_database_controller/services/neo4j_service.py` | Facade service | 7.5 |
| `apps/neo4j_database_controller/schemas/__init__.py` | Schemas module init | 7.1 |
| `apps/neo4j_database_controller/schemas/graph_schema.py` | Graph schema definitions | 7.1 |
| `apps/neo4j_database_controller/tests/__init__.py` | Tests module init | 7.7 |
| `apps/neo4j_database_controller/tests/conftest.py` | Test fixtures | 7.7 |
| `apps/neo4j_database_controller/tests/test_*.py` | Test files | 7.7 |
| `apps/neo4j_database_controller/views/__init__.py` | Views module init | 7.6 |
| `apps/neo4j_database_controller/views/node_views.py` | Node endpoints | 7.6 |
| `apps/neo4j_database_controller/views/relationship_views.py` | Relationship endpoints | 7.6 |
| `apps/neo4j_database_controller/views/query_views.py` | Query endpoints | 7.6 |
| `apps/neo4j_database_controller/views/health_views.py` | Health check endpoints | 7.6 |
| `apps/neo4j_database_controller/serializers.py` | DRF serializers | 7.6 |
| `apps/neo4j_database_controller/urls.py` | URL routing | 7.6 |
| `apps/neo4j_database_controller/docs/README.md` | Module documentation | 7.7 |
| `apps/neo4j_database_controller/docs/manual_test.md` | Manual test cases | 7.8 |

### Modified Files

| File | Changes | Submodule |
|------|---------|-----------|
| `pyproject.toml` | Add neo4j-driver dependency | 7.1 |
| `config/settings/base.py` | Verify NEO4J_CONFIG | 7.1 |
| `env/.env.local` | Add NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD | 7.1 |
| `config/urls.py` | Include neo4j URLs | 7.6 |

---

## Estimated Timeline

| Submodule | Estimated Hours | Working Days |
|-----------|-----------------|--------------|
| 7.1 Infrastructure Setup | 8.5h | 2 days |
| 7.2 Node Management | 11.5h | 2-3 days |
| 7.3 Relationship Management | 12h | 2-3 days |
| 7.4 Graph Query Operations | 15.5h | 3-4 days |
| 7.5 Service Layer & Integration | 15.5h | 3-4 days |
| 7.6 API Views Layer | 16h | 3-4 days |
| 7.7 Testing & Documentation | 17h | 3-4 days |
| 7.8 Manual Test Generation | 3.5h | 1 day |
| **Total** | **99.5h** | **19-25 days** |

---

*Generated: 2026-03-04*
*Plan for Phase 7: Neo4j Database Controller*
