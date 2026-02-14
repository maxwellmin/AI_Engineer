# Django REST API — melon

## 项目介绍
- 基于RAG技术的文档知识库处理工具
- 使用milvusdb作为向量数据库，支持多种文档格式的解析和处理
- 使用neo4j作为图数据库，支持复杂的关系查询和分析，作为图RAG的核心组件
- 当前项目为后台服务，提供REST API接口供前端调用，这个项目为了维护的简洁性和专注性，不包含前端代码，前端可以根据需要使用React、Vue等框架进行开发，并通过API与后端进行交互。
- 目标是基于 Django REST Framework提供的RESTful API 接口，可以通过curl，postman等工具进行测试和调用，或者通过前端应用进行交互。
- 项目需要通过poetry来管理依赖，使用pytest进行测试，使用Docker Compose来管理开发环境和部署环境，确保项目的可维护性和可扩展性。

## 技术栈

### 后端
- **Framework**: Django 5.1+
- **Python Version**: 3.12+
- **API Style**: Django REST Framework (DRF)
- **异步支持**: Django Channels (WebSocket)
- **任务队列**: Celery + Redis
- **API文档**: drf-spectacular (OpenAPI 3.0)
- **api gateway令牌认证**: knox

### 数据存储
- **关系型数据库**: PostgreSQL 14+
  - 用途：用户数据、会话记录、文档元数据、文档处理任务追踪（如uploaded， processed， failed， cancelled， done等）
  - 模型设计：用户（User）、文档（Document）、会话（Session）、实体（Entity）

- **向量数据库**: Milvus 2.4+
  - 用途：文档embeddings存储、语义搜索
  - Collection设计：
    - `documents`: 文档向量（dimension: 1536, OpenAI ada-002）
    - `chat_history`: 对话历史向量（用于上下文检索）
  - 索引类型：IVF_FLAT（适合中小规模数据，提供较快的查询速度和较高的准确率）
  - 索引参数：根据根据使用模型的维度和数据规模进行调整，如nlist=128，nprobe=10等
  - Milvus GUI: zilliz/attu:v2.6 （提供可视化管理界面，方便监控和调试）

- **图数据库**: Neo4j 5.x
  - 用途：知识图谱、实体关系、概念层级
  - 主要节点类型：`Document`, `Entity`, `Concept`, `User`
  - 关系类型：`CONTAINS`, `RELATES_TO`, `MENTIONED_IN`, `ASKED_BY`

- **缓存**: Redis
  - 任务队列: Celery + Redis
  - 缓存使用Redis存储，缓存如果需要，如缓存用户信息、会话信息、文档处理结果等

### AI/ML组件
- **LLM Provider**: 阿里云通义千问 API (Qwen-2-72B / Qwen-2-7B / Qwen-2-1.8B)
- **Embedding Model**: text-embedding-v1（阿里云通义千问嵌入模型, 1536维默认）
- **向量相似度**: Cosine Similarity（余弦相似度，该算法无厂商差异，保持不变）
- **RAG Framework**: LangChain 1.0+（LangChain 原生支持千问，框架无需替换，补充适配说明）, Langgraph 1.0+方便更高级的封装，如图RAG的实现

### 基础设施
- **容器化**: Docker + Docker Compose
- **开发用基础设施信息**: `dev_utils/*` docker-compose.yml README.md
- **开发环境基础设施操作**: 尽量人工自行操作，意见系统组件和端口冲突，claude console操作尽量和人工确认


## 技术架构

### 项目架构图
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

### 核心组件
- **Django Channels**: 处理 WebSocket 连接，实现实时通信功能
- **Django REST Framework**: 提供 RESTful API 接口
- **document parser**: 解析文档，拆分为句子、段落，形成符合逻辑的 chunking
- **milvus database controller**: 向量库的创建、插入、搜索、删除
- **neo4j database controller**: 知识图谱节点的创建、查询、更新、删除
- **embedding engine**: 文本向量化（sentence transformer + qwen api）
- **RAG processing pipeline**: 查询处理、上下文组装、LLM 生成
- **WebSocket manager**: WebSocket 连接管理、消息处理


## 项目目录架构

