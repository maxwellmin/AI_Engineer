# Skill 示例模板

## 说明

Skill 是可复用的技能模块，定义了特定任务的执行流程和参数。

## 文件命名规范

- 使用小写字母和下划线：`create_api_endpoint.md`
- 文件名应清晰表达 skill 的功能

---

# Create API Endpoint Skill

## 概述

创建符合项目规范的 Django REST Framework API 端点。

## 触发条件

- 用户请求创建新的 API 端点
- 用户请求添加 REST 接口
- 用户说 "创建 API" 或类似表述

## 执行步骤

### 1. 确认需求

询问用户：
- 所属 app 名称
- 端点功能描述
- 是否需要认证
- HTTP 方法（GET/POST/PUT/DELETE）

### 2. 检查项目结构

- 确认目标 app 是否存在
- 查看 models.py 了解数据模型
- 查看 serializers.py 了解现有序列化器

### 3. 创建视图

遵循项目 code_style.md 规范：
- 使用 DRF 的 GenericAPIView 或 ViewSet
- 显式指定 permission_classes
- 添加类型注解

### 4. 配置 URL

在 app 的 urls.py 中添加路由

### 5. 编写测试

创建对应的测试文件

## 模板

### views.py 模板

```python
from __future__ import annotations

import logging
from typing import Any

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class ExampleAPIView(GenericAPIView):
    """
    示例 API 视图。

    GET /api/v1/example/
    返回示例数据列表。
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ExampleSerializer

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """处理 GET 请求。"""
        logger.info(f"User {request.user.id} requested example data")
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
```

### urls.py 模板

```python
from django.urls import path

from .views import ExampleAPIView

urlpatterns = [
    path("example/", ExampleAPIView.as_view(), name="example-list"),
]
```

## 输出

完成后提供：
- 创建的文件列表
- API 端点 URL
- 测试命令示例

## 示例

```
输入: 创建一个获取用户文档列表的 API

执行:
1. 确认属于 documents_parser app
2. 检查 Document 模型
3. 创建 DocumentListView 视图
4. 添加 URL 路由
5. 创建测试文件

输出:
- apps/documents_parser/views.py (新增 DocumentListView)
- apps/documents_parser/urls.py (新增路由)
- apps/documents_parser/tests/test_views.py (新增测试)
- API: GET /api/v1/documents/
```

## 依赖

- 需要读取 docs/code_style.md 了解编码规范
- 需要检查 apps/ 目录了解项目结构
