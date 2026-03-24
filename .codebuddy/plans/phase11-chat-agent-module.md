# Phase 11: Chat Agent Module Implementation Plan

## Overview

Implement chat agent module for melon RAG project, providing real-time conversational AI capabilities based on RAG (Retrieval-Augmented Generation) technology with WebSocket streaming support.

## Status: Ready for Implementation

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Phase 2: Basic Setup | ✅ Completed | Django project structure ready |
| Phase 3: User Management Module | ✅ Completed | Authentication available |
| Phase 4: Document Parser Module | ✅ Completed | DocumentChunk model available |
| Phase 5: Object Storage Controller | ✅ Completed | File storage ready |
| Phase 6: Milvus Database Controller | ✅ Completed | SearchManager with vector/hybrid/BM25 search |
| Phase 7: Neo4j Database Controller | ✅ Completed | QueryManager with graph queries |
| Phase 8: Embedding Engine | ✅ Completed | EmbeddingService with embed_query |
| Phase 9: Document Pipeline Manager | ✅ Completed | Documents processed and indexed |
| Phase 10: Document RAG Search Module | ✅ Completed | SearchService with hybrid search |

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Communication Layer** | Django Channels + WebSocket | Real-time bidirectional communication for streaming responses |
| **Agent Framework** | LangGraph | Better state management for multi-turn conversations, supports cyclic graphs |
| **Agent Types** | Text RAG Agent + Graph RAG Agent | Text RAG for basic Q&A, Graph RAG for relationship-aware queries |
| **LLM Provider** | Qwen API (Alibaba) | Already configured in project, supports streaming |
| **Conversation Storage** | PostgreSQL + Milvus | PostgreSQL for metadata, Milvus for conversation embeddings |
| **Streaming Response** | AsyncIterator + WebSocket chunks | Real-time token-by-token output |
| **Context Assembly** | SearchService integration | Reuse Phase 10 hybrid search for retrieval |

---

## Architecture Overview

### Layered Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     WebSocket Layer                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  ChatConsumer (Django Channels)                             ││
│  │  - Connection management                                     ││
│  │  - Message routing                                           ││
│  │  - Authentication                                            ││
│  └─────────────────────────────────────────────────────────────┘│
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      Agent Layer                                 │
│  ┌──────────────────────┐  ┌──────────────────────┐             │
│  │   Text RAG Agent     │  │   Graph RAG Agent    │             │
│  │   (LangGraph)        │  │   (LangGraph)        │             │
│  │   - Basic Q&A        │  │   - Entity context   │             │
│  │   - Simple retrieval │  │   - Graph traversal  │             │
│  └──────────┬───────────┘  └──────────┬───────────┘             │
└─────────────┼─────────────────────────┼─────────────────────────┘
              │                         │
┌─────────────▼─────────────────────────▼─────────────────────────┐
│                     Service Layer                                │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────────┐  │
│  │ConversationSvc │ │ ContextService │ │   LLMService        │  │
│  │- CRUD          │ │ - Assembly     │ │ - Streaming         │  │
│  │- History       │ │ - Formatting   │ │ - Prompt building   │  │
│  └────────┬───────┘ └───────┬────────┘ └──────────┬─────────┘  │
└───────────┼─────────────────┼─────────────────────┼─────────────┘
            │                 │                     │
┌───────────▼─────────────────▼─────────────────────▼─────────────┐
│                       Data Layer                                 │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────┐           │
│  │PostgreSQL  │  │   Milvus     │  │   Qwen API    │           │
│  │Conversation│  │ chat_history │  │   (LLM)       │           │
│  │   Message  │  │              │  │               │           │
│  └────────────┘  └──────────────┘  └───────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Message (WebSocket)
    │
    ▼
ChatConsumer.receive()
    │
    ├── Authentication Check
    │
    ├── Parse Message
    │
    ▼
Agent Selection (Text RAG / Graph RAG)
    │
    ├── ContextService.assemble_context()
    │   │
    │   ├── SearchService.hybrid_search()  [Phase 10]
    │   │   └── Vector + Keyword + Graph Retrieval
    │   │
    │   ├── ConversationService.get_history()
    │   │   └── Milvus chat_history search
    │   │
    │   └── Format context window
    │
    ├── LLMService.stream_generate()
    │   │
    │   ├── Build prompt with context
    │   │
    │   └── Call Qwen API (streaming)
    │       │
    │       ▼
    │   WebSocket send chunk (real-time)
    │
    ▼
ConversationService.save_conversation()
    │
    ├── PostgreSQL: Save Message
    │
    └── Milvus: Store message embedding
        │
        ▼
WebSocket send complete
```

---

## Submodules

### Submodule 11.1: Django Channels Configuration

**Purpose**: Configure Django Channels for WebSocket support.

**Technical Approach**:
- Add `channels` to INSTALLED_APPS
- Configure ASGI application with ChannelLayers
- Set up Redis as channel layer backend
- Create routing configuration

**Files to Create/Modify**:

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `config/asgi.py` | ASGI application configuration | 50 |
| `config/routing.py` | WebSocket URL routing | 30 |
| `config/settings/base.py` | Add CHANNEL_LAYERS config | 30 |

**Tasks**:

#### Task 11.1.1: Install and Configure Django Channels
- **Description**: Add channels and channels_redis to dependencies, configure ASGI application
- **Acceptance Criteria**:
  - [ ] `channels` and `channels_redis` added to pyproject.toml
  - [ ] ASGI_APPLICATION configured in settings
  - [ ] CHANNEL_LAYERS configured with Redis backend
  - [ ] WebSocket connection can be established
- **Technical Notes**: Use existing Redis instance (REDIS_URL from settings)
- **Dependencies**: None
- **Estimated Time**: 2 hours

#### Task 11.1.2: Create WebSocket Routing
- **Description**: Create routing configuration for WebSocket endpoints
- **Acceptance Criteria**:
  - [ ] `config/routing.py` created with URLRouter
  - [ ] ChatConsumer routed to `/ws/chat/<conversation_id>/`
  - [ ] AuthMiddlewareStack wraps consumer
- **Technical Notes**: Use AuthMiddlewareStack for authentication
- **Dependencies**: Task 11.1.1
- **Estimated Time**: 1 hour

---

### Submodule 11.2: Data Models

**Purpose**: Define Conversation and Message models for persistent storage.

**Technical Approach**:
- Create Conversation model linked to User
- Create Message model linked to Conversation
- Support message roles (user, assistant, system)
- Store message metadata for RAG context

**Files to Create**:

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `apps/chat_agent/__init__.py` | App initialization | 10 |
| `apps/chat_agent/apps.py` | App configuration | 15 |
| `apps/chat_agent/models.py` | Conversation and Message models | 150 |
| `apps/chat_agent/migrations/0001_initial.py` | Initial migration | Auto-generated |

**Model Design**:

```python
# apps/chat_agent/models.py

