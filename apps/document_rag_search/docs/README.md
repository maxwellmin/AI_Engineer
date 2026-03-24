# Document RAG Search Module

> 混合检索模块，提供向量检索、关键词检索和图谱检索的融合搜索能力。

## 概述

Document RAG Search 模块是 Melon RAG 项目的核心搜索层，提供混合检索功能，结合：

- **Milvus 向量检索** - 语义相似度搜索
- **PostgreSQL 全文检索** - 关键词匹配
- **Neo4j 图谱检索** - 实体关系上下文

使用 **RRF (Reciprocal Rank Fusion)** 算法进行结果融合和排序。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    External API Consumers                    │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Views Layer                           │
│  - SearchViews (search, hybrid, advanced search)            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    SearchService (Facade)                    │
│  - Unified search interface                                  │
│  - Result fusion and ranking                                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Vector     │ │    Graph     │ │   Keyword    │
│   Retriever  │ │   Retriever  │ │   Retriever  │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┴────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Modules                          │
│  - MilvusService (vector search)                             │
│  - Neo4jService (graph queries)                              │
│  - EmbeddingService (query embedding)                        │
│  - DocumentChunk model (PostgreSQL FTS)                      │
└─────────────────────────────────────────────────────────────┘
```

## 模块结构

```
apps/document_rag_search/
├── __init__.py                     # 模块初始化
├── apps.py                         # Django AppConfig
├── constants.py                    # 常量定义
├── exceptions.py                   # 异常类
├── dto.py                          # 数据传输对象
├── serializers.py                  # DRF 序列化器
├── urls.py                         # URL 路由
│
├── retrievers/                     # 检索器实现
│   ├── __init__.py
│   ├── base.py                     # BaseRetriever 抽象基类
│   ├── vector_retriever.py         # Milvus 向量检索
│   ├── keyword_retriever.py        # PostgreSQL 全文检索
│   ├── graph_retriever.py          # Neo4j 图谱检索
│   └── fts_utils.py                # FTS 工具函数
│
├── ranking/                        # 排序融合
│   ├── __init__.py
│   ├── rrf_fusion.py               # RRF 融合算法
│   ├── deduplication.py            # 结果去重
│   └── context_expansion.py        # 上下文扩展
│
├── services/                       # 服务层
│   ├── __init__.py
│   └── search_service.py           # SearchService 门面
│
├── views/                          # API 视图
│   ├── __init__.py
│   └── search_views.py             # 搜索 API 端点
│
├── docs/                           # 文档
│   ├── README.md                   # 本文件
│   └── manual_test.md              # 手动测试指南
│
└── tests/                          # 测试
    ├── conftest.py                 # 测试 fixtures
    ├── test_retrievers.py          # 检索器测试
    ├── test_fusion.py              # 融合算法测试
    ├── test_service.py             # 服务层测试
    ├── test_api_views.py           # API 测试
    ├── test_fts_utils.py           # FTS 工具测试
    └── test_integration.py         # 集成测试
```

## 快速开始

### 1. 基本搜索

```python
from apps.document_rag_search.services import SearchService

service = SearchService()

# 简单搜索
response = service.search(
    query="What is machine learning?",
    top_k=10,
)

for result in response.results:
    print(f"Score: {result.score:.2f} - {result.text[:100]}")
```

### 2. 混合搜索

```python
from apps.document_rag_search.dto import HybridSearchRequest
from apps.document_rag_search.services import SearchService

service = SearchService()

request = HybridSearchRequest(
    query="What is machine learning?",
    top_k=10,
    use_vector=True,     # 启用向量检索
    use_keyword=True,    # 启用关键词检索
    use_graph=True,      # 启用图谱检索
    rrf_k=60,            # RRF 参数
)

response = service.hybrid_search(request)

print(f"Total results: {response.total}")
print(f"Retrievers used: {response.retrievers_used}")
print(f"Query time: {response.query_time_ms:.2f}ms")
```

### 3. 高级搜索（带过滤器）

```python
from datetime import datetime, timedelta
from apps.document_rag_search.dto import AdvancedSearchRequest
from apps.document_rag_search.services import SearchService

service = SearchService()

request = AdvancedSearchRequest(
    query="Python programming",
    top_k=10,
    user_id="user-uuid-here",
    document_ids=["doc-uuid-1", "doc-uuid-2"],
    date_from=datetime.now() - timedelta(days=30),
    date_to=datetime.now(),
    use_vector=True,
    use_keyword=True,
    expand_context=True,      # 启用上下文扩展
    context_window=1,         # 扩展窗口大小
)

response = service.advanced_search(request)
```

### 4. 搜索建议

```python
from apps.document_rag_search.dto import SearchSuggestionsRequest
from apps.document_rag_search.services import SearchService

