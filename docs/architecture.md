## 项目架构图
```
┌────────────────────────────────────────────────────────────┐
│                         test tool                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     curl     │  │     wcat     │  │  post man    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────┬────────────────┬────────────────┬─────────────┘
             │ WebSocket      │ HTTP           │ HTTP
             │                │                │
┌────────────▼────────────────▼────────────────▼──────────────┐
│                    Django Backend                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Django Channels (WebSocket)               │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │          Django REST Framework (REST API)            │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              RAG Processing Pipeline                 │   │
│  │   Query → Embedding → Vector Search → Context        │   │
│  │   Assembly → LLM Generation → Response               │   │
│  └──────────────────────────────────────────────────────┘   │
└────┬──────────────┬──────────────┬──────────────┬───────────┬───────────┘
     │              │              │              │           │
     ▼              ▼              ▼              ▼           ▼
┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│PostgreSQL│ │  Milvus  │  │  Neo4j   │  │  MinIO   │  │ QWEN API     │
│ (主数据) │  │ (向量库)  │  │ (知识图)  │  │ (文件存储)│  │ (LLM+Embed)  │
└─────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────────┘
```

## 项目核心组件和模块

### Django Backend
- **Django Channels**: 处理 WebSocket 连接，实现实时通信功能。
- **Django REST Framework**: 提供 RESTful API 接口，支持 curl、wcat、postman 等工具进行测试和交互。

### document parser(document processing)
- **document parser**: 用于解析文档，拆分文档为句子，段落，形成符合逻辑的chunking, 方便后续通过LLM Embeding进行向量化存储和搜索。
- **document meta management(文档级别)**: 用于维护文档元数据，如文档ID，文档名称，文档路径，文档创建时间，文档更新时间，文档大小，文档类型，文档状态等。
- **document deduplication**: 用于去重文档，避免重复存储和处理相同的文档。结合meta以及chunking的元数据，可以快速找到chunking的部分是否已经被向量化和存储，从而避免重复处理。

### Document Chunking Strategy

采用 **Recursive Character Text Splitter**（递归字符分割）作为主策略，结合 **Semantic Chunking**（语义分块）作为优化方案。

#### 策略选择

| 策略 | 适用场景 | 优势 | 劣势 |
|------|----------|------|------|
| **Recursive Character Splitter** | 通用文档 | 保持段落完整性、实现简单 | 可能切断语义边界 |
| **Semantic Chunking** | 高精度检索场景 | 语义完整性高、检索质量好 | 计算成本高、需要 embedding 调用 |
| **Markdown-Aware Splitter** | Markdown 文档 | 保留标题层级结构 | 仅适用于 Markdown |

#### 推荐方案：Recursive + Semantic 混合策略

```
┌─────────────────────────────────────────────────────────────┐
│                    Chunking Pipeline                        │
│                                                             │
│  Raw Document                                               │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────────────────────┐                   │
│  │  1. Document Preprocessing          │                   │
│  │     - 去除无关页眉页脚               │                   │
│  │     - 提取文档标题/章节结构          │                   │
│  └─────────────────────────────────────┘                   │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────────────────────┐                   │
│  │  2. Recursive Character Split       │                   │
│  │     - 按 ["\n\n", "\n", "。", " "] 分割              │
│  │     - chunk_size: 512 tokens                          │
│  │     - chunk_overlap: 50 tokens                         │
│  └─────────────────────────────────────┘                   │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────────────────────┐                   │
│  │  3. Semantic Merge (Optional)       │                   │
│  │     - 计算相邻 chunk 语义相似度      │                   │
│  │     - 相似度 > 0.8 则合并           │                   │
│  └─────────────────────────────────────┘                   │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────────────────────┐                   │
│  │  4. Metadata Enrichment             │                   │
│  │     - 添加文档标题上下文             │                   │
│  │     - 记录章节层级信息               │                   │
│  │     - 生成 chunk summary             │                   │
│  └─────────────────────────────────────┘                   │
│       │                                                     │
│       ▼                                                     │
│    Chunk List → Milvus                                     │
└─────────────────────────────────────────────────────────────┘
```

#### 按文档类型的参数配置