class Conversation(models.Model):
    """Conversation session model."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    title = models.CharField(max_length=255, blank=True, default="")
    
    # Configuration
    agent_type = models.CharField(
        max_length=20,
        choices=[("text_rag", "Text RAG"), ("graph_rag", "Graph RAG")],
        default="text_rag",
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "conversations"
        ordering = ["-updated_at"]


class Message(models.Model):
    """Message in a conversation."""
    
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    
    # RAG context
    sources = models.JSONField(default=list, blank=True)  # List of source chunk IDs
    retrieval_scores = models.JSONField(default=dict, blank=True)  # Retrieval scores
    
    # Metadata
    token_count = models.PositiveIntegerField(default=0)
    model_used = models.CharField(max_length=50, blank=True, default="")
    
    # Milvus reference
    embedding_id = models.CharField(max_length=100, blank=True, default="")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]
```

**Tasks**:

#### Task 11.2.1: Create Chat Agent App Structure
- **Description**: Create Django app with proper structure
- **Acceptance Criteria**:
  - [ ] `apps/chat_agent/` directory created
  - [ ] `__init__.py`, `apps.py` created
  - [ ] App registered in INSTALLED_APPS
- **Technical Notes**: Follow existing app structure pattern
- **Dependencies**: Task 11.1.1
- **Estimated Time**: 0.5 hours

#### Task 11.2.2: Implement Conversation Model
- **Description**: Create Conversation model with user relationship
- **Acceptance Criteria**:
  - [ ] Model defined with UUID primary key
  - [ ] Foreign key to User model
  - [ ] agent_type field with choices
  - [ ] Timestamps (created_at, updated_at)
  - [ ] Migration created
- **Technical Notes**: Use AUTH_USER_MODEL for user reference
- **Dependencies**: Task 11.2.1
- **Estimated Time**: 1 hour

#### Task 11.2.3: Implement Message Model
- **Description**: Create Message model with conversation relationship
- **Acceptance Criteria**:
  - [ ] Model defined with role choices (user, assistant, system)
  - [ ] Foreign key to Conversation
  - [ ] sources and retrieval_scores JSON fields
  - [ ] embedding_id for Milvus reference
  - [ ] Migration created
- **Technical Notes**: Store retrieval context for audit/debug
- **Dependencies**: Task 11.2.2
- **Estimated Time**: 1.5 hours

---

### Submodule 11.3: Service Layer

**Purpose**: Implement business logic services for conversation management and context assembly.

**Technical Approach**:
- ConversationService: CRUD operations for conversations and messages
- ContextService: Assemble context from search results and conversation history
- LLMService: Handle Qwen API calls with streaming support

**Files to Create**:

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `apps/chat_agent/services/__init__.py` | Services init | 20 |
| `apps/chat_agent/services/conversation_service.py` | Conversation management | 200 |
| `apps/chat_agent/services/context_service.py` | Context assembly | 180 |
| `apps/chat_agent/services/llm_service.py` | LLM streaming | 200 |

**Service Design**:

```python
# apps/chat_agent/services/conversation_service.py

class ConversationService:
    """Service for conversation management."""
    
    def create_conversation(
        self,
        user_id: str,
        agent_type: str = "text_rag",
        title: str = "",
    ) -> Conversation:
        """Create a new conversation."""
        pass
    
    def get_conversation(
        self,
        conversation_id: str,
        user_id: str,
    ) -> Conversation | None:
        """Get conversation by ID with user check."""
        pass
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sources: list[str] | None = None,
        retrieval_scores: dict | None = None,
    ) -> Message:
        """Add message to conversation."""
        pass
    
    def get_history(
        self,
        conversation_id: str,
        limit: int = 10,
    ) -> list[Message]:
        """Get recent conversation history."""
        pass
    
    def store_message_embedding(
        self,
        message: Message,
        embedding: list[float],
    ) -> str:
        """Store message embedding in Milvus chat_history collection."""
        pass
    
    def search_similar_messages(
        self,
        query_embedding: list[float],
        conversation_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        """Search similar messages from conversation history."""
        pass


# apps/chat_agent/services/context_service.py

class ContextService:
    """Service for context assembly."""
    
    def __init__(self) -> None:
        self._search_service = SearchService()
        self._conversation_service = ConversationService()
        self._embedding_service = EmbeddingService()
    
    def assemble_context(
        self,
        query: str,
        conversation_id: str,
        use_graph: bool = False,
        top_k: int = 5,
        history_limit: int = 5,
    ) -> ContextResult:
        """
        Assemble context for RAG generation.
        
        1. Get conversation history (from Milvus + PostgreSQL)
        2. Perform hybrid search via SearchService
        3. Combine and format context window
        """
        pass
    
    def _format_context_window(
        self,
        search_results: SearchResponse,
        history_messages: list[Message],
        max_tokens: int = 4000,
    ) -> str:
        """Format context window for LLM prompt."""
        pass


# apps/chat_agent/services/llm_service.py

class LLMService:
    """Service for LLM operations."""
    
    def __init__(self) -> None:
        self._config = QWEN_CONFIG
        self._client = OpenAI(
            api_key=self._config["api_key"],
            base_url=self._config["base_url"],
        )
    
    async def stream_generate(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncIterator[str]:
        """
        Stream generate response from LLM.
        
        Yields token chunks for real-time display.
        """
        pass
    
    def build_prompt(
        self,
        system_prompt: str,
        context: str,
        history: list[dict],
        query: str,
    ) -> list[dict]:
        """Build message list for LLM API."""
        pass
```

**Tasks**:

#### Task 11.3.1: Implement ConversationService
- **Description**: Create service for conversation CRUD and history management
- **Acceptance Criteria**:
  - [ ] create_conversation() implemented
  - [ ] get_conversation() with user authorization
  - [ ] add_message() with sources storage
  - [ ] get_history() returns recent messages
  - [ ] store_message_embedding() integrates with MilvusService
  - [ ] search_similar_messages() uses Milvus vector search
- **Technical Notes**: Integrate with MilvusService for chat_history collection
- **Dependencies**: Task 11.2.3
- **Estimated Time**: 3 hours

#### Task 11.3.2: Implement ContextService
- **Description**: Create service for context assembly
- **Acceptance Criteria**:
  - [ ] assemble_context() combines history + search results
  - [ ] Integrates with SearchService (Phase 10)
  - [ ] Integrates with ConversationService for history
  - [ ] _format_context_window() respects token limit
  - [ ] Returns ContextResult with sources
- **Technical Notes**: Use SearchService.hybrid_search() for retrieval
- **Dependencies**: Task 11.3.1, Phase 10
- **Estimated Time**: 2.5 hours

#### Task 11.3.3: Implement LLMService
- **Description**: Create service for LLM streaming generation
- **Acceptance Criteria**:
  - [ ] stream_generate() uses OpenAI-compatible API
  - [ ] AsyncIterator yields token chunks
  - [ ] build_prompt() constructs proper message format
  - [ ] Error handling for API failures
  - [ ] Timeout and retry logic
- **Technical Notes**: Qwen API is OpenAI-compatible
- **Dependencies**: Task 11.3.2
- **Estimated Time**: 2.5 hours

---

### Submodule 11.4: Agent Layer (LangGraph)

**Purpose**: Implement RAG agents using LangGraph for stateful conversation management.

**Technical Approach**:
- Create base RAG agent with LangGraph StateGraph
- Implement Text RAG Agent for basic Q&A
- Implement Graph RAG Agent for relationship-aware queries
- Support streaming output through state updates

**Files to Create**:

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `apps/chat_agent/agents/__init__.py` | Agents init | 15 |
| `apps/chat_agent/agents/base.py` | Base agent class | 100 |
| `apps/chat_agent/agents/text_rag_agent.py` | Text RAG agent | 180 |
| `apps/chat_agent/agents/graph_rag_agent.py` | Graph RAG agent | 200 |
| `apps/chat_agent/agents/state.py` | Agent state definitions | 80 |

**Agent Design**:

```python
# apps/chat_agent/agents/state.py

from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State for RAG agent."""
    
    # Conversation
    conversation_id: str
    user_id: str
    query: str
    
    # Context
    context: str
    sources: list[dict]
    history: list[dict]
    
    # Generation
    response: str
    response_chunks: Annotated[list[str], add_messages]
    
    # Metadata
    retrieval_scores: dict
    token_count: int
    error: str | None


