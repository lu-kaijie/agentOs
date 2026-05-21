# 持续交互主链路详解

这篇文档不是产品概览，而是结合代码解释 `agentOs` 的主链路、各模块职责、关键函数以及实现策略。重点放在“持续交互 shell”这条主路径上，同时补充 deterministic fallback、上下文管理、session 持久化、工具层策略和当前边界。

## 1. 先回答：这个项目到底在做什么

`agentOs` 是一个可以安装到终端里的 coding-agent shell。它想做的不是“一次性跑完一个 prompt 的 demo”，而是一个能长期交互、持续维护上下文、可观察、可恢复、带工具能力的命令行 agent 原型。

代码上它有两条执行路径：

1. 真实模型主路径
   入口通常是 `agentos shell` 中的自然语言输入，或者 `agentos run "<task>" --model`。
   这条路径由 `planner -> executor -> reviewer` 三段式工作流驱动，真实调用 OpenAI 兼容模型。

2. deterministic fallback
   入口通常是 `run:`、`search:`、`read:`、`write:`、`patch:`、`test:` 这种显式 DSL。
   这条路径不依赖真实模型，而是靠 LangGraph 状态机和确定性路由规则执行。

这两条路径不是互相替代，而是共同组成产品能力：

- 主路径负责自然语言交互、连续会话和真实 agent 行为。
- fallback 负责在模型不可用时保持基础可用性，也负责给系统提供一条更稳定、可验证的执行底座。

## 2. 模块总览：每个目录负责什么

核心代码都在 `src/agentos/` 下，和持续交互主链路最相关的模块如下：

| 模块 | 作用 | 关键文件 |
|---|---|---|
| CLI 层 | 解析命令、选择 shell 展示层、输出状态 | `cli.py` |
| 应用装配层 | 把 settings、runtime、context、session、tools 装配起来 | `app.py` |
| model-backed runtime | 真实模型三段式工作流 | `runtime/model_backed.py` |
| deterministic runtime | LangGraph 状态机、fallback 和显式 DSL 执行 | `runtime/app.py` |
| role 协议 | planner / executor / reviewer 的结构化输入输出 | `runtime/roles.py` |
| context 管理 | session 消息存取、上下文 bundle、长期记忆维护 | `context/manager.py`、`context/policy.py`、`context/lifecycle.py`、`context/models.py` |
| tool runtime | 工具注册、调用、记录收集 | `tools/registry.py` |
| session 持久化 | 每轮 turn 的原始 state 落盘与恢复 | `sessions/manager.py` |
| 本地执行器 | shell/test 等命令的实际 subprocess 边界 | `harness/execution/local.py` |
| 配置层 | 环境变量、目录路径、模型分层选择 | `config.py` |

如果你只想先抓主链路，建议按这个顺序读代码：

1. `src/agentos/cli.py`
2. `src/agentos/app.py`
3. `src/agentos/runtime/model_backed.py`
4. `src/agentos/context/manager.py`
5. `src/agentos/context/policy.py`
6. `src/agentos/context/lifecycle.py`
7. `src/agentos/tools/registry.py`
8. `src/agentos/sessions/manager.py`
9. `src/agentos/runtime/app.py`

## 3. 持续交互 shell：从输入一句话开始发生了什么

### 3.1 CLI 如何进入 shell

默认执行 `agentos` 时，会走 `src/agentos/cli.py` 里的 `default_entry()`。

这里做了三件事：

1. 解析 `--session-id`、`--plain`、`--tui`、`--approve`、`--max-iterations`。
2. 调用 `_launch_shell()`。
3. 在 `_launch_shell()` 中优先尝试 Textual TUI，失败则回退到 plain shell。

plain shell 的核心循环在 `_run_plain_shell()`：

- 打印 shell banner
- 如果模型没配置，打印模型配置指引
- 循环读取用户输入
- `/status` 读取 session 最新状态
- `/exit` 退出
- 普通自然语言优先尝试 model-backed
- DSL 任务或模型不可用时走 deterministic runtime

这也是持续交互和 one-shot `run` 的第一个区别：

- shell 是常驻进程，进程内持续接收任务。
- `run` 是单次构造应用、执行、输出、退出。

### 3.2 什么时候走 model-backed，什么时候走 fallback

判断逻辑也在 `_run_plain_shell()`：

- 如果 `application.model_runtime.is_configured()` 为真，且输入不是 legacy DSL，就走 model-backed。
- 否则走 `stream_session_task()`，进入 deterministic runtime。

