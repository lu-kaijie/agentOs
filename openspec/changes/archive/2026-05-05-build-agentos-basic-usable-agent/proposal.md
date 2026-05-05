## Why

第二条 change 会把 `agentOs` 推进到“更真实的 agent loop 原型”，但那仍然主要解决 runtime 形态问题，还不足以构成一个可以持续使用的 coding-agent 工具。第三条 change 需要在这个原型之上补齐会话持久化、上下文工程、工具体系和交互体验，让项目从“学习型 runtime”走向“基本可用 agent”。

## What Changes

- 增强会话与任务持久化，使 runtime 可以查看历史、恢复执行、回放状态与追踪关键事件。
- 把现有 harness 扩展成更完整的工具体系，包括文件读写、搜索、补丁应用和标准化的 tool registry。
- 深化上下文工程能力，引入任务相关上下文选择、摘要压缩、工作区索引与多来源 context merge。
- 在 runtime 内引入更接近 coding-agent 的角色化流程，如 planner / executor / reviewer 的受控协作。
- 将 CLI 从当前的分散命令增强为更连续的交互体验，包括会话查看、恢复、日志和流式过程展示。
- 延续前两条 change 的节奏：每个子阶段都可体验、可测试、可打 tag，并继续使用 `.venv-agentos` 与锁版本依赖。

## Capabilities

### New Capabilities
- `session-persistence-and-replay`: 定义会话、任务、trace 和恢复执行的持久化能力。
- `structured-tool-registry`: 定义面向 coding-agent 的标准化工具注册、调用和补丁执行能力。
- `advanced-context-engineering`: 定义上下文选择、摘要压缩、检索与多来源合并策略。
- `role-based-coding-workflow`: 定义 planner / executor / reviewer 等角色在 runtime 中的受控协作路径。
- `interactive-agent-cli`: 定义更连续的 CLI 交互、恢复、日志和运行观测体验。

### Modified Capabilities

- None.

## Impact

- 影响 runtime 状态模型、持久化目录结构、harness tool 接口、上下文管理器、CLI 命令设计和测试矩阵。
- 会明显扩大 LangChain / LangGraph 的实际覆盖面，尤其是 memory、message state、tool binding、retrieval、multi-step orchestration 和 tracing。
- 会让项目更接近真正长期可用的 coding-agent 原型，但仍不会直接追求完整产品级自治。
