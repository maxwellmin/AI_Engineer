# Phase 8: Embedding Engine 模块手动测试指南

本文档提供 embedding_engine 模块 API 的完整手动测试步骤，涵盖文本向量化功能的所有端点。

## 测试凭据

> 以下凭据用于测试过程中的认证，每次测试会话后更新

| 字段 | 值 |
|------|-----|
| Username | testuser |
| Password | testpass123 |
| Access Token | (登录后获取) |
| User ID | 1 |

---

## 目录

1. [前置条件](#前置条件)
2. [测试工具](#测试工具)
3. [API 端点总览](#api-端点总览)
4. [认证流程测试](#认证流程测试)
5. [健康检查测试](#健康检查测试)
6. [单文本向量化测试](#单文本向量化测试)
7. [批量文本向量化测试](#批量文本向量化测试)
8. [查询向量化测试](#查询向量化测试)
9. [支持的模型查询测试](#支持的模型查询测试)
10. [错误场景测试](#错误场景测试)
11. [错误码说明](#错误码说明)
12. [故障排除](#故障排除)

---

## 前置条件

### 1. 启动 Django 开发服务器

```bash
cd /Users/maxrocketman/myproject/melon
poetry run python manage.py runserver
```

### 2. 确保数据库迁移已应用

```bash
poetry run python manage.py migrate
```

### 3. 环境变量配置

在 `.env` 或环境变量中配置 Qwen API：

```bash
# Qwen API Configuration
QWEN_API_KEY=sk-your-api-key-here
QWEN_EMBEDDING_MODEL=text-embedding-v1
EMBEDDING_PROVIDER=qwen  # or 'mock' for testing
```

### 4. (可选) 使用 Mock Provider 进行测试

如果不想消耗 API 配额，可以配置使用 Mock Provider：

```bash
EMBEDDING_PROVIDER=mock
```

Mock Provider 会返回随机生成的向量，适合功能测试。

### 5. 确保 PostgreSQL 正在运行

---

## 测试工具

### Swagger UI (推荐)

访问 http://localhost:8000/swagger/，提供交互式 "Try it out" 功能。

### ReDoc

访问 http://localhost:8000/redoc/，用于查看 API 文档。

### curl / Postman

使用命令行工具或 Postman 进行测试。

---

## API 端点总览

### Phase 8: embedding_engine 模块

所有端点需要 **IsAuthenticated** 认证。

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/embedding/health/` | 健康检查 | Yes (JWT) |
| POST | `/api/v1/embedding/embed/` | 单文本向量化 | Yes (JWT) |
| POST | `/api/v1/embedding/embed-batch/` | 批量文本向量化 | Yes (JWT) |
| POST | `/api/v1/embedding/embed-query/` | 查询向量化 | Yes (JWT) |
| GET | `/api/v1/embedding/models/` | 支持的模型列表 | Yes (JWT) |

---

## 认证流程测试

### 测试 1: 用户登录获取 Token

**目的**: 获取访问令牌用于后续 API 调用

**curl 命令**:
```bash
# 登录获取 token
# 描述: 使用用户名密码登录系统，获取访问令牌
curl -X POST "http://localhost:8000/api/v1/accounts/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123"
  }'
```

**预期请求格式**:
```json
{
  "username": "string",
  "password": "string"
}
```

**预期响应 (200 OK)**:
```json
{
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "testuser@example.com"
  },
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "knox_token": "abc123def456..."
}
```

**验证要点**:
- [ ] 返回 200 状态码
- [ ] 响应包含 `access` 字段
- [ ] 响应包含 `refresh` 字段（可选）
- [ ] 记录 `access` token 用于后续测试

**Status**: ⏳ PENDING

---

### 测试 2: 配置 Swagger 认证

1. 访问 http://localhost:8000/swagger/
2. 点击页面右上角 **Authorize** 按钮
3. 输入：`Bearer <your_access_token>` (替换为实际的 token)
4. 点击 "Authorize" 然后点击 "Close"

**Status**: ⏭️ SKIP - 配置步骤

---

## 健康检查测试

### 测试 3: 健康检查接口

**目的**: 验证 Embedding 服务是否正常运行

**curl 命令**:
```bash
# 健康检查
# 描述: 检查 Embedding 服务健康状态，返回 provider、model、dimension 等信息
curl -X GET "http://localhost:8000/api/v1/embedding/health/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json"
```

**预期响应 (200 OK - Healthy)**:
```json
{
  "healthy": true,
  "provider": "qwen",
  "model": "text-embedding-v1",
  "dimension": 1536,
  "latency_ms": 123.45,
  "error": null
}
```

**预期响应 (503 Service Unavailable - Unhealthy)**:
```json
{
  "healthy": false,
  "provider": "qwen",
  "model": "text-embedding-v1",
  "dimension": 1536,
  "latency_ms": null,
  "error": "Failed to connect to embedding API: Connection refused"
}
```

**验证要点**:
- [ ] 返回 200 状态码（服务正常）
- [ ] `healthy` 字段为 `true`
- [ ] `provider` 字段正确显示（qwen/mock）
- [ ] `model` 字段显示当前使用的模型
- [ ] `dimension` 字段显示向量维度（1536 for v1, 1024 for v3）
- [ ] `latency_ms` 字段显示响应延迟
- [ ] `error` 字段为 `null`（正常情况下）

**Status**: ⏳ PENDING

---

## 单文本向量化测试

### 测试 4: 单文本向量化（默认 task_type）

**目的**: 验证单文本向量化功能正常工作

**curl 命令**:
```bash
# 单文本向量化
# 描述: 将单个文本转换为向量，默认使用 retrieval.document task_type
curl -X POST "http://localhost:8000/api/v1/embedding/embed/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world, this is a test document for embedding."
  }'
```

**预期请求格式**:
```json
{
  "text": "string (required, max 100000 chars)",
  "task_type": "retrieval.document | retrieval.query (optional, default: retrieval.document)"
}
```

**预期响应 (200 OK)**:
```json
{
  "embedding": [0.123, -0.456, 0.789, 0.012, ...],
  "dimension": 1536,
  "model": "text-embedding-v1",
  "tokens_used": 10
}
```

**验证要点**:
- [ ] 返回 200 状态码
- [ ] `embedding` 数组长度等于 `dimension`（1536）
- [ ] `embedding` 数组元素为浮点数
- [ ] `dimension` 字段显示正确的向量维度
- [ ] `model` 字段显示使用的模型名称
- [ ] `tokens_used` 字段显示消耗的 token 数量

**Status**: ⏳ PENDING

---

### 测试 5: 单文本向量化（指定 task_type=document）

**目的**: 验证 task_type 参数正确传递

**curl 命令**:
```bash
# 单文本向量化 - document task type
# 描述: 使用 retrieval.document task type，适用于存储到向量数据库的文档
curl -X POST "http://localhost:8000/api/v1/embedding/embed/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
    "task_type": "retrieval.document"
  }'
```

**预期响应 (200 OK)**:
```json
{
  "embedding": [0.234, -0.567, 0.89, ...],
  "dimension": 1536,
  "model": "text-embedding-v1",
  "tokens_used": 18
}
```

**验证要点**:
- [ ] 返回 200 状态码
- [ ] `embedding` 数组长度正确
- [ ] 响应时间合理（< 5s）

**Status**: ⏳ PENDING

---

### 测试 6: 单文本向量化（指定 task_type=query）

**目的**: 验证 query task type 正常工作

**curl 命令**:
```bash
# 单文本向量化 - query task type
# 描述: 使用 retrieval.query task type，适用于搜索查询
curl -X POST "http://localhost:8000/api/v1/embedding/embed/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What is machine learning?",
    "task_type": "retrieval.query"
  }'
```

**预期响应 (200 OK)**:
```json
{
  "embedding": [0.345, -0.678, 0.901, ...],
  "dimension": 1536,
  "model": "text-embedding-v1",
  "tokens_used": 5
}
```

**验证要点**:
- [ ] 返回 200 状态码
- [ ] `embedding` 数组长度正确
- [ ] 与相同文本的 document task_type 生成的向量不同（理论上）

**Status**: ⏳ PENDING

---

### 测试 7: 长文本向量化

**目的**: 验证较长文本的处理能力

**curl 命令**:
```bash
# 长文本向量化
# 描述: 测试较长文本的向量化处理
curl -X POST "http://localhost:8000/api/v1/embedding/embed/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Natural language processing (NLP) is a subfield of linguistics, computer science, and artificial intelligence concerned with the interactions between computers and human language, in particular how to program computers to process and analyze large amounts of natural language data. The result is a computer capable of understanding the contents of documents, including the contextual nuances of the language within them. The technology can then accurately extract information and insights contained in the documents as well as categorize and organize the documents themselves."
  }'
```

**预期响应 (200 OK)**:
```json
{
  "embedding": [0.456, -0.789, 0.012, ...],
  "dimension": 1536,
  "model": "text-embedding-v1",
  "tokens_used": 85
}
```

**验证要点**:
- [ ] 返回 200 状态码
- [ ] `tokens_used` 反映实际 token 数量
- [ ] 响应时间合理

**Status**: ⏳ PENDING

---

## 批量文本向量化测试

### 测试 8: 批量文本向量化（小批量）

**目的**: 验证批量文本向量化功能

**curl 命令**:
```bash
# 批量文本向量化
# 描述: 批量处理多个文本，返回所有向量
curl -X POST "http://localhost:8000/api/v1/embedding/embed-batch/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "Hello world",
      "This is a test",
      "Machine learning is fascinating"
    ],
    "task_type": "retrieval.document",
    "batch_size": 20
  }'
```

**预期请求格式**:
```json
{
  "texts": ["string1", "string2", ...],  // required, 1-100 items
  "task_type": "retrieval.document | retrieval.query",  // optional
  "batch_size": 20  // optional, 1-50, default 20
}
```

**预期响应 (200 OK)**:
```json
{
  "embeddings": [
    [0.1, -0.2, 0.3, ...],
    [0.4, -0.5, 0.6, ...],
    [0.7, -0.8, 0.9, ...]
  ],
  "dimension": 1536,
  "model": "text-embedding-v1",
  "total_tokens": 12,
  "success_count": 3,
  "failed_count": 0
}
```

**验证要点**:
- [ ] 返回 200 状态码
- [ ] `embeddings` 数组长度等于输入 `texts` 数组长度
- [ ] 每个 `embedding` 长度等于 `dimension`
- [ ] `total_tokens` 显示总 token 消耗
- [ ] `success_count` 等于输入文本数量
- [ ] `failed_count` 为 0

**Status**: ⏳ PENDING

---

### 测试 9: 批量文本向量化（自定义 batch_size）

**目的**: 验证 batch_size 参数正确传递

**curl 命令**:
```bash
# 批量文本向量化 - 自定义 batch_size
# 描述: 指定每批处理的文本数量
curl -X POST "http://localhost:8000/api/v1/embedding/embed-batch/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "Document 1 content",
      "Document 2 content",
      "Document 3 content",
      "Document 4 content",
      "Document 5 content"
    ],
    "task_type": "retrieval.document",
    "batch_size": 2
  }'
```

**预期响应 (200 OK)**:
```json
{
  "embeddings": [
    [0.1, ...],
    [0.2, ...],
    [0.3, ...],
    [0.4, ...],
    [0.5, ...]
  ],
  "dimension": 1536,
  "model": "text-embedding-v1",
  "total_tokens": 15,
  "success_count": 5,
  "failed_count": 0
}
```

**验证要点**:
- [ ] 返回 200 状态码
- [ ] 所有文本成功处理
- [ ] batch_size=2 意味着会分 3 批处理（2+2+1）

**Status**: ⏳ PENDING

---

### 测试 10: 批量文本向量化（大批量）

**目的**: 验证大批量处理能力

**curl 命令**:
```bash
# 批量文本向量化 - 大批量
# 描述: 测试大量文本的处理能力（生成 50 个测试文本）
curl -X POST "http://localhost:8000/api/v1/embedding/embed-batch/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "Text sample 1 for batch processing test",
      "Text sample 2 for batch processing test",
      "Text sample 3 for batch processing test",
      "Text sample 4 for batch processing test",
      "Text sample 5 for batch processing test",
      "Text sample 6 for batch processing test",
      "Text sample 7 for batch processing test",
      "Text sample 8 for batch processing test",
      "Text sample 9 for batch processing test",
      "Text sample 10 for batch processing test"
    ],
    "task_type": "retrieval.document",
    "batch_size": 5
  }'