service = SearchService()

request = SearchSuggestionsRequest(
    prefix="mach",
    limit=5,
)

response = service.get_search_suggestions(request)

for suggestion in response.suggestions:
    print(suggestion)
```

## API 端点

### POST /api/v1/search/simple/

简单向量搜索。

**请求:**
```json
{
    "query": "What is machine learning?",
    "top_k": 10,
    "user_id": "optional-user-uuid"
}
```

**响应:**
```json
{
    "results": [
        {
            "chunk_id": "uuid",
            "document_id": "uuid",
            "text": "Machine learning is...",
            "score": 0.95,
            "source": "document.pdf",
            "metadata": {
                "chunk_index": 0,
                "page_number": 1
            },
            "retriever_scores": {
                "vector": 0.95
            }
        }
    ],
    "total": 1,
    "query_time_ms": 150.5,
    "retrievers_used": ["vector"]
}
```

### POST /api/v1/search/hybrid/

混合搜索，支持多种检索器。

**请求:**
```json
{
    "query": "What is machine learning?",
    "top_k": 10,
    "use_vector": true,
    "use_keyword": true,
    "use_graph": false,
    "filters": {
        "user_id": "uuid",
        "document_ids": ["uuid1", "uuid2"]
    },
    "rrf_k": 60,
    "weights": {
        "vector": 0.5,
        "keyword": 0.3,
        "graph": 0.2
    }
}
```

### POST /api/v1/search/advanced/

高级搜索，支持更多过滤器。

**请求:**
```json
{
    "query": "Python programming",
    "top_k": 10,
    "use_vector": true,
    "use_keyword": true,
    "user_id": "uuid",
    "document_ids": ["uuid"],
    "date_from": "2026-01-01T00:00:00Z",
    "date_to": "2026-12-31T23:59:59Z",
    "file_types": ["pdf", "docx"],
    "expand_context": true,
    "context_window": 1
}
```

### GET /api/v1/search/suggestions/

搜索建议。

**请求:**
```
GET /api/v1/search/suggestions/?prefix=mach&limit=5
```

**响应:**
```json
{
    "suggestions": [
        "machine learning algorithms",
        "machine learning models",
        "machine learning techniques"
    ],
    "total": 3
}
```

### GET /api/v1/search/health/

健康检查。

**响应:**
```json
{
    "vector": true,
    "keyword": true,
    "graph": true,
    "overall": true
}
```

## 配置

在 `config/settings/base.py` 中配置：

```python
SEARCH_CONFIG = {
    # 默认参数
    "default_top_k": 10,
    "default_rrf_k": 60,
    "max_query_length": 500,
    "min_query_length": 2,

    # 检索器权重
    "retriever_weights": {
        "vector": 0.4,
        "keyword": 0.3,
        "graph": 0.3,
    },

    # 检索器设置
    "retrievers": {
        "vector": {
            "enabled": True,
            "collection_name": "documents",
            "anns_field": "text_dense",
        },
        "keyword": {
            "enabled": True,
            "fts_config": "simple",
        },
        "graph": {
            "enabled": True,
            "max_depth": 2,
        },
    },

    # 上下文扩展
    "context_expansion": {
        "enabled": False,
        "window_size": 1,
    },

    # 搜索建议
    "suggestions": {
        "enabled": True,
        "min_prefix_length": 2,
        "limit": 5,
    },
}
```

## 检索器说明

### VectorRetriever

使用 Milvus 进行向量相似度搜索。

**特点:**
- 语义相似度匹配
- 支持单字段和多字段混合搜索
- 支持 user_id 和 document_ids 过滤

**适用场景:**
- 概念性查询
- 相似内容发现
- 跨语言搜索

### KeywordRetriever

使用 PostgreSQL 全文检索。

**特点:**
- 精确关键词匹配
- 支持中英文混合搜索
- 自动降级到 LIKE 搜索

**适用场景:**
- 专业术语搜索
- 精确匹配需求
- 无向量索引时的备选方案

### GraphRetriever

使用 Neo4j 知识图谱进行实体检索。

**特点:**
- 基于实体关系的上下文发现
- 多跳关系遍历
- 简单关键词提取（MVP）

**适用场景:**
- 实体相关内容发现
- 关系推理
- 知识图谱增强检索

## RRF 融合算法

Reciprocal Rank Fusion (RRF) 是一种简单有效的多路结果融合算法。

**公式:**
```
score(d) = Σ (weight_i / (k + rank_i(d)))
```

其中:
- `d` 是文档
- `rank_i(d)` 是文档 d 在检索器 i 中的排名
- `k` 是 RRF 参数（默认 60）
- `weight_i` 是检索器 i 的权重

**示例:**
```python
# 文档 A 在向量检索中排名第 1，在关键词检索中排名第 3
# k = 60, weights = {"vector": 0.4, "keyword": 0.3}

