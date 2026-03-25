# Chat Agent Module

## Overview

This module provides real-time conversational AI capabilities based on RAG (Retrieval-Augmented Generation) technology with WebSocket streaming support.

## Features

- **Real-time Chat**: WebSocket-based real-time communication
- **RAG Integration**: Document retrieval + LLM generation
- **Multiple Agent Types**: Text RAG and Graph RAG agents
- **Conversation History**: Persistent storage with semantic search
- **Streaming Responses**: Token-by-token streaming output

---

## Architecture

### Layer Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     WebSocket Layer                              │
│                    ChatConsumer                                  │
│         (Auth, Connection Management, Message Routing)           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      Agent Layer                                 │
│  ┌──────────────────────┐  ┌──────────────────────┐             │
│  │   Text RAG Agent     │  │   Graph RAG Agent    │             │
│  │   (LangGraph)        │  │   (LangGraph)        │             │
│  └──────────┬───────────┘  └──────────┬───────────┘             │
└─────────────┼─────────────────────────┼─────────────────────────┘
              │                         │
┌─────────────▼─────────────────────────▼─────────────────────────┐
│                     Service Layer                                │
│  ConversationService  │  ContextService  │  LLMService          │
│  (Session Management) │  (Context Build) │  (Stream Generate)   │
└───────────────────────┴──────────────────┴──────────────────────┘
              │                 │                     │
┌─────────────▼─────────────────▼─────────────────────▼───────────┐
│                       Data Layer                                 │
│  PostgreSQL  │    Milvus    │    Neo4j    │    Qwen API         │
│  (Session)   │  (Vector)    │  (Graph)    │    (LLM)            │
└──────────────┴──────────────┴─────────────┴─────────────────────┘
```

---

## Core Workflow

### 1. User Initiates Conversation

```javascript
// User sends message via WebSocket
ws.send(JSON.stringify({
    type: 'chat.message',
    content: 'What is machine learning?'
}));
```

### 2. WebSocket Layer Processing

```python
# ChatConsumer.receive_json() receives message
async def receive_json(self, content: dict) -> None:
    if content.get("type") == "chat.message":
        await self._handle_chat_message(content)
```

### 3. Agent Selection and Execution

```python
# Select agent based on conversation type
agent = TextRAGAgent()  # or GraphRAGAgent()

# Agent executes via LangGraph state machine
async for state in agent.run(conversation_id, query, user_id):
    # Stream each chunk
    await self.send_json({
        "type": "chat.response.chunk",
        "content": state["response_chunks"][-1]
    })
```

### 4. RAG Retrieval Flow

**retrieve node**:
```python
async def _retrieve_node(self, state: AgentState) -> dict:
    # 1. ContextService assembles context
    context_result = await self._context_service.assemble_context(
        query=state["query"],
        conversation_id=state["conversation_id"],
        top_k=5,
        history_limit=10
    )
    # 2. Return retrieved documents and history
    return {
        "context": context_result.context,
        "sources": context_result.sources,
        "history": context_result.history
    }
```

**generate node**:
```python
async def _generate_node(self, state: AgentState) -> dict:
    # 1. LLMService builds prompt
    messages = self._llm_service.build_prompt(
        system_prompt=SYSTEM_PROMPT,
        context=state["context"],
        history=state["history"],
        query=state["query"]
    )

    # 2. Stream call to Qwen API
    async for chunk in self._llm_service.stream_generate(messages):
        yield {"response_chunks": [chunk]}
```

**save node**:
```python
async def _save_node(self, state: AgentState) -> dict:
    # 1. Save user message to PostgreSQL
    user_msg = await self._conversation_service.add_message(
        conversation_id, "user", query
    )

    # 2. Save assistant response
    assistant_msg = await self._conversation_service.add_message(
        conversation_id, "assistant",
        content=state["response"],
        sources=state["sources"]
    )

    # 3. Store message embedding to Milvus chat_history
    await self._conversation_service.store_message_embedding(assistant_msg)
```

---

## Key Components

### LangGraph State Machine

```python
# TextRAGAgent linear flow
retrieve → generate → save