```

**预期响应 (200 OK)**:
```json
{
  "embeddings": [
    [0.1, ...],
    [0.2, ...],
    ...
  ],
  "dimension": 1536,
  "model": "text-embedding-v1",
  "total_tokens": 70,
  "success_count": 10,
  "failed_count": 0
}
```

**验证要点**:
- [ ] 返回 200 状态码
- [ ] 所有文本成功处理
- [ ] 响应时间合理（批量处理可能需要较长时间）

**Status**: ⏳ PENDING

---

## 查询向量化测试

### 测试 11: 查询向量化

**目的**: 验证专用的查询向量化接口

**curl 命令**:
```bash
# 查询向量化
# 描述: 专为搜索查询优化的向量化接口，自动使用 retrieval.query task_type
curl -X POST "http://localhost:8000/api/v1/embedding/embed-query/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning and how does it work?"
  }'
```

**预期请求格式**:
```json
{
  "query": "string (required, max 10000 chars)"
}
```

**预期响应 (200 OK)**:
```json
{
  "embedding": [0.567, -0.89, 0.123, ...],
  "dimension": 1536,
  "model": "text-embedding-v1",
  "tokens_used": 10
}
```

**验证要点**:
- [ ] 返回 200 状态码
- [ ] `embedding` 数组长度正确
- [ ] 此接口自动使用 `retrieval.query` task_type

**Status**: ⏳ PENDING

---

### 测试 12: 查询向量化（短查询）

**目的**: 验证短查询的处理

**curl 命令**:
```bash
# 短查询向量化
# 描述: 测试短查询的向量化
curl -X POST "http://localhost:8000/api/v1/embedding/embed-query/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI"
  }'
