---
name: verification-loop
description: "A comprehensive verification system for Claude Code sessions."
---

# 验证循环 Skill

Claude Code 会话的综合验证系统。

## 使用时机

在以下情况调用此 skill：
- 完成功能或重要代码变更后
- 创建 PR 前
- 想确保质量关卡通过
- 重构后

## 验证阶段

### 阶段 1：构建验证
```bash
# 检查项目是否构建成功
npm run build 2>&1 | tail -20
# 或
pnpm build 2>&1 | tail -20
```

如果构建失败，停止并修复后再继续。

### 阶段 2：类型检查
```bash
# TypeScript 项目
npx tsc --noEmit 2>&1 | head -30

# Python 项目
pyright . 2>&1 | head -30
```

报告所有类型错误。修复关键错误后再继续。

### 阶段 3：Lint 检查
```bash
# JavaScript/TypeScript
npm run lint 2>&1 | head -30

# Python
ruff check . 2>&1 | head -30
```

### 阶段 4：测试套件
```bash
# 运行测试并生成覆盖率
npm run test -- --coverage 2>&1 | tail -50

# 检查覆盖率阈值
# 目标：最低 80%
```

报告：
- 总测试数：X
- 通过：X
- 失败：X
- 覆盖率：X%

### 阶段 5：安全扫描
```bash
# 检查密钥
grep -rn "sk-" --include="*.ts" --include="*.js" . 2>/dev/null | head -10
grep -rn "api_key" --include="*.ts" --include="*.js" . 2>/dev/null | head -10

# 检查 console.log
grep -rn "console.log" --include="*.ts" --include="*.tsx" src/ 2>/dev/null | head -10
```

### 阶段 6：Diff 审查
```bash
# 显示变更内容
git diff --stat
git diff HEAD~1 --name-only
```

审查每个变更文件的：
- 非预期变更
- 缺失的错误处理
- 潜在的边界情况

## 输出格式

运行所有阶段后，生成验证报告：

```
VERIFICATION REPORT
==================

Build:     [PASS/FAIL]
Types:     [PASS/FAIL] (X errors)
Lint:      [PASS/FAIL] (X warnings)
Tests:     [PASS/FAIL] (X/Y passed, Z% coverage)
Security:  [PASS/FAIL] (X issues)
Diff:      [X files changed]

Overall:   [READY/NOT READY] for PR

Issues to Fix:
1. ...
2. ...
```

## 持续模式

对于长时间会话，每 15 分钟或在重大变更后运行验证：

```markdown
设置心理检查点：
- 完成每个函数后
- 完成组件后
- 进入下一个任务前

运行: /verify
```

## 与 Hooks 集成

此 skill 补充 PostToolUse hooks 但提供更深入的验证。
Hooks 立即捕获问题；此 skill 提供全面审查。
