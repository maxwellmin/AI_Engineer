# Documents Parser 模块手动测试指南

本文档提供 documents_parser 模块 API 的手动验证步骤。

## 前置条件

1. **启动 Django 开发服务器**
   ```bash
   cd /Users/maxrocketman/myproject/melon
   poetry run python manage.py runserver
   ```

2. **确保数据库迁移已应用**
   ```bash
   poetry run python manage.py migrate
   ```

3. **确保 PostgreSQL 正在运行**

4. **获取认证 Token**
   - 先通过 accounts 模块注册/登录获取 JWT access token
   - 参考 `apps/accounts/docs/manual_test.md` 获取 token

---

## 测试工具

### Swagger UI（推荐）

访问 http://localhost:8000/swagger/，提供交互式 "Try it out" 功能。

### ReDoc

访问 http://localhost:8000/redoc/，用于查看 API 文档。

### curl / Postman

使用命令行工具或 Postman 进行测试。

---

## API 端点列表

| 方法 | 端点 | 描述 | 需要认证 |
|------|------|------|----------|
| GET | `/api/v1/documents/` | 获取文档列表 | 是 (JWT) |
| POST | `/api/v1/documents/` | 上传文档 | 是 (JWT) |
| GET | `/api/v1/documents/{id}/` | 获取文档详情 | 是 (JWT) |
| DELETE | `/api/v1/documents/{id}/delete/` | 删除文档 | 是 (JWT) |

---

## 支持的文件类型

| 类型 | 扩展名 | 说明 |
|------|--------|------|
| PDF | `.pdf` | PDF 文档 |
| Word | `.docx`, `.doc` | Microsoft Word 文档 |
| 文本 | `.txt` | 纯文本文件 |
| Markdown | `.md` | Markdown 文档 |

**文件大小限制**: 默认 100MB

---

## Swagger UI 测试流程

### 准备工作：获取认证 Token

1. 通过 accounts 模块登录获取 access token
2. 访问 http://localhost:8000/swagger/
3. 点击页面右上角 **Authorize** 按钮
4. 输入：`Bearer <your_access_token>`（替换为实际的 token）
5. 点击 "Authorize" 然后点击 "Close"

### 测试 1: 上传文档（PDF）

