---
name: strategic-compact
description: Suggests manual context compaction at logical intervals to preserve context through task phases rather than arbitrary auto-compaction.
---

# 战略压缩 Skill

在工作流的战略点建议手动 `/compact`，而非依赖任意的自动压缩。

## 激活时机

- 运行接近上下文限制的长会话（200K+ tokens）
- 处理多阶段任务（研究 → 规划 → 实现 → 测试）
- 在同一会话中切换不相关任务
- 完成主要里程碑后开始新工作
- 当响应变慢或不够连贯时（上下文压力）

## 为什么战略压缩？

自动压缩在任意点触发：
- 经常在任务中间，丢失重要上下文
- 不感知逻辑任务边界
- 可能中断复杂的多步操作

在逻辑边界的战略压缩：
- **探索后、执行前** — 压缩研究上下文，保留实现计划
- **完成里程碑后** — 为下一阶段重新开始
- **重大上下文切换前** — 在切换到不同任务前清理探索上下文

## 工作原理

`suggest-compact.js` 脚本在 PreToolUse（Edit/Write）时运行：

1. **追踪工具调用** — 统计会话中的工具调用次数
2. **阈值检测** — 在可配置阈值（默认：50 次调用）时建议
3. **周期性提醒** — 阈值后每 25 次调用提醒一次

## Hook 设置

添加到您的 `~/.codebuddy/settings.json`：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit",
        "hooks": [{ "type": "command", "command": "node ~/.codebuddy/skills/strategic-compact/suggest-compact.js" }]
      },
      {
        "matcher": "Write",
        "hooks": [{ "type": "command", "command": "node ~/.codebuddy/skills/strategic-compact/suggest-compact.js" }]
      }
    ]
  }
}
```

## 配置

环境变量：
- `COMPACT_THRESHOLD` — 首次建议前的工具调用次数（默认：50）

## 压缩决策指南

使用此表决定何时压缩：

| 阶段转换 | 压缩？ | 原因 |
|---------|--------|------|
| 研究 → 规划 | 是 | 研究上下文庞大；计划是提炼后的输出 |
| 规划 → 实现 | 是 | 计划在 TodoWrite 或文件中；释放上下文用于代码 |
| 实现 → 测试 | 可能 | 如果测试引用最近代码则保留；切换焦点则压缩 |
| 调试 → 下一功能 | 是 | 调试痕迹会污染不相关工作的上下文 |
| 实现过程中 | 否 | 丢失变量名、文件路径和部分状态代价很高 |
| 失败方法后 | 是 | 在尝试新方法前清理死胡同推理 |

## 什么能在压缩后保留

理解什么会持久化有助于放心压缩：

| 保留 | 丢失 |
|------|------|
| CLAUDE.md 指令 | 中间推理和分析 |
| TodoWrite 任务列表 | 之前读取的文件内容 |
| 内存文件（`~/.codebuddy/memory/`） | 多轮对话上下文 |
| Git 状态（提交、分支） | 工具调用历史和计数 |
| 磁盘上的文件 | 口头表达的细致用户偏好 |

## 最佳实践

1. **规划后压缩** — 计划在 TodoWrite 中确定后，压缩以重新开始
2. **调试后压缩** — 在继续前清理错误解决上下文
3. **不要在实现过程中压缩** — 为相关变更保留上下文
4. **阅读建议** — Hook 告诉你*何时*，你决定*是否*
5. **压缩前写入** — 在压缩前将重要上下文保存到文件或内存
6. **带摘要使用 `/compact`** — 添加自定义消息：`/compact 接下来专注于实现认证中间件`

## 相关资源

- [The Longform Guide](https://x.com/affaanmustafa/status/2014040193557471352) — Token 优化部分
- 内存持久化 hooks — 用于在压缩后保留的状态
- `continuous-learning` skill — 在会话结束前提取模式
