# Hooks 系统

## Hook 类型

- **PreToolUse**：工具执行前（验证、参数修改）
- **PostToolUse**：工具执行后（自动格式化、检查）
- **Stop**：会话结束时（最终验证）

## 自动接受权限

谨慎使用：
- 为可信、定义明确的计划启用
- 探索性工作时禁用
- 绝不使用 dangerously-skip-permissions 标志
- 改为在 `~/.codebuddy.json` 中配置 `allowedTools`

## 任务管理最佳实践

使用 TaskCreate/TaskUpdate/TaskList 工具：
- 跟踪多步骤任务的进度
- 验证对指令的理解
- 启用实时引导
- 展示细粒度的实现步骤

任务列表可以揭示：
- 顺序错误的步骤
- 缺失的项目
- 多余不必要的项目
- 错误的粒度
- 误解的需求