# GraphRAGAgent with entity context
retrieve → entity_context → generate → save
```

State defined via TypedDict for type safety:
```python
class AgentState(TypedDict):
    conversation_id: str
    query: str
    context: str           # Retrieved context
    sources: list[dict]    # Source documents
    response: str          # Complete response
    response_chunks: list[str]  # Streaming chunks
```

### Context Assembly (ContextService)

```python
def assemble_context(self, query: str, conversation_id: str) -> ContextResult:
    # 1. Call Phase 10 SearchService for hybrid search
    search_result = self._search_service.hybrid_search(
        query=query, top_k=5
    )

    # 2. Search similar history messages from Milvus chat_history
    history = self._conversation_service.search_similar_messages(
        query_embedding=query_embedding,
        conversation_id=conversation_id
    )

    # 3. Format context window (limit token count)
    context = self._format_context_window(
        search_results=search_result,
        history_messages=history,
        max_tokens=4000
    )

    return ContextResult(context=context, sources=sources, history=history)
```

### Streaming LLM Calls (LLMService)

```python
async def stream_generate(self, messages: list[dict]) -> AsyncIterator[str]:
    # Use OpenAI-compatible API to call Qwen
    stream = await self._client.chat.completions.create(
        model="qwen-turbo",
        messages=messages,
        stream=True,
        temperature=0.7
    )

    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

---

## Data Storage Design

| Storage | Purpose | Content |
|---------|---------|---------|
| PostgreSQL | Session metadata | Conversation, Message models |
| Milvus `chat_history` | Conversation vectors | message_id, embedding, role, conversation_id |
| Milvus `documents` | Document vectors | Implemented in Phase 6, for retrieval |
| Neo4j | Entity relationships | Used by GraphRAG, queries related entities |

---

## Quick Start

### 1. Create Conversation

```bash
POST /api/v1/chat/conversations/
{
    "title": "My Chat",
    "agent_type": "text_rag"
}
```

### 2. Connect WebSocket

**Important**: WebSocket connections require JWT authentication. The project uses a custom `JWTAuthMiddleware` instead of Django's default `AuthMiddlewareStack` to support JWT token authentication.

#### Authentication Methods

**Method 1: Authorization Header (Recommended)**

```bash
# Using wscat
wscat -c "ws://localhost:8000/ws/chat/<conversation_id>/" \
    -H "Authorization: Bearer <jwt_token>"
```

**Method 2: Query Parameter**

```javascript
// Browser WebSocket API doesn't support custom headers
// Use query parameter instead
const ws = new WebSocket(
    `ws://localhost:8000/ws/chat/${conversationId}/?token=${jwtToken}`
);
```

#### Connection Flow

```
Client Connect
     │
     ▼
JWTAuthMiddleware
     │
     ├─► Extract token from Authorization header or query parameter
     │
     ├─► Validate JWT signature using rest_framework_simplejwt
     │
     ├─► Decode user_id from token payload
     │
     └─► Query User from database and set scope["user"]
         │
         ▼
     ChatConsumer
         │
         └─► Check scope["user"] - reject anonymous users
```

#### Error Handling

If authentication fails:
- Invalid/expired token: Connection accepted but user is `AnonymousUser`, then rejected by `ChatConsumer`
- Missing token: Connection accepted but user is `AnonymousUser`, then rejected by `ChatConsumer`

```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data);
};
```

### 3. Send Message

```javascript
ws.send(JSON.stringify({
    type: 'chat.message',
    content: 'What is machine learning?'
}));
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat/conversations/` | Create conversation |
| GET | `/api/v1/chat/conversations/` | List conversations |
| GET | `/api/v1/chat/conversations/{id}/` | Get conversation |
| DELETE | `/api/v1/chat/conversations/{id}/` | Delete conversation |
| GET | `/api/v1/chat/conversations/{id}/messages/` | Get messages |

---

## WebSocket Events

### Client → Server

```json
{
    "type": "chat.message",
    "content": "User question"
}
```

### Server → Client

```json
// Status update
{"type": "chat.status", "status": "retrieving"}

// Response chunk
{"type": "chat.response.chunk", "content": "...", "is_final": false}