| 文档类型 | chunk_size (tokens) | chunk_overlap | 分隔符优先级 | 特殊处理 |
|----------|---------------------|---------------|--------------|----------|
| **技术文档 (Markdown)** | 512 | 50 | `["\n## ", "\n### ", "\n\n", "\n", " "]` | 保留标题层级，添加 breadcrumb |
| **学术论文 (PDF)** | 768 | 100 | `["\n\n", "\n", ". ", " "]` | 保留引用上下文，提取图表说明 |
| **法律合同 (PDF/DOCX)** | 1024 | 200 | `["\n\n", "\n第", "\n", " "]` | 按条款分割，保留条款编号 |
| **通用文本 (TXT)** | 512 | 50 | `["\n\n", "\n", "。", " ", ""]` | 无特殊处理 |

#### Chunk 元数据结构

```python
{
    "chunk_id": "uuid",
    "document_id": "uuid",           # 父文档 ID
    "text": "原始文本内容",
    "summary": "LLM 生成的摘要",      # 用于 summary_dense 向量
    "chunk_index": 0,                # 在文档中的顺序
    "chunk_type": "paragraph",       # paragraph | title | table | code

    # 层级上下文
    "breadcrumb": ["第一章", "1.1 概述"],  # 章节路径
    "page_number": 5,                # 原始页码（PDF）
    "start_char": 1200,              # 在原文中的字符位置
    "end_char": 1800,

    # 邻居索引（用于上下文窗口扩展）
    "prev_chunk_id": "uuid | null",
    "next_chunk_id": "uuid | null",

    # 向量字段
    "text_dense": [float] * dim,     # 文本密集向量
    "summary_dense": [float] * dim,  # 摘要密集向量
    "text_sparse": sparse_vector     # BM25 稀疏向量
}
```

#### 上下文窗口扩展策略

检索时支持动态扩展上下文窗口：

```python
def expand_context(chunk_id: str, window_size: int = 1) -> List[Chunk]:
    """
    根据 chunk_id 扩展上下文窗口

    Args:
        chunk_id: 核心 chunk ID
        window_size: 向前后扩展的 chunk 数量

    Returns:
        扩展后的 chunk 列表（按顺序）
    """
    # 1. 从 Milvus 获取目标 chunk
    # 2. 通过 prev_chunk_id / next_chunk_id 链式查询
    # 3. 拼接相邻 chunk 文本
    # 4. 返回完整上下文
```

**检索流程**：
```
Query → Vector Search (top_k=5)
    → 对每个结果调用 expand_context(window_size=1)
    → 拼接 [prev_chunk] + [current_chunk] + [next_chunk]
    → 构建完整上下文
```

#### 实现依赖

| 组件 | 库/工具 | 说明 |
|------|---------|------|
| Recursive Splitter | LangChain `RecursiveCharacterTextSplitter` | 主分割器 |
| Markdown Splitter | LangChain `MarkdownHeaderTextSplitter` | Markdown 结构化分割 |
| Semantic Splitter | LlamaIndex `SemanticSplitterNodeParser` | 语义分块（可选） |
| Token 计数 | tiktoken / QWEN Tokenizer | 准确计算 token 数量 |
| Summary 生成 | QWEN API | 为每个 chunk 生成摘要 |

#### 质量保障

1. **最小 chunk 限制**: 单个 chunk 不小于 100 tokens，避免语义碎片化
2. **最大 chunk 限制**: 单个 chunk 不超过 1500 tokens，控制 embedding 质量
3. **重叠检查**: 确保 overlap 区域内容一致性
4. **摘要验证**: Summary 与原文语义相似度 > 0.7

### object storage controller
- **upload file**: 用于上传文件到 S3 兼容存储（MinIO/AWS S3）
- **download file**: 用于从存储下载文件
- **delete file**: 用于删除存储中的文件
- **generate presigned url**: 用于生成临时访问链接
- **bucket management**: 用于管理存储桶

#### 存储后端切换策略

项目支持两种存储后端，通过环境变量 `USE_S3_STORAGE` 进行静态切换：

| 环境 | USE_S3_STORAGE | 存储后端 | 说明 |
|------|----------------|----------|------|
| 开发环境 | `false` | LocalStorageBackend | 本地文件系统，存储在 `MEDIA_ROOT` |
| 生产环境 | `true` | S3StorageBackend | AWS S3 或 MinIO |

**切换机制**：
- 应用启动时根据环境变量确定使用哪个后端
- 运行时不可动态切换（避免状态同步问题）
- 每个 Document 记录实际使用的 `storage_backend` 字段

**预签名 URL 差异**：
- S3 模式：返回真正的预签名 URL，前端可直接使用
- Local 模式：返回相对路径，需通过后端 API 认证下载

