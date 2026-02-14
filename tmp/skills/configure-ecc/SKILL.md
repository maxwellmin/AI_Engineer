---
name: configure-ecc
description: Interactive installer for Everything Claude Code — guides users through selecting and installing skills and rules to user-level or project-level directories, verifies paths, and optionally optimizes installed files.
---

# 配置 Everything Claude Code (ECC)

Everything Claude Code 项目的交互式分步安装向导。使用 `AskUserQuestion` 引导用户选择性安装 skills 和 rules，然后验证正确性并提供优化选项。

## 激活时机

- 用户说 "configure ecc"、"install ecc"、"setup everything claude code" 或类似表述
- 用户想选择性安装此项目的 skills 或 rules
- 用户想验证或修复现有的 ECC 安装
- 用户想为其项目优化已安装的 skills 或 rules

## 前置条件

此 skill 必须在激活前对 Claude Code 可用。两种引导方式：
1. **通过插件**：`/plugin install everything-claude-code` — 插件会自动加载此 skill
2. **手动**：仅复制此 skill 到 `~/.codebuddy/skills/configure-ecc/SKILL.md`，然后说 "configure ecc" 激活

---

## 步骤 0：克隆 ECC 仓库

安装前，将最新 ECC 源码克隆到 `/tmp`：

```bash
rm -rf /tmp/everything-claude-code
git clone https://github.com/affaan-m/everything-claude-code.git /tmp/everything-claude-code
```

将 `ECC_ROOT=/tmp/everything-claude-code` 设为后续所有复制操作的源目录。

如果克隆失败（网络问题等），使用 `AskUserQuestion` 请求用户提供现有 ECC 克隆的本地路径。

---

## 步骤 1：选择安装级别

使用 `AskUserQuestion` 询问用户安装位置：

```
Question: "ECC 组件应该安装到哪里？"
Options:
  - "用户级 (~/.codebuddy/)" — "应用于所有 Claude Code 项目"
  - "项目级 (.codebuddy/)" — "仅应用于当前项目"
  - "两者" — "通用/共享项安装到用户级，项目专用项安装到项目级"
```

将选择存储为 `INSTALL_LEVEL`。设置目标目录：
- 用户级：`TARGET=~/.codebuddy`
- 项目级：`TARGET=.codebuddy`（相对于当前项目根目录）
- 两者：`TARGET_USER=~/.codebuddy`、`TARGET_PROJECT=.codebuddy`

如果目标目录不存在则创建：
```bash
mkdir -p $TARGET/skills $TARGET/rules
```

---

## 步骤 2：选择并安装 Skills

### 2a：选择 Skill 分类

共有 27 个 skills 分为 4 类。使用 `AskUserQuestion` 并设置 `multiSelect: true`：

```
Question: "要安装哪些 skill 分类？"
Options:
  - "框架与语言" — "Django、Spring Boot、Go、Python、Java、前端、后端模式"
  - "数据库" — "PostgreSQL、ClickHouse、JPA/Hibernate 模式"
  - "工作流与质量" — "TDD、验证、学习、安全审查、压缩"
  - "所有 skills" — "安装所有可用的 skills"
```

### 2b：确认具体 Skills

对于每个选中的分类，打印完整 skill 列表并让用户确认或取消选择特定项。如果列表超过 4 项，以文本形式打印列表，使用 `AskUserQuestion` 提供"安装所有列出的"选项，外加"其他"让用户粘贴具体名称。

**分类：框架与语言（16 个 skills）**

