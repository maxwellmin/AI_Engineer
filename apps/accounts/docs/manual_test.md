# Accounts 模块手动测试指南

本文档提供 accounts 模块 API 的手动验证步骤。

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
| POST | `/api/v1/accounts/auth/register/` | 用户注册 | 否 |
| POST | `/api/v1/accounts/auth/login/` | 用户登录 | 否 |
| POST | `/api/v1/accounts/auth/logout/` | 用户登出 | 是 (JWT) |
| POST | `/api/v1/accounts/auth/refresh/` | 刷新 Token | 否 (refresh token) |
| GET | `/api/v1/accounts/profile/` | 获取用户资料 | 是 (JWT) |
| PATCH | `/api/v1/accounts/profile/` | 更新用户资料 | 是 (JWT) |
| POST | `/api/v1/accounts/password/change/` | 修改密码 | 是 (JWT) |

---

## Swagger UI 测试流程

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
6. **预期结果**: 201 Created，返回用户数据 + JWT tokens

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
5. **预期结果**: 200 OK，返回用户数据 + JWT tokens + Knox token
6. **复制 `access` token** 用于后续测试

### 测试 3: 获取用户资料（需要认证）

1. 点击页面右上角 **Authorize** 按钮
2. 输入：`Bearer <your_access_token>`（替换为实际的 token）
3. 点击 "Authorize" 然后点击 "Close"
4. 找到 **GET /api/v1/accounts/profile/**
5. 点击 "Try it out" 然后 "Execute"
6. **预期结果**: 200 OK，返回用户资料数据

### 测试 4: 更新用户资料（需要认证）

1. 确保 Authorize 状态有效
2. 找到 **PATCH /api/v1/accounts/profile/**
3. 点击 "Try it out"
4. 输入请求体：
   ```json
   {
     "bio": "这是我的个人简介",
     "phone": "13899999999"
   }
   ```
5. 点击 "Execute"
6. **预期结果**: 200 OK，返回更新后的资料

### 测试 5: 修改密码（需要认证）

1. 确保 Authorize 状态有效
2. 找到 **POST /api/v1/accounts/password/change/**
3. 点击 "Try it out"
4. 输入请求体：
   ```json
   {
     "old_password": "testpass123",
     "new_password": "newpass456",
     "new_password_confirm": "newpass456"
   }
   ```
5. 点击 "Execute"
6. **预期结果**: 200 OK，返回成功消息

### 测试 6: 用户登出（需要认证）

1. 确保 Authorize 状态有效
2. 找到 **POST /api/v1/accounts/auth/logout/**
3. 点击 "Try it out"
4. 可选：输入 refresh token 以将其加入黑名单
   ```json
   {
     "refresh": "<your_refresh_token>"
   }
   ```
5. 点击 "Execute"
6. **预期结果**: 200 OK，返回成功消息

---

## curl 命令参考

### 用户注册
```bash
curl -X POST http://localhost:8000/api/v1/accounts/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "testuser@example.com",
    "password": "testpass123",
    "password_confirm": "testpass123"
  }'
```

### 用户登录
```bash
curl -X POST http://localhost:8000/api/v1/accounts/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123"
  }'
```

### 获取用户资料
```bash
curl -X GET http://localhost:8000/api/v1/accounts/profile/ \
  -H "Authorization: Bearer <your_access_token>"
```

### 更新用户资料
```bash
curl -X PATCH http://localhost:8000/api/v1/accounts/profile/ \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "bio": "新简介",
    "phone": "13899999999"
  }'
```

### 修改密码
```bash
curl -X POST http://localhost:8000/api/v1/accounts/password/change/ \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "testpass123",
    "new_password": "newpass456",
    "new_password_confirm": "newpass456"
  }'
```

### 用户登出
```bash
curl -X POST http://localhost:8000/api/v1/accounts/auth/logout/ \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "<your_refresh_token>"
  }'
```

---

## 错误码说明

| 状态码 | 说明 |
|--------|------|
| 200 OK | 请求成功 |
| 201 Created | 资源创建成功 |
| 400 Bad Request | 请求参数错误 |
| 401 Unauthorized | 未认证或 token 无效 |
| 429 Too Many Requests | 请求频率超限（登录/注册 5次/分钟） |

---

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| Connection refused | 确保 Django 服务器正在运行 |
| 401 Unauthorized | 检查 token 格式：`Bearer <token>` |
| 400 Bad Request | 检查请求体 JSON 格式是否正确 |
| CORS 错误 | 使用 Swagger UI 或确保 local settings 中 CORS_ALLOW_ALL_ORIGINS=True |
| Token 过期 | 使用 refresh token 获取新的 access token |
