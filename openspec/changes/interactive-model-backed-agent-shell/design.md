## Context

当前 `agentOs` 第三条 change 已经形成了 coding-agent 骨架：有 session persistence、structured tool registry、task-aware context bundle 和受控的 `planner / executor / reviewer` workflow。但这一版仍然保留了四个明显的产品性边界。第一，`role` 仍然是 runtime 图中的硬编码阶段，而不是具备独立输入输出协议的 agent-role abstraction。第二，`tool` 虽然已经结构化，但还没有切到 LangChain 原生的 tool schema、tool binding 和模型驱动调用主路径。第三，`context` 仍然依赖手写 bundle 规则，不是可配置的 policy / retriever / compressor pipeline。第四，runtime 还没有真正调用大模型 API，因此系统仍未跨过“能真实使用”的门槛。

下一条 change 的目标不是做一个继续偏教学的中间层，而是尽快做出一个常驻交互式、真实模型驱动的 agent shell。在此基础上，role、tool、context 和 model 四层只要适合用 LangChain / LangGraph，就优先直接使用，而不是为了保留自定义骨架刻意绕开框架。

## Goals / Non-Goals

**Goals:**
- 提供一个常驻交互式 CLI shell，支持连续输入、连续输出、连续 session 和记忆复用，而不是每轮重新发一条命令。
- 为 `planner / executor / reviewer` 定义统一的 agent-role 协议，包括 role 输入、role 输出、handoff 记录和 role-local state view。
- 让 tool runtime 以 LangChain tool abstraction 为主实现，同时只保留与 harness、安全边界和持久化 schema 强绑定的最小内部补位层。
- 为现有 context bundle 体系增加可配置的 context policy、retriever 和 compressor pipeline，替换当前手写选择规则。
- 让 role agent 能显式消费 `context_bundle`、`tool_results`、task state、workspace signals 和真实模型输出，而不是依赖硬编码函数上下文。
- 接入真实模型 API，并确保至少一条 planner/executor/reviewer 路径可在受控模式下完成真实模型推理和工具调用体验。
- 尽量直接复用 LangChain / LangGraph 原生能力，例如 tool binding、structured tool schema、checkpoint/state、streaming、message history 和 runnable composition。

**Completion Standard:**  
这条 change 完成后，项目应当呈现为一个“基于 LangChain / LangGraph、真实模型驱动、常驻交互式、可连续使用的 Claude Code 风格 agent shell 原型”。验收重点不是抽象是否优雅，而是你能否打开一个持久 shell，在同一窗口里连续和 agent 工作，并让 agent 真实复用 tool、context、role、session 和 delegated work 能力。

完成态还必须覆盖高频核心场景：
- 阅读和理解代码
- 搜索仓库与定位相关文件
- 修改、写入和 patch 代码
- 运行测试并根据结果继续修复
- 在同一会话内持续推进多轮 coding 任务
- 中断后恢复并继续先前任务

**Non-Goals:**
- 这一条 change 不直接实现完全开放式的多 agent 自治协商。
- 不在这一条 change 中一次性删除全部 deterministic fallback。
- 不在没有明确定义 role protocol 的前提下直接引入复杂 remote agent、distributed agent 或 plugin marketplace。

## Decisions

### 1. 常驻 shell 是这条 change 的验收标准，不是附带体验层

这一条 change 的主要验收标准应是：用户可以启动一个常驻交互式窗口，连续与 agent 对话，并让 agent 在同一会话中持续使用工具、上下文、role workflow 和 session persistence。

理由：
- 当前最重要的验收标准已经不是“抽象是否优雅”，而是“产品能不能连续工作”。
- 只有交互式 shell 成立，真实模型接入、context policy 和 role abstraction 的价值才会被完整验证。

备选方案：
- 继续以单命令 CLI 为主，把 shell 放到后续 change。放弃，因为这会继续延后“真正能用”的门槛。

### 2. 先把 role 提升为受控 agent abstraction，再决定是否多实例化

`planner / executor / reviewer` 将先提升为统一的 `RoleAgent` 抽象，而不是继续扩展硬编码节点函数。

理由：
- 这样可以保留当前单图、可检查、可测试的优势。
- 也能让你先学清楚“agent”最本质的边界：输入、输出、handoff、state，而不是一开始就陷入多实例编排。

备选方案：
- 直接把每个 role 做成完全独立子图或多线程 agent。放弃，因为当前教学复杂度过高，且会把注意力从 role 协议本身转移到并发编排。

### 3. 优先直接用 LangChain / LangGraph，可保留最少必要内部边界

只要当前某一层已经明显属于 LangChain / LangGraph 的强项，就优先直接接入，而不是继续保留过多自定义替代层。内部协议只保留那些与 harness、安全边界、持久化 schema 直接绑定的部分。

理由：
- 现在产品可用性优先于教学分层美观。
- 你已经明确要求“当前代码里能用这两个框架的地方就尽量用，直接用”。

