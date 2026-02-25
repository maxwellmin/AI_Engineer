# Document Parser S3/Local 存储切换设计

> **注意**: 本设计已简化，采用环境变量静态切换方案，不再包含熔断器和健康检查机制。

## 设计目标

1. **环境隔离**: 开发环境使用 Local 存储，生产环境使用 S3
2. **透明切换**: 通过环境变量控制，上层业务代码无感知
3. **可追溯性**: 记录每个文档实际使用的存储后端
4. **简化架构**: 静态配置切换，避免运行时复杂性

---

## 当前架构分析

### 已有组件

| 组件 | 位置 | 功能 |
|------|------|------|
| `StorageBackend` ABC | `object_storage_controller/backends/base.py` | 统一存储接口 |
| `S3StorageBackend` | `object_storage_controller/backends/s3.py` | S3/MinIO 实现 |
| `LocalStorageBackend` | `object_storage_controller/backends/local.py` | 本地文件系统 |
| `get_storage_backend()` | `object_storage_controller/services/factory.py` | 工厂方法（单例） |
| Document 模型 | `documents_parser/models.py` | 存储 `file_path` 字符串 |

### 当前问题

1. **单点故障**: `USE_S3_STORAGE=True` 时，S3 不可用则服务完全失败
2. **无降级策略**: 无法在运行时切换存储后端
3. **状态缓存**: 单例模式缓存后端实例，无法动态切换

---

## 架构设计方案

### 方案概述（简化版）

```
┌─────────────────────────────────────────────────────────────┐
│              Storage Backend Factory                         │
│                                                              │
│  USE_S3_STORAGE=true                                         │
│  ┌─────────────────────┐                                    │
│  │  S3StorageBackend   │  ──▶ 生产环境：AWS S3 / MinIO       │
│  └─────────────────────┘                                    │
│                                                              │
│  USE_S3_STORAGE=false                                        │
│  ┌─────────────────────┐                                    │
│  │ LocalStorageBackend │  ──▶ 开发环境：本地文件系统         │
│  └─────────────────────┘                                    │
│                                                              │
│  静态切换：启动时决定，运行时不变                             │
└─────────────────────────────────────────────────────────────┘
```

### 关键设计决策

1. **静态切换**: 通过环境变量 `USE_S3_STORAGE` 控制，应用启动时确定
2. **无运行时切换**: 避免状态管理和同步问题
3. **存储标识**: 每个文档记录实际使用的存储后端（`storage_backend` 字段）
4. **预签名 URL 差异**: S3 返回真正的预签名 URL，Local 返回相对路径

---

## 核心组件设计

### 1. StorageResult 扩展

```python
# apps/object_storage_controller/backends/base.py

@dataclass(frozen=True)
class StorageResult:
    """Immutable result of file storage operation."""

    file_path: str  # Object key in storage
    file_size: int  # File size in bytes
    file_type: str  # File extension (e.g., 'pdf', 'docx')
    etag: str = ""  # S3 ETag for verification (optional)
    backend_type: str = "s3"  # NEW: "s3" or "local"
```

### 2. PresignedUrlResult 扩展

```python
# apps/object_storage_controller/backends/base.py

@dataclass(frozen=True)
class PresignedUrlResult:
    """Immutable result of presigned URL generation."""

    url: str  # Presigned URL or relative path
    expires_in: int  # Expiry time in seconds (0 for local)
    method: str  # HTTP method ('GET' or 'PUT')
    backend_type: str = "s3"  # NEW: "s3" or "local"
    is_presigned: bool = True  # NEW: True for S3, False for local
```

### 3. 工厂方法（已实现）

```python
# apps/object_storage_controller/services/factory.py

def get_storage_backend() -> StorageBackend:
    """Get storage backend based on settings.

    Static switching based on USE_S3_STORAGE environment variable.
    """
    if settings.USE_S3_STORAGE:
        return S3StorageBackend()
    return LocalStorageBackend()
```

### 4. Document 模型扩展

```python
# apps/documents_parser/models.py

class Document(models.Model):
    # ... existing fields ...

    # Storage metadata
    storage_backend = models.CharField(max_length=20, default="s3")  # "s3" or "local"
    storage_metadata = models.JSONField(default=dict, blank=True)  # Optional: etag, etc.
```

---

## 配置管理

### 环境变量

```bash
# .env.local 或 .env.production

# S3 配置（生产环境）
USE_S3_STORAGE=true
S3_ENDPOINT_URL=  # 留空使用 AWS S3，或填写 MinIO 地址
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=melon-documents
S3_REGION_NAME=us-east-1

# Local 存储配置（开发环境）
USE_S3_STORAGE=false
```

### Settings 配置

```python
# config/settings/base.py

# =============================================================================
# Storage Configuration
# =============================================================================

USE_S3_STORAGE = os.environ.get("USE_S3_STORAGE", "false").lower() == "true"

# Local storage path
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"
```

---

## API 调整建议

### 1. 预签名 URL 流程差异

**S3 模式**: 返回真正的预签名 URL，前端直接使用
**Local 模式**: 返回相对路径，需通过后端 API 认证下载

