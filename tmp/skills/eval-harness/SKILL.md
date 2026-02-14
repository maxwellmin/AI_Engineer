---
name: eval-harness
description: Formal evaluation framework for Claude Code sessions implementing eval-driven development (EDD) principles
tools: Read, Write, Edit, Bash, Grep, Glob
---

# 评估框架 Skill

Claude Code 会话的正式评估框架，实现评估驱动开发（EDD）原则。

## 激活时机

- 为 AI 辅助工作流设置评估驱动开发（EDD）
- 定义 Claude Code 任务完成的通过/失败标准
- 使用 pass@k 指标衡量 Agent 可靠性
- 为提示词或 Agent 变更创建回归测试套件
- 跨模型版本对 Agent 性能进行基准测试

## 理念

评估驱动开发将评估视为"AI 开发的单元测试"：
- 在实现前定义预期行为
- 在开发过程中持续运行评估
- 每次变更都追踪回归
- 使用 pass@k 指标衡量可靠性

## 评估类型

### 能力评估
测试 Claude 是否能做以前做不到的事情：
```markdown
[CAPABILITY EVAL: feature-name]
Task: Claude 应该完成的任务描述
Success Criteria:
  - [ ] 标准 1
  - [ ] 标准 2
  - [ ] 标准 3
Expected Output: 预期结果描述
```

### 回归评估
确保变更不会破坏现有功能：
```markdown
[REGRESSION EVAL: feature-name]
Baseline: SHA 或检查点名称
Tests:
  - existing-test-1: PASS/FAIL
  - existing-test-2: PASS/FAIL
  - existing-test-3: PASS/FAIL
Result: X/Y 通过（之前是 Y/Y）
```

## 评分器类型

### 1. 基于代码的评分器
使用代码进行确定性检查：
```bash
# 检查文件是否包含预期模式
grep -q "export function handleAuth" src/auth.ts && echo "PASS" || echo "FAIL"

# 检查测试是否通过
npm test -- --testPathPattern="auth" && echo "PASS" || echo "FAIL"

# 检查构建是否成功
npm run build && echo "PASS" || echo "FAIL"
```

### 2. 基于模型的评分器
使用 Claude 评估开放式输出：
```markdown
[MODEL GRADER PROMPT]
评估以下代码变更：
1. 是否解决了所述问题？
2. 结构是否良好？
3. 边界情况是否处理？
4. 错误处理是否恰当？

Score: 1-5（1=差，5=优秀）
Reasoning: [解释]
```

### 3. 人工评分器
标记需要人工审查：
```markdown
[HUMAN REVIEW REQUIRED]
Change: 变更内容描述
Reason: 为什么需要人工审查
Risk Level: LOW/MEDIUM/HIGH
```

## 指标

### pass@k
"k 次尝试中至少一次成功"
- pass@1：首次尝试成功率
- pass@3：3 次尝试内成功
- 典型目标：pass@3 > 90%

### pass^k
"k 次试验全部成功"
- 更高的可靠性标准
- pass^3：连续 3 次成功
- 用于关键路径

## 评估工作流

### 1. 定义（编码前）
```markdown
## EVAL DEFINITION: feature-xyz

### 能力评估
1. 可以创建新用户账户
2. 可以验证邮箱格式
3. 可以安全地哈希密码

### 回归评估
1. 现有登录仍然可用
2. 会话管理不变
3. 登出流程完整

### 成功指标
- 能力评估 pass@3 > 90%
- 回归评估 pass^3 = 100%
```

### 2. 实现
编写代码以通过定义的评估。

### 3. 评估
```bash
# 运行能力评估
[运行每个能力评估，记录 PASS/FAIL]

# 运行回归评估
npm test -- --testPathPattern="existing"

# 生成报告
```

### 4. 报告
```markdown
EVAL REPORT: feature-xyz
========================

Capability Evals:
  create-user:     PASS (pass@1)
  validate-email:  PASS (pass@2)
  hash-password:   PASS (pass@1)
  Overall:         3/3 passed

Regression Evals:
  login-flow:      PASS
  session-mgmt:    PASS
  logout-flow:     PASS
  Overall:         3/3 passed

Metrics:
  pass@1: 67% (2/3)
  pass@3: 100% (3/3)

Status: READY FOR REVIEW
```

## 集成模式

### 实现前
```
/eval define feature-name
```
在 `.claude/evals/feature-name.md` 创建评估定义文件

### 实现过程中
```
/eval check feature-name
```
运行当前评估并报告状态

### 实现后
```
/eval report feature-name
```
生成完整评估报告

## 评估存储

在项目中存储评估：
```
.claude/
  evals/
    feature-xyz.md      # 评估定义
    feature-xyz.log     # 评估运行历史
    baseline.json       # 回归基线
```

## 最佳实践

1. **编码前定义评估** - 强制清晰思考成功标准
2. **频繁运行评估** - 及早发现回归
3. **随时间追踪 pass@k** - 监控可靠性趋势
4. **尽可能使用代码评分器** - 确定性优于概率性
5. **安全检查需要人工审查** - 永远不要完全自动化安全检查
6. **保持评估快速** - 慢的评估不会被运行
7. **评估与代码一起版本控制** - 评估是一等公民

## 示例：添加认证

```markdown
## EVAL: add-authentication

### Phase 1: 定义（10 分钟）
Capability Evals:
- [ ] 用户可以用邮箱/密码注册
- [ ] 用户可以用有效凭据登录
- [ ] 无效凭据被拒绝并返回正确错误
- [ ] 会话在页面刷新后保持
- [ ] 登出清除会话

Regression Evals:
- [ ] 公开路由仍可访问
- [ ] API 响应不变
- [ ] 数据库结构兼容

### Phase 2: 实现（不定）
[编写代码]

### Phase 3: 评估
运行: /eval check add-authentication

### Phase 4: 报告
EVAL REPORT: add-authentication
==============================
Capability: 5/5 passed (pass@3: 100%)
Regression: 3/3 passed (pass^3: 100%)
Status: SHIP IT
```
