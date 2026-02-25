# Phases 3-5 模块手动测试指南

本文档提供 accounts、documents_parser、object_storage_controller 模块 API 的完整手动测试步骤。

## 测试凭据

> 以下凭据用于测试过程中的认证，每次测试会话后更新

| 字段 | 值 |
|------|-----|
| Username | testuser |
| Password | testpass123 |
| Access Token | (登录后获取) |
| Refresh Token | (登录后获取) |
| User ID | 1 |

---

## 目录

1. [前置条件](#前置条件)
2. [测试工具](#测试工具)
3. [API 端点总览](#api-端点总览)
4. [认证流程测试](#认证流程测试)
5. [文档上传测试](#文档上传测试)
6. [存储模块测试](#存储模块测试)
7. [错误码说明](#错误码说明)
8. [故障排除](#故障排除)

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

### 3. 确保 PostgreSQL 正在运行

### 4. (可选) 启动 MinIO 用于 S3 存储测试

```bash
docker run -d --name minio \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
```

MinIO Console: http://localhost:9001 (minioadmin/minioadmin)

### 5. 环境变量配置

在 `.env` 或 `config/settings/local.py` 中配置存储模式：

```bash
# S3 Mode (use MinIO for local development)
USE_S3_STORAGE=true
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=melon-documents
PRESIGNED_URL_EXPIRY=3600

# Local Mode (file system storage)
# USE_S3_STORAGE=false
```

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

### Phase 3: accounts 模块

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/accounts/auth/register/` | User registration | No |
| POST | `/api/v1/accounts/auth/login/` | User login | No |
| POST | `/api/v1/accounts/auth/logout/` | User logout | Yes (JWT) |
| POST | `/api/v1/accounts/auth/refresh/` | Refresh JWT token | No (refresh token) |
| GET | `/api/v1/accounts/profile/` | Get user profile | Yes (JWT) |
| PATCH | `/api/v1/accounts/profile/` | Update user profile | Yes (JWT) |
| POST | `/api/v1/accounts/password/change/` | Change password | Yes (JWT) |

### Phase 4: documents_parser 模块

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/v1/documents/` | List documents | Yes (JWT) |
| POST | `/api/v1/documents/` | Upload document (direct) | Yes (JWT) |
| GET | `/api/v1/documents/{id}/` | Get document detail | Yes (JWT) |
| GET | `/api/v1/documents/{id}/presigned-url/` | Get presigned download URL | Yes (JWT) |
| GET | `/api/v1/documents/{id}/download/` | Download file (Local mode) | Yes (JWT) |
| DELETE | `/api/v1/documents/{id}/delete/` | Delete document | Yes (JWT) |

### Phase 5: object_storage_controller 模块

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/storage/presigned-upload/` | Generate presigned upload URL | Yes (JWT) |
| GET | `/api/v1/storage/presigned-download/` | Generate presigned download URL | Yes (JWT) |
| POST | `/api/v1/storage/confirm-upload/` | Confirm upload & create document | Yes (JWT) |

---

## 认证流程测试

### 测试 1: 用户注册

1. 访问 http://localhost:8000/swagger/
2. 找到 **POST /api/v1/accounts/auth/register/**
3. 点击 "Try it out"
4. 输入请求体：
   ```json
   {
     "username": "testuser",
     "email": "testuser@example.com",
     "password": "testpass123",
     "password_confirm": "testpass123",
     "phone": "13812345678"
   }
   ```
5. 点击 "Execute"
6. **预期结果**: 201 Created
   ```json
   {
     "user": {
       "id": 1,
       "username": "testuser",
       "email": "testuser@example.com",
       "phone": "13812345678",
       "avatar": "",
       "bio": "",
       "is_verified": false,
       "created_at": "2026-02-25T10:00:00Z",
       "updated_at": "2026-02-25T10:00:00Z"
     },
     "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
     "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
   }
   ```

**Status**: ✅ PASS - 201 Created, 用户注册成功

### 测试 2: 用户登录

1. 找到 **POST /api/v1/accounts/auth/login/**
2. 点击 "Try it out"
3. 输入请求体：
   ```json
   {
     "username": "testuser",
     "password": "testpass123"
   }
   ```
4. 点击 "Execute"
5. **预期结果**: 200 OK
   ```json
   {
     "user": { ... },
     "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
     "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
     "knox_token": "abc123def456..."
   }
   ```
6. **复制 `access` token** 用于后续测试

**Status**: ✅ PASS - 200 OK, 返回 access/refresh/knox_token

### 测试 3: 配置认证

1. 点击页面右上角 **Authorize** 按钮
2. 输入：`Bearer <your_access_token>` (替换为实际的 token)
3. 点击 "Authorize" 然后点击 "Close"

**Status**: ⏭️ SKIP - 配置步骤

### 测试 4: 获取用户资料

1. 找到 **GET /api/v1/accounts/profile/**
2. 点击 "Try it out" 然后 "Execute"
3. **预期结果**: 200 OK
   ```json
   {
     "id": 1,
     "username": "testuser",
     "email": "testuser@example.com",
     "phone": "13812345678",
     "avatar": "",
     "bio": "",
     "is_verified": false,
     "created_at": "2026-02-25T10:00:00Z",
     "updated_at": "2026-02-25T10:00:00Z"
   }
   ```

**Status**: ✅ PASS - 200 OK, 返回用户资料

### 测试 5: 更新用户资料

1. 找到 **PATCH /api/v1/accounts/profile/**
2. 点击 "Try it out"
3. 输入请求体：
   ```json
   {
     "bio": "This is my bio",
     "phone": "13999999999"
   }
   ```
4. 点击 "Execute"
5. **预期结果**: 200 OK，返回更新后的资料

**Status**: ✅ PASS - 200 OK, bio 和 phone 已更新

### 测试 6: 用户登出

1. 找到 **POST /api/v1/accounts/auth/logout/**
2. 点击 "Try it out"
3. 可选输入 refresh token 以将其加入黑名单：
   ```json
   {
     "refresh": "<your_refresh_token>"
   }
   ```
4. 点击 "Execute"
5. **预期结果**: 200 OK
   ```json
   {
     "message": "Successfully logged out"
   }
   ```

**Status**: ✅ PASS - 200 OK, 用户已登出

---

## 文档上传测试

### 方式一: 直接上传 (通过 Django)

#### 测试 7: 上传 PDF 文档

1. 找到 **POST /api/v1/documents/**
2. 点击 "Try it out"
3. 填写表单数据：
   - **file**: 选择一个 PDF 文件
   - **title**: (可选) 输入文档标题
   - **description**: (可选) 输入文档描述
4. 点击 "Execute"
5. **预期结果**: 201 Created
   ```json
   {
     "id": "550e8400-e29b-41d4-a716-446655440000",
     "name": "report_abc12345.pdf",
     "original_name": "My Document.pdf",
     "file_type": "pdf",
     "file_size": 102400,
     "status": "uploaded",
     "title": "My Title",
     "description": "Description",
     "created_at": "2026-02-25T10:00:00Z"
   }
   ```

**Status**: ✅ PASS

**Test Results (Executed: 2026-02-25 15:42:04 CST)**

- **Actual Status Code**: 201 Created
- **Actual Response**:
  ```json
  {
    "id": "eeab74e7-4c2f-47e5-8d58-33035f14fb44",
    "name": "CASI_RefGuide_d4577d80.pdf",
    "original_name": "CASI_RefGuide.pdf",
    "file_type": "pdf",
    "file_size": 13977822,
    "status": "uploaded",
    "title": "CASI Reference Guide",
    "description": "Test PDF document upload",
    "created_at": "2026-02-25T07:42:04.744815Z"
  }
  ```
- **Notes**:
  - 测试前需要确保 MinIO bucket `melon-documents` 存在
  - 文件成功上传到 MinIO 存储
  - 响应格式符合预期，包含所有必要字段
  - 文件大小约 14MB，上传处理正常

#### 测试 8: 上传重复文档 (去重测试)

1. 使用之前上传过的同一文件再次上传
2. **预期结果**: 200 OK (非 201 Created)
   ```json
   {
     "id": "existing-document-uuid",
     "name": "report_abc12345.pdf",
     "original_name": "My Document.pdf",
     "file_type": "pdf",
     "file_size": 102400,
     "status": "uploaded",
     "message": "Document already exists",
     "created_at": "2026-02-25T10:00:00Z"
   }
   ```

**Status**: ⏳ TODO

#### 测试 9: 上传不支持的文件类型

1. 尝试上传一个 `.xlsx` 或 `.jpg` 文件
2. **预期结果**: 400 Bad Request
   ```json
   {
     "file": [
       "Unsupported file type '.xlsx'. Supported types: pdf, docx, doc, txt, md"
     ]
   }
   ```

**Status**: ⏳ TODO

#### 测试 10: 获取文档列表

1. 找到 **GET /api/v1/documents/**
2. 点击 "Try it out"
3. 点击 "Execute"
4. **预期结果**: 200 OK
   ```json
   {
     "success": true,
     "data": [
       {
         "id": "uuid-string",
         "name": "report_abc12345.pdf",
         "original_name": "My Document.pdf",
         "file_type": "pdf",
         "file_size": 102400,
         "status": "uploaded",
         "title": "My Document",
         "storage_backend": "s3",
         "created_at": "2026-02-25T10:00:00Z"
       }
     ],
     "pagination": {
       "count": 1,
       "page": 1,
       "page_size": 20,
       "total_pages": 1,
       "has_next": false,
       "has_previous": false
     }
   }
   ```

**Status**: ⏳ TODO

#### 测试 11: 按状态筛选文档列表

1. 找到 **GET /api/v1/documents/**
2. 在 **status** 参数中输入：`uploaded`
3. 点击 "Execute"
4. **预期结果**: 200 OK，仅返回状态为 "uploaded" 的文档

**Status**: ⏳ TODO

**可用的状态值**:
- `uploaded` - 已上传
- `processing` - 处理中
- `processed` - 已处理
- `failed` - 处理失败
- `cancelled` - 已取消
- `done` - 已完成

#### 测试 12: 获取文档详情

1. 找到 **GET /api/v1/documents/{id}/**
2. 输入之前上传的文档 UUID
3. 点击 "Execute"
4. **预期结果**: 200 OK
   ```json
   {
     "id": "uuid-string",
     "name": "report_abc12345.pdf",
     "original_name": "My Document.pdf",
     "file_size": 102400,
     "file_type": "pdf",
     "status": "uploaded",
     "title": "My Document",
     "description": "Description",
     "author": "",
     "storage_backend": "s3",
     "chunks_count": 0,
     "chunks": [],
     "error_message": "",
     "created_at": "2026-02-25T10:00:00Z",
     "updated_at": "2026-02-25T10:00:00Z"
   }
   ```

**Status**: ⏳ TODO

### 方式二: Presigned URL 上传 (S3 直传)

> 此方式适用于大文件上传，前端直接上传到 S3，减轻服务器负担。

#### 测试 13: 获取 Presigned Upload URL

1. 找到 **POST /api/v1/storage/presigned-upload/**
2. 点击 "Try it out"
3. 输入请求体：
   ```json
   {
     "file_name": "test-document.pdf",
     "file_type": "application/pdf",
     "file_size": 102400
   }
   ```
4. 点击 "Execute"
5. **预期结果**: 200 OK
   ```json
   {
     "upload_url": "https://s3.amazonaws.com/bucket/documents/2026/02/25/abc12345-test-document.pdf?signature=...",
     "file_path": "documents/2026/02/25/abc12345-test-document.pdf",
     "expires_in": 3600
   }
   ```

**Status**: ⏳ TODO

#### 测试 14: 使用 Presigned URL 上传文件

使用返回的 `upload_url` 直接上传文件到 S3：

**S3 Mode (MinIO/S3)**:
```bash
curl -X PUT "<upload_url>" \
  -H "Content-Type: application/pdf" \
  --data-binary @test-document.pdf
```

**Local Mode**: 此方式不可用，返回的 URL 将是无效路径。

**Status**: ⏳ TODO

#### 测试 15: 确认上传并创建文档记录

1. 找到 **POST /api/v1/storage/confirm-upload/**
2. 点击 "Try it out"
3. 输入请求体：
   ```json
   {
     "file_path": "documents/2026/02/25/abc12345-test-document.pdf",
     "file_name": "test-document.pdf",
     "file_size": 102400,
     "file_type": "pdf",
     "title": "My Uploaded Document",
     "description": "Uploaded via presigned URL"
   }
   ```
4. 点击 "Execute"
5. **预期结果**: 201 Created
   ```json
   {
     "id": "new-uuid-string",
     "name": "test-document.pdf",
     "file_path": "documents/2026/02/25/abc12345-test-document.pdf",
     "file_size": 102400,
     "file_type": "pdf",
     "status": "uploaded",
     "message": "Document uploaded successfully"
   }
   ```

**Status**: ⏳ TODO

---

## 存储模块测试

### 文档下载测试

#### 测试 16: 获取 Presigned Download URL

1. 找到 **GET /api/v1/documents/{id}/presigned-url/**
2. 输入文档 UUID
3. 点击 "Execute"
4. **预期结果 (S3 Mode)**: 200 OK
   ```json
   {
     "url": "https://s3.amazonaws.com/bucket/documents/...?signature=...",
     "expires_in": 3600,
     "method": "GET",
     "backend_type": "s3",
     "is_presigned": true
   }
   ```

5. **预期结果 (Local Mode)**: 200 OK
   ```json
   {
     "url": "/media/documents/2026/02/25/report.pdf",
     "expires_in": 0,
     "method": "GET",
     "backend_type": "local",
     "is_presigned": false
   }
   ```

**Status**: ⏳ TODO

#### 测试 17: 使用 Presigned URL 下载

**S3 Mode**: 前端直接使用返回的 URL 下载文件
```bash
curl -X GET "<presigned_url>" -o downloaded-file.pdf
```

**Local Mode**: 使用认证下载 API

**Status**: ⏳ TODO

#### 测试 18: 认证下载 (Local Mode)

1. 找到 **GET /api/v1/documents/{id}/download/**
2. 输入文档 UUID
3. 点击 "Execute"
4. **预期结果**: 200 OK，返回文件内容

**Status**: ⏳ TODO

#### 测试 19: 获取 Presigned Download URL (Storage API)

1. 找到 **GET /api/v1/storage/presigned-download/**
2. 点击 "Try it out"
3. 输入查询参数：
   - **file_path**: `documents/2026/02/25/abc12345-test-document.pdf`
   - **expires_in**: (可选) `3600`
4. 点击 "Execute"
5. **预期结果**: 200 OK
   ```json
   {
     "download_url": "https://s3.amazonaws.com/bucket/documents/...?signature=...",
     "expires_in": 3600
   }
   ```

**Status**: ⏳ TODO

### 文档删除测试

#### 测试 20: 删除文档

1. 找到 **DELETE /api/v1/documents/{id}/delete/**
2. 输入要删除的文档 UUID
3. 点击 "Execute"
4. **预期结果**: 204 No Content (无响应体)

**Status**: ⏳ TODO

#### 测试 21: 删除后再获取该文档

1. 尝试获取已删除的文档
2. **预期结果**: 404 Not Found

**Status**: ⏳ TODO

---

## 边界条件测试

| # | Test Case | Expected Result | Status |
|---|-----------|-----------------|--------|
| 1 | Upload file > 100MB | 400 Bad Request | [ ] |
| 2 | Get non-existent document | 404 Not Found | [ ] |
| 3 | Delete non-existent document | 404 Not Found | [ ] |
| 4 | Access other user's document | 404 Not Found | [ ] |
| 5 | Invalid file type (xlsx, jpg) | 400 Bad Request | [ ] |
| 6 | No authentication token | 401 Unauthorized | [✓] |
| 7 | Invalid/expired token | 401 Unauthorized | [ ] |
| 8 | Rate limit exceeded (auth endpoints) | 429 Too Many Requests | [ ] |

---

## curl 命令参考

### 环境变量设置

```bash
export BASE_URL="http://localhost:8000/api/v1"
export ACCESS_TOKEN="<your_access_token>"
```

### Accounts 模块

```bash
# Register
curl -X POST "$BASE_URL/accounts/auth/register/" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"pass123","password_confirm":"pass123"}'

# Login
curl -X POST "$BASE_URL/accounts/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"pass123"}'

# Get Profile
curl -X GET "$BASE_URL/accounts/profile/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Update Profile
curl -X PATCH "$BASE_URL/accounts/profile/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"bio":"New bio"}'

# Logout
curl -X POST "$BASE_URL/accounts/auth/logout/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refresh":"<refresh_token>"}'
```

### Documents 模块

```bash
# Upload Document
curl -X POST "$BASE_URL/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@test.pdf" \
  -F "title=Test Document"

# List Documents
curl -X GET "$BASE_URL/documents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# List Documents with Filter
curl -X GET "$BASE_URL/documents/?status=uploaded&page=1" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Get Document Detail
curl -X GET "$BASE_URL/documents/<document_id>/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Get Presigned URL
curl -X GET "$BASE_URL/documents/<document_id>/presigned-url/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Download (Local mode)
curl -X GET "$BASE_URL/documents/<document_id>/download/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -O -J

# Delete Document
curl -X DELETE "$BASE_URL/documents/<document_id>/delete/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### Storage 模块

```bash
# Get Presigned Upload URL
curl -X POST "$BASE_URL/storage/presigned-upload/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"file_name":"test.pdf","file_size":102400}'

# Upload to S3 (use returned upload_url)
curl -X PUT "<upload_url>" \
  -H "Content-Type: application/pdf" \
  --data-binary @test.pdf

# Confirm Upload
curl -X POST "$BASE_URL/storage/confirm-upload/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"file_path":"documents/2026/02/25/...","file_name":"test.pdf","file_size":102400}'

# Get Presigned Download URL
curl -X GET "$BASE_URL/storage/presigned-download/?file_path=documents/2026/02/25/..." \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

## 错误码说明

| Status Code | Description |
|-------------|-------------|
| 200 OK | Request successful (duplicate document returns this status) |
| 201 Created | Resource created successfully |
| 204 No Content | Delete successful (no response body) |
| 400 Bad Request | Request parameter error (unsupported file type, file too large, etc.) |
| 401 Unauthorized | Not authenticated or invalid token |
| 404 Not Found | Resource not found or no access permission |
| 429 Too Many Requests | Rate limit exceeded (auth endpoints: 5 req/min) |
| 500 Internal Server Error | Server error |

---

## 故障排除

| Problem | Solution |
|---------|----------|
| Connection refused | Ensure Django server is running |
| 401 Unauthorized | Check token format: `Bearer <token>`, verify token not expired |
| 400 Bad Request (file type) | Confirm file extension is in supported list: pdf, docx, doc, txt, md |
| 400 Bad Request (file size) | Confirm file size does not exceed 100MB |
| 404 Not Found | Confirm document UUID is correct and belongs to current user |
| CORS error | Use Swagger UI or ensure `CORS_ALLOW_ALL_ORIGINS=True` in local settings |
| Token expired | Use refresh token to get new access token |
| Presigned URL not working | Check `USE_S3_STORAGE` setting, verify MinIO/S3 is running |
| Upload confirmation fails | Ensure file was uploaded to S3 before calling confirm endpoint |

---

## 数据库验证

### 查看上传的文档

```bash
poetry run python manage.py dbshell
```

```sql
-- View all documents
SELECT id, original_name, file_type, status, storage_backend, created_at
FROM documents_parser_document
ORDER BY created_at DESC;

-- View documents for specific user
SELECT id, original_name, status
FROM documents_parser_document
WHERE user_id = 'user-uuid';

-- Count documents by status
SELECT status, COUNT(*)
FROM documents_parser_document
GROUP BY status;
```

---

## 存储模式对比

| Feature | S3 Mode (USE_S3_STORAGE=true) | Local Mode (USE_S3_STORAGE=false) |
|---------|-------------------------------|-----------------------------------|
| File storage | MinIO/S3 bucket | Local filesystem (media/) |
| Presigned upload | Real S3 presigned URL | Not available |
| Presigned download | Real S3 presigned URL | Relative path |
| Direct download | Not needed | Required (via API) |
| Frontend complexity | Lower (direct S3) | Higher (proxy through Django) |
| Server load | Lower | Higher |
| Scalability | Better | Limited |

---

## 模块依赖关系

```
accounts (User Model)
    │
    │ provides User model
    ▼
documents_parser (Document Model + Storage Service)
    │
    │ depends on storage abstraction
    ▼
object_storage_controller (Storage Backend Abstraction)
    │
    ├── S3Backend (MinIO/S3)
    └── LocalBackend (filesystem)
```