```

**预期响应 (200 OK)**:
```json
{
  "embedding": [0.678, -0.901, 0.234, ...],
  "dimension": 1536,
  "model": "text-embedding-v1",
  "tokens_used": 1
}
```

**验证要点**:
- [ ] 返回 200 状态码
- [ ] 即使短查询也能正确处理

**Status**: ⏳ PENDING

---

### 测试 13: 查询向量化（复杂查询）

**目的**: 验证复杂查询的处理

**curl 命令**:
```bash
# 复杂查询向量化
# 描述: 测试复杂查询的向量化
curl -X POST "http://localhost:8000/api/v1/embedding/embed-query/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How can I implement a machine learning model for natural language processing tasks such as sentiment analysis, named entity recognition, and text classification?"
  }'
```

**预期响应 (200 OK)**:
```json
{
  "embedding": [0.789, -0.012, 0.345, ...],
  "dimension": 1536,
  "model": "text-embedding-v1",
  "tokens_used": 25
}
```

**验证要点**:
- [ ] 返回 200 状态码
- [ ] 复杂查询正确处理

**Status**: ⏳ PENDING

---

## 支持的模型查询测试

### 测试 14: 获取支持的模型列表

**目的**: 查询系统支持的 embedding 模型

**curl 命令**:
```bash
# 获取支持的模型
# 描述: 返回系统支持的所有 embedding 模型列表
curl -X GET "http://localhost:8000/api/v1/embedding/models/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json"
```

**预期响应 (200 OK)**:
```json
{
  "models": ["text-embedding-v1", "text-embedding-v3"]
}
```

**验证要点**:
- [ ] 返回 200 状态码
- [ ] `models` 数组包含支持的模型名称
- [ ] 至少包含 `text-embedding-v1`

**Status**: ⏳ PENDING

---

## 错误场景测试

### 测试 15: 未认证访问

**目的**: 验证未认证请求被正确拒绝

**curl 命令**:
```bash
# 未认证访问
# 描述: 不携带 token 访问需要认证的端点
curl -X GET "http://localhost:8000/api/v1/embedding/health/" \
  -H "Content-Type: application/json"
