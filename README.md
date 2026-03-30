# Melon - RAG Document Knowledge Base System

A RAG (Retrieval-Augmented Generation) based document knowledge base processing tool with real-time chat capabilities.

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Architecture](#project-architecture)
- [Chat Agent Workflow](#chat-agent-workflow)
- [Directory Structure](#directory-structure)
- [Getting Started](#getting-started)
- [API Documentation](#api-documentation)

---

## Overview

Melon is a backend service that provides REST API interfaces for document processing, knowledge retrieval, and real-time chat. Built on Django REST Framework, it integrates:

- **Milvus** for vector database operations
- **Neo4j** for graph database and knowledge graph
- **Qwen API** for LLM and embeddings
- **PostgreSQL** for relational data storage
- **Redis** for caching and task queues

---

## Tech Stack

### Backend
| Component | Technology |
|-----------|------------|
| Framework | Django 5.1+ |
| Python Version | 3.12+ |
| API Style | Django REST Framework (DRF) |
| Async Support | Django Channels (WebSocket) |
| Task Queue | Celery + Redis |
| API Documentation | drf-spectacular (OpenAPI 3.0) |
| Authentication | Knox (Token-based) |

### Data Storage
| Storage | Technology | Purpose |
|---------|------------|---------|
| Relational DB | PostgreSQL 14+ | User data, sessions, document metadata |
| Vector DB | Milvus 2.4+ | Document embeddings, semantic search |
| Graph DB | Neo4j 5.x | Knowledge graph, entity relationships |
| Cache | Redis | Session cache, Celery broker |
| Object Storage | MinIO / AWS S3 | Document file storage |

### AI/ML Components
| Component | Provider |
|-----------|----------|
| LLM Provider | Alibaba Qwen API (Qwen-Plus) |
| Embedding Model | text-embedding-v1 (1536 dimensions) |
| Vector Similarity | Cosine Similarity |
| RAG Framework | LangChain 1.0+, LangGraph 1.0+ |

---

## Project Architecture

```
+------------------------------------------------------------------+
|                          Test Tools                               |
|   +-------------+   +-------------+   +-------------+             |
|   |    curl     |   |    wscat    |   |  Postman    |             |
|   +-------------+   +-------------+   +-------------+             |
+----------+------------------+------------------+------------------+
           | WebSocket        | HTTP             | HTTP
           v                  v                  v
+------------------------------------------------------------------+
|                      Django Backend                               |
|   +----------------------------------------------------------+   |
|   |              Django Channels (WebSocket)                 |   |
|   +----------------------------------------------------------+   |
|   +----------------------------------------------------------+   |
|   |            Django REST Framework (REST API)              |   |
|   +----------------------------------------------------------+   |
|   +----------------------------------------------------------+   |
|   |               RAG Processing Pipeline                    |   |
|   |   Query -> Embedding -> Vector Search -> Context         |   |
|   |   Assembly -> LLM Generation -> Response                 |   |
|   +----------------------------------------------------------+   |
+----+--------------+--------------+--------------+-------+-------+
     |              |              |              |       |
     v              v              v              v       v
+---------+  +----------+  +----------+  +-------+  +----------+
|PostgreSQL| |  Milvus  |  |  Neo4j   |  | MinIO |  | QWEN API |
| (Main DB)| | (Vector) |  |  (Graph) |  | (S3)  |  |(LLM+Embed)|
+---------+  +----------+  +----------+  +-------+  +----------+
```

---

## Chat Agent Workflow

### Overall Architecture

```
+------------------------------------------------------------------+
|                  Chat Agent Complete Workflow                     |
+------------------------------------------------------------------+

                              WebSocket Connection
                                      |
                                      v
+------------------------------------------------------------------+
|  1. ChatConsumer.receive_json()                                  |
|     - Parse message type: chat.message                           |
|     - Extract query content                                       |
|     - Get conversation info                                       |
+------------------------------------------------------------------+
                                      |
                                      v
+------------------------------------------------------------------+
|  2. Agent Selection (_get_agent)                                 |
|     - text_rag -> TextRAGAgent                                   |
|     - graph_rag -> GraphRAGAgent                                 |
+------------------------------------------------------------------+
                                      |
                                      v
+------------------------------------------------------------------+
|  3. Agent.run_with_streaming() - LangGraph State Machine         |
|                                                                  |
|     Text RAG Flow:                                               |
|     +----------+    +----------+    +----------+                 |
|     | retrieve | -> | generate | -> |   save   |                 |
|     +----------+    +----------+    +----------+                 |
|                                                                  |
|     Graph RAG Flow:                                              |
|     +----------+    +-------------+    +----------+    +---+     |
|     | retrieve | -> | entity_ctx  | -> | generate | -> |save|    |
|     +----------+    +-------------+    +----------+    +---+     |
+------------------------------------------------------------------+
                                      |
                 +--------------------+--------------------+
                 v                    v                    v
           +----------+         +----------+         +----------+
           |  status  |         |  chunk   |         | complete |
           | (update) |         |(streaming)|        | (finish) |
           +----------+         +----------+         +----------+
                 |                    |                    |
                 +--------------------+--------------------+
                                      v
                           WebSocket send_json()
```

### Detailed Workflow Breakdown

#### Phase 1: WebSocket Message Reception

**Code Location**: `apps/chat_agent/consumers/chat_consumer.py:157-175`

```python
async def receive_json(self, content: dict) -> None:
    message_type = content.get("type", "")

    if message_type == MessageType.CHAT_MESSAGE.value:
        await self._handle_chat_message(content)
    elif message_type == MessageType.CHAT_STOP.value:
        await self._handle_stop_generation()
```

**Message Format**:
```json
{
    "type": "chat.message",
    "content": "What is binding in snowboarding?"
}
```

#### Phase 2: Agent Selection and Initialization

**Code Location**: `apps/chat_agent/consumers/chat_consumer.py:176-238`

```python
async def _handle_chat_message(self, content: dict) -> None:
    query = content.get("content", "").strip()

    # Get conversation
    conversation = await self._get_or_create_conversation()

    # Select Agent based on agent_type
    agent = self._get_agent(conversation.agent_type)  # text_rag or graph_rag

    # Run Agent with streaming
    async for event_type, data in agent.run_with_streaming(...):
        if event_type == "status":
            await self.send_json({"type": "chat.status", "status": data})
        elif event_type == "chunk":
            await self.send_json({"type": "chat.response.chunk", "content": data})
        elif event_type == "complete":
            await self.send_json({"type": "chat.response.complete", ...})
```

### Agent Core Workflow

#### Text RAG Agent (Basic Version)

**Code Location**: `apps/chat_agent/agents/text_rag_agent.py`

```
+------------------------------------------------------------------+
|                    Text RAG Agent Workflow                        |
+------------------------------------------------------------------+

Step 1: retrieve (Retrieval Phase)
--------------------------------------------------------------------------------
|
|  _retrieve_node()
|       |
|       v
|  ContextService.assemble_context()
|       |
|       +---------------------+---------------------+
|       v                     v                     v
|  +--------------+    +--------------+    +--------------+
|  | Get History  |    | Hybrid Search|    | Assemble     |
|  | (PostgreSQL) |    | (Milvus)     |    | Context      |
|  +--------------+    +--------------+    +--------------+
|
|  Output: {context, sources, history, retrieval_scores}
+------------------------------------------------------------------+
                                      |
                                      v
Step 2: generate (Generation Phase)
--------------------------------------------------------------------------------
|
|  _generate_node()
|       |
|       v
|  LLMService.build_rag_prompt()
|       |
|       v
|  LLMService.stream_generate() --[streaming]--> chunks
|       |
|       v
|  Output: {response, response_chunks, token_count}
+------------------------------------------------------------------+
                                      |
                                      v
Step 3: save (Save Phase)
--------------------------------------------------------------------------------
|
|  _save_node()
|       |
|       +---------------------+
|       v                     v
|  +--------------+    +--------------+
|  | Save User    |    | Save Asst    |
|  | Message      |    | Message      |
|  | (PostgreSQL) |    | (PostgreSQL) |
|  +--------------+    +--------------+
|       |                     |
|       +----------+----------+
|                  v
|         Store Message Embeddings (Milvus)
|                  |
|                  v
|         Output: {message_id}
+------------------------------------------------------------------+
```

#### Graph RAG Agent (Enhanced Version)

**Code Location**: `apps/chat_agent/agents/graph_rag_agent.py`

The difference from Text RAG is the additional `entity_context` node:

```
+------------------------------------------------------------------+
|                  Graph RAG Agent Extra Step                      |
+------------------------------------------------------------------+

Step 1.5: entity_context (Entity Context Enrichment)
--------------------------------------------------------------------------------
|
|  _entity_context_node()
|       |
|       v
|  _extract_entities(query)
|       |
|       v
|  _get_entity_context(entities)
|       |
|       +---------------------+
|       v                     v
|  +--------------+    +--------------+
|  | Query Entity |    | Get Graph    |
|  | Relations    |    | Context      |
|  | (Neo4j)      |    | (Neo4j)      |
|  +--------------+    +--------------+
|       |                     |
|       +----------+----------+
|                  v
|         Append to context: "=== Knowledge Graph Context ==="
|                  |
|                  v
|         Output: {context: enriched_context, sources: updated_sources}
+------------------------------------------------------------------+
```

### Retrieval Phase Details

**Code Location**: `apps/chat_agent/services/context_service.py`

```
+------------------------------------------------------------------+
|                  ContextService.assemble_context()               |
+------------------------------------------------------------------+

Input: query, conversation_id, user_id
Output: {context, sources, history, retrieval_scores}
                                      |
        +-----------------------------+-----------------------------+
        v                             v                             v
+---------------+            +---------------+            +---------------+
| Get History   |            | Hybrid Search |            | Format       |
| _get_history()|            | _retrieve_docs|            | Context      |
+-------+-------+            +-------+-------+            +-------+-------+
        |                            |                            |
        v                            v                            |
+---------------+            +---------------+                    |
| PostgreSQL    |            | SearchService |                    |
| Message table |            | .hybrid_search|                    |
| (last N msgs) |            +-------+-------+                    |
+---------------+                    |                            |
                                     v                            |
                     +-------------------------------+            |
                     |    SearchService Workflow     |            |
                     +-------------------------------+            |
                                     |                            |
        +----------------------------+------------------------+   |
        v                            v                        v   |
+---------------+            +---------------+      +-----------+ |
| VectorRetriever|            |KeywordRetriever|     |GraphRetriever|
| (Milvus Vector)|            | (PostgreSQL FTS)|    | (Neo4j)    | |
+-------+-------+            +-------+-------+      +-----+-----+ |
        |                            |                    |       |
        +----------------------------+--------------------+       |
                                     v                            |
                           +---------------+                      |
                           |  RRF Fusion   |                      |
                           | (Result Merge)|                      |
                           +-------+-------+                      |
                                   |                              |
                                   v                              |
                          Retrieved Results (top_k docs)          |
                                                                  |
        +---------------------------------------------------------+
        v
+------------------------------------------------------------------+
|                      Context Formatting                          |
|                                                                  |
|  === Conversation History ===                                    |
|  User: Previous question...                                      |
|  Assistant: Previous answer...                                   |
|                                                                  |
|  === Relevant Documents ===                                      |
|  [Document 1]                                                    |
|  Content: Retrieved document content...                          |
|  Score: 0.892                                                    |
|  ...                                                             |
|                                                                  |
|  (Truncated if exceeds MAX_CONTEXT_TOKENS)                       |
+------------------------------------------------------------------+
```

### Hybrid Search Details

**Code Location**: `apps/document_rag_search/services/search_service.py`

```
+------------------------------------------------------------------+
|                   SearchService.hybrid_search()                  |
+------------------------------------------------------------------+

Input: HybridSearchRequest {query, top_k, use_vector, use_keyword, use_graph}
Output: SearchResponse {results, total, query_time_ms, retrievers_used}
                                      |
                                      v
+------------------------------------------------------------------+
|  Step 1: Generate Query Embedding                                |
|  EmbeddingService.embed_query(query) -> embedding vector         |
+------------------------------------------------------------------+
                                      |
                                      v
+------------------------------------------------------------------+
|  Step 2: Execute Multiple Retrievers in Parallel                 |
|                                                                  |
|  +------------------------------------------------------------+ |
|  |  VectorRetriever (Milvus)                                  | |
|  |  -----------------------                                   | |
|  |  1. Build filter_expr (user_id, document_ids)              | |
|  |  2. MilvusService.search()                                 | |
|  |     - collection: documents                                | |
|  |     - anns_field: text_dense / summary_dense               | |
|  |     - metric: COSINE                                       | |
|  |  3. Return: RetrieverResult {items, query_time_ms, total}  | |
|  +------------------------------------------------------------+ |
|                                                                  |
|  +------------------------------------------------------------+ |
|  |  KeywordRetriever (PostgreSQL FTS)                         | |
|  |  ---------------------------------                         | |
|  |  1. Use PostgreSQL full-text search                        | |
|  |  2. DocumentChunk.objects.filter(content__search=query)    | |
|  |  3. Return: RetrieverResult {items, query_time_ms, total}  | |
|  +------------------------------------------------------------+ |
|                                                                  |
|  +------------------------------------------------------------+ |
|  |  GraphRetriever (Neo4j)                                    | |
|  |  ----------------------                                    | |
|  |  1. Extract entities from query                            | |
|  |  2. Neo4j graph traversal for related nodes                | |
|  |  3. Return: RetrieverResult {items, query_time_ms, total}  | |
|  +------------------------------------------------------------+ |
|                                                                  |
+------------------------------------------------------------------+
                                      |
                                      v
+------------------------------------------------------------------+
|  Step 3: RRF Fusion (Reciprocal Rank Fusion)                    |
|                                                                  |
|  Formula: RRF_score(d) = sum (weight_r / (k + rank_r(d)))       |
|                                                                  |
|  Default Weights:                                                |
|  - vector: 0.4                                                   |
|  - keyword: 0.3                                                  |
|  - graph: 0.3                                                    |
|  - k = 60 (RRF parameter)                                        |
|                                                                  |
|  Output: List[RankedResult] sorted by fused_score               |
+------------------------------------------------------------------+
                                      |
                                      v
+------------------------------------------------------------------+
|  Step 4: Return SearchResponse                                  |
|                                                                  |
|  {                                                               |
|    "results": [                                                  |
|      {"chunk_id": "...", "document_id": "...", "text": "..."}    |
|    ],                                                            |
|    "total": 5,                                                   |
|    "query_time_ms": 384.23,                                      |
|    "retrievers_used": ["vector", "keyword"]                      |
|  }                                                               |
+------------------------------------------------------------------+
```

### LLM Generation Phase

**Code Location**: `apps/chat_agent/services/llm_service.py`

```
+------------------------------------------------------------------+
|                      LLM Generation Phase                        |
+------------------------------------------------------------------+

Input: query, context, history
Output: Streaming response chunks
                                      |
                                      v
+------------------------------------------------------------------+
|  Step 1: Build Prompt                                           |
|                                                                  |
|  build_rag_prompt()                                              |
|  ------------------                                              |
|                                                                  |
|  messages = [                                                    |
|    {                                                             |
|      "role": "system",                                           |
|      "content": "You are a helpful AI assistant...               |
|                  === Context ===                                 |
|                  [Retrieved context content]"                    |
|    },                                                            |
|    {"role": "user", "content": "Previous question 1"},           |
|    {"role": "assistant", "content": "Previous answer 1"},        |
|    {"role": "user", "content": "Current user question"}          |
|  ]                                                               |
+------------------------------------------------------------------+
                                      |
                                      v
+------------------------------------------------------------------+
|  Step 2: Call Qwen API (OpenAI Compatible)                      |
|                                                                  |
|  AsyncOpenAI.chat.completions.create(                           |
|      model="qwen-plus",                                          |
|      messages=messages,                                          |
|      temperature=0.7,                                            |
|      max_tokens=2000,                                            |
|      stream=True   <- Key: Enable streaming output               |
|  )                                                               |
+------------------------------------------------------------------+
                                      |
                                      v
+------------------------------------------------------------------+
|  Step 3: Stream Response Chunks                                 |
|                                                                  |
|  async for chunk in response:                                    |
|      if chunk.choices[0].delta.content:                          |
|          yield chunk.choices[0].delta.content                    |
|                                                                  |
|  Each chunk is immediately sent to client via WebSocket          |
+------------------------------------------------------------------+
```

### Complete Message Flow Example

```
+------------------------------------------------------------------+
|                     Complete Message Flow Example                |
+------------------------------------------------------------------+

Client -> Server:
--------------------------------------------------------------------------------
{
    "type": "chat.message",
    "content": "What is binding in snowboarding?"
}

Server -> Client (Text RAG):
--------------------------------------------------------------------------------
{"type": "chat.status", "status": "retrieving"}        <- Retrieval started

{"type": "chat.status", "status": "generating"}        <- Generation started

{"type": "chat.response.chunk", "content": "In snowboarding, ", "is_final": false}
{"type": "chat.response.chunk", "content": "**bindings** are ", "is_final": false}
{"type": "chat.response.chunk", "content": "the devices that ", "is_final": false}
... (more chunks)

{"type": "chat.status", "status": "saving"}            <- Saving started

{
    "type": "chat.response.complete",
    "message_id": "da1144bc-9d94-4902-850a-75c39e99105d",
    "sources": [
        {"chunk_id": "8c3dac80-...", "text": "...", "score": 1.0},
        {"chunk_id": "adc0144b-...", "text": "...", "score": 0.74},
        {"chunk_id": "9c63bc83-...", "text": "...", "score": 0.48}
    ],
    "token_count": 262
}

--------------------------------------------------------------------------------
Server -> Client (Graph RAG):
--------------------------------------------------------------------------------
{"type": "chat.status", "status": "retrieving"}        <- Retrieval started
{"type": "chat.status", "status": "analyzing_entities"} <- Entity analysis (Graph RAG only)
{"type": "chat.status", "status": "generating"}        <- Generation started
... (chunks)
{"type": "chat.status", "status": "saving"}            <- Saving started
{"type": "chat.response.complete", ...}                <- Completed
```

### Modules and Files Summary

| Module | File | Responsibility |
|--------|------|----------------|
| **chat_agent** | `consumers/chat_consumer.py` | WebSocket connection management, message routing |
| **chat_agent** | `agents/base.py` | Agent base class, defines core nodes |
| **chat_agent** | `agents/text_rag_agent.py` | Text RAG Agent implementation |
| **chat_agent** | `agents/graph_rag_agent.py` | Graph RAG Agent implementation |
| **chat_agent** | `services/context_service.py` | Context assembly service |
| **chat_agent** | `services/llm_service.py` | LLM invocation service |
| **chat_agent** | `services/conversation_service.py` | Conversation management service |
| **document_rag_search** | `services/search_service.py` | Hybrid search service |
| **document_rag_search** | `retrievers/vector_retriever.py` | Milvus vector retrieval |
| **document_rag_search** | `retrievers/keyword_retriever.py` | PostgreSQL FTS retrieval |
| **document_rag_search** | `retrievers/graph_retriever.py` | Neo4j graph retrieval |
| **document_rag_search** | `ranking/rrf_fusion.py` | RRF result fusion |
| **embedding_engine** | `services/embedding_service.py` | Embedding service |
| **milvus_database_controller** | `services/milvus_service.py` | Milvus database operations |
| **neo4j_database_controller** | `services/neo4j_query_service.py` | Neo4j graph database operations |

### Key Data Structures

#### AgentState (LangGraph State)

```python
# apps/chat_agent/agents/state.py
class AgentState(TypedDict):
    conversation_id: str
    user_id: str
    query: str                    # User question
    context: str                  # Assembled context
    sources: list[dict]           # Retrieval sources
    history: list[dict]           # Conversation history
    response: str                 # LLM complete response
    response_chunks: list[str]    # Streaming response fragments
    retrieval_scores: dict        # Retrieval scores
    token_count: int              # Token count
    error: str | None             # Error message
    message_id: str | None        # Saved message ID
```

---

## Directory Structure

```
dev_utils/               # Development environment tools
  docker-compose.yml     # Docker container configuration
docs/
  architecture.md        # Architecture design documentation
  code_style.md          # Code standards
  dev_plan.md            # Development plan
  reference.md           # Reference materials
config/
  settings/
    base.py              # Common configuration
    local.py             # Development environment override (DEBUG=True)
    production.py        # Production environment configuration
  urls.py                # Root URL configuration
  celery.py              # Celery application configuration
apps/
  accounts/              # User authentication, registration, profile
  documents_parser/      # Document parsing and processing
  document_pipeline_manager/  # Document processing pipeline management
  object_storage_controller/  # S3/MinIO object storage controller
  milvus_database_controller/ # Milvus database controller
  neo4j_database_controller/  # Neo4j database controller
  embedding_engine/      # Text embedding
  document_rag_search/   # RAG search module
  chat_agent/            # Chat agent and WebSocket manager
core/
  exceptions.py          # Custom API exceptions
  permissions.py         # Shared permission classes
  pagination.py          # Custom pagination
tests/                   # Project-level tests
env/                     # Environment configuration files
pyproject.toml           # Poetry configuration file
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- Poetry
- Docker & Docker Compose
- PostgreSQL 14+
- Redis

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd melon

# Install dependencies
poetry install

# Set up environment variables
cp env/.env.example env/.env.local

# Run database migrations
poetry run python manage.py migrate

# Start development server
DJANGO_SETTINGS_MODULE=config.settings.local poetry run python manage.py runserver

# Or use Daphne for WebSocket support
DJANGO_SETTINGS_MODULE=config.settings.local poetry run daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

### Running Tests

```bash
# Run all tests
pytest --cov=apps --cov-report=term-missing

# Run specific app tests
pytest apps/chat_agent/tests/ -v

# Run with parallel execution
pytest -n auto
```

---

## API Documentation

### REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/accounts/auth/login/` | POST | User login, returns JWT token |
| `/api/v1/accounts/auth/register/` | POST | User registration |
| `/api/v1/chat/conversations/` | GET/POST | List/Create conversations |
| `/api/v1/chat/conversations/{id}/` | GET/DELETE | Get/Delete conversation |
| `/api/v1/chat/conversations/{id}/messages/` | GET | Get message history |
| `/api/v1/documents/` | GET/POST | List/Upload documents |
| `/api/v1/search/` | POST | Hybrid search |

### WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| `ws://localhost:8000/ws/chat/{conversation_id}/` | Real-time chat |

**Authentication**: Pass JWT token via `Authorization: Bearer <token>` header or `?token=<jwt>` query parameter.

---

## License

MIT License
