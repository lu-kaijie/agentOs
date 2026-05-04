## Why

第一条 change 已经把 `agentOs` 搭成了一个具备主要核心部件的 agent/harness 学习型底座，但它仍然不是一个更真实可用的 coding-agent 系统：当前 runtime 仍是一次性有向流程，没有真正的 agent loop，后台任务结果也不会重新进入决策过程，委派控制面还没有接成实际执行流。现在需要第二条 change，把这个底座推进到更接近真实 agent 的运行形态，同时继续保持“分阶段、可打 tag、可学习”的实现方式。

## What Changes

- 将当前一次性 LangGraph 流程推进为可恢复、可继续消化新状态的 agent loop，并把后台任务结果回流到下一轮决策中。
- 将现有 coordination control plane 从“可记录 work unit”推进为“可驱动受控 delegated execution”的执行流。
- 引入更明确的权限与审批策略，让 runtime 在执行工具时不只依赖硬编码示例，而是逐步形成可解释的安全边界。
- 扩展 LangChain / LangGraph 的实际使用方式，让结构化决策、消息状态、checkpoint、后台结果整合和委派结果回流形成更接近真实 agent 的链路。
- 延续第一条 change 的节奏：继续小步实现、每步可体验、每步可打 tag 发布到 GitHub，并继续使用 `.venv-agentos` 与锁版本依赖。

## Capabilities

### New Capabilities
- `resumable-agent-loop`: 定义一个可持续运行、可重新进入下一轮决策的 agent loop，而不是当前单次到 `END` 的图。
- `background-result-reentry`: 定义后台任务结果如何重新进入 runtime 状态并影响后续路由与决策。
- `delegated-execution-runtime`: 定义 work unit 如何从协调控制面推进到真实受控执行流。
- `permission-and-approval-policy`: 定义更清晰的执行权限与审批策略，使 runtime 的安全边界可解释且可扩展。

### Modified Capabilities

- None.

## Impact

- 影响 runtime 状态定义、LangGraph 路由方式、后台任务处理方式和协调控制面。
- 提高系统的真实运行复杂度，使其更接近长生命周期 agent，而不只是演示型 graph。
- 扩大 LangChain / LangGraph 的实际覆盖面，尤其是消息状态、structured output、checkpoint、路由回流和执行边界。
- 保持 GitHub 里程碑式推进方式，继续要求每步可测试、可演示、可打 tag。
