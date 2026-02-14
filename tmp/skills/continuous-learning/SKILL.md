---
name: continuous-learning
description: Automatically extract reusable patterns from Claude Code sessions and save them as learned skills for future use.
---

# 持续学习技能

在会话结束时自动评估 Claude Code 会话，提取可复用的模式并保存为学习到的技能。

## 何时激活

- 设置从 Claude Code 会话自动提取模式
- 配置 Stop hook 进行会话评估
- 审查或管理 `~/.codebuddy/skills/learned/` 中学习到的技能
- 调整提取阈值或模式类别
- 比较 v1（本版本）与 v2（基于本能）的方法

## 工作原理

此技能作为 **Stop hook** 在每个会话结束时运行：

1. **会话评估**：检查会话是否有足够多的消息（默认：10+）
2. **模式检测**：从会话中识别可提取的模式
3. **技能提取**：将有用模式保存到 `~/.codebuddy/skills/learned/`

## 配置

编辑 `config.json` 进行自定义：

```json
{
  "min_session_length": 10,
  "extraction_threshold": "medium",
  "auto_approve": false,
  "learned_skills_path": "~/.codebuddy/skills/learned/",
  "patterns_to_detect": [
    "error_resolution",
    "user_corrections",
    "workarounds",
    "debugging_techniques",
    "project_specific"
  ],
  "ignore_patterns": [
    "simple_typos",
    "one_time_fixes",
    "external_api_issues"
  ]
}
```

## 模式类型

| 模式 | 描述 |
|---------|-------------|
| `error_resolution` | 特定错误如何被解决 |
| `user_corrections` | 来自用户纠正的模式 |
| `workarounds` | 框架/库特性的解决方案 |
| `debugging_techniques` | 有效的调试方法 |
| `project_specific` | 项目特定约定 |

## Hook 设置

添加到你的 `~/.codebuddy/settings.json`：

```json
{
  "hooks": {
    "Stop": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "~/.codebuddy/skills/continuous-learning/evaluate-session.sh"
      }]
    }]
  }
}
```

## 为什么使用 Stop Hook？

- **轻量级**：仅在会话结束时运行一次
- **非阻塞**：不会给每条消息增加延迟
- **完整上下文**：可访问完整的会话记录

## 相关资源

- [The Longform Guide](https://x.com/affaanmustafa/status/2014040193557471352) - 持续学习章节
- `/skill-learn` 命令 - 会话中手动提取模式

---

## 对比说明（研究：2025年1月）

### 与 Homunculus 对比 (github.com/humanplane/homunculus)

Homunculus v2 采用了更复杂的方法：

| 特性 | 我们的方法 | Homunculus v2 |
|---------|--------------|---------------|
| 观察 | Stop hook（会话结束时） | PreToolUse/PostToolUse hooks（100% 可靠） |
| 分析 | 主上下文 | 后台 agent (GLM-5.0-lite) |
| 粒度 | 完整技能 | 原子"本能" |
| 置信度 | 无 | 0.3-0.9 加权 |
| 演进 | 直接变为技能 | 本能 → 聚类 → 技能/命令/agent |
| 共享 | 无 | 导出/导入本能 |

**来自 homunculus 的关键洞察：**
> "v1 依赖技能来观察。技能是概率性的——它们大约 50-80% 的时间会触发。v2 使用 hooks 进行观察（100% 可靠），并将本能作为学习行为的基本单元。"

### 潜在的 v2 增强

1. **基于本能的学习** - 更小的原子行为，带置信度评分
2. **后台观察者** - GLM-5.0-lite agent 并行分析
3. **置信度衰减** - 如果被反驳，本能为置信度降低
4. **领域标签** - code-style、testing、git、debugging 等
5. **演进路径** - 将相关本能聚类为技能/命令