```

**预期响应 (401 Unauthorized)**:
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**验证要点**:
- [ ] 返回 401 状态码
- [ ] 错误消息提示需要认证

**Status**: ⏳ PENDING

---

### 测试 16: 空 text 参数

**目的**: 验证空文本输入验证

**curl 命令**:
```bash
# 空文本输入
# 描述: 发送空字符串作为 text 参数
curl -X POST "http://localhost:8000/api/v1/embedding/embed/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": ""
  }'
```

**预期响应 (400 Bad Request)**:
```json
{
  "error": "ValidationError",
  "message": "Invalid input data",
  "detail": {
    "text": ["This field may not be blank."]
  }
}
```

**或 (EmptyInputError)**:
```json
{
  "error": "EmptyInputError",
  "message": "Input text cannot be empty"
}
```

**验证要点**:
- [ ] 返回 400 状态码
- [ ] 错误消息明确说明问题

**Status**: ⏳ PENDING

---

### 测试 17: 缺少 text 参数

**目的**: 验证缺少必需参数的处理

**curl 命令**:
```bash
# 缺少 text 参数
# 描述: 不发送必需的 text 参数
curl -X POST "http://localhost:8000/api/v1/embedding/embed/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**预期响应 (400 Bad Request)**:
```json
{
  "error": "ValidationError",
  "message": "Invalid input data",
  "detail": {
    "text": ["This field is required."]
  }
}
```