# apps/chat_agent/agents/base.py

from abc import ABC, abstractmethod
from langgraph.graph import StateGraph


class BaseRAGAgent(ABC):
    """Base class for RAG agents."""
    
    def __init__(self) -> None:
        self._context_service = ContextService()
        self._llm_service = LLMService()
        self._conversation_service = ConversationService()
    
    @abstractmethod
    def build_graph(self) -> StateGraph:
        """Build agent graph."""
        pass
    
    async def run(
        self,
        conversation_id: str,
        query: str,
        user_id: str,
    ) -> AsyncIterator[AgentState]:
        """Run agent and yield state updates."""
        pass
    
    async def _retrieve_node(self, state: AgentState) -> dict:
        """Retrieve relevant context."""
        pass
    
    async def _generate_node(self, state: AgentState) -> dict:
        """Generate response with LLM."""
        pass
    
    async def _save_node(self, state: AgentState) -> dict:
        """Save conversation turn."""
        pass


# apps/chat_agent/agents/text_rag_agent.py

class TextRAGAgent(BaseRAGAgent):
    """Text RAG agent for basic Q&A."""
    
    def build_graph(self) -> StateGraph:
        """
        Build graph: retrieve -> generate -> save
        
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ retrieve │ -> │ generate │ -> │   save   │
        └──────────┘    └──────────┘    └──────────┘
        """
        graph = StateGraph(AgentState)
        
        graph.add_node("retrieve", self._retrieve_node)
        graph.add_node("generate", self._generate_node)
        graph.add_node("save", self._save_node)
        
        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "generate")
        graph.add_edge("generate", "save")
        graph.set_finish_point("save")
        
        return graph.compile()


# apps/chat_agent/agents/graph_rag_agent.py

class GraphRAGAgent(BaseRAGAgent):
    """Graph RAG agent for relationship-aware queries."""
    
    def build_graph(self) -> StateGraph:
        """
        Build graph with entity extraction:
        
        ┌──────────┐    ┌─────────────┐    ┌──────────┐    ┌──────────┐
        │ retrieve │ -> │ entity_ctx  │ -> │ generate │ -> │   save   │
        └──────────┘    └─────────────┘    └──────────┘    └──────────┘
        """
        graph = StateGraph(AgentState)
        
        graph.add_node("retrieve", self._retrieve_node)
        graph.add_node("entity_context", self._entity_context_node)
        graph.add_node("generate", self._generate_node)
        graph.add_node("save", self._save_node)
        
        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "entity_context")
        graph.add_edge("entity_context", "generate")
        graph.add_edge("generate", "save")
        graph.set_finish_point("save")
        
        return graph.compile()
    
    async def _entity_context_node(self, state: AgentState) -> dict:
        """Extract entities and enrich context from Neo4j."""
        pass