### 4. Tool 层默认直接采用 LangChain runtime，自定义层只做边界补位

现有 `ToolRegistry / ToolInvocation / ToolResult` 不再作为未来主工具运行时的中心抽象；下一条 change 中，tool schema、binding 和 invocation 默认直接建立在 LangChain tool runtime 之上。内部自定义层只保留那些与 harness 执行边界、安全审批、工作区约束和持久化结果直接绑定的部分。

理由：
- 你已经明确要求“能用框架的就直接用框架”，tool 是最适合直接切到框架的一层。
- LangChain 已经提供了足够成熟的 tool schema、binding 和 execution 接口，没有必要为了保留自定义骨架继续套一层主运行时。

备选方案：
- 继续以内置 registry 为主，再在外层补一层适配。放弃，因为这会继续拖慢产品可用性推进，也违背你现在的框架优先原则。

### 5. role handoff 必须显式持久化，而不是隐式藏在 trace 文本里

新增 role handoff record，记录：
- 来源 role
- 目标 role
- handoff summary
- 相关 context source
- 相关 tool result 引用

理由：
- 这能让 role workflow 从“阶段序列”升级为“inspectable agent handoff graph”。
- 也方便后续 CLI / chat 展示和恢复执行。

### 6. LangChain tool runtime 先解决 schema / binding / invocation，不急着一次性接最复杂自治

这一条 change 先做三层直接接入：
- LangChain-native tool schema
- LangChain-native tool binding
- 与本地 harness / policy / persistence 的补位适配

理由：
- 先把 tool 定义层切到框架主路径，后面模型调用、交互式 shell 和 role workflow 才不会继续被双层抽象拖累。
- 这也更符合你现在的产品优先策略。

### 7. Context 必须提升为 policy runtime，而不是继续堆手写 bundle 规则

现有 `build_context_bundle(...)` 继续作为早期实现参考，但下一条 change 需要把上下文构造拆成独立 policy pipeline：
- task selector
- history reducer / compressor
- workspace retriever
- role-specific context view

理由：
- 如果 role 和 tool 都抽象升级后，context 仍停留在硬编码规则，会立即成为新的瓶颈。
- 这也是 LangChain 更值得深入学习的一层：retriever、document transform、compression、runnable composition。

### 8. 真实模型调用必须进入主链路，而不是继续停留在预留接口

下一条 change 必须至少接通一条真实模型调用路径，让 agent 能在实际 API 下运行，而不是只保留 deterministic 逻辑。

理由：
- 你最开始的目标就包括“最后能用”，而不是一直停留在骨架。
- 真正接 API 之后，LangChain tool runtime、role protocol、context policy 的价值才会被实际验证。

## Risks / Trade-offs

- [Role abstraction 设计过重] → Mitigation：先限定在 planner / executor / reviewer 三种内建 role，不做任意 role plugin 化。
- [交互式 shell 引入长期运行状态后故障面增大] → Mitigation：第一版 shell 先限制在单进程本地会话，并复用现有 session persistence 做恢复。
- [直接切到 LangChain tool runtime 可能引入框架耦合] → Mitigation：只保留与 harness、安全和持久化强绑定的最小补位层，避免重新长出 registry-first 双层抽象。
- [Context policy 过早复杂化] → Mitigation：第一版只覆盖 task selector、history reducer、workspace retriever 和 role-specific view 四个稳定部件。
- [role handoff 过度形式化导致实现成本升高] → Mitigation：第一版只记录必要字段，先满足 inspectability 与 resume。
- [真实模型接入后测试稳定性下降] → Mitigation：保留 deterministic fallback、为 API 路径提供可隔离的集成测试和显式开关。

## Migration Plan

1. 建立常驻交互式 shell，先打通连续输入输出、会话绑定、streaming 输出和退出/恢复约定。
2. 接入真实模型 API，并让 shell 至少有一条稳定主链路可以真实调用模型。
3. 抽象当前 planner / executor / reviewer 为统一 role protocol，并把现有 role records 升级为 agent-role records。
4. 引入 role handoff record 和 role-local state view，接到 session persistence。
5. 将当前 context bundle 规则拆成可配置的 context policy / retriever / compressor pipeline。
6. 将现有主要工具迁移到 LangChain-native tool runtime，并只在 harness、安全和持久化边界保留最小补位层。
7. 在 runtime 中增加 role agent 调度层，使 role 选择和 handoff 不再依赖硬编码节点分支。

## Open Questions

- 第一版 `RoleAgent` 是否只在单进程单图内执行，还是需要立即支持子图嵌套？
- LangChain tool runtime 第一版是否采用 `StructuredTool` 为主，还是同时保留更通用的 Runnable 适配？
- 第一版真实模型接入时，tool 选择是先替换 executor，还是先让 planner 参与工具选择？
- context policy 第一版是否直接引入 LangChain retriever abstraction，还是先以最薄的内部 policy 组合 LangChain 组件落地？
