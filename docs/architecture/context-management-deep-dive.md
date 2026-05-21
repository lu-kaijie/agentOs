# 上下文管理机制详解

这篇文档只讲一件事：`agentOs` 如何管理上下文。

如果把 harness 工程类比成一个操作系统，那么：

- `session` 像磁盘上的进程状态与检查点
- `memory_state` 像进程的结构化工作内存
- `context bundle` 像一次调度前真正装入 CPU cache 的那部分可执行上下文

对 agent 系统来说，上下文是稀缺资源。它既不能无限增长，也不能丢掉真正影响后续决策的信息。`agentOs` 当前的设计目标不是“把完整历史喂给模型”，而是把上下文分成可持久化、可压缩、可按角色分配的多层结构。

## 1. 总体原则

当前上下文系统遵循四个原则：

1. 默认不回放完整历史，只回放结构化的关键状态。
2. session、memory、bundle 分层保存，避免把“可恢复状态”和“模型可见上下文”混成一层。
3. planner / executor / reviewer 不看同一份原始上下文，而是看 role-aware 视图。
4. 每次上下文整理都留下审计痕迹，能解释“为什么压缩”“保留了什么”“丢掉了什么”。

## 2. 三层结构

最重要的是先区分三层：

### 2.1 Session State

session turn 文件位于：

- `.agentos/sessions/<session_id>/turn_xxxx.json`

这里保存的是整轮执行状态，典型字段包括：

- `user_task`
- `pending_tasks`
- `completed_tasks`
- `step_outputs`
- `tool_results`
- `role_records`
- `role_handoffs`
- `context_policy_records`
- `context_audit_records`
- `memory_state`
- `execution_trace`
- `final_output`

这一层的目标是：

- `session-show` 可检查
- `resume` 可恢复
- `watch` 可轮询

它追求的是“恢复性”和“可观测性”，不是 prompt 最小化。

### 2.2 Layered Memory

memory 文件位于：

- `.agentos/context/<session_id>.memory.json`

对应的数据结构在 [src/agentos/context/models.py](/home/mi/agentOs/src/agentos/context/models.py:1) 的 `LayeredMemory`。

这一层的目标是：

- 把长期有价值的信息抽成结构化层
- 让下一轮构造 context bundle 时不必重新扫完整历史

### 2.3 Context Bundle

bundle 不单独持久化为独立文件，但会嵌进 turn state 的 `context_bundle`。

它是一次 role 调度前真正给模型或 runtime 使用的“装载态上下文”，来源是：

- session 派生的历史摘要
- layered memory
- 最近工具结果
- 工作区信号
- role-specific budget

`ContextManager.prepare_role_context(...)` 是主入口，位于 [src/agentos/context/manager.py](/home/mi/agentOs/src/agentos/context/manager.py:97)。

## 3. Layered Memory 字段详解

`LayeredMemory` 的定义在 [src/agentos/context/models.py](/home/mi/agentOs/src/agentos/context/models.py:146)。

### 3.1 `recent_messages`

类型：

- `list[dict[str, object]]`

含义：

- 最近保留的消息快照
- 不是完整 transcript，只保留少量最近消息

作用：

- 在无法完全依赖结构化摘要时，保留局部会话语义

当前裁剪策略：

- lifecycle 中最多保留最近 4 条

### 3.2 `working_memory`

类型：

- `WorkingMemory`

字段定义在 [src/agentos/context/models.py](/home/mi/agentOs/src/agentos/context/models.py:9)。

字段说明：

- `current_goal`
  当前任务目标。优先来自本轮 `task`。
- `accepted_constraints`
  已识别并应继续遵守的约束，例如“请用中文”“不要删文件”。
- `rejected_approaches`
  明确不该继续走的路径。
- `active_plan`
  当前待执行计划，通常来自 `pending_tasks` 前几项。
- `completed_actions`
  最近已完成动作，通常来自 `completed_tasks`。
- `open_questions`
  当前未解决问题。
