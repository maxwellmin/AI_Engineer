---
name: security-scan
description: Scan your CodeBuddy Code configuration (~/.codebuddy/ directory) for security vulnerabilities, misconfigurations, and injection risks using AgentShield. Checks CODEBUDDY.md, settings.json, MCP servers, hooks, and agent definitions.
---

# 安全扫描技能

使用 [AgentShield](https://github.com/affaan-m/agentshield) 审计您的 CodeBuddy Code 配置中的安全问题。

## 何时激活

- 设置新的 CodeBuddy Code 项目
- 修改 `~/.codebuddy/settings.json`、`CODEBUDDY.md` 或 MCP 配置后
- 提交配置更改前
- 接入具有现有 CodeBuddy Code 配置的新仓库时
- 定期安全卫生检查

## 扫描内容

| 文件 | 检查项 |
|------|--------|
| `CODEBUDDY.md` | 硬编码密钥、自动运行指令、提示注入模式 |
| `settings.json` | 权限过宽的允许列表、缺少拒绝列表、危险绕过标志 |
| `mcp.json` | 风险 MCP 服务器、硬编码环境密钥、npx 供应链风险 |
| `hooks/` | 通过插值的命令注入、数据泄露、静默错误抑制 |
| `agents/*.md` | 不受限制的工具访问、提示注入面、缺少模型规格 |

## 先决条件

必须安装 AgentShield。检查并按需安装：

```bash
# 检查是否已安装
npx ecc-agentshield --version

# 全局安装（推荐）
npm install -g ecc-agentshield

# 或直接通过 npx 运行（无需安装）
npx ecc-agentshield scan .
```

## 使用方法

### 基本扫描

针对当前项目的 `~/.codebuddy/` 目录运行：

```bash
# 扫描当前项目
npx ecc-agentshield scan

# 扫描指定路径
npx ecc-agentshield scan --path /path/to/.codebuddy

# 使用最低严重级别过滤
npx ecc-agentshield scan --min-severity medium
```

### 输出格式

```bash
# 终端输出（默认）— 带评分的彩色报告
npx ecc-agentshield scan

# JSON — 用于 CI/CD 集成
npx ecc-agentshield scan --format json

# Markdown — 用于文档
npx ecc-agentshield scan --format markdown

# HTML — 自包含暗色主题报告
npx ecc-agentshield scan --format html > security-report.html
```

### 自动修复

自动应用安全修复（仅修复标记为可自动修复的项目）：

```bash
npx ecc-agentshield scan --fix
```

这将：
- 用环境变量引用替换硬编码密钥
- 将通配符权限收紧为限定范围的替代方案
- 永远不修改仅限手动处理建议

### GLM-5.0-reasoning 深度分析

运行对抗性三代理流水线进行更深入的分析：

```bash
# 需要 ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY=your-key
npx ecc-agentshield scan --opus --stream
```

这将运行：
1. **攻击者（红队）** — 发现攻击向量
2. **防御者（蓝队）** — 推荐加固措施
3. **审计者（最终裁决）** — 综合双方视角

### 初始化安全配置

从零开始搭建新的安全 `~/.codebuddy/` 配置：

```bash
npx ecc-agentshield init
```

创建：
- 带限定范围权限和拒绝列表的 `settings.json`
- 带安全最佳实践的 `CODEBUDDY.md`
- `mcp.json` 占位符

### GitHub Action

添加到您的 CI 流水线：

```yaml
- uses: affaan-m/agentshield@v1
  with:
    path: '.'
    min-severity: 'medium'
    fail-on-findings: true
```

## 严重级别

| 评级 | 分数 | 含义 |
|-------|-------|---------|
| A | 90-100 | 安全配置 |
| B | 75-89 | 轻微问题 |
| C | 60-74 | 需要关注 |
| D | 40-59 | 显著风险 |
| F | 0-39 | 严重漏洞 |

## 解读结果

### 严重发现（立即修复）
- 配置文件中的硬编码 API 密钥或令牌
- 允列表中的 `Bash(*)`（不受限制的 shell 访问）
- 通过 `${file}` 插值在 hooks 中的命令注入
- 运行 shell 的 MCP 服务器

### 高危发现（生产前修复）
- CODEBUDDY.md 中的自动运行指令（提示注入向量）
- 权限中缺少拒绝列表
- 具有不必要 Bash 访问权限的代理

### 中危发现（推荐）
- hooks 中的静默错误抑制（`2>/dev/null`、`|| true`）
- 缺少 PreToolUse 安全 hooks
- MCP 服务器配置中的 `npx -y` 自动安装

### 低危发现（了解即可）
- MCP 服务器缺少描述
- 正确标记为良好实践的禁止指令

## 链接

- **GitHub**: [github.com/affaan-m/agentshield](https://github.com/affaan-m/agentshield)
- **npm**: [npmjs.com/package/ecc-agentshield](https://www.npmjs.com/package/ecc-agentshield)