```

**Tasks**:

#### Task 11.4.1: Define Agent State
- **Description**: Create AgentState TypedDict with proper annotations
- **Acceptance Criteria**:
  - [ ] AgentState defined with all required fields
  - [ ] response_chunks uses add_messages annotation
  - [ ] Includes error handling fields
- **Technical Notes**: Use LangGraph's add_messages for streaming
- **Dependencies**: Task 11.3.3
- **Estimated Time**: 1 hour

#### Task 11.4.2: Implement BaseRAGAgent
- **Description**: Create abstract base class for RAG agents
- **Acceptance Criteria**:
  - [ ] Abstract build_graph() method
  - [ ] run() method with async generator
  - [ ] _retrieve_node() integrates ContextService
  - [ ] _generate_node() integrates LLMService
  - [ ] _save_node() integrates ConversationService
- **Technical Notes**: Use LangGraph StateGraph for graph building
- **Dependencies**: Task 11.4.1
- **Estimated Time**: 2 hours

#### Task 11.4.3: Implement TextRAGAgent
- **Description**: Create basic RAG agent with linear flow
- **Acceptance Criteria**:
  - [ ] build_graph() creates linear graph
  - [ ] Nodes properly connected
  - [ ] Streaming output works
  - [ ] Unit tests pass
- **Technical Notes**: Simple retrieve -> generate -> save flow
- **Dependencies**: Task 11.4.2
- **Estimated Time**: 2 hours

#### Task 11.4.4: Implement GraphRAGAgent
- **Description**: Create graph RAG agent with entity context
- **Acceptance Criteria**:
  - [ ] build_graph() includes entity_context node
  - [ ] _entity_context_node() extracts entities from query
  - [ ] Enriches context with Neo4j graph data
  - [ ] Unit tests pass
- **Technical Notes**: Use Neo4jService for entity relationships
- **Dependencies**: Task 11.4.3
- **Estimated Time**: 3 hours

---

### Submodule 11.5: WebSocket Consumer

**Purpose**: Implement WebSocket consumer for real-time communication.

**Technical Approach**:
- Create ChatConsumer inheriting from AsyncJsonWebsocketConsumer
- Handle connection lifecycle (connect, disconnect, receive)
- Route messages to appropriate agent
- Stream responses in real-time

**Files to Create**:

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `apps/chat_agent/consumers/__init__.py` | Consumers init | 10 |
| `apps/chat_agent/consumers/chat_consumer.py` | WebSocket consumer | 200 |

**Consumer Design**:

```python
# apps/chat_agent/consumers/chat_consumer.py

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for chat."""
    
    async def connect(self) -> None:
        """Handle WebSocket connection."""
        # Get conversation_id from URL
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        
        # Authenticate user
        if self.scope["user"].is_anonymous:
            await self.close()
            return
        
        self.user_id = str(self.scope["user"].id)
        
        # Join conversation group
        await self.channel_layer.group_add(
            f"chat_{self.conversation_id}",
            self.channel_name,
        )
        
        await self.accept()
    
    async def disconnect(self, code: int) -> None:
        """Handle WebSocket disconnection."""
        await self.channel_layer.group_discard(
            f"chat_{self.conversation_id}",
            self.channel_name,
        )
    
    async def receive_json(self, content: dict) -> None:
        """Handle incoming WebSocket message."""
        message_type = content.get("type")
        
        if message_type == "chat.message":
            await self._handle_chat_message(content)
        elif message_type == "chat.stop":
            await self._handle_stop_generation()
    
    async def _handle_chat_message(self, content: dict) -> None:
        """Handle chat message."""
        query = content.get("content", "")
        
        # Get or create conversation
        conversation = await self._get_or_create_conversation()
        
        # Select agent based on conversation type
        agent = self._get_agent(conversation.agent_type)
        
        # Run agent with streaming
        async for state in agent.run(
            conversation_id=self.conversation_id,
            query=query,
            user_id=self.user_id,
        ):
            # Send response chunks
            if state.get("response_chunks"):
                await self.send_json({
                    "type": "chat.response.chunk",
                    "content": state["response_chunks"][-1],
                    "is_final": False,
                })
        
        # Send completion
        await self.send_json({
            "type": "chat.response.complete",
            "message_id": state.get("message_id"),
            "sources": state.get("sources", []),
        })
    
    def _get_agent(self, agent_type: str) -> BaseRAGAgent:
        """Get agent instance by type."""
        if agent_type == "graph_rag":
            return GraphRAGAgent()
        return TextRAGAgent()
    
    async def chat_message(self, event: dict) -> None:
        """Handle messages from channel layer."""
        await self.send_json(event["message"])
```

**WebSocket Message Format**:

```python
# Client → Server
{
    "type": "chat.message",
    "content": "用户问题",
    "conversation_id": "uuid"  # Optional, for new conversations
}

# Server → Client (streaming)
{
    "type": "chat.response.chunk",
    "content": "AI回复片段",
    "is_final": false
}

# Server → Client (complete)
{
    "type": "chat.response.complete",
    "message_id": "uuid",
    "sources": [
        {
            "chunk_id": "uuid",
            "document_id": "uuid",
            "text": "相关文本片段",
            "score": 0.85
        }
    ]
}

# Server → Client (error)
{
    "type": "chat.error",
    "error_code": "RATE_LIMIT",
    "message": "请求频率过高，请稍后重试"
}
```

**Tasks**:

#### Task 11.5.1: Create ChatConsumer Basic Structure
- **Description**: Create consumer with connect/disconnect handlers
- **Acceptance Criteria**:
  - [ ] Inherits from AsyncJsonWebsocketConsumer
  - [ ] connect() authenticates user
  - [ ] disconnect() cleans up resources
  - [ ] Joins/leaves channel layer groups
- **Technical Notes**: Use AuthMiddlewareStack for authentication
- **Dependencies**: Task 11.1.2
- **Estimated Time**: 2 hours

#### Task 11.5.2: Implement Message Handling
- **Description**: Implement receive_json for message processing
- **Acceptance Criteria**:
  - [ ] receive_json() routes by message type
  - [ ] _handle_chat_message() runs agent
  - [ ] Response chunks sent in real-time
  - [ ] Completion message sent with sources
- **Technical Notes**: Use async for agent streaming
- **Dependencies**: Task 11.5.1, Task 11.4.3
- **Estimated Time**: 2.5 hours

#### Task 11.5.3: Implement Error Handling
- **Description**: Add comprehensive error handling
- **Acceptance Criteria**:
  - [ ] Authentication errors handled
  - [ ] Rate limiting implemented
  - [ ] Agent errors caught and reported
  - [ ] Timeout handling for long generations
- **Technical Notes**: Use try/except with proper error messages
- **Dependencies**: Task 11.5.2
- **Estimated Time**: 1.5 hours

---

### Submodule 11.6: REST API Endpoints

**Purpose**: Provide REST API endpoints for conversation management.

**Technical Approach**:
- Create conversation CRUD endpoints
- List conversations with pagination
- Get conversation history
- Create/delete conversations

**Files to Create**:

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `apps/chat_agent/serializers.py` | DRF serializers | 120 |
| `apps/chat_agent/views.py` | API views | 200 |
| `apps/chat_agent/urls.py` | URL routing | 40 |

**API Endpoints**:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat/conversations/` | Create new conversation |
| GET | `/api/v1/chat/conversations/` | List user conversations |
| GET | `/api/v1/chat/conversations/{id}/` | Get conversation details |
| DELETE | `/api/v1/chat/conversations/{id}/` | Delete conversation |
| GET | `/api/v1/chat/conversations/{id}/messages/` | Get conversation history |
| POST | `/api/v1/chat/conversations/{id}/messages/` | Send message (HTTP fallback) |

**Serializer Design**:

```python
# apps/chat_agent/serializers.py

class ConversationSerializer(serializers.ModelSerializer):
    """Conversation serializer."""
    
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            "id", "title", "agent_type", "is_active",
            "message_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
    
    def get_message_count(self, obj: Conversation) -> int:
        return obj.messages.count()


class ConversationCreateSerializer(serializers.Serializer):
    """Create conversation request."""
    
    title = serializers.CharField(max_length=255, required=False, default="")
    agent_type = serializers.ChoiceField(
        choices=["text_rag", "graph_rag"],
        default="text_rag",
    )


class MessageSerializer(serializers.ModelSerializer):
    """Message serializer."""
    
    class Meta:
        model = Message
        fields = [
            "id", "role", "content", "sources",
            "token_count", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SendMessageSerializer(serializers.Serializer):
    """Send message request (HTTP fallback)."""
    
    content = serializers.CharField(max_length=4000)
```

**Tasks**:

#### Task 11.6.1: Create Serializers
- **Description**: Implement DRF serializers for conversation and message
- **Acceptance Criteria**:
  - [ ] ConversationSerializer with message_count
  - [ ] ConversationCreateSerializer with validation
  - [ ] MessageSerializer with sources
  - [ ] SendMessageSerializer for HTTP fallback
- **Technical Notes**: Use ModelSerializer for simplicity
- **Dependencies**: Task 11.2.3
- **Estimated Time**: 1.5 hours

#### Task 11.6.2: Implement Conversation Views
- **Description**: Create views for conversation CRUD
- **Acceptance Criteria**:
  - [ ] ConversationListView with pagination
  - [ ] ConversationDetailView with authorization
  - [ ] Filter by agent_type, is_active
  - [ ] Unit tests pass
- **Technical Notes**: Use DRF generics or viewsets
- **Dependencies**: Task 11.6.1
- **Estimated Time**: 2 hours

#### Task 11.6.3: Implement Message Views
- **Description**: Create views for message history
- **Acceptance Criteria**:
  - [ ] MessageListView with pagination
  - [ ] Ordering by created_at
  - [ ] HTTP fallback for sending messages
  - [ ] Unit tests pass
- **Technical Notes**: Filter by conversation_id
- **Dependencies**: Task 11.6.2
- **Estimated Time**: 1.5 hours

#### Task 11.6.4: Configure URL Routing
- **Description**: Create URL patterns and register with main URLs
- **Acceptance Criteria**:
  - [ ] URLs defined in apps/chat_agent/urls.py
  - [ ] Registered in config/urls.py
  - [ ] OpenAPI documentation generated
- **Technical Notes**: Use drf_yasg for OpenAPI docs
- **Dependencies**: Task 11.6.3
- **Estimated Time**: 0.5 hours

---

### Submodule 11.7: Milvus Chat History Collection

**Purpose**: Create and manage chat_history collection in Milvus for conversation embedding storage.

**Technical Approach**:
- Create chat_history collection in MilvusService
- Store message embeddings with metadata
- Support semantic search over conversation history
- Enable context retrieval from past conversations

**Files to Modify**:

| File | Changes |
|------|---------|
| `apps/milvus_database_controller/services.py` | Add chat_history collection methods |
| `apps/milvus_database_controller/dto.py` | Add DTOs for chat history |

**Collection Schema**:

```python
# chat_history collection schema

{
    "pk": VARCHAR (primary key, message_id),
    "embedding": FLOAT_VECTOR (dim=1536),
    "message": VARCHAR (max_length=65535),
    "role": VARCHAR (max_length=20),  # user | assistant
    "conversation_id": VARCHAR (max_length=100),
    "user_id": VARCHAR (max_length=100),
    "timestamp": INT64,  # Unix timestamp
}
```

**Tasks**:

#### Task 11.7.1: Create Chat History Collection
- **Description**: Add chat_history collection to MilvusService
- **Acceptance Criteria**:
  - [ ] Collection created with proper schema
  - [ ] HNSW index on embedding field
  - [ ] Supports insert, search, delete operations
- **Technical Notes**: Use existing MilvusService patterns
- **Dependencies**: Phase 6 (Milvus Database Controller)
- **Estimated Time**: 2 hours

#### Task 11.7.2: Implement Chat History Operations
- **Description**: Add methods for chat history CRUD
- **Acceptance Criteria**:
  - [ ] insert_chat_message() stores embedding
  - [ ] search_similar_messages() vector search
  - [ ] delete_conversation_history() cleanup
  - [ ] DTOs defined for request/response
- **Technical Notes**: Similar to documents collection operations
- **Dependencies**: Task 11.7.1
- **Estimated Time**: 2 hours

---

### Submodule 11.8: Testing

**Purpose**: Comprehensive testing for all components.

**Test Categories**:

| Category | Marker | Description |
|----------|--------|-------------|
| Unit Tests | `@pytest.mark.unit` | Mock dependencies, test logic |
| Integration Tests | `@pytest.mark.integration` | Real services (Milvus, Neo4j, Qwen) |
| WebSocket Tests | `@pytest.mark.websocket` | WebSocket communication tests |

**Files to Create**:

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `apps/chat_agent/tests/__init__.py` | Tests init | 5 |
| `apps/chat_agent/tests/conftest.py` | Pytest fixtures | 150 |
| `apps/chat_agent/tests/test_models.py` | Model tests | 100 |
| `apps/chat_agent/tests/test_services.py` | Service tests | 250 |
| `apps/chat_agent/tests/test_agents.py` | Agent tests | 200 |
| `apps/chat_agent/tests/test_consumers.py` | Consumer tests | 180 |
| `apps/chat_agent/tests/test_api_views.py` | API tests | 200 |
| `apps/chat_agent/tests/test_integration.py` | Integration tests | 150 |

**Tasks**:

#### Task 11.8.1: Create Test Fixtures
- **Description**: Set up pytest fixtures for testing
- **Acceptance Criteria**:
  - [ ] User fixture
  - [ ] Conversation fixture
  - [ ] Message fixture
  - [ ] Mock LLMService fixture
  - [ ] Mock SearchService fixture
- **Technical Notes**: Use factory_boy for test data
- **Dependencies**: Task 11.6.4
- **Estimated Time**: 2 hours

#### Task 11.8.2: Write Unit Tests
- **Description**: Write unit tests for all components
- **Acceptance Criteria**:
  - [ ] Models tested (80%+ coverage)
  - [ ] Services tested (80%+ coverage)
  - [ ] Agents tested (80%+ coverage)
  - [ ] Consumers tested (80%+ coverage)
- **Technical Notes**: Mock external dependencies
- **Dependencies**: Task 11.8.1
- **Estimated Time**: 4 hours

#### Task 11.8.3: Write Integration Tests
- **Description**: Write integration tests with real services
- **Acceptance Criteria**:
  - [ ] WebSocket connection test
  - [ ] Full chat flow test
  - [ ] Milvus chat_history integration
  - [ ] SearchService integration
- **Technical Notes**: Requires running services
- **Dependencies**: Task 11.8.2
- **Estimated Time**: 3 hours

#### Task 11.8.4: Verify Test Coverage
- **Description**: Ensure test coverage meets requirements
- **Acceptance Criteria**:
  - [ ] Overall coverage >= 80%
  - [ ] No critical code paths untested
  - [ ] Coverage report generated
- **Technical Notes**: Use pytest-cov
- **Dependencies**: Task 11.8.3
- **Estimated Time**: 1 hour

---

### Submodule 11.9: Manual Test Generation

**Purpose**: Generate manual test cases for end-to-end verification.

**Tasks**:

#### Task 11.9.1: Invoke Manual Test Generator
- **Description**: Call manual_test_generator agent to create test document
- **Acceptance Criteria**:
  - [ ] Manual test document created
  - [ ] Test scenarios documented
  - [ ] WebSocket test cases included
- **Technical Notes**: Use agent from user's agent directory
- **Dependencies**: Task 11.8.4
- **Estimated Time**: 0.5 hours

#### Task 11.9.2: Create Manual Test Document
- **Description**: Create `apps/chat_agent/docs/manual_test.md`
- **Acceptance Criteria**:
  - [ ] WebSocket connection test cases
  - [ ] Chat message flow test cases
  - [ ] Error scenario test cases
  - [ ] Performance test cases
- **Technical Notes**: Follow format from Phase 10
- **Dependencies**: Task 11.9.1
- **Estimated Time**: 1.5 hours

---

## Constants Design

```python
# apps/chat_agent/constants.py

from enum import Enum


class AgentType(str, Enum):
    """Agent type for conversation."""
    
    TEXT_RAG = "text_rag"
    GRAPH_RAG = "graph_rag"


class MessageRole(str, Enum):
    """Message role in conversation."""
    
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, Enum):
    """WebSocket message type."""
    
    CHAT_MESSAGE = "chat.message"
    CHAT_RESPONSE_CHUNK = "chat.response.chunk"
    CHAT_RESPONSE_COMPLETE = "chat.response.complete"
    CHAT_ERROR = "chat.error"
    CHAT_STOP = "chat.stop"


# Default settings
DEFAULT_HISTORY_LIMIT = 10
DEFAULT_TOP_K = 5
DEFAULT_MAX_TOKENS = 2000
DEFAULT_TEMPERATURE = 0.7
MAX_CONTEXT_TOKENS = 4000
MAX_MESSAGE_LENGTH = 4000
```

---

## Exception Design

```python
# apps/chat_agent/exceptions.py

class ChatAgentError(Exception):
    """Base exception for chat agent errors."""
    
    def __init__(self, message: str = "Chat agent error") -> None:
        self.message = message
        super().__init__(self.message)


class ConversationNotFoundError(ChatAgentError):
    """Conversation not found."""
    
    def __init__(self, conversation_id: str) -> None:
        super().__init__(f"Conversation not found: {conversation_id}")


class UnauthorizedAccessError(ChatAgentError):
    """Unauthorized access to conversation."""
    
    def __init__(self) -> None:
        super().__init__("Unauthorized access to conversation")


class AgentError(ChatAgentError):
    """Error during agent execution."""
    
    def __init__(self, agent_type: str, reason: str = "") -> None:
        super().__init__(f"Agent '{agent_type}' error: {reason}")


class LLMError(ChatAgentError):
    """Error during LLM generation."""
    
    def __init__(self, reason: str = "") -> None:
        super().__init__(f"LLM error: {reason}")


class ContextAssemblyError(ChatAgentError):
    """Error during context assembly."""
    
    def __init__(self, reason: str = "") -> None:
        super().__init__(f"Context assembly error: {reason}")
```

---

## Configuration Design

### Settings (base.py)

```python
# config/settings/base.py - Add to existing file

# =============================================================================
# Chat Agent Configuration
# =============================================================================

CHAT_AGENT_CONFIG = {
    # Agent settings
    "default_agent_type": "text_rag",
    "default_temperature": 0.7,
    "default_max_tokens": 2000,
    
    # Context settings
    "max_context_tokens": 4000,
    "history_limit": 10,
    "search_top_k": 5,
    
    # WebSocket settings
    "websocket_heartbeat": 30,  # seconds
    "connection_timeout": 300,  # seconds
    
    # Rate limiting
    "rate_limit": {
        "messages_per_minute": 20,
        "tokens_per_minute": 10000,
    },
    
    # LLM settings (reuse QWEN_CONFIG)
    "llm": {
        "model": QWEN_CHAT_MODEL,
        "temperature": 0.7,
        "max_tokens": 2000,
    },
}

# Channel Layers Configuration
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
            "capacity": 1500,
            "expiry": 10,
        },
    },
}
```

---

## Project Directory Structure

```
apps/chat_agent/
├── __init__.py
├── apps.py
├── models.py
├── constants.py
├── exceptions.py
│
├── agents/
│   ├── __init__.py
│   ├── base.py
│   ├── state.py
│   ├── text_rag_agent.py
│   └── graph_rag_agent.py
│
├── consumers/
│   ├── __init__.py
│   └── chat_consumer.py
│
├── services/
│   ├── __init__.py
│   ├── conversation_service.py
│   ├── context_service.py
│   └── llm_service.py
│
├── views/
│   ├── __init__.py
│   └── chat_views.py
│
├── serializers.py
├── urls.py
│
├── docs/
│   ├── README.md
│   └── manual_test.md
│
├── migrations/
│   └── __init__.py
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_models.py
    ├── test_services.py
    ├── test_agents.py
    ├── test_consumers.py
    ├── test_api_views.py
    └── test_integration.py
```

---

## Integration with Other Modules

### SearchService Integration (Phase 10)

```python
# In ContextService
from apps.document_rag_search.services import SearchService
from apps.document_rag_search.dto import HybridSearchRequest


class ContextService:
    def __init__(self) -> None:
        self._search_service = SearchService()
    
    def _retrieve_documents(
        self,
        query: str,
        top_k: int = 5,
    ) -> SearchResponse:
        """Retrieve documents using hybrid search."""
        request = HybridSearchRequest(
            query=query,
            top_k=top_k,
            use_vector=True,
            use_keyword=True,
            use_graph=False,  # Graph context handled separately in GraphRAGAgent
        )
        return self._search_service.hybrid_search(request)
```

### EmbeddingService Integration (Phase 8)

```python
# In ConversationService
from apps.embedding_engine.services import EmbeddingService


class ConversationService:
    def __init__(self) -> None:
        self._embedding_service = EmbeddingService()
    
    async def store_message_embedding(
        self,
        message: Message,
    ) -> str:
        """Store message embedding in Milvus."""
        # Generate embedding
        result = self._embedding_service.embed_query(message.content)
        
        # Store in Milvus chat_history
        embedding_id = self._milvus_service.insert_chat_message(
            message_id=str(message.id),
            embedding=result.embedding,
            message=message.content,
            role=message.role,
            conversation_id=str(message.conversation_id),
            user_id=str(message.conversation.user_id),
        )
        
        return embedding_id
```

### MilvusService Integration (Phase 6)

```python
# In ConversationService
from apps.milvus_database_controller.services import MilvusService


class ConversationService:
    def search_similar_messages(
        self,
        query_embedding: list[float],
        conversation_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        """Search similar messages from conversation history."""
        filter_expr = None
        if conversation_id:
            filter_expr = f'conversation_id == "{conversation_id}"'
        
        results = self._milvus_service.search(
            collection_name="chat_history",
            query_vector=query_embedding,
            top_k=top_k,
            filter_expr=filter_expr,
        )
        
        return results
```

---

## Acceptance Criteria

### Core Functionality (Submodule 11.1-11.5)
- [ ] Django Channels configured with Redis backend
- [ ] WebSocket connection established and authenticated
- [ ] Conversation and Message models created
- [ ] ConversationService handles CRUD operations
- [ ] ContextService assembles context from SearchService
- [ ] LLMService streams responses from Qwen API
- [ ] TextRAGAgent processes basic Q&A queries
- [ ] GraphRAGAgent enriches context with graph data
- [ ] ChatConsumer handles WebSocket messages
- [ ] Streaming responses work in real-time

### API Layer (Submodule 11.6)
- [ ] REST API endpoints for conversation management
- [ ] Proper authentication (IsAuthenticated)
- [ ] Request validation with DRF serializers
- [ ] Consistent response format
- [ ] OpenAPI documentation complete
- [ ] API tests with >= 80% coverage

### Chat History (Submodule 11.7)
- [ ] chat_history collection created in Milvus
- [ ] Message embeddings stored
- [ ] Semantic search over history works
- [ ] Conversation cleanup removes embeddings

### Testing & Documentation (Submodule 11.8-11.9)
- [ ] Unit tests for all components
- [ ] Integration tests with real services
- [ ] Test coverage >= 80%
- [ ] Module documentation complete
- [ ] Manual test cases documented

---

## Risks & Considerations

| Risk | Mitigation |
|------|------------|
| WebSocket Connection Stability | Implement heartbeat, reconnection logic |
| LLM Streaming Latency | Use async, timeout handling, graceful degradation |
| Context Window Overflow | Token counting, truncation strategy |
| Rate Limiting | Implement token bucket, per-user limits |
| Memory Usage (Long Conversations) | Limit history, pagination, cleanup old messages |
| Agent State Management | Use LangGraph checkpointing, handle interruptions |
| Error Recovery | Graceful error messages, retry logic |
| Test Complexity | Mock LLM responses, use pytest fixtures |

---

## Execution Order

Recommended execution order:

```
Phase 11.1 (Django Channels Configuration)
    │
    ├── 11.1.1 Install and Configure Django Channels
    └── 11.1.2 Create WebSocket Routing
    │
    ▼
Phase 11.2 (Data Models)
    │
    ├── 11.2.1 Create Chat Agent App Structure
    ├── 11.2.2 Implement Conversation Model
    └── 11.2.3 Implement Message Model
    │
    ▼
Phase 11.7 (Milvus Chat History)  ← Early for integration
    │
    ├── 11.7.1 Create Chat History Collection
    └── 11.7.2 Implement Chat History Operations
    │
    ▼
Phase 11.3 (Service Layer)
    │
    ├── 11.3.1 Implement ConversationService
    ├── 11.3.2 Implement ContextService
    └── 11.3.3 Implement LLMService
    │
    ▼
Phase 11.4 (Agent Layer)
    │
    ├── 11.4.1 Define Agent State
    ├── 11.4.2 Implement BaseRAGAgent
    ├── 11.4.3 Implement TextRAGAgent
    └── 11.4.4 Implement GraphRAGAgent
    │
    ▼
Phase 11.5 (WebSocket Consumer)
    │
    ├── 11.5.1 Create ChatConsumer Basic Structure
    ├── 11.5.2 Implement Message Handling
    └── 11.5.3 Implement Error Handling
    │
    ▼
Phase 11.6 (REST API Endpoints)
    │
    ├── 11.6.1 Create Serializers
    ├── 11.6.2 Implement Conversation Views
    ├── 11.6.3 Implement Message Views
    └── 11.6.4 Configure URL Routing
    │
    ▼
Phase 11.8 (Testing)
    │
    ├── 11.8.1 Create Test Fixtures
    ├── 11.8.2 Write Unit Tests
    ├── 11.8.3 Write Integration Tests
    └── 11.8.4 Verify Test Coverage
    │
    ▼
Phase 11.9 (Manual Test Generation)
    │
    ├── 11.9.1 Invoke Manual Test Generator
    └── 11.9.2 Create Manual Test Document
```

---

## Estimated Timeline

| Submodule | Estimated Hours | Working Days |
|-----------|-----------------|--------------|
| 11.1 Django Channels Configuration | 3h | 0.5 day |
| 11.2 Data Models | 3h | 0.5 day |
| 11.3 Service Layer | 8h | 1-2 days |
| 11.4 Agent Layer | 8h | 1-2 days |
| 11.5 WebSocket Consumer | 6h | 1 day |
| 11.6 REST API Endpoints | 5.5h | 1 day |
| 11.7 Milvus Chat History | 4h | 0.5-1 day |
| 11.8 Testing | 10h | 2 days |
| 11.9 Manual Test Generation | 2h | 0.5 day |
| **Total** | **49.5h** | **8-10 days** |

---

## Files to Create/Modify

### New Files

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `config/asgi.py` | ASGI application | 50 |
| `config/routing.py` | WebSocket routing | 30 |
| `apps/chat_agent/__init__.py` | App initialization | 10 |
| `apps/chat_agent/apps.py` | App configuration | 15 |
| `apps/chat_agent/models.py` | Conversation and Message models | 150 |
| `apps/chat_agent/constants.py` | Constants and enums | 60 |
| `apps/chat_agent/exceptions.py` | Custom exceptions | 80 |
| `apps/chat_agent/agents/__init__.py` | Agents init | 15 |
| `apps/chat_agent/agents/base.py` | Base agent class | 100 |
| `apps/chat_agent/agents/state.py` | Agent state definitions | 80 |
| `apps/chat_agent/agents/text_rag_agent.py` | Text RAG agent | 180 |
| `apps/chat_agent/agents/graph_rag_agent.py` | Graph RAG agent | 200 |
| `apps/chat_agent/consumers/__init__.py` | Consumers init | 10 |
| `apps/chat_agent/consumers/chat_consumer.py` | WebSocket consumer | 200 |
| `apps/chat_agent/services/__init__.py` | Services init | 20 |
| `apps/chat_agent/services/conversation_service.py` | Conversation management | 200 |
| `apps/chat_agent/services/context_service.py` | Context assembly | 180 |
| `apps/chat_agent/services/llm_service.py` | LLM streaming | 200 |
| `apps/chat_agent/serializers.py` | DRF serializers | 120 |
| `apps/chat_agent/urls.py` | URL routing | 40 |
| `apps/chat_agent/views.py` | API views | 200 |
| `apps/chat_agent/tests/*.py` | All test files | 800 |
| `apps/chat_agent/docs/README.md` | Documentation | 200 |
| `apps/chat_agent/docs/manual_test.md` | Manual tests | 150 |

### Modified Files

| File | Changes |
|------|---------|
| `config/settings/base.py` | Add CHANNEL_LAYERS, CHAT_AGENT_CONFIG |
| `config/urls.py` | Include chat agent URLs |
| `apps/milvus_database_controller/services.py` | Add chat_history collection methods |
| `apps/milvus_database_controller/dto.py` | Add DTOs for chat history |
| `pyproject.toml` | Add channels, channels_redis, langgraph dependencies |

---

## Summary

Phase 11 implements the Chat Agent Module as the conversational AI layer for the RAG system:

1. **WebSocket Layer**: Real-time bidirectional communication using Django Channels
2. **Agent Layer**: LangGraph-based RAG agents with state management
3. **Service Layer**: Business logic for conversation, context, and LLM operations
4. **Data Layer**: PostgreSQL for metadata, Milvus for conversation embeddings

Key integrations:
- **Phase 10**: SearchService for hybrid document retrieval
- **Phase 8**: EmbeddingService for message embeddings
- **Phase 6**: MilvusService for chat_history collection
- **Phase 7**: Neo4jService for Graph RAG context

The module provides:
- Real-time streaming responses via WebSocket
- Conversation history management
- Context-aware RAG generation
- Graph RAG for relationship-aware queries
- REST API for conversation management