```
dev_utils/               # 开发环境工具
  docker-compose.yml     # Docker 容器配置
docs/
  architecture.md        # 架构设计文档
  code_style.md          # 代码规范
  dev_plan.md            # 开发计划
  reference.md           # 参考资料
  BM25_procedure.md      # BM25 相关设计文档
  environment_variables.md # 环境变量说明
config/
  settings/
    base.py              # 通用配置
    local.py             # 开发环境覆盖配置（DEBUG=True）
    production.py        # 生产环境配置
  urls.py                # 根 URL 配置
  celery.py              # Celery 应用配置
apps/
  accounts/              # 用户认证、注册、个人资料
  documents_parser/      # 文档解析和处理
  document_pipeline_manager/  # 文档处理流水线管理
  milvus_database_controller/ # Milvus 数据库控制器
  neo4j_database_controller/  # Neo4j 数据库控制器
  embedding_engine/      # 文本向量化
  RAGprocessing/         # RAG 流水线和 Agent
  WebSocket manager/     # WebSocket 管理器
core/
  exceptions.py          # 自定义 API 异常
  permissions.py         # 共享权限类
  pagination.py          # 自定义分页
  middleware.py          # 请求日志、耗时统计
tests/                   # 项目级测试
env/                     # 环境配置文件
pyproject.toml           # Poetry 配置文件
```


## 核心代码规范

> 详细规范参见 `docs/code_style.md`

### Python 编码约定
- 所有函数签名必须添加类型注解 — 需引入 `from __future__ import annotations`
- 禁止使用 `print()` 语句 — 统一使用 `logging.getLogger(__name__)` 记录日志
- 字符串格式化使用 f-string，禁止使用 `%` 或 `.format()`
- 文件操作使用 `pathlib.Path`，禁止使用 `os.path`
- 导入语句按 isort 规则排序：标准库 → 第三方库 → 本地模块

### 数据库规范
- 所有数据库查询使用 Django ORM — 仅在必要时通过 `.raw()` 使用参数化查询
- 数据库迁移文件需提交至 git — 生产环境禁止使用 `--fake` 参数
- 使用 `select_related()` 和 `prefetch_related()` 避免 N+1 查询问题
- 所有模型必须包含 `created_at` 和 `updated_at` 自动字段
- 所有用于 `filter()`、`order_by()` 或 `WHERE` 子句的字段需添加索引

### 认证规范
- 基于 `djangorestframework-simplejwt` 实现 JWT 认证 — 访问令牌（15 分钟）+ 刷新令牌（7 天）
- 所有视图必须显式指定权限类 — 禁止依赖默认权限配置
- 基础权限使用 `IsAuthenticated`，对象级别的访问控制需自定义权限类

### 序列化器规范
- 简单 CRUD 操作使用 `ModelSerializer`，复杂校验场景使用 `Serializer`
- 输入/输出数据结构不同时，拆分读/写序列化器
- 校验逻辑放在序列化器层实现，视图层保持轻量

### 异常处理规范
- 使用 DRF 异常处理器保证错误响应格式统一
- 业务逻辑相关的自定义异常放在 `core/exceptions.py` 中
- 禁止向客户端暴露内部错误详情

### 代码风格规范
- 代码和注释中禁止使用表情符号
- 最大行长度：120 个字符
- 命名规范：类使用 PascalCase，函数/变量使用 snake_case，常量使用 UPPER_SNAKE_CASE
- 视图层保持轻量 — 业务逻辑放在服务函数或模型方法中
- 函数行数建议 <40 行，复杂度建议 <10


## 数据流设计

> 详细设计参见 `docs/architecture.md`

### 文档上传流程
```
User Upload → Django API → Document Parser → Text Chunking
    → Embedding Generation → Milvus Storage
    → Entity Extraction → Neo4j Graph Update
    → PostgreSQL Metadata Storage
```

### Chat 对话流程
```
User Message (WebSocket) → Django Channels Consumer
    → Query Embedding → Milvus Similarity Search (top_k=5)
    → Neo4j Graph Context Retrieval
    → Context Assembly (retrieved docs + graph info)
    → LLM Prompt Construction → QWEN API Call
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

### RAG Processing Pipeline
1. **Query Processing**: 用户问题预处理（去停用词、标准化）、生成 query embedding
2. **Retrieval Stage**: Milvus 向量检索 + Neo4j 图检索 + PostgreSQL 关键词检索
3. **Context Assembly**: 检索结果去重排序、构建上下文窗口（max 4000 tokens）
4. **Generation Stage**: Prompt 模板渲染、流式调用 LLM API

### WebSocket 消息格式
```python
# 客户端 → 服务端
{
    "type": "chat.message",
    "content": "用户问题",
    "conversation_id": "uuid"
}

# 服务端 → 客户端（流式响应）
{
    "type": "chat.response.chunk",
    "content": "AI回复片段",
    "is_final": false
}