这里的 legacy DSL 由 `_looks_like_legacy_task()` 判断，前缀包括：

- `run:`
- `knowledge:`
- `search:`
- `read:`
- `write:`
- `patch:`
- `test:`
- `steps:`
- `code:`

这个设计很直接：自然语言默认给真实模型，显式任务 DSL 默认给确定性 runtime。

## 4. `AgentOsApp`：所有能力是怎么装起来的

主装配入口是 `src/agentos/app.py` 的 `AgentOsApp.bootstrap()`。

它会创建下面这些核心对象：

1. `Settings`
   从环境变量读取项目根目录、workspace、`.agentos` 目录、模型名称、role 级别和 API key。

2. `LocalCommandExecutor`
   负责真正执行本地命令，底层是 `subprocess.run(...)`。

3. `KnowledgeLoader`
   负责加载 `knowledge/` 下的知识内容。

4. `ContextManager`
   负责 session 消息、layered memory、context bundle。

5. `SessionManager`
   负责 turn 级 state 落盘和 resume。

6. `BackgroundExecutionManager`
   负责后台任务。

7. `WorkspaceManager`
   负责隔离工作区。

8. `CoordinationManager`
   负责多 work unit 协调。

9. `CommandApprovalPolicy`
   负责命令审批策略。

10. `ToolRegistry`
    把 shell / knowledge / search / read / write / patch / test 封装成 LangChain tool。

11. `ModelBackedAgentRuntime`
    负责真实模型三段式工作流。

12. `RuntimeBootstrap`
    负责 deterministic runtime 的 LangGraph 状态机。

这层的作用不是做业务，而是把“一个 shell 产品需要的上下文、工具、session、模型、fallback”全部接成一套可用系统。

## 5. 真实模型主路径：带外层循环的 planner -> executor -> reviewer

真实模型主链路的总入口是 `AgentOsApp.run_model_session_task()`。

### 5.1 为什么这条路径和 fallback 分开

`run_model_session_task()` 没有直接复用 `runtime/app.py` 的 LangGraph 节点，而是单独写了一条工作流。原因是这条路径要做的事情不同：

- 它不是为了支持很多显式 DSL 分支。
- 它要优先保证自然语言任务的真实模型交互。
- 它要把长期上下文按 role 分开准备。
- 它要额外维护一份适合下轮复用的消息历史。

### 5.2 这条路径的整体步骤

`run_model_session_task()` 现在不是单次固定三段式回合，而是一个 bounded outer loop。每一轮都按顺序做这些事情：

1. 从 `SessionManager.load_latest_turn()` 读取上一次 turn 的 `state`。
2. 初始化本轮 outer-loop `state`，包括 `tool_results`、`memory_state`、`context_*_records`、`role_*`、`execution_trace`、`iteration_count` 和 `loop_status`。
3. 分别为 `planner`、`executor`、`reviewer` 调用 `ContextManager.prepare_role_context(...)`。
4. 把三个 role 的 bundle 一起交给 `ModelBackedAgentRuntime.run_turn(...)`。
5. 收集 planner / executor / reviewer 三段结果，并把新增工具结果、handoff、audit 和 trace 合并回 `state`。
6. 根据 reviewer 结论和本轮进展决定是否继续下一轮。
7. loop 结束后调用 `SessionManager.record_turn(...)` 把整轮结果写到 `.agentos/sessions/<session>/turn_xxxx.json`。

这里要注意两个关键设计：

1. 每个 role 拿到的是不同视图的 context bundle，而且这些 bundle 是每一轮重新准备的。
2. 最终 state 是结构化的，里面不仅有 `final_output`，还有：
   - `tool_results`
   - `role_records`
   - `role_handoffs`
   - `context_policy_records`
   - `context_audit_records`
   - `memory_state`
   - `execution_trace`
   - `iteration_count`
   - `loop_status`

也就是说，这个系统不是只关心“最后说了什么”，而是把“怎么做的”也当成一等产物保留下来。

### 5.3 模型路径外层循环的结束条件

当前 outer loop 有三种终态：

1. `completed`
   reviewer 不再要求 follow-up。
2. `stopped:max_iterations`
   reviewer 仍要求继续，但已经达到 `--max-iterations` 上限。
3. `stopped:no_progress`
   reviewer 仍要求继续，但新一轮没有新增工具结果，且 planner steps、executor output、reviewer summary 都没有变化。