| Skill | 描述 |
|-------|------|
| `backend-patterns` | 后端架构、API 设计、Node.js/Express/Next.js 服务端最佳实践 |
| `coding-standards` | TypeScript、JavaScript、React、Node.js 的通用编码标准 |
| `django-patterns` | Django 架构、DRF REST API、ORM、缓存、信号、中间件 |
| `django-security` | Django 安全：认证、CSRF、SQL 注入、XSS 防护 |
| `django-tdd` | Django 测试：pytest-django、factory_boy、mocking、覆盖率 |
| `django-verification` | Django 验证循环：迁移、linting、测试、安全扫描 |
| `frontend-patterns` | React、Next.js、状态管理、性能、UI 模式 |
| `golang-patterns` | 惯用 Go 模式、健壮 Go 应用的约定 |
| `golang-testing` | Go 测试：表驱动测试、子测试、基准测试、模糊测试 |
| `java-coding-standards` | Spring Boot 的 Java 编码标准：命名、不可变性、Optional、流 |
| `python-patterns` | Python 惯用法、PEP 8、类型提示、最佳实践 |
| `python-testing` | Python 测试：pytest、TDD、fixtures、mocking、参数化 |
| `springboot-patterns` | Spring Boot 架构、REST API、分层服务、缓存、异步 |
| `springboot-security` | Spring Security：认证/授权、验证、CSRF、密钥、限流 |
| `springboot-tdd` | Spring Boot TDD：JUnit 5、Mockito、MockMvc、Testcontainers |
| `springboot-verification` | Spring Boot 验证：构建、静态分析、测试、安全扫描 |

**分类：数据库（3 个 skills）**

| Skill | 描述 |
|-------|------|
| `clickhouse-io` | ClickHouse 模式、查询优化、分析、数据工程 |
| `jpa-patterns` | JPA/Hibernate 实体设计、关系、查询优化、事务 |
| `postgres-patterns` | PostgreSQL 查询优化、结构设计、索引、安全 |

**分类：工作流与质量（8 个 skills）**

| Skill | 描述 |
|-------|------|
| `continuous-learning` | 从会话中自动提取可复用模式作为学习的 skills |
| `continuous-learning-v2` | 基于直觉的学习，带置信度评分，演化为 skills/commands/agents |
| `eval-harness` | 评估驱动开发（EDD）的正式评估框架 |
| `iterative-retrieval` | 子 Agent 上下文问题的渐进式上下文精化 |
| `security-review` | 安全检查清单：认证、输入、密钥、API、支付功能 |
| `strategic-compact` | 在逻辑间隔建议手动上下文压缩 |
| `tdd-workflow` | 强制 80%+ 覆盖率的 TDD：单元、集成、E2E |
| `verification-loop` | 验证和质量循环模式 |

**独立**

| Skill | 描述 |
|-------|------|
| `project-guidelines-example` | 创建项目专用 skills 的模板 |

### 2c：执行安装

对于每个选中的 skill，复制整个 skill 目录：
```bash
cp -r $ECC_ROOT/skills/<skill-name> $TARGET/skills/
```

注意：`continuous-learning` 和 `continuous-learning-v2` 有额外文件（config.json、hooks、scripts）— 确保复制整个目录，不仅仅是 SKILL.md。

---

## 步骤 3：选择并安装 Rules

使用 `AskUserQuestion` 并设置 `multiSelect: true`：

```
Question: "要安装哪些规则集？"
Options:
  - "通用规则（推荐）" — "语言无关原则：编码风格、git 工作流、测试、安全等（8 个文件）"
  - "TypeScript/JavaScript" — "TS/JS 模式、hooks、Playwright 测试（5 个文件）"
  - "Python" — "Python 模式、pytest、black/ruff 格式化（5 个文件）"
  - "Go" — "Go 模式、表驱动测试、gofmt/staticcheck（5 个文件）"
```

执行安装：
```bash
# 通用规则（平铺复制到 rules/）
cp -r $ECC_ROOT/rules/common/* $TARGET/rules/

# 语言特定规则（平铺复制到 rules/）
cp -r $ECC_ROOT/rules/typescript/* $TARGET/rules/   # 如已选择
cp -r $ECC_ROOT/rules/python/* $TARGET/rules/        # 如已选择
cp -r $ECC_ROOT/rules/golang/* $TARGET/rules/        # 如已选择
```

**重要**：如果用户选择了任何语言特定规则但未选择通用规则，警告用户：
> "语言特定规则是对通用规则的扩展。不安装通用规则可能导致覆盖不完整。是否也安装通用规则？"

---

## 步骤 4：安装后验证

安装后，执行这些自动检查：

### 4a：验证文件存在

列出所有已安装文件并确认它们存在于目标位置：
```bash
ls -la $TARGET/skills/
ls -la $TARGET/rules/
```

### 4b：检查路径引用

扫描所有已安装的 `.md` 文件中的路径引用：
```bash
grep -rn "~/.codebuddy/" $TARGET/skills/ $TARGET/rules/
grep -rn "../common/" $TARGET/rules/
grep -rn "skills/" $TARGET/skills/
```

