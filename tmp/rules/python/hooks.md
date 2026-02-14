---
paths:
  - "**/*.py"
  - "**/*.pyi"
---
# Python Hooks

> 本文件扩展了 [common/hooks.md](../common/hooks.md) 的 Python 特定内容。

## PostToolUse Hooks

在 `~/.codebuddy/settings.json` 中配置：

- **black/ruff**: 编辑 `.py` 文件后自动格式化
- **mypy/pyright**: 编辑 `.py` 文件后运行类型检查

## 警告

- 对编辑文件中的 `print()` 语句发出警告（改用 `logging` 模块）