第三种终态是专门为了防止“reviewer 一直说继续，但系统其实没有带来新信息”时空转。

### 5.4 `ModelBackedAgentRuntime.run_turn()` 的具体执行过程

核心实现位于 `src/agentos/runtime/model_backed.py`。

#### 第一步：加载可复用消息

`_load_prior_messages(session_id)` 会从 `ContextManager.load_session()` 读出此前持久化的消息。

但它不会原样复用，而是经过 `_sanitize_reusable_messages()` 清洗：

- 丢弃 `SystemMessage`
- 丢弃 `ToolMessage`
- 如果某条 `AIMessage` 带 `tool_calls`，只保留安全的文本内容

这么做的原因是：ReAct/tool-calling 协议消息不适合在下一轮继续当对话上下文回放，否则容易把“历史工具协议”误当成“当前轮输入”。

#### 第二步：planner 先做结构化计划

planner 阶段会：

1. 构造 `RoleInput`
2. 使用内置 `PlannerRoleAgent` 生成 fallback summary
3. 用 `PydanticOutputParser(PlannerPlan)` 约束模型输出 JSON
4. 调用 `planner_model.invoke(planner_prompt)`

planner 的目标不是直接干活，而是给 executor 一个短、 scoped 的执行框架。

`PlannerPlan` 只包含两个字段：

- `summary`
- `steps`

这个约束刻意做得很小，避免 planner 变成另一个大而全的 agent。

#### 第三步：executor 才拿工具做实际工作

executor 阶段最重要的代码是：

- `create_react_agent(...)`
- `self.tool_registry.as_langchain_tools()`
- `executor_agent.invoke({"messages": executor_messages})`

也就是说，真实模型路径里的 executor 不是手写决策树，而是一个带 LangChain tool 集合的 ReAct agent。

它的输入包括：

- 清洗后的 prior messages
- 当前 user task
- planner summary
- planner steps
- executor 专属 context bundle

同时系统通过 `tool_runtime_context(approved=approved, collector=observed_tool_results)` 给本轮工具调用挂上两个运行时选项：

- 审批状态
- 工具结果收集器

这样 executor 一旦实际调用工具，`ToolRegistry` 会把结果同步记进 `observed_tool_results`，供 reviewer 和最终 state 使用。

#### 补充：model-backed 路径里的 skill 是怎么逐步加载的

这条链路现在已经按“最小 catalog -> 按需 skill discovery”的方式工作，而不是默认把 `SKILL.md` 正文塞进 prompt。

在进入 `ModelBackedAgentRuntime.run_turn()` 之前，`ContextManager.prepare_role_context(...)` 会给 model path 注入一个非常小的 skills 视图：

- `skills_catalog`
- `skills_available`
- `skills_count`
- `skills_hint`

这里的 `skills_catalog` 只包含：

- `name`
- `description`
- `when_to_use`

也就是说，planner / executor / reviewer 默认只知道“仓库里有哪些 skill，大概什么时候该用”，并不知道 skill 的完整正文。

如果 executor 判断某个 skill 相关，它会按下面的顺序主动拉取：

1. `skill_list(role=...)`
   重新拿一份紧凑 catalog
2. `skill_load(name=<skill>, level="summary")`
   先拿 skill 元信息
3. `skill_load(name=<skill>, level="full")`
   再拿 `SKILL.md` 主体
4. `skill_load(name=<skill>, level="reference", target=...)`
   最后按需拿某个 checklist / example

一次已验证的模型路径样例保存在：

- `.agentos/sessions/shell2/turn_0001.json`

这条记录里能同时看到：

- `context_bundle.skills_catalog`
- `tool_name=skill_list`
- `tool_name=skill_load`

说明模型路径不是被动吃上下文，而是先看最小 catalog，再自己决定是否进入 deeper skill loading。

#### 第四步：reviewer 做 grounded 收尾

reviewer 阶段也有两层：

1. 内置 `ReviewerRoleAgent` fallback
2. 真实模型 `reviewer_model.invoke(reviewer_prompt)`

reviewer 的输入包括：

- 用户任务
- executor 最终回答
- 本轮观测到的工具结果
- reviewer 专属 context bundle

它的目标不是重新做任务，而是验证 executor 的结果是否有工具依据，并把当前状态总结给用户。

#### 第五步：持久化下一轮可复用历史

`_build_persisted_messages(...)` 会生成一份“紧凑 transcript”，内容只有：

