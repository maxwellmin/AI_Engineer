# Neo4j Database Controller

A comprehensive Neo4j database controller module for the melon RAG project, providing graph database operations including node management, relationship management, and knowledge graph query functionality.

## Overview

This module provides a layered architecture for Neo4j operations:

```
┌─────────────────────────────────────────────────────────────┐
│                    Neo4jService (Facade)                     │
│  - High-level API for all Neo4j operations                  │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┬───────────────┐
          ▼               ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│    Node      │ │ Relationship │ │   Graph      │ │    Query     │
│   Manager    │ │   Manager    │ │   Manager    │ │   Manager    │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Neo4jClient (Singleton)                   │
└─────────────────────────────────────────────────────────────┘
```

## Features

- **Node Management**: CRUD operations for Document, Chunk, Entity, Concept, User nodes
- **Relationship Management**: CRUD operations for CONTAINS, MENTIONS, RELATED_TO, ABOUT relationships
- **Graph Queries**: Path finding, neighbor discovery, entity context retrieval
- **RAG Integration**: Document graph retrieval, entity-based chunk discovery
- **REST API**: Full REST API with OpenAPI documentation

## Installation

The module requires the `neo4j` Python driver:

```bash
poetry add neo4j
```

## Configuration

Add the following environment variables to your `.env` file:

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j
```

## Quick Start

### Using Neo4jService

```python
from apps.neo4j_database_controller.services import Neo4jService

# Initialize service
service = Neo4jService()

# Create a document
doc_result = service.create_document(
    document_id="doc-001",
    title="Introduction to Python",
    source="python_intro.pdf",
)

# Add chunks
service.add_chunk_to_document(
    document_id="doc-001",
    chunk_id="chunk-001",
    text="Python is a programming language.",
    chunk_index=0,
)

# Create an entity
service.create_entity(
    entity_id="entity-python",
    name="Python",
    entity_type="technology",
)

# Link chunk to entity
service.link_chunk_to_entity(
    chunk_id="chunk-001",
    entity_id="entity-python",
    confidence=0.95,
)

# Get entity context for RAG
context = service.get_entity_context("entity-python")
print(f"Entity: {context.entity.properties['name']}")
print(f"Mentioned in {len(context.mentioned_in)} chunks")
```

### Using Node Manager Directly

```python
from apps.neo4j_database_controller.managers import NodeManager
from apps.neo4j_database_controller.constants import NodeLabel

manager = NodeManager()

# Create a node
result = manager.create_node(
    NodeLabel.ENTITY.value,
    {
        "id": "entity-001",
        "name": "Django",
        "entity_type": "technology",
    },
)

# Get node by ID
node = manager.get_node_by_label_and_id(
    NodeLabel.ENTITY.value,
    "entity-001",
)

# Update node
updated = manager.update_node(
    "entity-001",
    NodeLabel.ENTITY.value,
    {"description": "A Python web framework"},
)

# Delete node
manager.delete_node("entity-001", NodeLabel.ENTITY.value)
```

### Using Query Manager

```python
from apps.neo4j_database_controller.managers import QueryManager

manager = QueryManager()

# Find shortest path between entities
path = manager.find_shortest_path(
    from_node_id="entity-python",
    from_node_label="Entity",
    to_node_id="entity-django",
    to_node_label="Entity",
    max_depth=5,
)

# Get node neighbors
neighbors = manager.get_node_neighbors(
    node_id="entity-python",
    node_label="Entity",
    direction="OUTGOING",
)

# Get graph statistics
stats = manager.get_graph_stats()
print(f"Total nodes: {stats['total_nodes']}")
print(f"Total relationships: {stats['total_relationships']}")
```

## API Endpoints

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/neo4j/health/` | Health check |
| GET | `/api/v1/neo4j/health/stats/` | Graph statistics |
| POST | `/api/v1/neo4j/health/init-schema/` | Initialize schema |

### Nodes

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/neo4j/nodes/create/` | Create node |
| POST | `/api/v1/neo4j/nodes/batch-create/` | Batch create nodes |
| GET | `/api/v1/neo4j/nodes/{label}/{id}/` | Get node |
| GET | `/api/v1/neo4j/nodes/{label}/` | List nodes |
| PATCH | `/api/v1/neo4j/nodes/{label}/{id}/update/` | Update node |
| DELETE | `/api/v1/neo4j/nodes/{label}/{id}/delete/` | Delete node |

### Relationships

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/neo4j/relationships/create/` | Create relationship |
| POST | `/api/v1/neo4j/relationships/batch-create/` | Batch create |
| GET | `/api/v1/neo4j/relationships/{id}/` | Get relationship |
| GET | `/api/v1/neo4j/relationships/from/{node_id}/` | Get node relationships |
| PATCH | `/api/v1/neo4j/relationships/{id}/update/` | Update relationship |
| DELETE | `/api/v1/neo4j/relationships/{id}/delete/` | Delete relationship |