- `conversation_summary`
  对最近执行进展的压缩总结。

这是最重要的一层。它决定了 agent 下一轮还能不能“记住自己在做什么”。

### 3.3 `user_preferences`

类型：

- `UserPreferences`

字段定义在 [src/agentos/context/models.py](/home/mi/agentOs/src/agentos/context/models.py:31)。

字段说明：

- `preferred_language`
  当前用户偏好语言，例如 `zh-CN`
- `output_preferences`
  输出风格偏好
- `collaboration_preferences`
  协作偏好，例如 `prefer direct implementation`

这层的价值在于：用户偏好通常跨任务稳定存在，不该埋在零散历史消息里。

### 3.4 `tool_facts`

类型：

- `list[ToolFact]`

字段定义在 [src/agentos/context/models.py](/home/mi/agentOs/src/agentos/context/models.py:47)。

字段说明：

- `tool_name`
- `summary`
- `related_paths`
- `command`
- `success`
- `exit_code`

这层是“硬事实缓存”。例如：

- 运行过哪个测试
- 退出码是多少
- 最近读写了哪些路径

它比自然语言总结更可靠，因为它来自结构化工具输出。

### 3.5 `workspace_state`

类型：

- `WorkspaceState`

字段定义在 [src/agentos/context/models.py](/home/mi/agentOs/src/agentos/context/models.py:73)。

字段说明：

- `top_level_entries`
  工作区顶层目录快照
- `touched_files`
  最近被涉及的文件
- `recent_reads`
  最近读取的文件
- `recent_writes`
  最近写入的文件

这层的意义是：很多 coding 任务的局部上下文不是对话语义，而是“我刚刚看了哪些文件、改了哪些文件”。

### 3.6 `failure_memory`

类型：

- `list[FailureFact]`

字段定义在 [src/agentos/context/models.py](/home/mi/agentOs/src/agentos/context/models.py:91)。

字段说明：

- `summary`
- `tool_name`
- `command`
- `reason`

作用：

- 让 agent 记住最近失败过什么
- 避免重复踩同样的坑
- 给 reviewer 更多风险信号

### 3.7 `session_summary`

类型：

- `str`

当前由 lifecycle 生成，见 [src/agentos/context/lifecycle.py](/home/mi/agentOs/src/agentos/context/lifecycle.py:271)。

典型内容类似：

```text
goal=修复 CLI 参数解析 | plan=补测试, 修代码 | tool_facts=3 | failures=1
```

这是非常高密度的摘要字段，用于快速描述“会话的主状态是什么”。

### 3.8 `lifecycle_audits`

类型：

- `list[LifecycleAuditRecord]`

字段定义在 [src/agentos/context/models.py](/home/mi/agentOs/src/agentos/context/models.py:109)。

字段说明：

- `trigger_reason`
- `before_size`
- `after_size`
- `compressed_layers`
- `retained_layers`
- `dropped_classes`
- `budget_allocations`
- `compression_mode`

它的地位非常重要，因为这层是上下文系统的“内存管理日志”。

## 4. Lifecycle：上下文是怎么维护出来的

主逻辑在 [src/agentos/context/lifecycle.py](/home/mi/agentOs/src/agentos/context/lifecycle.py:28) 的 `ContextLifecycleManager.maintain(...)`。

一次维护的步骤是：

1. 读取已有 memory
2. 收集最近消息
3. 估算维护前大小 `before_size`
4. 抽取：
   - `tool_facts`
   - `failure_memory`
   - `working_memory`
   - `user_preferences`
   - `workspace_state`
5. 组装新的 `LayeredMemory`
6. 判断是否需要压缩
7. 生成 `LifecycleAuditRecord`
8. 落盘新的 memory

### 4.1 触发原因 `trigger_reason`

当前常见触发原因包括：

- `prepare_context`
- `role_handoff`
- `session_resume`
- `turn_complete`
- `large_tool_output`

