## Why

当前 `agentOs` 已经具备受控的 `planner / executor / reviewer` 工作流、结构化工具层和 `context_bundle`，但这三层仍然停留在骨架阶段：`role` 还是硬编码节点，`tool` 还没有切到 LangChain 原生工具主路径，`context` 仍然是手写规则，且 runtime 还没有真正调用大模型 API。下一条 change 需要把这四道边界一起跨过去，让项目尽快进入“真正可用的交互式 agent shell”阶段。

## What Changes

- 将现有 `planner / executor / reviewer` 从硬编码工作流阶段提升为受控的 agent-role abstraction，并尽量直接复用 LangGraph / LangChain 现成能力。
- 将 tool runtime 默认切换到 LangChain tool abstraction，优先直接使用框架提供的 tool schema、binding 和 invocation 路径；仅保留与 harness、安全和持久化强绑定的最小内部边界。
- 将现有 `context_bundle` 从硬编码规则提升为可配置的 context-policy / retriever / compressor pipeline，优先直接使用 LangChain / LangGraph 相关组件。
- 接入真实大模型 API 路径，让 planner / executor / reviewer 主链路能够在受控模式下调用模型完成真实推理与工具使用体验。
- 新增一个常驻交互式 CLI shell，让你可以像使用 Claude Code 一样，打开一个窗口后持续与 agent 工作，而不是继续停留在单条命令模式。
- 将当前代码里适合由 LangChain / LangGraph 承担的层尽量直接迁移到框架原生实现，不再为了教学节奏刻意保留过多自定义骨架。

## Capabilities

### New Capabilities
- `interactive-agent-shell`: 定义常驻交互式 CLI shell、连续会话输入输出和长期运行的 agent 操作面。
- `agent-role-runtime`: 定义受控的 planner / executor / reviewer agent 抽象、handoff 记录和角色化 runtime 协议。
- `langchain-tool-runtime`: 定义基于 LangChain tool abstraction 的主工具运行时，以及必要的 harness 边界补位层。
- `context-policy-runtime`: 定义可配置的上下文选择、压缩、检索和 role-specific context policy。
- `model-backed-agent-runtime`: 定义真实大模型 API 接入、受控模型调用路径和可验证的 agent 推理体验。

### Modified Capabilities
- `role-based-coding-workflow`: 现有 role workflow 的 requirement 将从“硬编码 role stage”扩展为“可检查的 agent-role runtime”。
- `structured-tool-registry`: 现有工具 requirement 将从“自定义注册与调用”扩展为“可被 LangChain 原生工具运行时直接消费、同时保留必要 harness 边界的调用路径”。
- `advanced-context-engineering`: 现有 context requirement 将从“手写 bundle 规则”扩展为“可配置 context policy runtime”。

## Impact

- 影响 runtime 状态模型、role record 结构、tool registry 接口、context policy 层、模型调用配置、LangChain/LangGraph 集成层、交互式 CLI shell 和测试矩阵。
- 会新增 role agent 抽象层、LangChain tool runtime、context policy runtime 和真实模型调用层，但继续复用当前 harness、session 持久化和 policy 边界。
- 会显著提升 LangChain / LangGraph 的覆盖深度，尤其是 tool schema、tool binding、retriever/compressor pipeline、agent handoff、stateful orchestration、streaming 和真实模型驱动的 workflow。

## Acceptance Shape

完成这条 change 后，`agentOs` 的目标形态 SHALL 是一个“基于 LangChain / LangGraph、真实模型驱动、常驻交互式、可连续使用的 Claude Code 风格 agent shell 原型”，而不再只是分阶段演示用的单命令 runtime 骨架。

达到完成态时，贡献者应能：
- 启动一个常驻交互式 shell，并在同一窗口内连续多轮与 agent 工作
- 让 agent 在真实模型驱动下使用工具、上下文、role workflow 和会话持久化能力
- 在 shell 中继续利用已有的 session / resume / inspect / delegated work 等能力，而不需要频繁切回分散的一次性 CLI 子命令

完成这条 change 后，系统还应覆盖 Claude Code 风格 coding-agent 的高频核心场景，包括：
- 阅读和理解代码
- 搜索仓库与定位相关文件
- 修改或 patch 代码
- 运行测试并根据结果继续修复
- 在同一会话内连续多轮推进一个 coding 任务
- 中断后恢复并继续之前的工作
