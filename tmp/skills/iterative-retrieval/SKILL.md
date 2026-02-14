---
name: iterative-retrieval
description: Pattern for progressively refining context retrieval to solve the subagent context problem
---

# 迭代检索模式

解决多 Agent 工作流中的"上下文问题"，即子 Agent 在开始工作前不知道需要什么上下文。

## 激活时机

- 启动需要代码库上下文但无法预先确定的子 Agent
- 构建上下文逐步精化的多 Agent 工作流
- 遇到"上下文过大"或"缺少上下文"的 Agent 任务失败
- 设计类似 RAG 的代码探索检索流水线
- 优化 Agent 编排中的 token 使用

## 问题

子 Agent 启动时上下文有限，它们不知道：
- 哪些文件包含相关代码
- 代码库中存在哪些模式
- 项目使用什么术语

标准方法会失败：
- **发送所有内容**：超出上下文限制
- **什么都不发送**：Agent 缺少关键信息
- **猜测需要什么**：经常猜错

## 解决方案：迭代检索

一个 4 阶段循环，逐步精化上下文：

```
┌─────────────────────────────────────────────┐
│                                             │
│   ┌──────────┐      ┌──────────┐            │
│   │  分发    │─────▶│  评估    │            │
│   └──────────┘      └──────────┘            │
│        ▲                  │                 │
│        │                  ▼                 │
│   ┌──────────┐      ┌──────────┐            │
│   │   循环   │◀─────│  精化    │            │
│   └──────────┘      └──────────┘            │
│                                             │
│        最多 3 轮，然后继续                    │
└─────────────────────────────────────────────┘
```

### 阶段 1：分发（DISPATCH）

初始广泛查询以收集候选文件：

```javascript
// 从高层意图开始
const initialQuery = {
  patterns: ['src/**/*.ts', 'lib/**/*.ts'],
  keywords: ['authentication', 'user', 'session'],
  excludes: ['*.test.ts', '*.spec.ts']
};

// 分发给检索 Agent
const candidates = await retrieveFiles(initialQuery);
```

### 阶段 2：评估（EVALUATE）

评估检索内容的相关性：

```javascript
function evaluateRelevance(files, task) {
  return files.map(file => ({
    path: file.path,
    relevance: scoreRelevance(file.content, task),
    reason: explainRelevance(file.content, task),
    missingContext: identifyGaps(file.content, task)
  }));
}
```

评分标准：
- **高 (0.8-1.0)**：直接实现目标功能
- **中 (0.5-0.7)**：包含相关模式或类型
- **低 (0.2-0.4)**：有一定关联
- **无 (0-0.2)**：不相关，排除

### 阶段 3：精化（REFINE）

根据评估更新搜索条件：

```javascript
function refineQuery(evaluation, previousQuery) {
  return {
    // 添加在高相关性文件中发现的新模式
    patterns: [...previousQuery.patterns, ...extractPatterns(evaluation)],

    // 添加代码库中发现的术语
    keywords: [...previousQuery.keywords, ...extractKeywords(evaluation)],

    // 排除确认不相关的路径
    excludes: [...previousQuery.excludes, ...evaluation
      .filter(e => e.relevance < 0.2)
      .map(e => e.path)
    ],

    // 针对特定缺口
    focusAreas: evaluation
      .flatMap(e => e.missingContext)
      .filter(unique)
  };
}
```

### 阶段 4：循环（LOOP）

使用精化后的条件重复（最多 3 轮）：

```javascript
async function iterativeRetrieve(task, maxCycles = 3) {
  let query = createInitialQuery(task);
  let bestContext = [];

  for (let cycle = 0; cycle < maxCycles; cycle++) {
    const candidates = await retrieveFiles(query);
    const evaluation = evaluateRelevance(candidates, task);

    // 检查是否有足够的上下文
    const highRelevance = evaluation.filter(e => e.relevance >= 0.7);
    if (highRelevance.length >= 3 && !hasCriticalGaps(evaluation)) {
      return highRelevance;
    }

    // 精化并继续
    query = refineQuery(evaluation, query);
    bestContext = mergeContext(bestContext, highRelevance);
  }

  return bestContext;
}
```

## 实践示例

### 示例 1：Bug 修复上下文

```
任务："修复认证令牌过期 bug"

第 1 轮：
  分发：在 src/** 中搜索 "token"、"auth"、"expiry"
  评估：发现 auth.ts (0.9)、tokens.ts (0.8)、user.ts (0.3)
  精化：添加 "refresh"、"jwt" 关键词；排除 user.ts

第 2 轮：
  分发：搜索精化后的术语
  评估：发现 session-manager.ts (0.95)、jwt-utils.ts (0.85)
  精化：上下文充足（2 个高相关性文件）

结果：auth.ts、tokens.ts、session-manager.ts、jwt-utils.ts
```

### 示例 2：功能实现

```
任务："为 API 端点添加速率限制"

第 1 轮：
  分发：在 routes/** 中搜索 "rate"、"limit"、"api"
  评估：无匹配 - 代码库使用 "throttle" 术语
  精化：添加 "throttle"、"middleware" 关键词

第 2 轮：
  分发：搜索精化后的术语
  评估：发现 throttle.ts (0.9)、middleware/index.ts (0.7)
  精化：需要路由器模式

第 3 轮：
  分发：搜索 "router"、"express" 模式
  评估：发现 router-setup.ts (0.8)
  精化：上下文充足

结果：throttle.ts、middleware/index.ts、router-setup.ts
```

## 与 Agent 集成

在 Agent 提示词中使用：

```markdown
为此任务检索上下文时：
1. 从广泛的关键词搜索开始
2. 评估每个文件的相关性（0-1 分）
3. 识别仍然缺少什么上下文
4. 精化搜索条件并重复（最多 3 轮）
5. 返回相关性 >= 0.7 的文件
```

## 最佳实践

1. **从广到窄，逐步精化** - 初始查询不要过度限定
2. **学习代码库术语** - 第一轮通常会揭示命名约定
3. **追踪缺失内容** - 明确的缺口识别驱动精化
4. **适可而止** - 3 个高相关性文件胜过 10 个平庸文件
5. **果断排除** - 低相关性文件不会变得相关

## 相关资源

- [The Longform Guide](https://x.com/affaanmustafa/status/2014040193557471352) - 子 Agent 编排部分
- `continuous-learning` skill - 用于随时间改进的模式
- `~/.codebuddy/agents/` 中的 Agent 定义