- prior safe messages
- 本轮 `HumanMessage(user_task)`
- 本轮 executor 的 final `AIMessage`
- reviewer summary 的 `AIMessage`

这一步很关键，它意味着下一轮看到的是“用户问了什么、agent 最终回答了什么、reviewer 如何收尾”，而不是完整工具协议流。

### 5.5 真实模型路径的错误处理策略

`ModelBackedRuntimeError` 用来携带阶段级别的调试信息。

planner / executor / reviewer 每一段如果报错，都会包装成：

- `planner stage failed: ...`
- `executor stage failed: ...`
- `reviewer stage failed: ...`

并附带 `debug_lines`，例如：

- 当前 stage
- 使用的模型名
- prompt 消息数
- executor 使用的工具名
- prior_messages 数量
- context preview
- 原始模型输出或异常类型

CLI 层的 `_render_model_runtime_error()` 会把这些 debug lines 一起渲染出来。

策略上它不是做“自动修复”，而是优先把出错位置和上下文暴露清楚。

## 6. deterministic fallback：为什么还要保留这条路径

fallback 不是历史遗留，而是产品策略的一部分。

主实现位于 `src/agentos/runtime/app.py`。

### 6.1 它解决什么问题

它主要解决三类问题：

1. 没有配置模型时，系统仍可工作。
2. 基础工具路径可以更稳定、更容易测试。
3. 一些显式 DSL 不需要真实模型也能准确执行。

### 6.2 它怎么展开用户任务

`_expand_user_task()` 决定一条用户任务如何拆成 runtime 步骤：

- `code:` 会被扩展成 `role:planner:*` -> executor steps -> `role:reviewer:*`
- `steps:` 会按 `|` 拆成多步
- 普通任务就保留为一步

这也是 deterministic runtime 能模拟多阶段 coding flow 的基础。

### 6.3 它怎么做决策

`_decide_from_task()` 是这条路径的核心决策器。

当前是纯规则路由，不调用真实模型。支持：

- `knowledge:` -> `load_knowledge`
- `run:` -> `run_command`
- `search:` -> `repo_search`
- `read:` -> `file_read`
- `write:` -> `file_write`
- `patch:` -> `file_patch`
- `test:` -> `test_run`

如果都不匹配，就直接返回 `respond`，提示用户使用显式 DSL。

### 6.4 LangGraph 状态机里有哪些节点

`_build_graph()` 里构建了完整状态机，主要节点包括：

- `initialize_loop`
- `prepare_context`
- `planner_role`
- `model_decide`
- `approval_gate`
- `tool_execute`
- `respond_directly`
- `reviewer_role`
- `background_reentry`
- `finalize_iteration`

这里虽然函数名里有 `model_decide`，但当前 fallback 路径的决策并不真的调用模型，而是把规则路由结果包装成结构化 decision。

这条状态机的价值是：

- 即使不用真实模型，也能沿用统一的 state、trace、context、role record 结构。
- 模型路径和 fallback 路径在“可观察性”上尽量一致。

## 7. context 策略：为什么不是直接把历史消息全丢给模型

持续交互的关键不是“有 session”，而是“session 怎么压缩、筛选、预算化”。

这部分的核心对象是：

- `ContextManager`
- `ContextPolicyRuntime`
- `ContextLifecycleManager`
- `LayeredMemory`

### 7.1 `ContextManager` 做什么

`src/agentos/context/manager.py` 负责三件事：

1. 存取会话消息
   - `save_session()`
   - `load_session()`

2. 存取 layered memory
   - `save_memory()`
   - `load_memory()`

3. 为某个 role 准备 context
   - `prepare_role_context()`

`prepare_role_context()` 是主入口。它会先让 lifecycle manager 维护 memory，再调用 policy runtime 生成 context bundle。

### 7.2 `LayeredMemory` 为什么分层

`src/agentos/context/models.py` 定义了几层长期记忆：

- `recent_messages`
  最近几条对话消息的结构化快照

- `working_memory`
  当前目标、约束、活跃计划、已完成动作、未决问题、会话摘要

- `user_preferences`
  偏好语言、输出偏好、协作偏好

- `tool_facts`
  从历史工具结果提炼出的硬事实

- `workspace_state`
  顶层目录、最近读取文件、最近写入文件、触达文件

- `failure_memory`
  历史失败与失败原因

- `session_summary`
  一行摘要

- `lifecycle_audits`
  每次上下文维护前后的预算和压缩记录

设计思路是：不要把所有信息都当“聊天记录”，而是尽量提升成结构化状态。