这些值会进入 audit，方便你判断是哪类事件推动了本次压缩。

### 4.2 大小阈值

当前核心阈值在 [src/agentos/context/lifecycle.py](/home/mi/agentOs/src/agentos/context/lifecycle.py:31)：

- `ACTIVE_THRESHOLD_CHARS = 900`
- `LARGE_TOOL_OUTPUT_CHARS = 500`

注意这里不是 token，而是字符数近似估计。它的定位是轻量、可解释的本地预算控制，不是精确 tokenizer。

### 4.3 压缩判定

`_should_reduce(...)` 见 [src/agentos/context/lifecycle.py](/home/mi/agentOs/src/agentos/context/lifecycle.py:284)。

满足任一条件就会压缩：

1. 触发原因属于：
   - `session_resume`
   - `role_handoff`
   - `turn_complete`
   - `large_tool_output`
2. `before_size > ACTIVE_THRESHOLD_CHARS`
3. 任一 `tool_fact.summary` 长度超过 `LARGE_TOOL_OUTPUT_CHARS`

这说明系统是“事件驱动 + 尺寸驱动”的混合策略。

### 4.4 当前压缩动作

当前压缩动作比较克制，主要压两层：

- `recent_messages`
- `tool_facts`

具体行为：

- `recent_messages` 超过 4 条时，只保留最近 4 条
- `tool_facts` 超过 3 条时，只保留最近 3 条

这部分逻辑在 [src/agentos/context/lifecycle.py](/home/mi/agentOs/src/agentos/context/lifecycle.py:82)。

注意：

- `working_memory`
- `user_preferences`
- `workspace_state`
- `failure_memory`

这些层默认不做激进删除，因为它们的密度更高、价值也更稳定。

## 5. Working Memory 是怎么抽取的

主逻辑在 [src/agentos/context/lifecycle.py](/home/mi/agentOs/src/agentos/context/lifecycle.py:110) 的 `_extract_working_memory(...)`。

### 5.1 约束抽取

当前会从最近消息里用启发式规则识别约束，例如命中：

- `不要`
- `必须`
- `请用`
- `记得`

则加入 `accepted_constraints`。

同理，命中：

- `不要`
- `不能`
- `不要用`

则加入 `rejected_approaches`。

这不是 NLP 级深理解，而是高召回的工程启发式。

### 5.2 语言偏好

如果最近消息中包含“中文”，会把语言偏好记成：

- `preferred_language = "zh-CN"`

并补一个约束：

- `prefers Chinese output`

### 5.3 计划与动作

`active_plan` 来源：

- `pending_tasks` 前 5 项

`completed_actions` 来源：

- `completed_tasks` 后 5 项

### 5.4 会话总结

`conversation_summary` 初始来源：

- `step_outputs` 最近 3 项压缩

之后会进入 `SemanticMemoryCompressor` 做一次可选语义压缩。

## 6. SemanticMemoryCompressor：什么时候让模型参与压缩

组件定义在 [src/agentos/context/lifecycle.py](/home/mi/agentOs/src/agentos/context/lifecycle.py:357)。

默认情况下，它主要是启发式 fallback，不一定调用模型。

只有同时满足这些条件，才会尝试模型压缩：

1. `AGENTOS_CONTEXT_MODEL_COMPRESSION=1`
2. 存在 `OPENAI_API_KEY`
3. 语义负载超过阈值

如果模型压缩失败，会静默回退到启发式结果。

当前模型压缩只输出三个键：

- `conversation_summary`
- `accepted_constraints`
- `open_questions`

这说明目前的策略是：**只让模型帮助压缩语义层，不让模型重写整个 memory 结构。**

## 7. Context Bundle：真正给模型看的内容

bundle 的构造逻辑在 [src/agentos/context/policy.py](/home/mi/agentOs/src/agentos/context/policy.py:20)。

### 7.1 Pipeline 输入项

`RunnableParallel` 当前抽取这些输入：

