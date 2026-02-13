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
- 严格控制函数长度和复杂度 — 函数应保持单一职责，避免过长或过于复杂的函数实现。行数建议<40行，复杂度建议<10（由 ruff 强制校验）


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