# 服务端 → 客户端（完成）
{
    "type": "chat.response.complete",
    "message_id": "uuid",
    "sources": [...]
}
```


## 开发阶段

> 详细计划参见 `docs/dev_plan.md`

| 阶段 | 名称 | 核心目标 |
|-----|------|---------|
| 1 | 方案评估和开发计划 | 阅读文档，确定开发计划，对齐开发思路 |
| 2 | 基础搭建 | 创建 Django 工程和 app，数据库初始化，基础设施和环境变量配置 |
| 3 | 用户管理模块 | 用户注册、登录、权限管理，基于 Django 用户模块扩展 |
| 4 | document parser 模块 | 文档上传、解析、存储，元数据管理，文档去重 |
| 5 | milvus_database_controller | 向量数据库的增删改查，封装连接器和方法 |
| 6 | neo4j_database_controller | 图数据库的增删改查，封装连接器和方法 |
| 7 | embedding_module | 文本向量化功能，Service 方式提供给其他模块 |
| 8 | document pipeline manager | 文档处理流水线管理，状态跟踪和记录 |
| 9 | document rag search module | RAG 搜索功能，混合检索（向量+关键词+图） |
| 10 | chat agent module | 基于 RAG 的 chat agent，WebSocket 实时通信 |
| 11 | 集成测试 | 端到端测试，功能验证，问题优化 |


## 环境变量

> 详细配置参见 `docs/environment_variables.md`

- Django 配置（SECRET_KEY、DEBUG、ALLOWED_HOSTS）
- 数据库配置（PostgreSQL 连接信息）
- Redis 配置（Celery 用）
- Celery 配置
- Milvus 配置
- Qwen API 设置
- AI/ML 模型配置

不同环境在 `env/` 目录下创建对应配置文件：`.env_local.env`、`.env_production.env`、`.env_uat.env`


## 测试策略

```bash
# 运行所有测试
pytest --cov=apps --cov-report=term-missing

# 运行指定应用的测试
pytest apps/orders/tests/ -v

# 并行执行测试
pytest -n auto

# 仅运行上一次失败的测试
pytest --lf
```


## TDD 工作流

### pytest-django 配置

pytest 需要知道 Django 的配置模块路径，可选择以下配置方式之一：

**pyproject.toml（推荐）**：
```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.local"
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

**pytest.ini**：
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.local
```

### TDD 循环：Red -> Green -> Refactor

1. **Red**: 编写失败的测试
   ```bash
   pytest apps/accounts/tests/test_views.py::TestUserRegistration -v
   # 预期：FAILED
   ```

2. **Green**: 编写最小代码通过测试
   ```bash
   pytest apps/accounts/tests/test_views.py::TestUserRegistration -v
   # 预期：PASSED
   ```

3. **Refactor**: 重构代码，运行测试确认仍通过
   ```bash
   pytest apps/accounts/tests/ -v
   ruff check apps/accounts/
   ```

### pytest-django 关键装饰器

```python
import pytest

# 标记需要数据库访问的测试
@pytest.mark.django_db
def test_create_user():
    user = User.objects.create(username="test")
    assert user.username == "test"

# 标记整个测试类
@pytest.mark.django_db
class TestUserAPI:
    def test_list_users(self):
        ...

# 使用事务回滚
@pytest.mark.django_db(transaction=True)
def test_with_transaction():
    ...
```

### 测试命令速查

```bash
pytest                                    # 运行所有测试
pytest apps/accounts/tests/ -v            # 运行指定应用
pytest -n auto                            # 并行执行
pytest --lf                               # 仅运行失败测试
pytest --cov=apps --cov-report=term-missing  # 覆盖率报告
```

### 测试文件结构

```
apps/{app_name}/tests/
├── test_models.py       # 模型测试
├── test_views.py        # API 视图测试
├── test_serializers.py  # 序列化器测试
├── test_services.py     # 服务函数测试
├── factories.py         # Factory Boy 工厂
└── conftest.py          # 共享 fixtures
```


## Git 工作流

- 提交信息前缀规范：`feat:` 新功能，`fix:` 漏洞修复，`refactor:` 代码重构
- 基于 `main` 分支创建功能分支，合并需提交 PR
- 持续集成（CI）：ruff（代码检查 + 格式化）、mypy（类型校验）、pytest（单元测试）、safety（依赖安全检查）
- 部署方式：构建 Docker 镜像，通过 Kubernetes 或 Railway 管理


## 参考文档

| 文档 | 路径 | 说明 |
|-----|------|------|
| 架构设计 | `docs/architecture.md` | 系统架构、数据流、API 设计、数据库模型 |
| 代码规范 | `docs/code_style.md` | 编码约定、设计模式、测试模式 |
| 开发计划 | `docs/dev_plan.md` | 11 个开发阶段的详细说明 |
| 环境变量 | `docs/environment_variables.md` | 各服务的环境变量配置 |
| 参考资料 | `docs/reference.md` | RAG Pipeline 代码示例 |
| BM25 | `docs/BM25_procedure.md` | BM25 算法原理和集成流程 |

项目参考：
- https://github.com/stttt2003pk/medical-rag/blob/main/src/MedicalRag/rag/MultiDialogueRag.py
- https://github.com/stttt2003pk/What-to-eat-today