**API 响应示例**：
```python
# S3 模式
{
    "url": "https://s3.amazonaws.com/bucket/docs/...?signature=...",
    "expires_in": 3600,
    "backend_type": "s3",
    "is_presigned": true
}

# Local 模式
{
    "url": "/media/documents/2026/02/24/report.pdf",
    "expires_in": 0,
    "backend_type": "local",
    "is_presigned": false
}
```

**前端处理**：
```javascript
if (presignedResult.is_presigned) {
    // S3: 直接使用预签名 URL
    window.open(presignedResult.url, '_blank');
} else {
    // Local: 通过后端 API 认证下载
    fetch(`/api/v1/documents/${docId}/download/`, { headers });
}
```

### document pipeline manager
- **document pipeline manager**: 用于管理文档处理流水线，包括文档解析、向量化存储、向量搜索、知识图谱构建、LLM生成等步骤。结合postgreSQL跟踪记录文档处理进度，以及向量库和知识图谱的更新，可以快速找到文档处理进度，以及向量库和知识图谱的更新。

### milvus database controller
- **create collection**: 用于创建向量库，并设置向量库的参数，如向量维度，向量类型，向量索引类型，向量索引参数，向量索引数量等操作
- **insert data**: 用于向向量库插入数据，并返回插入数据的ID
- **search data**: 用于向向量库搜索数据，并返回搜索结果
- **delete data**: 用于向向量库删除数据，并返回删除数据的ID

### neo4j database controller
- **create node**: 用于创建知识图谱节点，并返回创建节点的ID
- **create relationship**: 用于创建知识图谱关系，并返回创建关系的ID
- **query node**: 用于查询知识图谱节点，并返回查询结果
- **query relationship**: 用于查询知识图谱关系，并返回查询结果
- **delete node**: 用于删除知识图谱节点，并返回删除节点的ID
- **delete relationship**: 用于删除知识图谱关系，并返回删除关系的ID
- **update node**: 用于更新知识图谱节点，并返回更新节点的ID
- **update relationship**: 用于更新知识图谱关系，并返回更新关系的ID

### vector embedding engine
- **sentence transformer**: 用于将文本转换为向量，并返回向量
- **qwen api**: 用于将向量转换为文本，并返回文本
- **embedding management(向量级别)**: 用于管理向量，包括向量的创建，更新，删除，查询等操作。结合postgreSQL跟踪记录向量的元数据，如向量ID，向量名称，向量维度，向量类型，向量索引类型，向量索引参数，向量索引数量等，可以快速找到向量的元数据，以及向量库的更新。

### RAG processing pipeline
- **query processing**: 用于处理用户查询，包括查询解析，查询向量化，查询向量搜索，查询结果过滤，查询结果排序等操作。
- **context assembly**: 用于将查询结果组装成上下文，并返回上下文。结合知识图谱的查询结果，可以快速找到相关的上下文信息，并将其组装成符合LLM输入要求的格式。
- **LLM generation**: 用于将上下文输入LLM，并返回生成结果。结合QWEN API，可以快速将上下文输入LLM，并返回生成结果。

### WebSocket manager
- **WebSocket manager**: 用于处理WebSocket连接，并返回WebSocket连接ID。结合Django Channels，可以快速处理WebSocket连接，并返回WebSocket连接ID。
- **WebSocket message manager**: 用于处理WebSocket消息，并返回WebSocket消息ID。结合Django Channels，可以快速处理WebSocket消息，并返回WebSocket消息ID。
- **WebSocket close manager**: 用于处理WebSocket关闭，并返回WebSocket关闭ID。结合Django Channels，可以快速处理WebSocket关闭，并返回WebSocket关闭ID。
- **WebSocket error manager**: 用于处理WebSocket错误，并返回WebSocket错误ID。结合Django Channels，可以快速处理WebSocket错误，并返回WebSocket错误ID。

#### WebSocket JWT Authentication

Django Channels 默认使用 `AuthMiddlewareStack` 进行 session 认证，但本项目使用 JWT token 认证。因此实现了自定义的 `JWTAuthMiddleware` 来支持 WebSocket 连接的 JWT 认证。

**架构图**：