**验证要点**:
- [ ] 返回 400 状态码
- [ ] 错误消息指出缺少 text 字段

**Status**: ⏳ PENDING

---

### 测试 18: 无效的 task_type

**目的**: 验证 task_type 参数验证

**curl 命令**:
```bash
# 无效的 task_type
# 描述: 发送无效的 task_type 值
curl -X POST "http://localhost:8000/api/v1/embedding/embed/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world",
    "task_type": "invalid_type"
  }'
```

**预期响应 (400 Bad Request)**:
```json
{
  "error": "ValidationError",
  "message": "Invalid input data",
  "detail": {
    "task_type": ["\"invalid_type\" is not a valid choice."]
  }
}
```

**验证要点**:
- [ ] 返回 400 状态码
- [ ] 错误消息指出无效的 task_type

**Status**: ⏳ PENDING

---

### 测试 19: 批量请求空 texts 数组

**目的**: 验证批量请求空数组验证

**curl 命令**:
```bash
# 批量请求空 texts 数组
# 描述: 发送空的 texts 数组
curl -X POST "http://localhost:8000/api/v1/embedding/embed-batch/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": []
  }'
```

**预期响应 (400 Bad Request)**:
```json
{
  "error": "ValidationError",
  "message": "Invalid input data",
  "detail": {
    "texts": ["This list may not be empty."]
  }
}
```

**验证要点**:
- [ ] 返回 400 状态码
- [ ] 错误消息指出 texts 不能为空

**Status**: ⏳ PENDING

---

### 测试 20: 批量请求 texts 超过限制

**目的**: 验证批量请求数量限制

**curl 命令**:
```bash
# 批量请求 texts 超过限制
# 描述: 发送超过 100 个文本的批量请求
# 注意: 需要实际构造一个超过 100 个文本的请求
# 这里仅展示概念，实际测试需要生成 100+ 文本
curl -X POST "http://localhost:8000/api/v1/embedding/embed-batch/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["text1", "text2", ... (101+ items)]
  }'
```

**预期响应 (400 Bad Request)**:
```json
{
  "error": "ValidationError",
  "message": "Invalid input data",
  "detail": {
    "texts": ["Ensure this field has no more than 100 elements."]
  }
}
```

**验证要点**:
- [ ] 返回 400 状态码
- [ ] 错误消息指出超过最大数量限制

**Status**: ⏳ PENDING

---

### 测试 21: 批量请求 batch_size 超过限制

**目的**: 验证 batch_size 参数限制

**curl 命令**:
```bash
# batch_size 超过限制
# 描述: 发送超过 50 的 batch_size
curl -X POST "http://localhost:8000/api/v1/embedding/embed-batch/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["text1", "text2", "text3"],
    "batch_size": 100
  }'
```

**预期响应 (400 Bad Request)**:
```json
{
  "error": "ValidationError",
  "message": "Invalid input data",
  "detail": {
    "batch_size": ["Ensure this value is less than or equal to 50."]
  }
}
```