### Queries

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/neo4j/query/path/shortest/` | Find shortest path |
| POST | `/api/v1/neo4j/query/path/all/` | Find all paths |
| GET | `/api/v1/neo4j/query/neighbors/{label}/{id}/` | Get neighbors |
| GET | `/api/v1/neo4j/query/entity-context/{id}/` | Get entity context |
| GET | `/api/v1/neo4j/query/document-graph/{id}/` | Get document graph |
| POST | `/api/v1/neo4j/query/search-entities/` | Search entities |

## API Examples

### Create Document

```bash
curl -X POST http://localhost:8000/api/v1/neo4j/nodes/create/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "label": "Document",
    "properties": {
      "id": "doc-001",
      "title": "Test Document",
      "source": "test.pdf"
    }
  }'
```

### Create Relationship

```bash
curl -X POST http://localhost:8000/api/v1/neo4j/relationships/create/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "rel_type": "CONTAINS",
    "from_node_id": "doc-001",
    "from_node_label": "Document",
    "to_node_id": "chunk-001",
    "to_node_label": "Chunk",
    "properties": {"order": 0}
  }'
```

### Get Entity Context

```bash
curl -X GET "http://localhost:8000/api/v1/neo4j/query/entity-context/entity-001/?include_chunks=true&include_related_entities=true" \
  -H "Authorization: Bearer <token>"
```

## Graph Schema

### Node Labels

| Label | Properties |
|-------|------------|
| Document | id, title, source, doc_type, status, created_at, updated_at |
| Chunk | id, text, chunk_index, page_number, document_id |
| Entity | id, name, entity_type, description, confidence |
| Concept | id, name, description, category |
| User | id, username, email |

### Relationship Types

| Type | From → To | Description |
|------|-----------|-------------|
| CONTAINS | Document → Chunk | Document contains chunks |
| MENTIONS | Chunk → Entity | Chunk mentions entity |
| RELATED_TO | Entity → Entity | Entity relationships |
| ABOUT | Document → Concept | Document about concept |

## Testing

Run tests with pytest:

```bash
# Run all Neo4j tests
pytest apps/neo4j_database_controller/tests/ -v

# Run with coverage
pytest apps/neo4j_database_controller/tests/ --cov=apps/neo4j_database_controller

# Skip integration tests (requires running Neo4j)
SKIP_NEO4J_TESTS=true pytest apps/neo4j_database_controller/tests/ -v
```

## Error Handling

The module provides custom exceptions:

```python
from apps.neo4j_database_controller.exceptions import (
    Neo4jError,
    Neo4jConnectionError,
    Neo4jQueryError,
    NodeNotFoundError,
    RelationshipNotFoundError,
    ConstraintViolationError,
    InvalidNodeLabelError,
    InvalidRelationshipTypeError,
)
```

## Entity Extraction Interface

The module provides a reserved interface for LLM-based entity extraction:

```python
from apps.neo4j_database_controller.services import Neo4jService, EntityExtractorInterface

class MyEntityExtractor(EntityExtractorInterface):
    def extract_entities(self, text: str) -> list[dict]:
        # Use LLM to extract entities
        return [{"name": "...", "entity_type": "...", "confidence": 0.9}]

    def extract_relationships(self, text: str, entities: list[dict]) -> list[dict]:
        # Use LLM to extract relationships
        return [{"from_entity": "...", "to_entity": "...", "relation_type": "..."}]

# Set the extractor
service = Neo4jService()
service.set_entity_extractor(MyEntityExtractor())

# Extract and store entities
result = service.extract_and_store_entities(
    chunk_id="chunk-001",
    text="Python and Django are used for web development.",
)
```

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Neo4j SDK | neo4j-driver (Official) | Official driver with connection pooling |
| Connection | Singleton Driver | Connection reuse, consistent with Milvus |
| Query Layer | Manager classes | Separation of concerns, testable |
| API Layer | DRF ViewSets | Consistent with other modules |
| Documentation | drf-yasg | OpenAPI/Swagger support |

## License

MIT License