- `task_hints`
- `history_entries`
- `tool_results`
- `execution_trace`
- `workspace_signals`
- `memory_state`
- `active_skills`
- `matched_skills`
- `skills_catalog`
- `skills_available`
- `skills_count`
- `skills_hint`
- `context_audit_records`
- `role_name`
- `session_id`
- `task`

这一步相当于“把多个来源的上下文原料先并行取出来”。

### 7.2 `task_hints`

来源：

- task 文本前缀解析

当前支持把任务解析成：

- `action`
- `raw`
- `path`
- `pattern`
- `topic`
- `command`

其意义是：后续 workspace 检索和 role 视图不需要再从原始 task 文本重复猜测。

### 7.3 `workspace_signals`

当前最多构造三类信号：

- `file`
  如果 task hint 有路径
- `search`
  如果 task hint 有 pattern
- `workspace`
  顶层目录快照

这是一种非常廉价但很实用的检索层。

### 7.4 Bundle 主要字段

`_assemble_bundle()` 生成的关键字段包括：

- `session_id`
- `task`
- `role`
- `task_hints`
- `active_skills`
- `matched_skills`
- `skills_catalog`
- `skills_available`
- `skills_count`
- `skills_hint`
- `history_summary`
- `recent_history`
- `tool_summary`
- `recent_tool_results`
- `tool_facts`
- `trace_summary`
- `workspace_signals`
- `sources`
- `memory_summary`
- `layered_memory`
- `budget_allocations`
- `context_audit_records`
- `role_view`
- `bundle_preview`

## 8. Role-Aware 策略：为什么不同角色看到不同上下文

`_role_view(...)` 位于 [src/agentos/context/policy.py](/home/mi/agentOs/src/agentos/context/policy.py:282)。

### 8.1 Planner

planner 视图偏重：

- 最近历史
- skill 名称
- `working_memory`
- workspace 顶层信号

因为 planner 更关心：

- 任务是什么
- 当前目标是什么
- 该如何拆步骤

### 8.2 Reviewer

reviewer 视图偏重：

- 最近工具结果
- `tool_facts`
- `failure_memory`
- 少量 matched skills

因为 reviewer 的主要职责不是执行，而是验证。

### 8.3 Executor

executor 视图偏重：

- 最近历史
- 最近工具结果
- skills catalog
- `working_memory`
- `workspace_state`

因为 executor 要实际推进任务，需要同时知道：

- 刚刚做了什么
- 仓库里发生过什么
- 还有什么技能可按需加载

## 9. Budget Allocation：当前是怎么分预算的

bundle 内会带 `budget_allocations`，来源于 role-specific 策略。

当前预算配置在：

- lifecycle: [src/agentos/context/lifecycle.py](/home/mi/agentOs/src/agentos/context/lifecycle.py:310)
- policy: [src/agentos/context/policy.py](/home/mi/agentOs/src/agentos/context/policy.py:423)

planner 典型预算：

- `working_memory`: 260
- `user_preferences`: 80
- `recent_messages`: 120
- `workspace_state`: 100

reviewer 典型预算：

- `working_memory`: 180
- `tool_facts`: 220
- `failure_memory`: 120
- `recent_messages`: 80

executor 典型预算：

- `working_memory`: 180
- `tool_facts`: 180
- `workspace_state`: 160
- `recent_messages`: 80

这些数字当前更像“软预算说明”，主要用于解释系统优先级，而不是精确 token 剪枝器。

## 10. Model Path 与 Fallback Path 的差异

### 10.1 Model Path

`AgentOsApp.run_model_session_task()` 现在是一个 bounded outer loop。每一轮都会分别为：

- planner
- executor
- reviewer

各自调用一次 `prepare_role_context(...)`，见 [src/agentos/app.py](/home/mi/agentOs/src/agentos/app.py:161)。

特点：