**对于项目级安装**，标记任何对 `~/.codebuddy/` 路径的引用：
- 如果 skill 引用 `~/.codebuddy/settings.json` — 通常没问题（设置始终是用户级的）
- 如果 skill 引用 `~/.codebuddy/skills/` 或 `~/.codebuddy/rules/` — 如果仅安装在项目级可能有问题
- 如果 skill 按名称引用另一个 skill — 检查被引用的 skill 是否也已安装

### 4c：检查 Skills 之间的交叉引用

某些 skills 引用其他 skills。验证这些依赖：
- `django-tdd` 可能引用 `django-patterns`
- `springboot-tdd` 可能引用 `springboot-patterns`
- `continuous-learning-v2` 引用 `~/.codebuddy/homunculus/` 目录
- `python-testing` 可能引用 `python-patterns`
- `golang-testing` 可能引用 `golang-patterns`
- 语言特定规则引用 `common/` 对应文件

### 4d：报告问题

对于发现的每个问题，报告：
1. **文件**：包含问题引用的文件
2. **行号**：行号
3. **问题**：问题所在（如"引用 ~/.codebuddy/skills/python-patterns 但 python-patterns 未安装"）
4. **建议修复**：应如何处理（如"安装 python-patterns skill"或"更新路径为 .codebuddy/skills/"）

---

## 步骤 5：优化已安装文件（可选）

使用 `AskUserQuestion`：

```
Question: "是否要为您的项目优化已安装的文件？"
Options:
  - "优化 skills" — "移除无关章节、调整路径、针对技术栈定制"
  - "优化 rules" — "调整覆盖率目标、添加项目特定模式、自定义工具配置"
  - "两者都优化" — "对所有已安装文件进行完整优化"
  - "跳过" — "保持所有内容原样"
```

### 如果优化 skills：
1. 读取每个已安装的 SKILL.md
2. 询问用户其项目的技术栈（如果尚不清楚）
3. 对于每个 skill，建议移除无关章节
4. 在安装目标就地编辑 SKILL.md 文件（不是源仓库）
5. 修复步骤 4 中发现的任何路径问题

### 如果优化 rules：
1. 读取每个已安装的 rule .md 文件
2. 询问用户的偏好：
   - 测试覆盖率目标（默认 80%）
   - 首选格式化工具
   - Git 工作流约定
   - 安全要求
3. 在安装目标就地编辑 rule 文件

**关键**：仅修改安装目标中的文件（`$TARGET/`），永远不要修改源 ECC 仓库中的文件（`$ECC_ROOT/`）。

---

## 步骤 6：安装摘要

清理 `/tmp` 中克隆的仓库：

```bash
rm -rf /tmp/everything-claude-code
```

然后打印摘要报告：

```
## ECC 安装完成

### 安装目标
- 级别：[用户级 / 项目级 / 两者]
- 路径：[目标路径]

### 已安装 Skills ([数量])
- skill-1, skill-2, skill-3, ...

### 已安装 Rules ([数量])
- common (8 个文件)
- typescript (5 个文件)
- ...

### 验证结果
- 发现 [数量] 个问题，已修复 [数量] 个
- [列出任何剩余问题]

### 已应用的优化
- [列出所做的更改，或"无"]
```

---

## 故障排除

### "Skills 未被 Claude Code 识别"
- 验证 skill 目录包含 `SKILL.md` 文件（不仅仅是散落的 .md 文件）
- 用户级：检查 `~/.codebuddy/skills/<skill-name>/SKILL.md` 是否存在
- 项目级：检查 `.codebuddy/skills/<skill-name>/SKILL.md` 是否存在

### "Rules 不生效"
- Rules 是平铺文件，不在子目录中：`$TARGET/rules/coding-style.md`（正确）vs `$TARGET/rules/common/coding-style.md`（平铺安装时错误）
- 安装 rules 后重启 Claude Code

### "项目级安装后路径引用错误"
- 某些 skills 假定 `~/.codebuddy/` 路径。运行步骤 4 验证来发现和修复这些问题。
- 对于 `continuous-learning-v2`，`~/.codebuddy/homunculus/` 目录始终是用户级的 — 这是预期行为，不是错误。
