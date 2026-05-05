# 系统总览

`agentOs` 当前可以分成六层理解：

## 1. CLI / Shell 层

负责：

- `agentos` 命令入口
- `shell / run / status / session-show / watch` 等命令面
- plain shell 与 Textual shell 的表现层

## 2. Runtime 编排层

负责：

- 接收用户任务
- 驱动 LangGraph 状态流
- 组织 planner / executor / reviewer
- 决定何时调用工具、何时收束结果

## 3. Tool Runtime 层

负责：

- ToolRegistry
- LangChain `StructuredTool`
- 文件、搜索、patch、测试等工具调用
- 工具结果结构化回写

## 4. Context Engine 层

负责：

- 从历史、工具结果、工作区信号中提取上下文
- 压缩与分层记忆
- 控制 prompt budget
- 记录 lifecycle audit

## 5. Session / Memory 层

负责：

- 持久化 session
- resume / watch
- 记忆状态保存与恢复

## 6. Harness / Workspace 层

负责：

- 命令执行边界
- 工作区隔离
- delegated work unit 的执行基础