**验证要点**:
- [ ] 返回 400 状态码
- [ ] 错误消息指出 batch_size 超限

**Status**: ⏳ PENDING

---

### 测试 22: 文本过长（InputTooLong）

**目的**: 验证超长文本的处理

**curl 命令**:
```bash
# 文本过长
# 描述: 发送超过 token 限制的文本
# 注意: 需要构造一个超过 8000 tokens 的文本
curl -X POST "http://localhost:8000/api/v1/embedding/embed/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Very long text that exceeds the maximum token limit..."
  }'
```

**预期响应 (400 Bad Request)**:
```json
{
  "error": "InputTooLongError",
  "message": "Input text too long: 8500 tokens (max: 8000)",
  "detail": {
    "token_count": 8500,
    "max_tokens": 8000
  }
}
```

**验证要点**:
- [ ] 返回 400 状态码
- [ ] 错误消息显示实际 token 数和最大限制

**Status**: ⏳ PENDING

---

### 测试 23: 查询参数为空

**目的**: 验证查询向量化空输入处理

**curl 命令**:
```bash
# 查询参数为空
# 描述: 发送空字符串作为 query 参数
curl -X POST "http://localhost:8000/api/v1/embedding/embed-query/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": ""
  }'
```

**预期响应 (400 Bad Request)**:
```json
{
  "error": "ValidationError",
  "message": "Invalid input data",
  "detail": {
    "query": ["This field may not be blank."]
  }
}
```

**验证要点**:
- [ ] 返回 400 状态码
- [ ] 错误消息指出 query 不能为空

**Status**: ⏳ PENDING

---

### 测试 24: API 错误（模拟服务不可用）

**目的**: 验证 API 错误处理

> 此测试需要模拟后端 API 故障，可通过以下方式：
> 1. 临时禁用网络连接
> 2. 配置错误的 API Key
> 3. 配置不可达的 API endpoint

**curl 命令**:
```bash
# API 错误场景
# 描述: 当后端 API 不可用时的错误处理
curl -X POST "http://localhost:8000/api/v1/embedding/embed/" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world"
  }'
```

**预期响应 (502 Bad Gateway)**:
```json
{
  "error": "APIError",
  "message": "Failed to connect to embedding API: Connection refused"
}
```

**验证要点**:
- [ ] 返回 502 状态码
- [ ] 错误消息说明 API 连接问题

**Status**: ⏳ PENDING

---

### 测试 25: Rate Limit 场景（模拟）

**目的**: 验证 Rate Limit 错误处理

> 此测试需要触发 API Rate Limit，可能需要大量请求或配置较低的 limit

**预期响应 (429 Too Many Requests)**:
```json
{
  "error": "APIError",
  "message": "Rate limit exceeded. Retry after 60s"
}
```

**验证要点**:
- [ ] 返回 429 状态码或 502 状态码
- [ ] 错误消息说明 Rate Limit 问题

**Status**: ⏳ PENDING

---

## 错误码说明

| Status Code | Error Type | Description |
|-------------|------------|-------------|
| 200 OK | - | 请求成功 |
| 400 Bad Request | ValidationError | 请求参数验证失败 |
| 400 Bad Request | EmptyInputError | 输入文本为空 |
| 400 Bad Request | InputTooLongError | 输入文本超过 token 限制 |
| 401 Unauthorized | - | 未认证或 token 无效 |
| 403 Forbidden | - | 无权限访问 |
| 502 Bad Gateway | APIError | 后端 API 错误 |
| 503 Service Unavailable | - | 服务不可用（健康检查失败） |

---

## 故障排除

| Problem | Solution |
|---------|----------|
| Connection refused | 确保 Django 服务器正在运行 |
| 401 Unauthorized | 检查 token 格式: `Bearer <token>`，验证 token 未过期 |
| 502 Bad Gateway | 检查 QWEN_API_KEY 是否正确配置，检查网络连接 |
| 503 Service Unavailable | 检查 embedding provider 配置，确认 API 可达 |
| Token expired | 使用 refresh token 获取新的 access token |
| Empty input error | 确保请求 body 中的 text/query 字段非空 |
| Input too long | 减少输入文本长度，最大支持约 8000 tokens |
| Batch size error | 确保 batch_size 在 1-50 范围内 |
| Texts count error | 确保 texts 数组包含 1-100 个元素 |