// Completion
{
    "type": "chat.response.complete",
    "message_id": "uuid",
    "sources": [...],
    "token_count": 100
}

// Error
{"type": "chat.error", "error_code": "...", "message": "..."}
```

---

## Configuration

Configuration is in `config/settings/base.py` under `CHAT_AGENT_CONFIG`:

```python
CHAT_AGENT_CONFIG = {
    "default_agent_type": "text_rag",
    "default_temperature": 0.7,
    "default_max_tokens": 2000,
    "max_context_tokens": 4000,
    "history_limit": 10,
    "search_top_k": 5,
}
```

---

## Agent Types

### Text RAG Agent
- Basic Q&A with document retrieval
- Linear workflow: retrieve → generate → save

### Graph RAG Agent
- Entity-aware context enrichment
- Uses Neo4j for relationship queries
- Workflow: retrieve → entity_context → generate → save

---

## Architecture Advantages

1. **Real-time**: WebSocket + streaming output, users see word-by-word generation
2. **Extensible**: LangGraph state machine makes it easy to add new nodes (intent recognition, multi-turn dialogue)
3. **Context-aware**: Hybrid search + conversation history provides precise answers
4. **Persistent**: PostgreSQL + Milvus dual storage supports history backtracking

---

## Testing

```bash
# Run all tests
pytest apps/chat_agent/tests/ -v

# Run specific test file
pytest apps/chat_agent/tests/test_models.py -v

# Run with coverage
pytest apps/chat_agent/tests/ --cov=apps/chat_agent
```

---

## Dependencies

- Django Channels (WebSocket)
- LangGraph (Agent framework)
- OpenAI-compatible API (Qwen)
- Milvus (Vector search)
- Neo4j (Graph RAG, optional)
- rest_framework_simplejwt (JWT authentication)

---

## WebSocket Authentication

### JWTAuthMiddleware

The project uses a custom `JWTAuthMiddleware` for WebSocket authentication because Django Channels' default `AuthMiddlewareStack` only supports session-based authentication, while the REST API uses JWT tokens.

**Code Location**: `apps/chat_agent/middleware.py`

**ASGI Configuration** (`config/asgi.py`):

```python
from apps.chat_agent.middleware import JWTAuthMiddleware

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddleware(URLRouter(websocket_urlpatterns))
    ),
})
```

### Token Extraction Priority

1. **Authorization header** (Bearer token) - preferred
2. **Query parameter** (`?token=<jwt>`) - for browser compatibility

### Implementation Details

```python
class JWTAuthMiddleware:
    """JWT authentication middleware for Django Channels WebSocket."""

    async def __call__(self, scope, receive, send):
        # Extract token from header or query string
        token = self._get_token(scope)

        if token:
            # Validate JWT and get user
            user = await self._get_user_from_token(token)
            scope["user"] = user

        return await self.inner(scope, receive, send)
```

---

## File Structure

```
apps/chat_agent/
├── __init__.py
├── apps.py
├── constants.py          # Enums and constants
├── exceptions.py         # Custom exceptions
├── middleware.py         # JWT authentication middleware for WebSocket
├── models.py             # Conversation, Message models
├── serializers.py        # DRF serializers
├── urls.py               # URL routing
├── agents/
│   ├── __init__.py
│   ├── base.py           # Abstract base agent
│   ├── state.py          # AgentState TypedDict
│   ├── text_rag_agent.py # Text RAG agent
│   └── graph_rag_agent.py# Graph RAG agent
├── consumers/
│   ├── __init__.py
│   └── chat_consumer.py  # WebSocket consumer
├── services/
│   ├── __init__.py
│   ├── conversation_service.py  # Conversation management
│   ├── context_service.py       # Context assembly
│   └── llm_service.py           # LLM streaming
├── views/
│   ├── __init__.py
│   └── chat_views.py     # REST API views
├── tests/
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_services.py
│   ├── test_agents.py
│   ├── test_middleware.py    # JWT middleware tests
│   └── ...
├── migrations/
│   └── 0001_initial.py
└── docs/
    ├── README.md
    └── manual_test.md
```