1. 找到 **POST /api/v1/documents/**
2. 点击 "Try it out"
3. 填写表单数据：
   - **file**: 选择一个 PDF 文件
   - **title**: （可选）输入文档标题
   - **description**: （可选）输入文档描述
4. 点击 "Execute"
5. **预期结果**: 201 Created
   ```json
   {
     "id": "uuid-string",
     "name": "document_20260224_123456.pdf",
     "original_name": "My Document.pdf",
     "file_type": "pdf",
     "file_size": 102400,
     "status": "uploaded",
     "title": "My Title",
     "description": "My Description",
     "created_at": "2026-02-24T10:00:00Z"
   }
   ```

### 测试 2: 上传文档（TXT）

1. 创建一个测试文本文件 `test.txt`：
   ```
   This is a test document.
   It contains multiple lines of text.
   The content will be parsed and chunked.
   ```
2. 找到 **POST /api/v1/documents/**
3. 上传该 TXT 文件
4. **预期结果**: 201 Created，file_type 为 "txt"

### 测试 3: 上传文档（DOCX）

1. 准备一个 .docx 文件
2. 找到 **POST /api/v1/documents/**
3. 上传该 DOCX 文件
4. **预期结果**: 201 Created，file_type 为 "docx"

### 测试 4: 上传重复文档（去重测试）

1. 使用之前上传过的同一文件再次上传
2. **预期结果**: 200 OK（非 201 Created）
   ```json
   {
     "id": "existing-document-uuid",
     "name": "document_20260224_123456.pdf",
     "original_name": "My Document.pdf",
     "file_type": "pdf",
     "file_size": 102400,
     "status": "uploaded",
     "message": "Document already exists",
     "created_at": "2026-02-24T10:00:00Z"
   }
   ```
   注意：返回的是已存在文档的 ID，status 为 200

### 测试 5: 上传不支持的文件类型

1. 尝试上传一个 `.xlsx` 或 `.jpg` 文件
2. **预期结果**: 400 Bad Request
   ```json
   {
     "file": [
       "Unsupported file type '.xlsx'. Supported types: pdf, docx, doc, txt, md"
     ]
   }
   ```

### 测试 6: 上传超大文件

1. 尝试上传超过 100MB 的文件
2. **预期结果**: 400 Bad Request
   ```json
   {
     "file": [
       "File size exceeds maximum allowed size of 100MB"
     ]
   }
   ```

### 测试 7: 获取文档列表

1. 找到 **GET /api/v1/documents/**
2. 点击 "Try it out"
3. 点击 "Execute"
4. **预期结果**: 200 OK，返回分页的文档列表
   ```json
   {
     "count": 5,
     "next": null,
     "previous": null,
     "results": [
       {
         "id": "uuid-string",
         "name": "document_20260224_123456.pdf",
         "original_name": "My Document.pdf",
         "file_type": "pdf",
         "file_size": 102400,
         "status": "uploaded",
         "title": "",
         "created_at": "2026-02-24T10:00:00Z"
       }
     ]
   }
   ```

### 测试 8: 按状态筛选文档列表

1. 找到 **GET /api/v1/documents/**
2. 点击 "Try it out"
3. 在 **status** 参数中输入：`uploaded`
4. 点击 "Execute"
5. **预期结果**: 200 OK，仅返回状态为 "uploaded" 的文档

**可用的状态值**:
- `uploaded` - 已上传
- `processing` - 处理中
- `processed` - 已处理
- `failed` - 处理失败
- `cancelled` - 已取消
- `done` - 已完成

### 测试 9: 获取文档详情

1. 找到 **GET /api/v1/documents/{id}/**
2. 点击 "Try it out"
3. 在 **id** 参数中输入之前上传的文档 UUID
4. 点击 "Execute"
5. **预期结果**: 200 OK
   ```json
   {
     "id": "uuid-string",
     "name": "document_20260224_123456.pdf",
     "original_name": "My Document.pdf",
     "file_size": 102400,
     "file_type": "pdf",
     "status": "uploaded",
     "title": "My Title",
     "description": "My Description",
     "author": "",
     "chunks_count": 0,
     "chunks": [],
     "error_message": "",
     "created_at": "2026-02-24T10:00:00Z",
     "updated_at": "2026-02-24T10:00:00Z"
   }
   ```

### 测试 10: 获取不存在的文档

1. 找到 **GET /api/v1/documents/{id}/**
2. 输入一个不存在的 UUID（如 `00000000-0000-0000-0000-000000000000`）
3. **预期结果**: 404 Not Found
   ```json
   {
     "detail": "Not found."
   }
   ```

### 测试 11: 删除文档

1. 找到 **DELETE /api/v1/documents/{id}/delete/**
2. 点击 "Try it out"
3. 在 **id** 参数中输入要删除的文档 UUID
4. 点击 "Execute"
5. **预期结果**: 204 No Content（无响应体）

### 测试 12: 删除后再获取该文档

1. 尝试获取已删除的文档
2. **预期结果**: 404 Not Found

### 测试 13: 无认证访问

1. 点击页面右上角 **Authorize** 按钮
2. 点击 **Logout** 清除认证
3. 尝试访问任何文档 API
4. **预期结果**: 401 Unauthorized
   ```json
   {
     "detail": "Authentication credentials were not provided."
   }
   ```

---

## curl 命令参考

### 设置环境变量

```bash
# 设置 access token（替换为实际 token）
export ACCESS_TOKEN="your_access_token_here"

# 设置基础 URL
export BASE_URL="http://localhost:8000/api/v1/documents"
```

### 上传文档

```bash
# 上传 PDF 文档
curl -X POST "$BASE_URL/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@/path/to/document.pdf" \
  -F "title=My Document Title" \
  -F "description=This is a test document"

# 上传 TXT 文档
curl -X POST "$BASE_URL/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@/path/to/test.txt"

# 上传 DOCX 文档
curl -X POST "$BASE_URL/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@/path/to/document.docx"
```

### 获取文档列表

```bash
# 获取所有文档
curl -X GET "$BASE_URL/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 按状态筛选
curl -X GET "$BASE_URL/?status=uploaded" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 分页查询
curl -X GET "$BASE_URL/?page=1&page_size=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 获取文档详情

```bash
# 替换 {id} 为实际文档 UUID
curl -X GET "$BASE_URL/{id}/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 删除文档

```bash
# 替换 {id} 为实际文档 UUID
curl -X DELETE "$BASE_URL/{id}/delete/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

## 测试场景清单

### 基础功能测试

| # | 测试场景 | 预期结果 | 状态 |
|---|----------|----------|------|
| 1 | 上传 PDF 文档 | 201 Created | [ ] |
| 2 | 上传 DOCX 文档 | 201 Created | [ ] |
| 3 | 上传 TXT 文档 | 201 Created | [ ] |
| 4 | 上传 MD 文档 | 201 Created | [ ] |
| 5 | 获取文档列表 | 200 OK + 列表数据 | [ ] |
| 6 | 按状态筛选列表 | 200 OK + 筛选结果 | [ ] |
| 7 | 获取文档详情 | 200 OK + 详情数据 | [ ] |
| 8 | 删除文档 | 204 No Content | [ ] |

### 边界条件测试

| # | 测试场景 | 预期结果 | 状态 |
|---|----------|----------|------|
| 9 | 上传重复文档 | 200 OK + message | [ ] |
| 10 | 上传不支持的文件类型 | 400 Bad Request | [ ] |
| 11 | 上传超大文件 | 400 Bad Request | [ ] |
| 12 | 获取不存在的文档 | 404 Not Found | [ ] |
| 13 | 删除不存在的文档 | 404 Not Found | [ ] |

### 认证与授权测试

| # | 测试场景 | 预期结果 | 状态 |
|---|----------|----------|------|
| 14 | 无 token 访问 API | 401 Unauthorized | [ ] |
| 15 | 无效 token 访问 API | 401 Unauthorized | [ ] |
| 16 | 访问其他用户的文档 | 404 Not Found | [ ] |

---

## 错误码说明

| 状态码 | 说明 |
|--------|------|
| 200 OK | 请求成功（重复文档返回此状态） |
| 201 Created | 文档创建成功 |
| 204 No Content | 删除成功（无响应体） |
| 400 Bad Request | 请求参数错误（文件类型不支持、文件过大等） |
| 401 Unauthorized | 未认证或 token 无效 |
| 404 Not Found | 文档不存在或无权访问 |

---

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| Connection refused | 确保 Django 服务器正在运行 |
| 401 Unauthorized | 检查 token 格式：`Bearer <token>`，确认 token 未过期 |
| 400 Bad Request (file type) | 确认文件扩展名在支持列表中 |
| 400 Bad Request (file size) | 确认文件大小不超过 100MB |
| 404 Not Found | 确认文档 UUID 正确，且属于当前用户 |
| CORS 错误 | 使用 Swagger UI 或确保 local settings 中 CORS_ALLOW_ALL_ORIGINS=True |
| Token 过期 | 使用 refresh token 获取新的 access token |

---

## 数据库验证

### 查看上传的文档

```bash
poetry run python manage.py dbshell
```

```sql
-- 查看所有文档
SELECT id, original_name, file_type, status, created_at
FROM documents
ORDER BY created_at DESC;

-- 查看特定用户的文档
SELECT id, original_name, status
FROM documents
WHERE user_id = 'user-uuid';

-- 查看文档数量
SELECT status, COUNT(*)
FROM documents
GROUP BY status;
```

### 查看文件存储

上传的文件存储在 `MEDIA_ROOT/documents/{year}/{month}/{day}/` 目录下：

```bash
# 查看存储的文件
ls -la media/documents/
```

---

## 下一步

文档上传成功后，后续流程包括：

1. **文档处理** - 由 document_pipeline_manager 模块处理
2. **向量化** - 由 embedding_engine 模块生成 embeddings
3. **向量存储** - 由 milvus_database_controller 模块存储到 Milvus
4. **知识图谱** - 由 neo4j_database_controller 模块构建图谱

这些功能将在后续 Phase 中实现。