### 7.3 `ContextLifecycleManager` 的策略是什么

`src/agentos/context/lifecycle.py` 负责把当前 state 和最近消息提炼成 layered memory。

它的策略大致是：

1. 从最近消息里提取工作目标、约束、问题和语言偏好。
2. 从历史工具结果里提取 `ToolFact`。
3. 从失败工具结果里提取 `FailureFact`。
4. 从工具结果和 completed tasks 推导 `WorkspaceState`。
5. 如果内容过大，压缩较老的 `recent_messages` 和 `tool_facts`。

当前压缩触发条件主要有：

- `trigger_reason` 是 `session_resume`、`role_handoff`、`turn_complete`、`large_tool_output`
- 估算大小超过 `ACTIVE_THRESHOLD_CHARS`
- 某条 tool fact summary 太长

策略上它不是“高级向量记忆”，而是更工程化的混合式压缩：

- 先提炼结构化硬事实
- 再在必要时缩减层数和数量
- 可选启用小模型做 semantic compression

### 7.4 `ContextPolicyRuntime` 如何为不同 role 选不同上下文

`src/agentos/context/policy.py` 的核心不是存储，而是“选什么给谁看”。

它通过 `RunnableParallel` 先并行取出：

- `task_hints`
- `history_entries`
- `tool_results`
- `execution_trace`
- `workspace_signals`
- `memory_state`
- `context_audit_records`
- `role_name`

然后在 `_assemble_bundle()` 里合成为 bundle。

关键策略有两个：

1. 每个 role 的 `role_view` 不一样
   - planner 关注任务拆解和 working memory
   - executor 关注执行相关历史、工具结果、workspace
   - reviewer 关注近期 tool results、tool facts、failure memory

2. 每个 role 的预算不一样
   - planner：偏重 `working_memory`
   - executor：偏重 `tool_facts` 和 `workspace_state`
   - reviewer：偏重 `tool_facts` 和 `failure_memory`

这就是“同一个 session，不同角色看到的上下文不是同一份原始历史”的实现基础。

## 8. 工具层策略：为什么说是 LangChain-native tool runtime

工具层实现位于 `src/agentos/tools/registry.py`。

### 8.1 现有工具有哪些

当前内置工具包括：

- `shell_command`
- `knowledge_load`
- `repo_search`
- `file_read`
- `file_write`
- `file_patch`
- `test_run`

这些工具都通过 `StructuredTool.from_function(...)` 注册成 LangChain tool，因此既能被 deterministic runtime 调用，也能被 model-backed executor 的 ReAct agent 调用。

### 8.2 `ToolRegistry.invoke()` 负责什么

`invoke()` 做了三件事：

1. 解析 `_approved` 这类运行时参数
2. 在 `tool_runtime_context(...)` 中执行目标 tool
3. 把返回值包装成统一的 `ToolResult`

最终每条工具结果都有：

- `tool_name`
- `status`
- `summary`
- `payload`

这使得：

- session 可落盘
- reviewer 可消费
- context lifecycle 可提炼 `ToolFact`
- CLI 可以统一渲染

### 8.3 工具层当前采用的几个策略

1. shell/test 命令都走审批策略
   通过 `CommandApprovalPolicy.evaluate(...)` 决定是否需要 `--approve`。

2. 文件操作被限制在 workspace 内
   `_resolve_workspace_path()` 会拒绝越界路径。

3. `repo_search` 优先用 `rg`
   如果没有 `rg`，才回退到 Python 搜索。

4. 工具调用结果会被收集
   `_emit_tool_record()` 会把结果 append 到当前 collector。

当前这层的主要边界也很明显：

- `repo_search` 和 `shell_command` 的输出还可能过大。
- JSON-safe 序列化还没统一做，`bytes` 仍可能引发问题。

## 9. session 与持续交互：为什么这个项目能“记住上一轮”

### 9.1 turn state 存在哪里

`SessionManager.record_turn()` 会把每轮执行结果写到：

- `.agentos/sessions/<session_id>/turn_0001.json`
- `.agentos/sessions/<session_id>/turn_0002.json`

同时更新：

- `.agentos/sessions/<session_id>/session.json`

其中 `turn_xxxx.json` 里会保存本轮的完整 `state`。

### 9.2 context 消息和 session state 不是一回事

这里有两个经常容易混淆的持久化层：

1. `SessionManager`
   保存的是 turn 级 state，偏 runtime 观测和恢复。