```
┌─────────────────────────────────────────────────────────────────┐
│                    WebSocket Authentication Flow                 │
│                                                                  │
│  Client WebSocket Connect                                        │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────┐                   │
│  │  Authorization Header or Query Param    │                   │
│  │  - Header: Authorization: Bearer <jwt>  │                   │
│  │  - Query: ?token=<jwt>                  │                   │
│  └─────────────────┬───────────────────────┘                   │
│                    │                                             │
│                    ▼                                             │
│  ┌─────────────────────────────────────────┐                   │
│  │         JWTAuthMiddleware               │                   │
│  │  1. Extract token from header/query     │                   │
│  │  2. Validate JWT signature              │                   │
│  │  3. Decode user_id from token           │                   │
│  │  4. Query User from database            │                   │
│  │  5. Set scope["user"]                   │                   │
│  └─────────────────┬───────────────────────┘                   │
│                    │                                             │
│                    ▼                                             │
│  ┌─────────────────────────────────────────┐                   │
│  │           ChatConsumer                  │                   │
│  │  - Access scope["user"]                 │                   │
│  │  - Reject anonymous users               │                   │
│  │  - Process chat messages                │                   │
│  └─────────────────────────────────────────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**代码位置**: `apps/chat_agent/middleware.py`

**ASGI 配置** (`config/asgi.py`):

```python
from apps.chat_agent.middleware import JWTAuthMiddleware

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddleware(URLRouter(websocket_urlpatterns))
    ),
})
```

**连接示例**：

```bash
# 使用 wscat (推荐)
wscat -c "ws://localhost:8000/ws/chat/<conversation_id>/" \
    -H "Authorization: Bearer <jwt_token>"

# 通过 query 参数 (适用于浏览器 WebSocket API)
const ws = new WebSocket('ws://localhost:8000/ws/chat/<conversation_id>/?token=<jwt_token>');
```

**认证流程**：
1. 客户端在 WebSocket 连接时通过 Authorization header 或 query 参数传递 JWT token
2. `JWTAuthMiddleware` 从 header 或 query 中提取 token
3. 使用 `rest_framework_simplejwt.tokens.AccessToken` 验证 token 有效性
4. 从 token payload 中提取 `user_id`
5. 从数据库查询 User 对象并设置到 `scope["user"]`
6. `ChatConsumer` 检查 `scope["user"]` 是否为匿名用户，拒绝匿名连接


## 数据流设计

### 文档上传流程
```
User Upload → Django API → Object Storage Controller (MinIO/S3)
    → Document Parser → Text Chunking
    → Embedding Generation → Milvus Storage
    → Entity Extraction → Neo4j Graph Update
    → PostgreSQL Metadata Storage
```

### Chat对话流程
```
User Message (WebSocket) → Django Channels Consumer
    → Query Embedding → Milvus Similarity Search (top_k=5)
    → Neo4j Graph Context Retrieval
    → Context Assembly (retrieved docs + graph info)
    → LLM Prompt Construction → OpenAI API Call
    → Response Streaming → WebSocket → Frontend Display
    → Conversation Storage (PostgreSQL + Milvus)
```

### 搜索流程
```
Search Query (HTTP) → Query Embedding
    → Hybrid Search:
        - Milvus Vector Search (semantic)
        - PostgreSQL Full-Text Search (keyword)
        - Neo4j Graph Traversal (related concepts)
    → Result Fusion & Ranking
    → Return to Tool
```

## RAG Processing Pipeline核心设计
BM25 reference: `docs/BM25_procedure.md`

### BM25 混合检索架构

项目采用 **Milvus 2.5+ 内置 BM25 Function** 实现混合检索，结合密集向量（dense vector）和稀疏向量（sparse vector）提供更准确的检索能力。

#### 技术选型

| 方案 | 说明 | 状态 |
|------|------|------|
| Milvus 内置 BM25 | 自动从文本生成 sparse vector，无需额外计算 | ✅ 已采用 |
| 自定义 BM25 | 使用 rank_bm25 库手动生成 sparse vector | ❌ 未采用 |

#### 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     Hybrid Search Architecture                   │
│                                                                  │
│  Query Text                                                      │
│      │                                                           │
│      ├─────────────────────────┬─────────────────────────┐      │
│      │                         │                         │      │
│      ▼                         ▼                         │      │
│  ┌───────────┐          ┌───────────┐                    │      │
│  │  Dense    │          │  BM25     │                    │      │
│  │ Embedding │          │ (Milvus)  │                    │      │
│  │  (QWEN)   │          │           │                    │      │
│  └─────┬─────┘          └─────┬─────┘                    │      │
│        │                      │                          │      │
│        ▼                      ▼                          │      │
│  ┌───────────┐          ┌───────────┐                    │      │
│  │  Vector   │          │  Sparse   │                    │      │
│  │  Search   │          │  Search   │                    │      │
│  │ (IP/COS)  │          │  (BM25)   │                    │      │
│  └─────┬─────┘          └─────┬─────┘                    │      │
│        │                      │                          │      │
│        └──────────┬───────────┘                          │      │
│                   │                                      │      │
│                   ▼                                      │      │
│            ┌───────────┐                                 │      │
│            │    RRF    │  Reciprocal Rank Fusion         │      │
│            │  Ranker   │  k=60 (default)                 │      │
│            └─────┬─────┘                                 │      │
│                  │                                       │      │
│                  ▼                                       │      │
│           Top-K Results                                  │      │
│                                                          │      │
└─────────────────────────────────────────────────────────────────┘
```

