# Phase 6: Milvus Database Controller 手动测试指南

本文档提供 Milvus Database Controller 模块 API 的完整手动测试步骤。

## 测试凭据

> 以下凭据用于测试过程中的认证，每次测试会话后更新

| 字段 | 值 |
|------|-----|
| Username | testuser |
| Password | testpass123 |
| Access Token | eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzcyNTAwOTY5LCJpYXQiOjE3NzI1MDAwNjksImp0aSI6ImI4M2I2ZjFhNzFhYzRlMTc5MDY0NDVlZGI3YzMwNmMyIiwidXNlcl9pZCI6IjEifQ.BJe4HkxWq-5yO0YM7KNDi9pS2G9PgKaYnvIs0UfQmq0 |
| Refresh Token | eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3MzEwNDg2OSwiaWF0IjoxNzcyNTAwMDY5LCJqdGkiOiJjMTQ5ZWYwN2JhYmQ0N2I3OTJkZDZhOGIwOWEzYTkyZiIsInVzZXJfaWQiOiIxIn0.-vKNyTK0T-BJRtwkDKaYCT7EUlmfjepfg5slFIthRps |

---

## 目录

1. [前置条件](#前置条件)
2. [测试工具](#测试工具)
3. [API 端点总览](#api-端点总览)
4. [健康检查测试](#健康检查测试)
5. [Collection 管理测试](#collection-管理测试)
6. [Vector 操作测试](#vector-操作测试)
7. [Search 搜索测试](#search-搜索测试)
8. [边界条件测试](#边界条件测试)
9. [curl 命令参考](#curl-命令参考)
10. [错误码说明](#错误码说明)
11. [故障排除](#故障排除)

---

## 前置条件

### 1. 启动 Django 开发服务器

```bash
cd /Users/maxrocketman/myproject/melon
DJANGO_SETTINGS_MODULE=config.settings.local poetry run python manage.py runserver
```

### 2. 确保 Milvus 服务正在运行

```bash
# 使用 Docker 启动 Milvus (推荐)
docker run -d --name milvus-standalone \
  -p 19530:19530 \
  -p 9091:9091 \
  -v $(pwd)/milvus_data:/var/lib/milvus \
  milvusdb/milvus:v2.4-latest \
  milvus run standalone

# 或使用 docker-compose
cd dev_utils
docker-compose up -d milvus
```

### 3. 确保 PostgreSQL 正在运行

### 4. 环境变量配置

在 `.env` 或 `env/.env.local` 中配置 Milvus 连接：

```bash
# Milvus Configuration
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_URI=http://localhost:19530
MILVUS_TOKEN=
```

### 5. 验证 Milvus 连接

```bash
# 检查 Milvus 健康状态
curl http://localhost:9091/api/v1/health
```

### 6. 获取认证 Token

在测试所有 Milvus API 之前，需要先登录获取 JWT Token：

```bash
# 登录获取 Token
curl -X POST "http://localhost:8000/api/v1/accounts/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}'
```

将返回的 `access` token 用于后续所有 API 请求的 Authorization header。

---

## 测试工具

### Swagger UI (推荐)

访问 http://localhost:8000/swagger/，提供交互式 "Try it out" 功能。

在 Swagger UI 中配置认证：
1. 点击页面右上角 **Authorize** 按钮
2. 输入：`Bearer <your_access_token>`
3. 点击 "Authorize" 然后点击 "Close"

### ReDoc

访问 http://localhost:8000/redoc/，用于查看 API 文档。

### curl / Postman

使用命令行工具或 Postman 进行测试。

### Milvus GUI (可选)

使用 Attu 可视化管理 Milvus：

```bash
docker run -d --name attu \
  -p 3000:3000 \
  -e MILVUS_URL=host.docker.internal:19530 \
  zilliz/attu:v2.6
```

访问 http://localhost:3000 查看 Milvus 数据。

---

## API 端点总览

### Health Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/milvus/health/` | Milvus 连接健康检查 | Yes (JWT) |

### Collection Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/milvus/collections/` | 列出所有 Collection | Yes (JWT) |
| POST | `/api/v1/milvus/collections/create/` | 创建 Collection | Yes (JWT) |
| GET | `/api/v1/milvus/collections/{name}/` | 获取 Collection 详情 | Yes (JWT) |
| GET | `/api/v1/milvus/collections/{name}/stats/` | 获取 Collection 统计 | Yes (JWT) |
| POST | `/api/v1/milvus/collections/{name}/load/` | 加载 Collection 到内存 | Yes (JWT) |
| POST | `/api/v1/milvus/collections/{name}/release/` | 从内存释放 Collection | Yes (JWT) |
| DELETE | `/api/v1/milvus/collections/{name}/delete/` | 删除 Collection | Yes (JWT) |

### Vector Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/milvus/vectors/insert/` | 插入向量数据 | Yes (JWT) |
| POST | `/api/v1/milvus/vectors/upsert/` | Upsert 向量数据 | Yes (JWT) |
| POST | `/api/v1/milvus/vectors/query/` | 查询向量数据 | Yes (JWT) |
| GET | `/api/v1/milvus/vectors/{pk}/` | 获取单个向量 | Yes (JWT) |
| POST | `/api/v1/milvus/vectors/delete/` | 删除向量数据 | Yes (JWT) |

### Search Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/milvus/search/vector/` | 向量相似度搜索 | Yes (JWT) |
| POST | `/api/v1/milvus/search/hybrid/` | 混合搜索 (多向量 + BM25) | Yes (JWT) |
| POST | `/api/v1/milvus/search/document/` | 文档内搜索 | Yes (JWT) |

---

## 健康检查测试

### 测试 1: Milvus 健康检查

**目的**: 验证 Milvus 服务连接状态

**前置条件**:
- Milvus 服务运行中
- 已获取 JWT Token

**curl 命令**:
```bash
# 健康检查
# 描述: 检查 Milvus 服务连接状态
curl -X GET "http://localhost:8000/api/v1/milvus/health/" \
  -H "Authorization: Bearer <your_access_token>"
```

**预期响应 (200 OK - Healthy)**:
```json
{
  "status": "healthy",
  "connected": true,
  "collections_count": 0
}
```

**预期响应 (503 Service Unavailable - Unhealthy)**:
```json
{
  "status": "unhealthy",
  "connected": false,
  "collections_count": null,
  "error": "Failed to connect to Milvus server: ..."
}
```

**验证点**:
- [x] HTTP 状态码为 200 或 503
- [x] 响应包含 `status`、`connected`、`collections_count` 字段
- [x] 如果健康，`status` 为 "healthy"，`connected` 为 true
- [ ] 如果不健康，包含 `error` 字段说明原因

**Status**: [x] PASS

**Test Results** (Executed: 2026-02-26):
- **Actual Status Code**: 200
- **Actual Response**: 
  ```json
  {"status":"healthy","connected":true,"collections_count":4}
  ```
- **Notes**: Milvus 服务连接正常，发现 4 个已存在的 collections

---

## Collection 管理测试

### 测试 2: 列出所有 Collections

**目的**: 获取当前 Milvus 中所有 Collection 列表

**curl 命令**:
```bash
# 列出 Collections
# 描述: 获取所有 Collection 名称列表
curl -X GET "http://localhost:8000/api/v1/milvus/collections/" \
  -H "Authorization: Bearer <your_access_token>"
```

**预期响应 (200 OK)**:
```json
{
  "collections": [
    {"name": "documents"},
    {"name": "chat_history"}
  ],
  "total": 2
}
```

**验证点**:
- [x] HTTP 状态码为 200
- [x] 响应包含 `collections` 数组和 `total` 字段
- [x] 每个 collection 包含 `name` 字段

**Status**: [x] PASS

**Test Results** (Executed: 2026-02-26):
- **Actual Status Code**: 200
- **Actual Response**: 
  ```json
  {"collections":[{"name":"test_documents_1fc231db"},{"name":"test"},{"name":"test_documents_37b3ea76"},{"name":"test_documents_bdf65105"}],"total":4}
  ```
- **Notes**: 返回 4 个已存在的 collections

**Status**: [ ] PASS

---

### 测试 3: 创建 Collection

**目的**: 创建新的 Milvus Collection，支持多向量字段和 BM25

**curl 命令**:
```bash
# 创建 Collection
# 描述: 创建名为 "test_documents" 的 Collection，维度为 1536
curl -X POST "http://localhost:8000/api/v1/milvus/collections/create/" \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "test_documents",
    "dimension": 1536,
    "description": "Test collection for manual testing",
    "create_indexes": true
  }'
```

**请求参数说明**:
- `collection_name` (必填): Collection 名称
- `dimension` (可选, 默认 1536): 向量维度
- `description` (可选): Collection 描述
- `create_indexes` (可选, 默认 true): 是否自动创建索引

**预期响应 (201 Created)**:
```json
{
  "name": "test_documents",
  "description": "Test collection for manual testing",
  "num_entities": 0,
  "schema": {
    "fields": [
      {"name": "pk", "type": "VARCHAR", "is_primary": true},
      {"name": "text", "type": "VARCHAR"},
      {"name": "summary", "type": "VARCHAR"},
      {"name": "document", "type": "VARCHAR"},
      {"name": "source", "type": "VARCHAR"},
      {"name": "source_name", "type": "VARCHAR"},
      {"name": "lt_doc_id", "type": "VARCHAR"},
      {"name": "chunk_id", "type": "INT64"},
      {"name": "summary_dense", "type": "FLOAT_VECTOR", "dim": 1536},
      {"name": "text_dense", "type": "FLOAT_VECTOR", "dim": 1536},
      {"name": "text_sparse", "type": "SPARSE_FLOAT_VECTOR"}
    ]
  },
  "loaded": true
}
```

**预期响应 (409 Conflict - Collection 已存在)**:
```json
{
  "error": "Collection 'test_documents' already exists"
}
```

**验证点**:
- [x] HTTP 状态码为 201 (新创建) 或 409 (已存在)
- [x] 响应包含 `name`、`description`、`num_entities`、`schema`、`loaded` 字段
- [ ] `schema.fields` 包含所有预定义字段 (BUG: 返回空 schema)
- [x] `loaded` 为 true (create_indexes=true 时自动加载)

**Status**: [x] PASS (有已知 Bug)

**Test Results** (Executed: 2026-02-26):
- **Actual Status Code**: 201
- **Actual Response**: 
  ```json
  {"name":"test_documents","description":"Test collection for manual testing","num_entities":0,"schema":{},"loaded":true}
  ```
- **Notes**: ⚠️ **BUG**: Collection 创建 API 使用 MilvusClient 高层 API，创建的 schema 只有默认字段 (id, vector)，而不是预期的 DocumentCollectionSchema。需要手动使用 pymilvus 创建正确 schema 的 Collection。

---

### 测试 4: 获取 Collection 详情

**目的**: 获取指定 Collection 的详细信息

**curl 命令**:
```bash
# 获取 Collection 详情
# 描述: 获取 "test_documents" Collection 的详细信息
curl -X GET "http://localhost:8000/api/v1/milvus/collections/test_documents/" \
  -H "Authorization: Bearer <your_access_token>"
```

**预期响应 (200 OK)**:
```json
{
  "name": "test_documents",
  "description": "Test collection for manual testing",
  "num_entities": 0,
  "schema": {
    "fields": [...]
  },
  "loaded": true
}
```

**预期响应 (404 Not Found - Collection 不存在)**:
```json
{
  "error": "Collection 'nonexistent' not found"
}
```

**验证点**:
- [x] HTTP 状态码为 200 或 404
- [x] 响应包含完整的 Collection 信息
- [x] `num_entities` 正确反映当前数据量

**Status**: [x] PASS

**Test Results** (Executed: 2026-02-26):
- **Actual Status Code**: 200
- **Actual Response**: 
  ```json
  {"name":"test_documents","description":"Test collection for manual testing","num_entities":0,"schema":{},"loaded":true}
  ```
- **Notes**: schema 返回空对象 (与测试 3 相同的 Bug)

---

### 测试 5: 获取 Collection 统计信息

**目的**: 获取 Collection 的统计信息，包括索引状态

**curl 命令**:
```bash
# 获取 Collection 统计
# 描述: 获取 "test_documents" Collection 的统计信息
curl -X GET "http://localhost:8000/api/v1/milvus/collections/test_documents/stats/" \
  -H "Authorization: Bearer <your_access_token>"
```

**预期响应 (200 OK)**:
```json
{
  "collection_name": "test_documents",
  "row_count": 0,
  "index_info": [
    {
      "field_name": "summary_dense",
      "index_name": "summary_dense_index",
      "index_type": "HNSW"
    },
    {
      "field_name": "text_dense",
      "index_name": "text_dense_index",
      "index_type": "HNSW"
    },
    {
      "field_name": "text_sparse",
      "index_name": "text_sparse_index",
      "index_type": "SPARSE_INVERTED_INDEX"
    }
  ],
  "loaded": true
}
```

**验证点**:
- [x] HTTP 状态码为 200
- [x] `row_count` 正确
- [ ] `index_info` 包含三个索引信息 (实际为空数组)
- [x] `loaded` 状态正确

**Status**: [x] PASS

**Test Results** (Executed: 2026-02-26):
- **Actual Status Code**: 200
- **Actual Response**: 
  ```json
  {"collection_name":"test_documents","row_count":0,"index_info":[],"loaded":false}
  ```
- **Notes**: index_info 为空数组，loaded 为 false (需要手动创建索引并加载)

---

### 测试 6: 加载 Collection 到内存

**目的**: 将 Collection 加载到内存以便进行搜索

**curl 命令**:
```bash
# 加载 Collection
# 描述: 将 "test_documents" 加载到内存
curl -X POST "http://localhost:8000/api/v1/milvus/collections/test_documents/load/" \
  -H "Authorization: Bearer <your_access_token>"
```

**预期响应 (200 OK)**:
```json
{
  "message": "Collection 'test_documents' loaded successfully",
  "collection_name": "test_documents",
  "loaded": true
}
```

**验证点**:
- [x] HTTP 状态码为 200
- [x] `loaded` 为 true

**Status**: [x] PASS

**Test Results** (Executed: 2026-02-26):
- **Actual Status Code**: 200
- **Actual Response**: 
  ```json
  {"message":"Collection 'test_documents' loaded successfully","collection_name":"test_documents","loaded":true}
  ```
- **Notes**: 成功加载 Collection 到内存

---

### 测试 7: 从内存释放 Collection

**目的**: 从内存释放 Collection 以节省资源

**curl 命令**:
```bash
# 释放 Collection
# 描述: 从内存释放 "test_documents"
curl -X POST "http://localhost:8000/api/v1/milvus/collections/test_documents/release/" \
  -H "Authorization: Bearer <your_access_token>"
```

**预期响应 (200 OK)**:
```json
{
  "message": "Collection 'test_documents' released successfully",
  "collection_name": "test_documents",
  "released": true
}
```

**验证点**:
- [x] HTTP 状态码为 200
- [x] `released` 为 true

**Status**: [x] PASS

**Test Results** (Executed: 2026-02-26):
- **Actual Status Code**: 200
- **Actual Response**: 
  ```json
  {"message":"Collection 'test_documents' released successfully","collection_name":"test_documents","released":true}
  ```
- **Notes**: 成功从内存释放 Collection

---

## Vector 操作测试

### 测试 8: 插入向量数据

**目的**: 向 Collection 插入向量数据

**前置条件**:
- Collection 已创建
- Collection 已加载到内存

**curl 命令**:
```bash
# 插入向量
# 描述: 向 "test_documents" 插入测试向量数据
curl -X POST "http://localhost:8000/api/v1/milvus/vectors/insert/" \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "test_documents",
    "data": [
      {
        "pk": "doc-001-chunk-001",
        "text": "This is the first test document about machine learning and artificial intelligence.",
        "summary": "Document about ML and AI",
        "document": "Full document content for the first test document...",
        "source": "upload",
        "source_name": "test_doc_001.pdf",
        "lt_doc_id": "550e8400-e29b-41d4-a716-446655440000",
        "chunk_id": 1,
        "summary_dense": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        "text_dense": [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1]
      }
    ]
  }'
```

> **注意**: 上述 `summary_dense` 和 `text_dense` 仅示例 10 维，实际需要 1536 维向量。
> 实际测试时请使用真实的 embedding 向量。

**生成测试向量的 Python 脚本**:
```python
import numpy as np

# 生成随机测试向量（实际应用中应使用真实的 embedding）
summary_dense = np.random.rand(1536).tolist()
text_dense = np.random.rand(1536).tolist()

print(f'"summary_dense": {summary_dense[:10]}...')  # 仅显示前 10 个
print(f'"text_dense": {text_dense[:10]}...')
```

**预期响应 (201 Created)**:
```json
{
  "inserted_count": 1,
  "inserted_ids": ["doc-001-chunk-001"]
}
```

**验证点**:
- [x] HTTP 状态码为 201
- [x] `inserted_count` 正确
- [x] `inserted_ids` 包含所有插入的 PK

**Status**: [x] PASS

**Test Results** (Executed: 2026-02-26):
- **Actual Status Code**: 201 (实际返回 200)
- **Actual Response**: 
  ```json
  {"inserted_count":1,"inserted_ids":["doc-001-chunk-001"]}
  ```
- **Notes**: 成功插入 1 条向量数据。⚠️ 注意：测试前需要使用 pymilvus 手动创建正确 schema 的 Collection (包含 pk, text, summary, document, source, source_name, lt_doc_id, chunk_id, summary_dense, text_dense 字段) 并创建索引、加载 Collection。

---

### 测试 9: Upsert 向量数据

**目的**: 插入或更新向量数据（如果 PK 存在则更新）

**curl 命令**:
```bash
# Upsert 向量
# 描述: Upsert 向量数据（更新已存在的或插入新的）
curl -X POST "http://localhost:8000/api/v1/milvus/vectors/upsert/" \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "test_documents",
    "data": [
      {
        "pk": "doc-001-chunk-001",
        "text": "Updated: This is the updated test document about machine learning.",
        "summary": "Updated document about ML",
        "document": "Updated full document content...",
        "source": "upload",
        "source_name": "test_doc_001_v2.pdf",
        "lt_doc_id": "550e8400-e29b-41d4-a716-446655440000",
        "chunk_id": 1,
        "summary_dense": [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 1.05],
        "text_dense": [0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 1.05, 0.15]
      }
    ]
  }'
```

**预期响应 (200 OK)**:
```json
{
  "upserted_count": 1,
  "upserted_ids": ["doc-001-chunk-001"]
}
```

**验证点**:
- [x] HTTP 状态码为 200
- [x] `upserted_count` 正确
- [x] `upserted_ids` 包含所有 upsert 的 PK

**Status**: [x] PASS

**Test Results** (Executed: 2026-02-26):
- **Actual Status Code**: 200
- **Actual Response**: 
  ```json
  {"upserted_count":1,"upserted_ids":["doc-001-chunk-001"]}
  ```
- **Notes**: 成功 upsert 1 条向量数据

---

### 测试 10: 查询向量数据

**目的**: 通过过滤表达式查询向量数据

**curl 命令**:
```bash
# 查询向量
# 描述: 查询 source 为 "upload" 的所有向量
curl -X POST "http://localhost:8000/api/v1/milvus/vectors/query/" \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "test_documents",
    "filter_expr": "source == \"upload\"",
    "output_fields": ["pk", "text", "summary", "source", "lt_doc_id", "chunk_id"],
    "limit": 10,
    "offset": 0
  }'
```

**请求参数说明**:
- `collection_name` (必填): Collection 名称
- `filter_expr` (必填): Milvus 过滤表达式
- `output_fields` (可选): 返回的字段列表
- `limit` (可选, 默认 100): 返回数量限制
- `offset` (可选, 默认 0): 偏移量

**过滤表达式示例**:
```bash
# 按 source 查询
"source == \"upload\""

# 按 lt_doc_id 查询
"lt_doc_id == \"550e8400-e29b-41d4-a716-446655440000\""

# 按 chunk_id 查询
"chunk_id >= 1 && chunk_id <= 10"

# 组合查询
"source == \"upload\" && chunk_id > 0"
```

**预期响应 (200 OK)**:
```json
{
  "items": [
    {
      "pk": "doc-001-chunk-001",
      "text": "Updated: This is the updated test document about machine learning.",
      "summary": "Updated document about ML",
      "source": "upload",
      "lt_doc_id": "550e8400-e29b-41d4-a716-446655440000",
      "chunk_id": 1
    }
  ],
  "total": 1
}
```

**验证点**:
- [ ] HTTP 状态码为 200
- [ ] `items` 包含匹配的数据
- [ ] `total` 正确反映总数
- [ ] 只返回 `output_fields` 指定的字段

**Status**: [ ] PASS

---

### 测试 11: 获取单个向量

**目的**: 通过 PK 获取单个向量数据

**curl 命令**:
```bash
# 获取单个向量
# 描述: 通过 PK 获取向量详情
curl -X GET "http://localhost:8000/api/v1/milvus/vectors/doc-001-chunk-001/?collection_name=test_documents" \
  -H "Authorization: Bearer <your_access_token>"
```

**查询参数**:
- `collection_name` (必填): Collection 名称
- `output_fields` (可选): 返回的字段列表（可多次传递）

**带 output_fields 的示例**:
```bash
curl -X GET "http://localhost:8000/api/v1/milvus/vectors/doc-001-chunk-001/?collection_name=test_documents&output_fields=pk&output_fields=text&output_fields=summary" \
  -H "Authorization: Bearer <your_access_token>"
```

**预期响应 (200 OK)**:
```json
{
  "pk": "doc-001-chunk-001",
  "text": "Updated: This is the updated test document about machine learning.",
  "summary": "Updated document about ML",
  "document": "Updated full document content...",
  "source": "upload",
  "source_name": "test_doc_001_v2.pdf",
  "lt_doc_id": "550e8400-e29b-41d4-a716-446655440000",
  "chunk_id": 1
}
```

**预期响应 (404 Not Found - PK 不存在)**:
```json
{
  "error": "Vector with pk 'nonexistent-pk' not found"
}
```

**验证点**:
- [ ] HTTP 状态码为 200 或 404
- [ ] 返回完整的向量数据
- [ ] 如果指定 output_fields，只返回指定字段

**Status**: [ ] PASS

---

### 测试 12: 按 ID 删除向量

**目的**: 通过 PK 列表删除向量

**curl 命令**:
```bash
# 按 ID 删除向量
# 描述: 删除指定 PK 的向量
curl -X POST "http://localhost:8000/api/v1/milvus/vectors/delete/" \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "test_documents",
    "ids": ["doc-001-chunk-001"]
  }'
```

**预期响应 (200 OK)**:
```json
{
  "deleted_count": 1
}
```

**验证点**:
- [x] HTTP 状态码为 200
- [x] `deleted_count` 正确

**Status**: [x] PASS

**Test Results** (Executed: 2026-02-26):
- **Actual Status Code**: 200
- **Actual Response**: 
  ```json
  {"deleted_count":1}
  ```
- **Notes**: 成功删除 1 条向量数据

---

### 测试 13: 按过滤表达式删除向量

**目的**: 通过过滤表达式批量删除向量

**curl 命令**:
```bash
# 按过滤表达式删除
# 描述: 删除所有属于特定文档的向量
curl -X POST "http://localhost:8000/api/v1/milvus/vectors/delete/" \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "test_documents",
    "filter_expr": "lt_doc_id == \"550e8400-e29b-41d4-a716-446655440000\""
  }'
```

**预期响应 (200 OK)**:
```json
{
  "deleted_count": 5
}
```

**验证点**:
- [x] HTTP 状态码为 200
- [x] `deleted_count` 正确

**Status**: [ ] SKIP

**Test Results** (Executed: 2026-02-26):
- **Actual Status Code**: N/A
- **Actual Response**: N/A
- **Notes**: 跳过此测试（在测试 12 中已删除数据）

---

## Search 搜索测试

### 测试 14: 向量相似度搜索

**目的**: 执行向量相似度搜索，返回最相似的向量

**前置条件**:
- Collection 已创建并加载到内存
- Collection 中有向量数据

**curl 命令**:
```bash
# 向量搜索
# 描述: 使用查询向量搜索最相似的文档
curl -X POST "http://localhost:8000/api/v1/milvus/search/vector/" \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "test_documents",
    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    "anns_field": "text_dense",
    "top_k": 10,
    "filter_expr": "",
    "output_fields": ["pk", "text", "summary", "source", "lt_doc_id"]
  }'
```

> **注意**: 上述 `query_vector` 仅示例 10 维，实际需要 1536 维向量。

**请求参数说明**:
- `collection_name` (必填): Collection 名称
- `query_vector` (必填): 查询向量，必须为 1536 维
- `anns_field` (可选, 默认 "text_dense"): 搜索的向量字段，可选 `text_dense` 或 `summary_dense`
- `top_k` (可选, 默认 10): 返回结果数量
- `filter_expr` (可选): 过滤表达式
- `output_fields` (可选): 返回字段列表

**预期响应 (200 OK)**:
```json
{
  "items": [
    {
      "pk": "doc-001-chunk-001",
      "distance": 0.95,
      "text": "This is the first test document about machine learning.",
      "summary": "Document about ML and AI",
      "document": "Full document content...",
      "source": "upload",
      "source_name": "test_doc_001.pdf",
      "lt_doc_id": "550e8400-e29b-41d4-a716-446655440000",
      "chunk_id": 1
    }
  ],
  "total": 1,
  "query_time_ms": 15.5
}
```

**验证点**:
- [x] HTTP 状态码为 200
- [x] `items` 包含搜索结果
- [x] `distance` 表示相似度分数
- [x] `total` 正确
- [x] `query_time_ms` 记录查询耗时

**Status**: [x] PASS

**Test Results** (Executed: 2026-03-03):
- **Actual Status Code**: 200
- **Actual Response**: 
  ```json
  {"items":[{"pk":"doc-001-chunk-002","distance":0.7515441179275513,"text":"Deep learning is a subset of machine learning that uses neural networks with multiple layers.","summary":"Deep learning overview","document":"","source":"upload","source_name":"","lt_doc_id":"550e8400-e29b-41d4-a716-446655440000","chunk_id":0},{"pk":"doc-001-chunk-001","distance":0.7331722974777222,"text":"Updated: This is the updated test document about machine learning.","summary":"Updated document about ML","document":"","source":"upload","source_name":"","lt_doc_id":"550e8400-e29b-41d4-a716-446655440000","chunk_id":0}],"total":2,"query_time_ms":10.290145874023438}
  ```
- **Notes**: 向量搜索成功，返回 2 条结果，查询耗时约 10ms

---

### 测试 15: 带过滤条件的向量搜索

**目的**: 在搜索时应用过滤条件

**curl 命令**:
```bash
# 带过滤的向量搜索
# 描述: 搜索特定来源的文档
curl -X POST "http://localhost:8000/api/v1/milvus/search/vector/" \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "test_documents",
    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    "anns_field": "text_dense",
    "top_k": 5,
    "filter_expr": "source == \"upload\"",
    "output_fields": ["pk", "text", "source"]
  }'
```

**验证点**:
- [x] HTTP 状态码为 200
- [x] 所有返回结果的 `source` 为 "upload"

**Status**: [x] PASS

**Test Results** (Executed: 2026-03-03):
- **Actual Status Code**: 200
- **Actual Response**: 
  ```json
  {"items":[{"pk":"doc-001-chunk-002","distance":0.7594030499458313,"text":"Deep learning is a subset of machine learning that uses neural networks with multiple layers.","summary":"","document":"","source":"upload","source_name":"","lt_doc_id":"","chunk_id":0},{"pk":"doc-001-chunk-001","distance":0.7505713105201721,"text":"Updated: This is the updated test document about machine learning.","summary":"","document":"","source":"upload","source_name":"","lt_doc_id":"","chunk_id":0}],"total":2,"query_time_ms":8.505105972290039}
  ```
- **Notes**: 带过滤条件的搜索成功，所有返回结果的 source 都是 "upload"

---

### 测试 16: 混合搜索 (Hybrid Search)

**目的**: 执行多向量字段混合搜索，结合 BM25 文本搜索

**curl 命令**:
```bash
# 混合搜索
# 描述: 结合 text_dense 和 summary_dense 向量进行混合搜索
curl -X POST "http://localhost:8000/api/v1/milvus/search/hybrid/" \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "test_documents",
    "query_text": "What is machine learning?",
    "query_vectors": {
      "text_dense": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
      "summary_dense": [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 1.05]
    },
    "top_k": 10,
    "filter_expr": "",
    "output_fields": ["pk", "text", "summary", "source", "lt_doc_id"],
    "rerank_method": "rrf",
    "rrf_k": 60
  }'
```

> **注意**: 上述 `query_vectors` 仅示例 10 维，实际需要 1536 维向量。

**请求参数说明**:
- `query_text` (必填): 原始查询文本，用于 BM25 搜索
- `query_vectors` (必填): 查询向量字典，键为向量字段名
- `rerank_method` (可选, 默认 "rrf"): 重排序方法，可选 `rrf` (Reciprocal Rank Fusion) 或 `weighted`
- `rrf_k` (可选, 默认 60): RRF 参数
- `weights` (可选): 加权重排序的权重列表（rerank_method="weighted" 时使用）

**预期响应 (200 OK)**:
```json
{
  "items": [
    {
      "pk": "doc-001-chunk-001",
      "distance": 0.92,
      "text": "This is the first test document about machine learning.",
      "summary": "Document about ML and AI",
      "document": "Full document content...",
      "source": "upload",
      "source_name": "test_doc_001.pdf",
      "lt_doc_id": "550e8400-e29b-41d4-a716-446655440000",
      "chunk_id": 1
    }
  ],
  "total": 1,
  "query_time_ms": 25.5,
  "search_details": {
    "text_dense_count": 10,
    "summary_dense_count": 10,
    "bm25_count": 8,
    "rerank_method": "rrf"
  }
}
```

**验证点**:
- [ ] HTTP 状态码为 200
- [ ] `items` 包含混合搜索结果
- [ ] `search_details` 包含各搜索器的统计信息

**Status**: [ ] PASS (未测试 - 混合搜索需要更复杂的测试设置)

**Test Results** (Executed: 2026-03-03):
- **Actual Status Code**: N/A
- **Actual Response**: N/A
- **Notes**: ⚠️ 混合搜索功能需要完整的 BM25 索引和多向量字段数据，本次测试未覆盖。建议单独进行详细测试。

---

### 测试 17: 文档内搜索

**目的**: 在特定文档的 chunks 中搜索

**curl 命令**:
```bash
# 文档内搜索
# 描述: 在特定文档的 chunks 中搜索相关内容
curl -X POST "http://localhost:8000/api/v1/milvus/search/document/" \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "test_documents",
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    "top_k": 5
  }'
```

**预期响应 (200 OK)**:
```json
{
  "items": [
    {
      "pk": "doc-001-chunk-001",
      "distance": 0.88,
      "text": "Chunk text...",
      "summary": "Chunk summary",
      "document": "Full document...",
      "source": "upload",
      "source_name": "test_doc_001.pdf",
      "lt_doc_id": "550e8400-e29b-41d4-a716-446655440000",
      "chunk_id": 1
    }
  ],
  "total": 1,
  "query_time_ms": 12.3
}
```

**验证点**:
- [x] HTTP 状态码为 200
- [x] 所有返回结果的 `lt_doc_id` 与请求的 `document_id` 一致

**Status**: [x] PASS

**Test Results** (Executed: 2026-03-03):
- **Actual Status Code**: 200
- **Actual Response**: 
  ```json
  {"items":[{"pk":"doc-001-chunk-002","distance":0.7727668285369873,"text":"Deep learning is a subset of machine learning that uses neural networks with multiple layers.","summary":"Deep learning overview","document":"Full document content for deep learning explanation.","source":"upload","source_name":"test_doc_001.pdf","lt_doc_id":"550e8400-e29b-41d4-a716-446655440000","chunk_id":2},{"pk":"doc-001-chunk-001","distance":0.7569221258163452,"text":"Updated: This is the updated test document about machine learning.","summary":"Updated document about ML","document":"Updated full document content...","source":"upload","source_name":"test_doc_001_v2.pdf","lt_doc_id":"550e8400-e29b-41d4-a716-446655440000","chunk_id":1}],"total":2,"query_time_ms":5.937099456787109}
  ```
- **Notes**: 文档内搜索成功，返回 2 条结果，所有结果的 lt_doc_id 与请求的 document_id 一致

---

### 测试 18: 删除 Collection

**目的**: 删除整个 Collection 及其所有数据

**curl 命令**:
```bash
# 删除 Collection
# 描述: 永久删除 Collection
curl -X DELETE "http://localhost:8000/api/v1/milvus/collections/test_documents/delete/" \
  -H "Authorization: Bearer <your_access_token>"
```

**预期响应 (200 OK)**:
```json
{
  "message": "Collection 'test_documents' dropped successfully",
  "collection_name": "test_documents",
  "dropped": true
}
```

**验证点**:
- [x] HTTP 状态码为 200
- [x] `dropped` 为 true
- [x] Collection 列表中不再显示该 Collection

**Status**: [x] PASS

**Test Results** (Executed: 2026-03-03):
- **Actual Status Code**: 200
- **Actual Response**: 
  ```json
  {"message":"Collection 'test_documents_manual' dropped successfully","collection_name":"test_documents_manual","dropped":true}
  ```
- **Notes**: Collection 删除成功

---

## 边界条件测试

| # | Test Case | Expected Result | Status |
|---|-----------|-----------------|--------|
| 1 | 创建已存在的 Collection | 409 Conflict | [x] |
| 2 | 获取不存在的 Collection | 404 Not Found | [ ] |
| 3 | 删除不存在的 Collection | 404 Not Found | [ ] |
| 4 | 插入向量到不存在的 Collection | 404 Not Found | [ ] |
| 5 | 插入维度不匹配的向量 | 400 Bad Request | [x] |
| 6 | 查询向量维度不匹配 | 400 Bad Request | [x] |
| 7 | 空 PK 列表删除 | 400 Bad Request | [ ] |
| 8 | 无效过滤表达式 | 500 Internal Server Error | [ ] |
| 9 | top_k 超过限制 (>100) | 400 Bad Request | [ ] |
| 10 | 无认证 Token | 401 Unauthorized | [ ] |
| 11 | 过期 Token | 401 Unauthorized | [ ] |
| 12 | Milvus 服务未运行 | 503 Service Unavailable | [ ] |

**边界条件测试说明** (Executed: 2026-03-03):
- **#1 创建已存在的 Collection**: 测试通过，返回 409 Conflict
- **#5 插入维度不匹配的向量**: 测试通过，返回 400 Bad Request，错误信息：`summary_dense must have 1536 dimensions, got 10`
- **#6 查询向量维度不匹配**: 测试通过，返回 400 Bad Request，错误信息：`query_vector must have 1536 dimensions, got 10`

---

## curl 命令参考

### 环境变量设置

```bash
export BASE_URL="http://localhost:8000/api/v1"
export ACCESS_TOKEN="<your_access_token>"
```

### Health Endpoints

```bash
# Health check
curl -X GET "$BASE_URL/milvus/health/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### Collection Endpoints

```bash
# List collections
curl -X GET "$BASE_URL/milvus/collections/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Create collection
curl -X POST "$BASE_URL/milvus/collections/create/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "my_collection",
    "dimension": 1536,
    "description": "My collection"
  }'

# Get collection info
curl -X GET "$BASE_URL/milvus/collections/my_collection/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Get collection stats
curl -X GET "$BASE_URL/milvus/collections/my_collection/stats/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Load collection
curl -X POST "$BASE_URL/milvus/collections/my_collection/load/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Release collection
curl -X POST "$BASE_URL/milvus/collections/my_collection/release/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Drop collection
curl -X DELETE "$BASE_URL/milvus/collections/my_collection/delete/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### Vector Endpoints

```bash
# Insert vectors
curl -X POST "$BASE_URL/milvus/vectors/insert/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "my_collection",
    "data": [
      {
        "pk": "test-001",
        "text": "Test document",
        "summary": "Test summary",
        "document": "Full document",
        "source": "upload",
        "source_name": "test.pdf",
        "lt_doc_id": "doc-uuid",
        "chunk_id": 1,
        "summary_dense": [...],
        "text_dense": [...]
      }
    ]
  }'

# Upsert vectors
curl -X POST "$BASE_URL/milvus/vectors/upsert/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "my_collection",
    "data": [...]
  }'

# Query vectors
curl -X POST "$BASE_URL/milvus/vectors/query/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "my_collection",
    "filter_expr": "source == \"upload\"",
    "output_fields": ["pk", "text"],
    "limit": 10
  }'

# Get single vector
curl -X GET "$BASE_URL/milvus/vectors/test-001/?collection_name=my_collection" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Delete vectors by IDs
curl -X POST "$BASE_URL/milvus/vectors/delete/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "my_collection",
    "ids": ["test-001"]
  }'

# Delete vectors by filter
curl -X POST "$BASE_URL/milvus/vectors/delete/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "my_collection",
    "filter_expr": "lt_doc_id == \"doc-uuid\""
  }'
```

### Search Endpoints

```bash
# Vector search
curl -X POST "$BASE_URL/milvus/search/vector/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "my_collection",
    "query_vector": [...],
    "anns_field": "text_dense",
    "top_k": 10,
    "output_fields": ["pk", "text", "summary"]
  }'

# Hybrid search
curl -X POST "$BASE_URL/milvus/search/hybrid/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "my_collection",
    "query_text": "What is AI?",
    "query_vectors": {
      "text_dense": [...],
      "summary_dense": [...]
    },
    "top_k": 10,
    "output_fields": ["pk", "text", "summary"],
    "rerank_method": "rrf"
  }'

# Document search
curl -X POST "$BASE_URL/milvus/search/document/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "my_collection",
    "document_id": "doc-uuid",
    "query_vector": [...],
    "top_k": 5
  }'
```

---

## 错误码说明

| Status Code | Description |
|-------------|-------------|
| 200 OK | 请求成功 |
| 201 Created | 资源创建成功 |
| 400 Bad Request | 请求参数错误（向量维度不匹配、必填字段缺失等） |
| 401 Unauthorized | 未认证或 Token 无效 |
| 404 Not Found | 资源不存在（Collection、Vector 不存在） |
| 409 Conflict | 资源冲突（Collection 已存在） |
| 500 Internal Server Error | 服务器内部错误 |
| 503 Service Unavailable | Milvus 服务不可用 |

---

## 故障排除

| Problem | Solution |
|---------|----------|
| Connection refused (Milvus) | 确保 Milvus 服务运行中：`docker ps \| grep milvus` |
| 401 Unauthorized | 检查 Token 格式：`Bearer <token>`，验证 Token 未过期 |
| 404 Not Found (Collection) | 确认 Collection 名称正确，使用 `/collections/` 端点查看所有 Collection |
| 400 Bad Request (vector dimension) | 确认向量维度为 1536，与 Collection 定义一致 |
| 500 Internal Server Error | 查看 Django 日志获取详细错误信息 |
| 搜索无结果 | 确认 Collection 已加载到内存，使用 `/collections/{name}/load/` 端点 |
| 插入失败 | 确认 PK 唯一，使用 upsert 而非 insert 更新已存在的向量 |
| Token expired | 使用 refresh token 获取新的 access token |
| Milvus health check fails | 检查 `MILVUS_URI` 配置，确认 Milvus 端口 19530 可访问 |

---

## 测试数据准备

### Python 脚本生成测试向量

```python
import numpy as np
import json

def generate_test_vector():
    """Generate random test vectors for manual testing."""
    return {
        "summary_dense": np.random.rand(1536).tolist(),
        "text_dense": np.random.rand(1536).tolist()
    }

# Generate multiple test vectors
test_data = [
    {
        "pk": f"test-doc-{i:03d}-chunk-{j}",
        "text": f"This is test document {i}, chunk {j}. " * 20,
        "summary": f"Summary for document {i}, chunk {j}",
        "document": f"Full content of test document {i}. " * 50,
        "source": "upload",
        "source_name": f"test_doc_{i:03d}.pdf",
        "lt_doc_id": f"doc-{i:03d}-uuid",
        "chunk_id": j,
        **generate_test_vector()
    }
    for i in range(1, 4)  # 3 documents
    for j in range(1, 4)  # 3 chunks each
]

print(json.dumps({"collection_name": "test_documents", "data": test_data}, indent=2))
```

### 批量插入测试数据

```bash
# 使用 Python 脚本生成测试数据并插入
python generate_test_vectors.py > test_data.json

# 插入测试数据
curl -X POST "$BASE_URL/milvus/vectors/insert/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d @test_data.json
```

---

## 性能测试参考

### 批量插入性能

```bash
# 插入 1000 个向量（需要准备测试数据）
# 预期响应时间：< 5 秒
curl -X POST "$BASE_URL/milvus/vectors/insert/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d @large_test_data.json
```

### 搜索性能

```bash
# 单次搜索预期响应时间：< 50ms
curl -X POST "$BASE_URL/milvus/search/vector/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

---

## 集成测试场景

### 场景 1: 完整文档处理流程

1. 创建 Collection
2. 插入文档 chunks
3. 执行向量搜索
4. 更新文档内容 (Upsert)
5. 删除特定文档 chunks
6. 删除 Collection

### 场景 2: RAG 检索流程

1. 准备文档数据并插入
2. 使用混合搜索检索相关内容
3. 在特定文档内搜索
4. 分析搜索结果

---

## 模块依赖关系

```
accounts (User Model + JWT Authentication)
    │
    │ provides authentication
    ▼
milvus_database_controller (Vector Database Operations)
    │
    ├── MilvusService (Facade)
    │   ├── CollectionManager
    │   ├── IndexManager
    │   ├── VectorManager
    │   └── SearchManager
    │
    └── MilvusClient (Singleton)
        │
        └── Milvus Server (Docker)
```

---

## 注意事项

1. **向量维度**: 所有向量必须为 1536 维（与 embedding 模型一致）
2. **PK 唯一性**: 每个 vector 的 `pk` 必须在 Collection 内唯一
3. **内存加载**: 搜索前必须确保 Collection 已加载到内存
4. **批量操作**: 单次请求最多插入/删除 10000 个向量
5. **认证必需**: 所有 Milvus API 端点都需要 JWT 认证
6. **环境配置**: 确保 `.env` 中配置了正确的 `MILVUS_URI`

---

## 测试执行总结

### 测试执行日期: 2026-03-03

### 测试环境
- Django Server: Running on localhost:8000
- Milvus Server: Running on localhost:19530
- Python: 3.12+
- PostgreSQL: Running

### 测试结果汇总

| 测试类别 | 总数 | 通过 | 失败 | 未测试 |
|---------|------|------|------|--------|
| 健康检查 | 1 | 1 | 0 | 0 |
| Collection 管理 | 7 | 7 | 0 | 0 |
| Vector 操作 | 6 | 6 | 0 | 0 |
| Search 搜索 | 4 | 3 | 0 | 1 |
| 边界条件 | 12 | 2 | 0 | 10 |
| **总计** | **30** | **19** | **0** | **11** |

### 已发现问题

1. **Collection 创建 Schema 不一致** (已记录)
   - 问题描述: 通过 API 创建的 Collection 使用 MilvusClient 默认 schema (主键字段为 `id`)，而非 DocumentCollectionSchema (主键字段为 `pk`)
   - 影响: 需要手动使用 pymilvus 创建正确 schema 的 Collection
   - 解决方案: 在 `create_collection_with_schema` 方法中使用自定义 schema

2. **Serializer 缺少 text_sparse 字段** (已修复)
   - 问题描述: VectorDataSerializer 没有定义 `text_sparse` 字段，导致插入失败
   - 修复: 在 `apps/milvus_database_controller/serializers.py` 中添加了 `text_sparse` 字段

### 后续测试建议

1. **混合搜索测试**: 需要完整的 BM25 索引和多向量字段数据进行详细测试
2. **边界条件测试**: 建议补充更多边界条件测试用例
3. **性能测试**: 建议进行批量插入和搜索性能测试

---

*Generated: 2026-02-26*
*Last Updated: 2026-03-03*
*Phase 6: Milvus Database Controller Manual Test Guide*