---

## curl 命令参考

### 环境变量设置

```bash
export BASE_URL="http://localhost:8000/api/v1"
export ACCESS_TOKEN="<your_access_token>"
```

### Embedding Engine 模块

```bash
# Health Check
curl -X GET "$BASE_URL/embedding/health/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Single Text Embedding
curl -X POST "$BASE_URL/embedding/embed/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world"}'

# Single Text Embedding with task_type
curl -X POST "$BASE_URL/embedding/embed/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "task_type": "retrieval.query"}'

# Batch Text Embedding
curl -X POST "$BASE_URL/embedding/embed-batch/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Hello", "World"], "task_type": "retrieval.document", "batch_size": 20}'

# Query Embedding
curl -X POST "$BASE_URL/embedding/embed-query/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is machine learning?"}'

# Supported Models
curl -X GET "$BASE_URL/embedding/models/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

## 测试执行顺序建议

1. **认证流程**: 测试 1-2（获取 token）
2. **健康检查**: 测试 3（验证服务可用性）
3. **基础功能**: 测试 4-7（单文本向量化）
4. **批量功能**: 测试 8-10（批量向量化）
5. **查询功能**: 测试 11-13（查询向量化）
6. **辅助功能**: 测试 14（模型列表）
7. **错误场景**: 测试 15-25（各种错误处理）

---

## 边界条件测试清单

| # | Test Case | Expected Result | Status |
|---|-----------|-----------------|--------|
| 1 | Empty text input | 400 Bad Request | [ ] |
| 2 | Missing text parameter | 400 Bad Request | [ ] |
| 3 | Invalid task_type | 400 Bad Request | [ ] |
| 4 | Empty texts array (batch) | 400 Bad Request | [ ] |
| 5 | Texts count > 100 (batch) | 400 Bad Request | [ ] |
| 6 | Batch size > 50 | 400 Bad Request | [ ] |
| 7 | Text too long (> 8000 tokens) | 400 Bad Request | [ ] |
| 8 | Query too long (> 10000 chars) | 400 Bad Request | [ ] |
| 9 | No authentication token | 401 Unauthorized | [ ] |
| 10 | Invalid/expired token | 401 Unauthorized | [ ] |
| 11 | API connection failure | 502 Bad Gateway | [ ] |
| 12 | Rate limit exceeded | 502/429 Error | [ ] |

---

## Mock Provider 测试模式

如果使用 Mock Provider 进行测试，可以设置环境变量：

```bash
export EMBEDDING_PROVIDER=mock
```

Mock Provider 特性：
- 返回固定维度的随机向量
- 不消耗 API 配额
- 响应速度快
- 适合功能测试和 CI/CD 环境

---

## 性能基准参考

| Operation | Expected Latency | Notes |
|-----------|-----------------|-------|
| Health Check | < 100ms | 轻量级检查 |
| Single Text (short) | < 500ms | ~10 tokens |
| Single Text (long) | < 2s | ~100 tokens |
| Batch (10 texts) | < 3s | batch_size=20 |
| Batch (50 texts) | < 10s | batch_size=20 |

> 以上基准基于 Qwen API 的典型响应时间，实际可能因网络状况和 API 负载而变化。

---

## 相关模块依赖

```
accounts (User Authentication)
    │
    │ provides JWT token
    ▼
embedding_engine (Text Vectorization)
    │
    │ provides embeddings for
    ▼
milvus_database_controller (Vector Storage)
    │
    └── RAG Processing Pipeline
```

---

## 附录：支持的模型和维度

| Model | Dimension | Provider | Description |
|-------|-----------|----------|-------------|
| text-embedding-v1 | 1536 | Qwen | 默认模型，适合大多数场景 |
| text-embedding-v3 | 1024 | Qwen | 新版本，更高效的向量表示 |

---

*文档版本: 1.0*
*最后更新: 2026-02-26*
*模块: embedding_engine (Phase 8)*