#### Collection Schema 关键配置

```python
# text 字段启用中文分词器
FieldDefinition(
    name="text",
    dtype=DataType.VARCHAR,
    max_length=65535,
    enable_analyzer=True,
    analyzer_params={"type": "chinese"},
    enable_match=True,
)

# text_sparse 字段（BM25 稀疏向量）
FieldDefinition(
    name="text_sparse",
    dtype=DataType.SPARSE_FLOAT_VECTOR,
)

# BM25 Function 自动生成 sparse vector
bm25_function = Function(
    name="bm25_text_to_sparse",
    function_type=FunctionType.BM25,
    input_field_names=["text"],
    output_field_names=["text_sparse"],
)
schema.add_function(bm25_function)
```

#### 索引配置

| 字段 | 索引类型 | 度量类型 | 参数 |
|------|---------|---------|------|
| summary_dense | HNSW | COSINE | M=32, efConstruction=200 |
| text_dense | HNSW | COSINE | M=32, efConstruction=200 |
| text_sparse | SPARSE_WAND | BM25 | bm25_k1=1.5, bm25_b=0.8 |

#### BM25 参数说明

| 参数 | 值 | 说明 |
|------|-----|------|
| k1 | 1.5 | 词频饱和因子，平衡词频重要性，适用于混合语料 |
| b | 0.8 | 长度归一化因子，强归一化确保长短文档公平竞争 |
| RRF k | 60 | Reciprocal Rank Fusion 参数 |

**参数调优依据**：
- 文档类型：技术文档（PDF）+ 问答
- 平均 chunk 大小：约 210 tokens（中等长度）
- 语言：中英混合

#### 混合检索 API

```python
# BM25 搜索
POST /api/v1/milvus/search/bm25/
{
    "collection_name": "documents",
    "query_text": "BM25 查询文本",
    "top_k": 10
}

# 混合检索（Dense + Sparse）
POST /api/v1/milvus/search/hybrid/
{
    "collection_name": "documents",
    "query_text": "查询文本",
    "query_vectors": {"text_dense": [...]},
    "top_k": 10,
    "include_sparse": true,
    "rrf_k": 60
}
```

**流程**:
1. **Query Processing**
   - 用户问题预处理（去停用词、标准化）
   - 生成 query embedding

2. **Retrieval Stage**
   - Milvus 向量检索（语义相似度）
   - Milvus BM25 检索（关键词匹配）
   - Neo4j 图检索（关联实体和概念）
   
3. **Context Assembly**
   - 检索结果去重和排序
   - 构建上下文窗口（max 4000 tokens）
   - 包含：相关文档片段 + 图谱关系 + 对话历史

4. **Generation Stage**
   - Prompt模板渲染
   - 流式调用OpenAI API
   - 实时返回响应块

## WebSocket实时通信

**消息类型**:
```python
# 客户端 → 服务端
{
    "type": "chat.message",
    "content": "用户问题",
    "conversation_id": "uuid"
}

# 服务端 → 客户端
{
    "type": "chat.response.chunk",  # 流式响应
    "content": "AI回复片段",
    "is_final": false
}

{
    "type": "chat.response.complete",
    "message_id": "uuid",
    "sources": [...]  # 引用来源
}
```


## 向量存储策略(向量的查询和存储可参考./docs/reference.md中的示例代码)
**Milvus Collections**:

1. **documents** (文档向量)
   ```python
   def _create_collection(self):
        """ 使用原生 Milvus 客户端创建Collection"""
        assert self.embedding_config.summary_dense.dimension == self.embedding_config.summary_dense.dimension, "多向量单行存储时，两个嵌入模型嵌入向量维度必须相同"
        dim = self.embedding_config.summary_dense.dimension
        if self.milvus_config.drop_old:
            if self.client.has_collection(collection_name=self.milvus_config.collection_name):
                self.client.drop_collection(collection_name=self.milvus_config.collection_name)
            schema = MilvusClient.create_schema(
                auto_id=self.milvus_config.auto_id,
                enable_dynamic_field=True,
            )
            if self.milvus_config.auto_id:
                schema.add_field(field_name="pk",datatype=DataType.INT64, is_primary=True)
            else:
                schema.add_field(field_name="pk",datatype=DataType.VARCHAR, max_length=65535, is_primary=True)
            schema.add_field(
                field_name="text",
                datatype=DataType.VARCHAR,
                max_length=65535,
                enable_analyzer=True
            )
            schema.add_field(
                field_name="summary",
                datatype=DataType.VARCHAR,
                max_length=65535
            )
            schema.add_field(
                field_name="document",
                datatype=DataType.VARCHAR,
                max_length=65535
            )
            schema.add_field(
                field_name="source",
                datatype=DataType.VARCHAR,
                max_length=65535
            )
            schema.add_field(
                field_name="source_name",
                datatype=DataType.VARCHAR,
                max_length=65535
            )
            schema.add_field(
                field_name="lt_doc_id",
                datatype=DataType.VARCHAR,
                max_length=65535
            )
            schema.add_field(
                field_name="chunk_id",
                datatype=DataType.INT64,
                max_length=65535
            )
            schema.add_field(
                field_name="summary_dense",
                datatype=DataType.FLOAT_VECTOR,
                dim=dim
            )
            schema.add_field(
                field_name="text_dense",
                datatype=DataType.FLOAT_VECTOR,
                dim=dim
            )
            schema.add_field(
                field_name="text_sparse",
                datatype=DataType.SPARSE_FLOAT_VECTOR
            )
            if self.embedding_config.text_sparse.provider == "Milvus":
                bm25_fn = Function(
                    name="bm25_text_to_sparse",
                    function_type=FunctionType.BM25,
                    input_field_names=["text"],
                    output_field_names=["text_sparse"],
                )
                schema.add_function(bm25_fn)
                
            self.client.create_collection(collection_name=self.milvus_config.collection_name, schema=schema)
            
            return self.client
        else:
            return self.client  # 如果不删除老集合，那就直接返回，不要创建
    
    def build_index(self):
        """ 构建合适的索引，构建完成之后load """
        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="summary_dense", 
            index_type="HNSW",
            index_name="summary_dense_index",
            metric_type="COSINE",
            params={ "M": 32, "efConstruction": 200 }
        )
        index_params.add_index(
            field_name="text_dense",
            index_type="HNSW",
            index_name="text_dense_index",
            metric_type="COSINE",
            params={ "M": 32, "efConstruction": 200 }
        )
        if self.embedding_config.text_sparse.provider == "self":
            index_params.add_index(
                field_name="text_sparse",
                index_type="SPARSE_INVERTED_INDEX",
                index_name="text_sparse_index",
                metric_type="IP",
                params={ "inverted_index_algo": "DAAT_MAXSCORE" }
            )
        else:
            index_params.add_index(
                field_name="text_sparse",
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="BM25",
                params={
                    "inverted_index_algo": "DAAT_MAXSCORE",
                    "bm25_k1": self.embedding_config.text_sparse.k1,
                    "bm25_b": self.embedding_config.text_sparse.b
                }
            )
        self.client.create_index(
            collection_name=self.milvus_config.collection_name,
            index_params=index_params
        )
        self.client.load_collection(self.milvus_config.collection_name)
   ```

2. **chat_history** (对话向量)
   ```python
   {
       "id": "uuid",
       "embedding": [float] * 1536,
       "message": "用户问题或AI回复",
       "role": "user|assistant",
       "conversation_id": "uuid",
       "timestamp": datetime
   }
   ```
   
## Neo4j图谱粗略设计

**节点类型**:
- `Document`: 文档
- `Chunk`: 文档片段
- `Entity`: 实体（人名、地名、组织等）
- `Concept`: 概念/主题
- `User`: 用户

**关系**:
- `(Document)-[:CONTAINS]->(Chunk)`
- `(Chunk)-[:MENTIONS]->(Entity)`
- `(Entity)-[:RELATED_TO]->(Entity)`
- `(Document)-[:ABOUT]->(Concept)`
- `(User)-[:ASKED]->(Question)-[:ANSWERED_BY]->(Chunk)`