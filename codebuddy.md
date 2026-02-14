# Django REST API — melon CLAUDE.md（中文版）


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
- **开发环境基础设施操作**： 尽量人工自行操作，意见系统组件和端口冲突，claude console操作尽量和人工确认


## 技术架构

### 架构文档
- 详细的架构设计文档位于 `docs/architecture.md`，包含系统组件、数据流、API设计、数据库模型等内容。
- 项目参考：
  - https://github.com/stttt2003pk/medical-rag/blob/main/src/MedicalRag/rag/MultiDialogueRag.py
  - https://github.com/stttt2003pk/What-to-eat-today
  - `docs/reference.md` 中包含了相关技术的参考资料和最佳实践链接。

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

## 项目目录架构

```
dev_utils/               # 开发环境工具
  docker-compose.yml     # Docker 容器配置
docs/
  architecture.md        # 架构设计文档
  reference.md           # 参考资料
  BM25_procedure.md       # BM25 相关设计文档
config/
  settings/
    base.py              # 通用配置
    local.py             # 开发环境覆盖配置（DEBUG=True）
    production.py        # 生产环境配置
  urls.py                # 根 URL 配置
  celery.py              # Celery 应用配置
apps/
  accounts/              # 用户认证、注册、个人资料
    models.py
    serializers.py
    views.py
    services.py
  documents_parser/      # 文档解析和处理
    models.py
    serializers.py
    views.py
    services.py
    meta_management      # 用于维护文档元数据，如文档ID，文档名称，文档路径，文档创建时间，文档更新时间，文档大小，文档类型，文档状态等。
    parser
    deduplication        # 用于文档去重，避免重复上传同一文档
    tests/
  document_pipeline_manager/      # 文档处理流水线管理的管理器
    models.py
    serializers.py
    views.py
    services.py
    pipelines            # 文档处理流水线
    tests/
  milvus_database_controller/      # Milvus 数据库控制器，提供向量数据库的增删改查接口
    models.py
    serializers.py
    views.py
    services.py
    create_collection # 用于创建向量库，并设置向量库的参数，如向量维度，向量类型，向量索引类型，向量索引参数，向量索引数量等操作
    insert_data       # 用于向向量库插入数据，并返回插入数据的ID
    search_data       # 用于向向量库搜索数据，并返回搜索结果
    delete_data       # 用于向向量库删除数据，并返回删除数据的ID
    tests/
  neo4j_database_controller/      # Neo4j 数据库控制器，提供图数据库的增删改查接口
    models.py
    serializers.py
    views.py
    services.py
    create_node                   # 用于创建知识图谱节点，并返回创建节点的ID
    create_relationship           # 用于创建知识图谱关系，并返回创建关系的ID
    query_node                    # 用于查询知识图谱节点，并返回查询结果
    query_relationship            # 用于查询知识图谱关系，并返回查询结果
    delete_node                   # 用于删除知识图谱节点，并返回删除节点的ID
    delete_relationship           # 用于删除知识图谱关系，并返回删除关系的ID
    update_node                   # 用于更新知识图谱节点，并返回更新节点的ID
    update_relationship           # 用于更新知识图谱关系，并返回更新关系的ID
    tests/
  embedding_engine/
    models.pymodels.py
    serializers.py
    views.py
    services.py
    sentence_transformer          # 用于将文本转换为向量，并返回向量
    qwen_api                      # 千问的api封装
    embedding_management          # 用于管理向量，包括向量的创建，更新，删除，查询等操作。结合postgreSQL跟踪记录向量的元数据，如向量ID，向量名称，向量维度，向量类型，向量索引类型，向量索引参数，向量索引数量等，可以快速找到向量的元数据，以及向量库的更新。
    tests/
  RAGprocessing/
    models.py
    serializers.py
    views.py
    services.py
    rag_pipeline          # RAG 流水线，包括查询、向量搜索、上下文组装、LLM生成等步骤的实现
    agents/               # 基于langchain和langgraph封装的agent实现，如基于图RAG的agent，基于文本RAG的agent等
    tests/
  WebSocket manager/      # WebSocket 管理器，提供 WebSocket 连接管理、消息处理等功能
    consumers.py
    routing.py
    tests/
core/
  exceptions.py          # 自定义 API 异常
  permissions.py         # 共享权限类
  pagination.py          # 自定义分页
  middleware.py          # 请求日志、耗时统计
  tests/
tests/                   # 项目级测试（如集成测试、端到端测试等）
env/                     # 环境配置文件（如 .env.example）
  .env_local.env         # 本地环境变量配置文件
  .env_production.env    # 生产环境变量配置文件
  .env_uat.env           # 测试环境变量配置文件
pyproject.toml                   # Poetry 配置文件
README.md                        # 项目简介和快速开始指南
.env                             # 环境变量配置文件（不提交至 git）
.gitignore                       # Git 忽略文件
Manage.py                        # Django 管理命令入口
```

## code style and design patterns

- 请跟随`docs/code_style.md`中的代码规范进行编码


## 环境变量

- 请跟随`docs/environment_variables.md`中的环境变量进行配置
- 开发过程中用到的可以也添加到`docs/environment_variables.md`中进行补充
- 注意不同的开发环境要根据环境进行配置，例如：开发环境、测试环境、生产环境等，可以在`env/`目录下创建不同的环境变量配置文件，如`.env_local.env`、`.env_production.env`、`.env_uat.env`等，并在项目中根据环境加载对应的环境变量文件。


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

## ECC 工作流

```bash
# 需求规划
/plan "新增基于 Stripe 集成的订单退款系统"

# 测试驱动开发（TDD）
/tdd                    # 基于 pytest 的 TDD 工作流

# 代码评审
/python-review          # Python 专项代码评审
/security-scan          # Django 安全审计
/code-review            # 通用质量检查

# 验证环节
/verify                 # 构建、代码检查、测试、安全扫描
```

## Git 工作流

- 提交信息前缀规范：`feat:` 新功能，`fix:` 漏洞修复，`refactor:` 代码重构
- 基于 `main` 分支创建功能分支，合并需提交 PR
- 持续集成（CI）：ruff（代码检查 + 格式化）、mypy（类型校验）、pytest（单元测试）、safety（依赖安全检查）
- 部署方式：构建 Docker 镜像，通过 Kubernetes 或 Railway 管理

---

### 说明
1. 所有技术术语保留通用英文表述（如 DRF、ORM、JWT 等），仅对描述性文字做中文适配；
2. 代码片段中的变量名、类名、注释等未做翻译（保证代码可直接运行），仅对注释的语义做了中文优化；
3. 保持原文档的结构、格式和代码完整性，你可基于此中文版自由修改适配自身项目。