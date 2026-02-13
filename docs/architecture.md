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
└────┬──────────────┬──────────────┬──────────────┬───────────┘
     │              │              │              │
     ▼              ▼              ▼              ▼
┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│PostgreSQL│ │  Milvus  │  │  Neo4j   │  │ QWEN API     │
│ (主数据) │  │ (向量库)  │  │ (知识图)  │  │ (LLM+Embed)  │
└─────────┘  └──────────┘  └──────────┘  └──────────────┘
```

## 项目核心组件和模块

### Django Backend
- **Django Channels**: 处理 WebSocket 连接，实现实时通信功能。
- **Django REST Framework**: 提供 RESTful API 接口，支持 curl、wcat、postman 等工具进行测试和交互。

### document parser(document processing)
- **document parser**: 用于解析文档，拆分文档为句子，段落，形成符合逻辑的chunking, 方便后续通过LLM Embeding进行向量化存储和搜索。
- **document meta management(文档级别)**: 用于维护文档元数据，如文档ID，文档名称，文档路径，文档创建时间，文档更新时间，文档大小，文档类型，文档状态等。
- **document deduplication**: 用于去重文档，避免重复存储和处理相同的文档。结合meta以及chunking的元数据，可以快速找到chunking的部分是否已经被向量化和存储，从而避免重复处理。

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


## 数据流设计

### 文档上传流程
```
User Upload → Django API → Document Parser → Text Chunking
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
**流程**:
1. **Query Processing**
   - 用户问题预处理（去停用词、标准化）
   - 生成query embedding

2. **Retrieval Stage**
   - Milvus向量检索（语义相似度）
   - Neo4j图检索（关联实体和概念）
   - PostgreSQL关键词检索（补充）
   
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