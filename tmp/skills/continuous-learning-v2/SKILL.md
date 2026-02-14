---
name: continuous-learning-v2
description: Instinct-based learning system that observes sessions via hooks, creates atomic instincts with confidence scoring, and evolves them into skills/commands/agents.
version: 2.0.0
---

# 持续学习 v2 - 基于本能的架构

一个先进的学习系统，通过原子"本能"——带有置信度评分的小型学习行为——将你的 Claude Code 会话转化为可复用的知识。

## 何时激活

- 设置从 Claude Code 会话自动学习
- 通过 hooks 配置基于本能的行为提取
- 调整学习行为的置信度阈值
- 审查、导出或导入本能库
- 将本能演化为完整技能、命令或 agent

## v2 新特性

| 特性 | v1 | v2 |
|---------|----|----|
| 观察 | Stop hook（会话结束时） | PreToolUse/PostToolUse（100% 可靠） |
| 分析 | 主上下文 | 后台 agent (GLM-5.0-lite) |
| 粒度 | 完整技能 | 原子"本能" |
| 置信度 | 无 | 0.3-0.9 加权 |
| 演进 | 直接变为技能 | 本能 → 聚类 → 技能/命令/agent |
| 共享 | 无 | 导出/导入本能 |

## 本能模型

本能是一个小型学习行为：

```yaml
---
id: prefer-functional-style
trigger: "when writing new functions"
confidence: 0.7
domain: "code-style"
source: "session-observation"
---

# 偏好函数式风格

## 行动
在适当的情况下，优先使用函数式模式而非类。

## 证据
- 观察到 5 次偏好函数式模式的情况
- 用户在 2025-01-15 将基于类的方法纠正为函数式
```

**属性：**
- **原子性** — 一个触发器，一个行动
- **置信度加权** — 0.3 = 试探性，0.9 = 近乎确定
- **领域标签** — code-style、testing、git、debugging、workflow 等
- **证据支撑** — 追踪哪些观察创建了它

## 工作原理

```
会话活动
      │
      │ Hooks 捕获提示 + 工具使用（100% 可靠）
      ▼
┌─────────────────────────────────────────┐
│         observations.jsonl              │
│   （提示、工具调用、结果）               │
└─────────────────────────────────────────┘
      │
      │ 观察者 agent 读取（后台，GLM-5.0-lite）
      ▼
┌─────────────────────────────────────────┐
│            模式检测                      │
│   • 用户纠正 → 本能                      │
│   • 错误解决 → 本能                      │
│   • 重复工作流 → 本能                    │
└─────────────────────────────────────────┘
      │
      │ 创建/更新
      ▼
┌─────────────────────────────────────────┐
│         instincts/personal/             │
│   • prefer-functional.md (0.7)          │
│   • always-test-first.md (0.9)          │
│   • use-zod-validation.md (0.6)         │
└─────────────────────────────────────────┘
      │
      │ /skill-evolve 聚类
      ▼
┌─────────────────────────────────────────┐
│              evolved/                   │
│   • commands/new-feature.md             │
│   • skills/testing-workflow.md          │
│   • agents/refactor-specialist.md       │
└─────────────────────────────────────────┘
```

## 快速开始

### 1. 启用观察 Hooks

添加到你的 `~/.codebuddy/settings.json`。

**作为插件安装**（推荐）：

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "${CODEBUDDY_PLUGIN_ROOT}/skills/continuous-learning-v2/hooks/observe.sh pre"
      }]
    }],
    "PostToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "${CODEBUDDY_PLUGIN_ROOT}/skills/continuous-learning-v2/hooks/observe.sh post"
      }]
    }]
  }
}
```

**手动安装**到 `~/.codebuddy/skills`：

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "~/.codebuddy/skills/continuous-learning-v2/hooks/observe.sh pre"
      }]
    }],
    "PostToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "~/.codebuddy/skills/continuous-learning-v2/hooks/observe.sh post"
      }]
    }]
  }
}
```

### 2. 初始化目录结构

Python CLI 会自动创建这些目录，但你也可以手动创建：

```bash
mkdir -p ~/.codebuddy/homunculus/{instincts/{personal,inherited},evolved/{agents,skills,commands}}
touch ~/.codebuddy/homunculus/observations.jsonl
```

