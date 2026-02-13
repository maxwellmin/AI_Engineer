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
- **开发用基础设施信息**: ./dev_utils/* docker-compose.yml README.md
- **开发环境基础设施操作**： 尽量人工自行操作，意见系统组件和端口冲突，claude console操作尽量和人工确认



**架构：** 领域驱动设计（按业务领域划分应用）。API 层基于 DRF 实现，异步任务基于 Celery 实现，测试基于 pytest 实现。所有接口均返回 JSON 格式数据——不涉及模板渲染。

## 核心规范

### Python 编码约定

- 所有函数签名必须添加类型注解 — 需引入 `from __future__ import annotations`
- 禁止使用 `print()` 语句 — 统一使用 `logging.getLogger(__name__)` 记录日志
- 字符串格式化使用 f-string，禁止使用 `%` 或 `.format()`
- 文件操作使用 `pathlib.Path`，禁止使用 `os.path`
- 导入语句按 isort 规则排序：标准库 → 第三方库 → 本地模块（由 ruff 强制校验）

### 数据库规范

- 所有数据库查询使用 Django ORM — 仅在必要时通过 `.raw()` 使用参数化查询的原生 SQL
- 数据库迁移文件需提交至 git — 生产环境禁止使用 `--fake` 参数
- 使用 `select_related()` 和 `prefetch_related()` 避免 N+1 查询问题
- 所有模型必须包含 `created_at` 和 `updated_at` 自动字段
- 所有用于 `filter()`、`order_by()` 或 `WHERE` 子句的字段需添加索引

```python
# 不良示例：N+1 查询
orders = Order.objects.all()
for order in orders:
    print(order.customer.name)  # 每个订单都会触发一次数据库查询

# 良好示例：关联查询（仅一次数据库请求）
orders = Order.objects.select_related("customer").all()
```

### 认证规范

- 基于 `djangorestframework-simplejwt` 实现 JWT 认证 — 访问令牌（15 分钟）+ 刷新令牌（7 天）
- 所有视图必须显式指定权限类 — 禁止依赖默认权限配置
- 基础权限使用 `IsAuthenticated`，对象级别的访问控制需自定义权限类
- 登出功能需启用令牌黑名单机制

### 序列化器规范

- 简单 CRUD 操作使用 `ModelSerializer`，复杂校验场景使用 `Serializer`
- 输入/输出数据结构不同时，拆分读/写序列化器
- 校验逻辑放在序列化器层实现，视图层保持轻量

```python
class CreateOrderSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=100)

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value, active=True).exists():
            raise serializers.ValidationError("商品不存在或已下架")
        return value

class OrderDetailSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    product = ProductSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "customer", "product", "quantity", "total", "status", "created_at"]
```

### 异常处理规范

- 使用 DRF 异常处理器保证错误响应格式统一
- 业务逻辑相关的自定义异常放在 `core/exceptions.py` 中
- 禁止向客户端暴露内部错误详情

```python
# core/exceptions.py
from rest_framework.exceptions import APIException

class InsufficientStockError(APIException):
    status_code = 409
    default_detail = "库存不足，无法创建订单"
    default_code = "insufficient_stock"
```

### 代码风格规范

- 代码和注释中禁止使用表情符号
- 最大行长度：120 个字符（由 ruff 强制校验）
- 命名规范：类使用 PascalCase，函数/变量使用 snake_case，常量使用 UPPER_SNAKE_CASE
- 视图层保持轻量 — 业务逻辑放在服务函数或模型方法中

## 文件结构

```
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
    services.py          # 业务逻辑层
    tests/
      test_views.py
      test_services.py
      factories.py       # Factory Boy 工厂类
  orders/                # 订单管理
    models.py
    serializers.py
    views.py
    services.py
    tasks.py             # Celery 异步任务
    tests/
  products/              # 商品目录
    models.py
    serializers.py
    views.py
    tests/
core/
  exceptions.py          # 自定义 API 异常
  permissions.py         # 共享权限类
  pagination.py          # 自定义分页
  middleware.py          # 请求日志、耗时统计
  tests/
```

## 核心设计模式

### 服务层模式

```python
# apps/orders/services.py
from django.db import transaction

def create_order(*, customer, product_id: uuid.UUID, quantity: int) -> Order:
    """创建订单（包含库存校验和支付预扣逻辑）。"""
    product = Product.objects.select_for_update().get(id=product_id)

    if product.stock < quantity:
        raise InsufficientStockError()

    with transaction.atomic():
        order = Order.objects.create(
            customer=customer,
            product=product,
            quantity=quantity,
            total=product.price * quantity,
        )
        product.stock -= quantity
        product.save(update_fields=["stock", "updated_at"])

    # 异步任务：发送订单确认邮件
    send_order_confirmation.delay(order.id)
    return order
```

### 视图层模式

```python
# apps/orders/views.py
class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if self.action == "create":
            return CreateOrderSerializer
        return OrderDetailSerializer

    def get_queryset(self):
        return (
            Order.objects
            .filter(customer=self.request.user)
            .select_related("product", "customer")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        order = create_order(
            customer=self.request.user,
            product_id=serializer.validated_data["product_id"],
            quantity=serializer.validated_data["quantity"],
        )
        serializer.instance = order
```

### 测试模式（pytest + Factory Boy）

```python
# apps/orders/tests/factories.py
import factory
from apps.accounts.tests.factories import UserFactory
from apps.products.tests.factories import ProductFactory

class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "orders.Order"

    customer = factory.SubFactory(UserFactory)
    product = factory.SubFactory(ProductFactory, stock=100)
    quantity = 1
    total = factory.LazyAttribute(lambda o: o.product.price * o.quantity)

# apps/orders/tests/test_views.py
import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
class TestCreateOrder:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(self.user)

    def test_create_order_success(self):
        product = ProductFactory(price=29_99, stock=10)
        response = self.client.post("/api/orders/", {
            "product_id": str(product.id),
            "quantity": 2,
        })
        assert response.status_code == 201
        assert response.data["total"] == 59_98

    def test_create_order_insufficient_stock(self):
        product = ProductFactory(stock=0)
        response = self.client.post("/api/orders/", {
            "product_id": str(product.id),
            "quantity": 1,
        })
        assert response.status_code == 409

    def test_create_order_unauthenticated(self):
        self.client.force_authenticate(None)
        response = self.client.post("/api/orders/", {})
        assert response.status_code == 401
```

## 环境变量

```bash
# Django 核心配置
SECRET_KEY=          # 密钥
DEBUG=False          # 调试模式
ALLOWED_HOSTS=api.example.com  # 允许的主机

# 数据库配置
DATABASE_URL=postgres://user:pass@localhost:5432/myapp

# Redis（Celery 消息队列 + 缓存）
REDIS_URL=redis://localhost:6379/0

# JWT 配置
JWT_ACCESS_TOKEN_LIFETIME=15       # 访问令牌有效期（分钟）
JWT_REFRESH_TOKEN_LIFETIME=10080   # 刷新令牌有效期（分钟，7 天）

# 邮件配置
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
```

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