- 每一轮都重新准备三份 role bundle
- `skill_mode="catalog"`
- 每轮三次 context audit
- 每轮都会把新增 `tool_results`、`memory_state`、`context_policy_records`、`context_audit_records` 合并回 state
- 最终 state 中保留最后一轮 reviewer bundle 作为本轮 `context_bundle`

### 10.2 Fallback Path

deterministic runtime 在 LangGraph 节点 `prepare_context` 中为当前 step 准备一次 bundle，见 [src/agentos/runtime/app.py](/home/mi/agentOs/src/agentos/runtime/app.py:283)。

特点：

- 按 step 迭代准备 context
- 默认 `skill_mode="matched"`
- context 与显式 DSL step 强绑定

这就是为什么两条路径虽然共用 context engine，但上下文注入方式不同。

## 11. Session 恢复时上下文如何流转

session 恢复分两类：

### 11.1 Model Path

model-backed 路径在 [src/agentos/app.py](/home/mi/agentOs/src/agentos/app.py:168) 会先读取 `latest_turn["state"]` 作为 `prior_state`，然后进入 outer loop；每一轮都重新构造三份 role bundle。

也就是说：

- turn state 提供恢复原料
- memory 再从 `prior_state` + session message 中重新维护
- bundle 每轮重新构造
- reviewer 结论会决定是否继续下一轮
- 如果连续一轮没有新增工具结果，且 planner/executor/reviewer 输出都没有变化，loop 会主动以 `stopped:no_progress` 退出

### 11.2 Deterministic Resume

`SessionManager.build_resume_state()` 在 [src/agentos/sessions/manager.py](/home/mi/agentOs/src/agentos/sessions/manager.py:70)。

它会把：

- `pending_tasks`
- `tool_results`
- `memory_state`
- `context_policy_records`
- `context_audit_records`

等字段带入下一次 runtime。

但如果 `pending_tasks` 已空，会做一次硬重置。

这意味着：

- session 是“恢复入口”
- memory 是“恢复后的上下文骨架”
- bundle 是“恢复后这一步真正给角色/模型看的装载态”

## 12. 当前系统的价值与边界

### 当前价值

当前这套上下文系统已经具备：

- 分层记忆
- role-aware context
- 历史与工具结果分离
- resume/watch 可恢复
- lifecycle 审计
- 可选语义压缩

### 当前边界

仍然存在一些明显边界：

1. 大小预算仍是字符级近似，不是精确 token budget。
2. 压缩动作仍偏简单，主要裁剪最近消息和工具事实。
3. 还没有真正的长期记忆检索器。
4. `skills_hint` 目前在 manager/policy 两处都参与生成，仍有统一空间。
5. 模型路径虽然已经有 outer loop，但 loop 的 continue / stop 仍主要依赖 reviewer verdict 和轻量 no-progress heuristics。
6. session / memory / bundle 的恢复契约虽然清晰，但还有进一步细化空间。

## 13. 推荐阅读顺序

如果你要真正读代码理解这套机制，建议顺序是：

1. [src/agentos/context/models.py](/home/mi/agentOs/src/agentos/context/models.py:1)
2. [src/agentos/context/lifecycle.py](/home/mi/agentOs/src/agentos/context/lifecycle.py:28)
3. [src/agentos/context/policy.py](/home/mi/agentOs/src/agentos/context/policy.py:20)
4. [src/agentos/context/manager.py](/home/mi/agentOs/src/agentos/context/manager.py:16)
5. [src/agentos/app.py](/home/mi/agentOs/src/agentos/app.py:161)
6. [src/agentos/runtime/app.py](/home/mi/agentOs/src/agentos/runtime/app.py:283)
7. [src/agentos/sessions/manager.py](/home/mi/agentOs/src/agentos/sessions/manager.py:70)

## 14. 一句话总结

`agentOs` 的上下文管理不是“把历史压缩一下”这么简单，而是把 session、memory、bundle 拆成三层，再通过 lifecycle、policy 和 role-aware 预算，把有限上下文像内存一样进行结构化分配、裁剪和装载。