2. `ContextManager`
   保存的是下一轮模型复用的消息 transcript 和 layered memory。

也就是说：

- session 负责“系统状态恢复”
- context 负责“模型上下文复用”

### 9.3 resume 时怎么恢复

`SessionManager.build_resume_state()` 会从上一个 turn 的 `state` 提取：

- `pending_tasks`
- `completed_tasks`
- `step_outputs`
- `tool_results`
- `role_records`
- `context_policy_records`
- `memory_state`
- `context_audit_records`

如果上轮已经完成，没有待执行任务，就把这些运行中状态清空，只保留必要的历史痕迹。

这个策略意味着：

- resume 更像“从上轮 unfinished work 继续”
- 而不是无脑把整份 state 原样接着跑

## 10. role 的设计目标：为什么非要 planner / executor / reviewer

`src/agentos/runtime/roles.py` 中的 role 设计很轻量，但作用明确。

### 10.1 planner

目标是把复杂任务先转成更清晰的执行范围，而不是直接开始动工具。

当前内置 `PlannerRoleAgent.run()` 主要是读取 pending steps，输出“准备了几个 executor step”的摘要。它更像一个 inspectable protocol，而不是强智能规划器。

### 10.2 executor

目标是实际执行任务。

在 deterministic runtime 里，executor 的价值是把工具执行结果包装成统一 role record。

在 model-backed runtime 里，executor 才是真正的 ReAct agent，负责：

- 决定是否调工具
- 调哪个工具
- 结合工具结果形成回答

### 10.3 reviewer

目标不是重新做任务，而是收尾验证。

当前 reviewer 有两层：

- 轻量内置 reviewer：检查最近工具结果里是否存在失败
- 真实模型 reviewer：判断 executor 输出是否 grounded

这种设计的价值是：

- 主路径里保留一个验证角色
- fallback 里也能保留最小 reviewer 结构
- role record / handoff / trace 的数据模型保持统一

## 11. 持续交互主链路里最值得关注的几个策略

如果你要理解“这个项目为什么不是简单包一层 LangChain”，下面这几条最重要。

### 11.1 双持久化策略

它同时保存：

- 一份 turn state
- 一份给模型下轮复用的安全 transcript

这样做比只存 chat history 更适合产品化，因为系统状态和模型输入不是一回事。

### 11.2 role-aware context

planner、executor、reviewer 看到的是不同的 context 视图，而不是同一份聊天记录。

### 11.3 deterministic fallback 不是备胎，是地基

很多 CLI、测试、工具和恢复逻辑都先在 deterministic runtime 下成立，再叠加真实模型路径。

### 11.4 inspectability 优先

整个系统到处都在保留“可检查记录”：

- `execution_trace`
- `tool_results`
- `role_records`
- `role_handoffs`
- `context_policy_records`
- `context_audit_records`

这说明它的目标不是单纯做一个好用的对话 agent，而是做一个能解释自己如何工作的终端产品原型。

## 12. 当前已经暴露出的边界

从代码和最近的实际交互来看，当前最明显的边界有这些：

1. 工具结果体积控制还不够
   大搜索结果可能把超长文本直接回灌给模型，触发 provider 400。

2. JSON-safe 序列化没有统一治理
   如果工具结果里混入 `bytes`，会在 state 或 CLI 输出时出错。

3. tool output 裁剪策略还弱
   目前很多工具仍倾向于返回完整 stdout/stderr。

4. fallback 的“智能性”较弱
   deterministic runtime 的路由本质上还是显式 DSL + 规则决策。

5. semantic compression 默认关闭
   长期记忆当前主要还是结构化提炼 + 数量裁剪，而不是强语义记忆系统。

## 13. 读代码建议

如果你打算继续增强这个项目，建议按下面的目标来读：

1. 想理解 shell 主链路
   先读 `cli.py` 和 `app.py`

2. 想理解真实模型路径
   读 `runtime/model_backed.py`

3. 想理解 fallback 和状态机
   读 `runtime/app.py`

4. 想理解上下文与长期记忆
   读 `context/manager.py`、`context/policy.py`、`context/lifecycle.py`

5. 想理解工具系统
   读 `tools/registry.py`

6. 想理解持久化和恢复
   读 `sessions/manager.py`

## 14. 一句话总结

`agentOs` 的核心不是“接了 LangChain 调模型”，而是把终端交互、role 工作流、结构化上下文、工具系统、session 持久化和 fallback 路径接成了一条可持续运行的 agent shell 主链路。