```python
# S3 模式响应
{
    "url": "https://s3.amazonaws.com/bucket/documents/...?signature=...",
    "expires_in": 3600,
    "method": "GET",
    "backend_type": "s3",
    "is_presigned": true
}

# Local 模式响应
{
    "url": "/media/documents/2026/02/24/report.pdf",
    "expires_in": 0,
    "method": "GET",
    "backend_type": "local",
    "is_presigned": false
}
```

**前端处理逻辑**:
```javascript
async function downloadFile(presignedResult) {
  if (presignedResult.is_presigned) {
    // S3: 直接使用预签名 URL
    window.open(presignedResult.url, '_blank');
  } else {
    // Local: 需要通过后端 API 认证下载
    const response = await fetch(`/api/v1/documents/${docId}/download/`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    // ... 处理下载
  }
}
```

### 2. Document 模型扩展

追踪文件实际存储位置，便于运维和排查问题：

```python
class Document(models.Model):
    # ... existing fields ...

    # Storage metadata
    storage_backend = models.CharField(max_length=20, default="s3")  # "s3" or "local"
    storage_metadata = models.JSONField(default=dict, blank=True)  # Additional storage info
```

**Migration**:
```python
# apps/documents_parser/migrations/XXXX_add_storage_backend.py

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('documents_parser', 'previous_migration'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='storage_backend',
            field=models.CharField(default='s3', max_length=20),
        ),
        migrations.AddField(
            model_name='document',
            name='storage_metadata',
            field=models.JSONField(default=dict, blank=True),
        ),
    ]
```

### 3. documents_parser 存储服务更新

更新 `documents_parser/services/storage.py`，在保存文件时记录实际的存储后端：

```python
# apps/documents_parser/services/storage.py

def save_file(*, uploaded_file: UploadedFile, user_id: str) -> StorageResult:
    """Save uploaded file to storage using the configured backend.

    Returns StorageResult with backend_type field indicating which
    backend was actually used.
    """
    file_type = validate_file(uploaded_file=uploaded_file)
    filename = uploaded_file.name or f"document.{file_type}"
    file_path = get_storage_path(filename=filename)

    backend = _get_storage_backend()
    result = backend.save(
        file_path=file_path,
        content=uploaded_file,
        content_type=uploaded_file.content_type or "application/octet-stream"
    )

    # Log backend type
    logger.info(
        f"Saved file to {result.backend_type} storage: {file_path}",
        extra={
            "file_path": result.file_path,
            "user_id": user_id,
            "backend_type": result.backend_type,
        }
    )

    return result
```

---

## 测试策略

### 1. 单元测试

```python
# apps/object_storage_controller/tests/test_backend_types.py

import pytest
from io import BytesIO

from apps.object_storage_controller.backends.s3 import S3StorageBackend
from apps.object_storage_controller.backends.local import LocalStorageBackend

class TestStorageBackendTypes:

    def test_s3_backend_returns_s3_type(self, mock_s3_client):
        """S3 backend should return backend_type='s3'."""
        backend = S3StorageBackend()
        result = backend.save("test.pdf", BytesIO(b"content"))

        assert result.backend_type == "s3"

    def test_local_backend_returns_local_type(self, tmp_path):
        """Local backend should return backend_type='local'."""
        backend = LocalStorageBackend()
        result = backend.save("test.pdf", BytesIO(b"content"))

        assert result.backend_type == "local"

    def test_s3_presigned_url_is_presigned(self, mock_s3_client):
        """S3 presigned URL should have is_presigned=True."""
        backend = S3StorageBackend()
        result = backend.get_presigned_url("test.pdf")

        assert result.is_presigned is True
        assert result.backend_type == "s3"

    def test_local_presigned_url_not_presigned(self, tmp_path):
        """Local presigned URL should have is_presigned=False."""
        backend = LocalStorageBackend()
        result = backend.get_presigned_url("test.pdf")

        assert result.is_presigned is False
        assert result.backend_type == "local"
```

### 2. 集成测试

```python
# apps/documents_parser/tests/test_storage_backend_tracking.py

import pytest
from django.test import override_settings

from apps.documents_parser.services.storage import save_file
from apps.documents_parser.models import Document

@pytest.mark.django_db
class TestStorageBackendTracking:

    @override_settings(USE_S3_STORAGE=False)
    def test_document_records_local_backend(self, user, uploaded_file):
        """Document should record storage_backend='local' when USE_S3_STORAGE=False."""
        result = save_file(uploaded_file=uploaded_file, user_id=str(user.id))

        doc = Document.objects.create(
            user=user,
            name="test.pdf",
            original_name="test.pdf",
            file_path=result.file_path,
            file_size=result.file_size,
            file_type=result.file_type,
            file_hash="abc123",
            storage_backend=result.backend_type,
        )

        assert doc.storage_backend == "local"
```

### 3. E2E 测试场景

| 场景 | 预期行为 |
|------|---------|
| USE_S3_STORAGE=true | 使用 S3StorageBackend，backend_type="s3" |
| USE_S3_STORAGE=false | 使用 LocalStorageBackend，backend_type="local" |
| 文档上传后 | Document.storage_backend 正确记录实际后端 |
| S3 预签名 URL | is_presigned=True，expires_in>0 |
| Local 预签名 URL | is_presigned=False，expires_in=0 |

