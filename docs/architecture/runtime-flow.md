# 运行链路

如果你想看结合代码、按函数名展开的详细版，请先读：

- [持续交互主链路详解](interactive-mainline-deep-dive.md)

## 交互式 shell 主链路

当你执行 `agentos` 时，主链路大致是：

1. CLI 入口解析参数
2. 进入 shell presentation
3. 接收用户输入
4. 把输入交给 runtime
5. runtime 组装 context bundle
6. 进入 LangGraph role / tool / review 流程
7. 持久化 session 和记忆
8. 把结果回显给用户

## one-shot `run` 主链路

当你执行 `agentos run "<task>" --model` 时：

1. CLI 构造 model-enabled runtime 请求
2. 请求进入和 fallback 相同的 LangGraph agent loop
3. `prepare_context` 在每次模型决策前整理上下文
4. `model_decide` 调用真实模型并要求返回一个结构化 `RuntimeDecision`
5. graph 根据 decision 进入 `approval_gate`、`tool_execute` 或 `respond_directly`
6. `finalize_iteration` 记录工具结果、完成步骤和 loop 状态
7. 如果还需要继续，下一轮重新进入 `prepare_context`

非 `--model` 的 `agentos run` 仍走同一套 LangGraph loop，但 decision 默认来自确定性的 `run:` / `read:` / `write:` / `test:` 等前缀解析。

## 上下文与工具边界

真实模型只负责决定下一步做什么，不直接绕过运行时执行命令。

每轮执行遵循：

```text
prepare_context
-> model_decide / deterministic_decide
-> approval_gate / tool_execute / respond_directly
-> finalize_iteration
```

命令和测试仍通过现有 harness：

- `ToolRegistry`
- `CommandApprovalPolicy`
- `CommandExecutor`
- `ExecutionRequest`
- `ExecutionResult`

这样模型路径和 fallback 路径都能被 session、memory、context audit、tool results 和 harness 边界观察到。

## 结构化记忆生命周期

上下文生命周期归 `agentos.context` 组件管理，`AgentGraphState` 只携带当轮运行快照。

每次 `prepare_context` 会读取当前 session 消息和已持久化的 `LayeredMemory`，然后生成新的分层记忆：

1. `StructuredMemoryExtractor` 从最近用户/助手消息和结构化 `ToolFact` 中生成 `MemoryDelta`
2. 优先使用模型工具调用输出结构化 delta；未配置或失败时回退到确定性抽取
3. delta 按字段合并进 `user_profile`、`remembered_facts`、`task_state`、`failure_memory`
4. 工具输出继续保留在 session/tool results 中，长期对话消息只保存用户输入和最终助手回答
5. `ContextPolicyRuntime` 把 `user_profile`、`remembered_facts`、`task_state` 投影进 context bundle
6. `GraphModelDecisionStrategy` 在模型提示中直接注入结构化记忆，而不是只依赖 recent messages

主要层级：

- `user_profile`：稳定画像，例如偏好中文、回答简短
- `remembered_facts`：用户明确要求记住的事实，按 stable key 合并和更新
- `task_state`：当前目标、完成动作、开放问题和计划
- `tool_facts`：工具结果的短摘要、相关路径、命令和成功状态
- `workspace_state`：最近读取/写入/触碰的工作区信号
- `failure_memory`：工具失败和错误原因的结构化记录
- `recent_messages`：压缩后的近期用户/最终助手消息

因此，最近消息被压缩后，明确记住的测试代号、用户回答偏好等仍应通过结构化层进入模型决策提示。

## 交互式审批链路

当模型或 deterministic decision 选择危险命令时：

1. `approval_gate` 记录 `pending_approval`
2. loop 状态进入 `waiting_approval`
3. 命令不会执行
4. 用户通过 shell `/approve`、`/reject` 或 CLI approval 命令恢复 session
5. 批准时只执行原 pending decision 中的命令
6. 拒绝时记录 rejection，命令不执行

## `watch` 主链路

当你执行 `agentos watch <session>` 时：

1. 轮询 session 状态
2. 检查是否有新 turn 或状态变化
3. 展示最新执行情况

当前 `watch` 是轮询式，不是主动推送式。