score_A = 0.4 / (60 + 1) + 0.3 / (60 + 3)
        = 0.00656 + 0.00476
        = 0.01132
```

## 测试

### 运行测试

```bash
# 运行所有测试
pytest apps/document_rag_search/tests/ -v

# 运行带覆盖率
pytest apps/document_rag_search/tests/ --cov=apps/document_rag_search --cov-report=term-missing

# 仅运行单元测试
pytest apps/document_rag_search/tests/ -v -m "not integration"

# 运行集成测试（需要运行中的服务）
pytest apps/document_rag_search/tests/ -v -m integration

# 运行 API 测试
pytest apps/document_rag_search/tests/test_api_views.py -v
```

### 测试覆盖率

当前测试覆盖率：**91%**

| 模块 | 覆盖率 |
|------|--------|
| constants.py | 100% |
| dto.py | 98% |
| rrf_fusion.py | 95% |
| vector_retriever.py | 97% |
| keyword_retriever.py | 93% |
| graph_retriever.py | 90% |
| search_service.py | 89% |
| search_views.py | 91% |

## 错误处理

模块定义了完整的异常层次结构：

```
SearchError (基类)
├── InvalidQueryError
│   ├── EmptyQueryError
│   ├── QueryTooLongError
│   └── QueryTooShortError
├── RetrieverError
│   ├── VectorRetrieverError
│   ├── KeywordRetrieverError
│   └── GraphRetrieverError
├── FusionError
└── NoResultsError
```

**示例:**
```python
from apps.document_rag_search.exceptions import (
    EmptyQueryError,
    QueryTooLongError,
    NoResultsError,
)
from apps.document_rag_search.services import SearchService

service = SearchService()

try:
    response = service.search(query="", top_k=10)
except EmptyQueryError:
    print("Query cannot be empty")
except QueryTooLongError as e:
    print(f"Query too long: {e.length} chars (max: {e.max_length})")
except NoResultsError:
    print("No results found")
```

## 扩展指南

### 添加新的检索器

1. 继承 `BaseRetriever`:

```python
from apps.document_rag_search.retrievers.base import BaseRetriever
from apps.document_rag_search.dto import RetrieverResult, SearchQuery

class CustomRetriever(BaseRetriever):
    @property
    def name(self) -> str:
        return "custom"

    def retrieve(
        self,
        query: SearchQuery,
        top_k: int = 10,
        **kwargs,
    ) -> RetrieverResult:
        # 实现检索逻辑
        pass

    def health_check(self) -> bool:
        # 实现健康检查
        pass
```

2. 在 `SearchService` 中注册:

```python
# services/search_service.py
from apps.document_rag_search.retrievers import CustomRetriever

class SearchService:
    def __init__(self) -> None:
        # ...
        self.custom_retriever = CustomRetriever()
```

### 添加新的排序方法

1. 创建新的 fusion 类:

```python
# ranking/custom_fusion.py
class CustomFusion:
    def fuse(
        self,
        retriever_results: dict[str, RetrieverResult],
        top_k: int,
    ) -> list[RankedResult]:
        # 实现融合逻辑
        pass
```

2. 在 `SearchService` 中使用:

```python
# services/search_service.py
from apps.document_rag_search.ranking.custom_fusion import CustomFusion

class SearchService:
    def _apply_custom_fusion(self, ...):
        fusion = CustomFusion()
        return fusion.fuse(...)
```

## 性能建议

1. **查询优化**
   - 限制 `top_k` 在合理范围（10-50）
   - 使用过滤器减少搜索空间
   - 避免过长的查询文本

2. **缓存策略**
   - 对高频查询实现结果缓存
   - 考虑查询向量缓存

3. **并发控制**
   - 检索器并行执行
   - 限制并发检索器数量

4. **资源监控**
   - 监控 Milvus/Neo4j 连接池
   - 关注查询延迟分布

## 依赖

| 模块 | 用途 |
|------|------|
| Phase 6: Milvus | 向量存储和检索 |
| Phase 7: Neo4j | 知识图谱存储和查询 |
| Phase 8: Embedding | 查询向量化 |
| Phase 9: Document Pipeline | 文档处理和索引 |

## 参考文档

- [RRF 论文](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [PostgreSQL 全文检索](https://www.postgresql.org/docs/current/textsearch.html)
- [Milvus 混合搜索](https://milvus.io/docs/multi-vector-search.md)
- [Neo4j Cypher 查询](https://neo4j.com/docs/cypher-manual/current/)

---

*Generated: 2026-03-18*
*Phase 10: Document RAG Search Module*