---

## 监控和日志

### 日志格式

```python
# 文件保存日志
{
    "level": "INFO",
    "message": "Saved file to s3 storage: documents/2026/02/24/report.pdf",
    "extra": {
        "file_path": "documents/2026/02/24/report.pdf",
        "user_id": "uuid",
        "backend_type": "s3",
        "timestamp": "2026-02-24T10:30:00Z"
    }
}
```

### 告警建议

基于日志配置告警规则（如有日志平台）：

- 监控存储操作失败
- 监控存储后端切换频率（如有异常）

---

## 实施计划

### 设计说明

本方案采用**环境变量静态切换**策略，通过 `USE_S3_STORAGE` 控制使用 S3 还是 Local 存储。S3 优先，静态切换，不支持运行时动态切换。

### Submodule 1: 存储后端标识扩展

| # | Task | Description | Status |
|---|------|-------------|--------|
| 1.1 | 扩展 StorageResult | 添加 `backend_type` 字段标识实际使用的存储后端 | 待办 |
| 1.2 | 扩展 PresignedUrlResult | 添加 `backend_type` 和 `is_presigned` 字段 | 待办 |
| 1.3 | 更新 S3StorageBackend | 返回结果中填充 `backend_type="s3"` | 待办 |
| 1.4 | 更新 LocalStorageBackend | 返回结果中填充 `backend_type="local"` | 待办 |
| 1.5 | 添加 Local 预签名 URL 说明 | 更新 `get_presigned_url` 方法注释，说明本地存储返回相对路径 | 待办 |

### Submodule 2: Document 模型扩展

| # | Task | Description | Status |
|---|------|-------------|--------|
| 2.1 | 添加 storage_backend 字段 | 在 Document 模型中添加 `storage_backend` 字段，默认 "s3" | 待办 |
| 2.2 | 创建数据库迁移 | 生成并应用迁移文件 | 待办 |
| 2.3 | 更新模型文档 | 添加字段说明注释 | 待办 |

### Submodule 3: 存储服务更新

| # | Task | Description | Status |
|---|------|-------------|--------|
| 3.1 | 更新 save_file 服务 | 保存文件后记录 `storage_backend` 到 Document 实例 | 待办 |
| 3.2 | 添加 storage_metadata 字段 | （可选）添加 JSONField 存储额外元数据如 etag | 待办 |
| 3.3 | 更新日志记录 | 在切换存储后端时记录日志 | 待办 |

### Submodule 4: 预签名 URL 处理优化

| # | Task | Description | Status |
|---|------|-------------|--------|
| 4.1 | 添加文档下载 API | Local 模式下需要认证的下载端点 | 待办 |
| 4.2 | 更新预签名 URL 响应 | 确保 `is_presigned=False` 时前端知道需要通过 API 下载 | 待办 |
| 4.3 | 更新 API 文档 | 说明两种存储模式下的下载流程差异 | 待办 |

### Submodule 5: 测试与验证

| # | Task | Description | Status |
|---|------|-------------|--------|
| 5.1 | 单元测试 - StorageResult | 测试两个后端的 `backend_type` 返回值 | 待办 |
| 5.2 | 单元测试 - PresignedUrlResult | 测试 S3 和 Local 的预签名 URL 差异 | 待办 |
| 5.3 | 集成测试 - Document 保存 | 验证 `storage_backend` 字段正确记录 | 待办 |
| 5.4 | 手动测试 - S3 模式 | 验证 S3 存储正常工作 | 待办 |
| 5.5 | 手动测试 - Local 模式 | 验证 Local 存储正常工作 | 待办 |

### Submodule 6: 文档与配置

| # | Task | Description | Status |
|---|------|-------------|--------|
| 6.1 | 更新环境变量文档 | 在 `docs/environment_variables.md` 中添加存储配置说明 | 待办 |
| 6.2 | 更新架构文档 | 在 `docs/architecture.md` 中说明存储切换策略 | 待办 |
| 6.3 | 添加部署说明 | 说明生产环境（S3）和开发环境（Local）的配置差异 | 待办 |

---

## 关键文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `object_storage_controller/backends/base.py` | 修改 | StorageResult/PresignedUrlResult 添加 backend_type |
| `object_storage_controller/backends/s3.py` | 修改 | 返回结果填充 backend_type="s3" |
| `object_storage_controller/backends/local.py` | 修改 | 返回结果填充 backend_type="local" |
| `documents_parser/models.py` | 修改 | 添加 storage_backend 字段 |
| `documents_parser/services/storage.py` | 修改 | 保存时记录 backend_type |
| `documents_parser/migrations/XXXX_add_storage_backend.py` | 新建 | 模型迁移 |
| `documents_parser/views.py` | 修改 | 添加 Local 模式下载 API（如需要） |
| `docs/architecture.md` | 更新 | 文档化存储切换策略 |
| `docs/environment_variables.md` | 更新 | 添加存储配置说明 |