### 3. 使用本能命令

```bash
/skill-instinct-status     # 显示学习到的本能及其置信度分数
/skill-evolve              # 将相关本能聚类为技能/命令
/skill-instinct-export     # 导出本能用于分享
/skill-instinct-import     # 从他人导入本能
```

## 命令

| 命令 | 描述 |
|---------|-------------|
| `/skill-instinct-status` | 显示所有学习到的本能及其置信度 |
| `/skill-evolve` | 将相关本能聚类为技能/命令 |
| `/skill-instinct-export` | 导出本能用于分享 |
| `/skill-instinct-import <file>` | 从他人导入本能 |

## 配置

编辑 `config.json`：

```json
{
  "version": "2.0",
  "observation": {
    "enabled": true,
    "store_path": "~/.codebuddy/homunculus/observations.jsonl",
    "max_file_size_mb": 10,
    "archive_after_days": 7
  },
  "instincts": {
    "personal_path": "~/.codebuddy/homunculus/instincts/personal/",
    "inherited_path": "~/.codebuddy/homunculus/instincts/inherited/",
    "min_confidence": 0.3,
    "auto_approve_threshold": 0.7,
    "confidence_decay_rate": 0.05
  },
  "observer": {
    "enabled": true,
    "model": "lite",
    "run_interval_minutes": 5,
    "patterns_to_detect": [
      "user_corrections",
      "error_resolutions",
      "repeated_workflows",
      "tool_preferences"
    ]
  },
  "evolution": {
    "cluster_threshold": 3,
    "evolved_path": "~/.codebuddy/homunculus/evolved/"
  }
}
```

## 文件结构

```
~/.codebuddy/homunculus/
├── identity.json           # 你的个人资料、技术水平
├── observations.jsonl      # 当前会话观察
├── observations.archive/   # 已处理的观察
├── instincts/
│   ├── personal/           # 自动学习的本能
│   └── inherited/          # 从他人导入的
└── evolved/
    ├── agents/             # 生成的专业 agent
    ├── skills/             # 生成的技能
    └── commands/           # 生成的命令
```

## 与 Skill Creator 集成

当你使用 [Skill Creator GitHub App](https://skill-creator.app) 时，它现在会生成**两种**：
- 传统 SKILL.md 文件（用于向后兼容）
- 本能集合（用于 v2 学习系统）

来自仓库分析的本能有 `source: "repo-analysis"`，并包含源仓库 URL。

## 置信度评分

置信度随时间演变：

| 分数 | 含义 | 行为 |
|-------|---------|----------|
| 0.3 | 试探性 | 建议但不强制执行 |
| 0.5 | 中等 | 相关时应用 |
| 0.7 | 强 | 自动批准应用 |
| 0.9 | 近乎确定 | 核心行为 |

**置信度增加**当：
- 模式被反复观察
- 用户没有纠正建议的行为
- 来自其他来源的类似本能达成一致

**置信度降低**当：
- 用户明确纠正该行为
- 长期未观察到该模式
- 出现矛盾证据

## 为什么用 Hooks 而非技能来观察？

> "v1 依赖技能来观察。技能是概率性的——根据 Claude 的判断，它们大约 50-80% 的时间会触发。"

Hooks **100% 的时间**都会触发，是确定性的。这意味着：
- 每个工具调用都被观察
- 不会遗漏任何模式
- 学习是全面的

## 向后兼容

v2 完全兼容 v1：
- 现有 `~/.codebuddy/skills/learned/` 技能仍然有效
- Stop hook 仍会运行（但现在也会输入到 v2）
- 渐进式迁移路径：可并行运行两者

## 隐私

- 观察数据**保留在本地**你的机器上
- 只有**本能**（模式）可以被导出
- 不共享实际的代码或对话内容
- 你控制什么被导出

## 相关资源

- [Skill Creator](https://skill-creator.app) - 从仓库历史生成本能
- [Homunculus](https://github.com/humanplane/homunculus) - v2 架构的灵感来源
- [The Longform Guide](https://x.com/affaanmustafa/status/2014040193557471352) - 持续学习章节

---

*基于本能的学习：一次一个观察，教会 Claude 你的模式。*
