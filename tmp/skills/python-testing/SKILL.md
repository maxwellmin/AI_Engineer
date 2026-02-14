---
name: python-testing
description: 使用 pytest 进行 Python 测试，包括 fixtures、参数化、mocking 和覆盖率最佳实践。
---

# Python 测试

使用 pytest 作为测试框架的 Python 特定测试内容。

> 本文件扩展了 [common/testing.md](../common/testing.md) 的 Python 特定内容。

## 框架

使用 **pytest** 作为测试框架。

## 覆盖率

```bash
pytest --cov=src --cov-report=term-missing
```

## 测试组织

使用 `pytest.mark` 进行测试分类：

```python
import pytest

@pytest.mark.unit
def test_calculate_total():
    ...

@pytest.mark.integration
def test_database_connection():
    ...
```

## 参考

参考 skill: `python-testing` 了解详细的 pytest 模式和 fixture。
