## Context

当前项目已经有第一条 change 的学习型基础底座，以及第二条 change 规划中的真实 agent loop、后台结果回流、委托执行和权限策略。第三条 change 不再以“让 runtime 成立”为主要目标，而是解决“怎样把这些能力整合成一个可以持续使用的 coding-agent 工具”。

这一阶段要特别注意两件事。第一，不能因为追求可用性而把系统做成黑盒，仍要保持教学可读性。第二，不能把所有高级能力都挤进一个无边界的 monster runtime，所以必须继续按照能力边界拆层推进。

## Goals / Non-Goals

**Goals:**

- 形成可查看、可恢复、可回放的 session / task 持久化基础。
- 建立更完整的 coding-agent 工具体系，而不再只停留在 shell execution 边界。
- 深化上下文工程，让 runtime 能基于任务和工作区做更有针对性的上下文组织。
- 引入更接近真实 coding-agent 的角色化执行路径，但保持受控和可观察。
- 把 CLI 体验推进到更适合连续使用和调试的阶段。

**Non-Goals:**

- 在这一条 change 中实现完整 GUI、Web IDE 或远程控制台。
- 一次性做完生产级插件市场、远程沙箱或复杂分布式执行。
- 让 agent 进入高自治黑盒模式，以至于难以解释决策和状态流转。
- 在没有清晰边界的情况下盲目堆叠更多工具和角色。

## Decisions

### 1. 先做“可恢复的使用面”，再追求更多自治

第三条 change 的优先级应先落在 session persistence、resume、watch/poll、logs、trace replay 和上下文可控性上，而不是先增加更多自治行为。

理由：
- 第二条 change 后系统会首次具备更真实的 loop 和后台回流，如果没有恢复、轮询和查看能力，学习和调试成本会急剧上升。
- “基本可用”首先意味着你能回来继续工作，而不是每次都从头开始。
- 在真正引入常驻 daemon 或主动推送之前，`resume` 与有边界的 `watch/poll` 是更稳的过渡形态。

### 2. 工具体系必须标准化，而不是继续堆独立命令

这一阶段应建立 tool registry、标准输入输出结构、错误模型和受控 patch/apply 路径，使工具调用成为 runtime 的一等能力。

理由：
- coding-agent 的核心价值最终落在“看代码、改代码、跑测试、验证结果”这些工具链上。
- LangChain / LangGraph 的高级实践也更适合建立在标准 tool 接口上。

### 3. 上下文工程要围绕“任务相关性”而不是纯堆积记忆

第三条 change 应把上下文工程重点放在相关性选择、压缩和检索，而不是仅仅累计更多 message history。

理由：
- 真实 coding-agent 很快会遇到上下文膨胀问题。
- 这也是 LangChain 更值得学习的一层：retrieval、compression、selection 和 merge。

### 4. 角色化工作流先做受控职责，不做自由多 agent 自治

planner / executor / reviewer 的引入应保持明确边界，例如只允许 planner 负责计划更新，executor 负责工具执行，reviewer 负责验证和反馈。

理由：
- 这样更适合教学与调试。
- 也能避免过早进入不可解释的多 agent 协商系统。

### 5. CLI 必须服务于“持续使用”而不是“单次演示”

应增加会话查看、恢复、有限轮询、日志、流式轨迹等命令，让你不必每次都依赖底层 JSON 输出来理解 runtime。

理由：
- 当系统复杂度升高后，只靠 `run` 一个命令和大 JSON 输出会迅速失去可用性。
- 这会让每一步的体验更接近真实工具，而不仅是 spec 演示。

### 6. 先做 session 级持续运行，再决定是否进入 daemon / push 架构

第三条 change 应优先支持 session 级的 `resume` 与 `watch/poll`，让一个已持久化 session 能在检测到后台结果后继续推进；不要求这一阶段就引入常驻监听进程或完整主动推送。

理由：
- 这样能把“后台结果回流”升级成更接近可用的持续运行体验，但不会过早引入复杂守护进程生命周期。
- `resume/watch` 能和 session persistence、CLI、trace replay 自然绑定，边界更清晰。

## Evolution Path

围绕后台结果与持续运行体验，建议按下面的演化路径推进：

1. 第二条 change：启动时扫描未消费后台结果，并将其重新注入 loop。
2. 第三条 change 前半段：支持 `session resume`，从持久化状态继续一个已有 session。
3. 第三条 change 中段：支持有边界的 `session watch/poll`，在指定 session 上轮询后台结果并自动续跑。
4. 第三条 change 后半段或第四条 change：再评估是否引入常驻 daemon、事件驱动 resume 或主动推送。

## Risks / Trade-offs

- [会话与日志持久化会引入更多状态文件] → 缓解：保持目录结构明确，并为每类状态定义稳定 schema。
- [工具体系扩展过快可能抬高权限风险] → 缓解：复用第二条 change 的 policy layer，并把新工具全部纳入统一策略判断。
- [上下文工程容易做成难以理解的隐式魔法] → 缓解：让每次上下文选择和压缩都产生可检查痕迹。
- [角色化流程可能和 delegated execution 重叠] → 缓解：第三条 change 只定义 coding workflow 层，保留第二条 change 的 execution/control 分层。
- [过早引入常驻监听会把项目拖入进程生命周期和并发恢复问题] → 缓解：第三条 change 先限制在 session 级 `resume/watch`，daemon/push 视后续阶段再定。

## Migration Plan

建议按如下顺序推进：

1. 建立 session / trace 持久化、恢复和回放基础。
2. 为已持久化 session 增加 `resume` 与有限 `watch/poll` 能力，先打通后台结果驱动的续跑体验。
3. 扩展 tool registry，并先打通文件读写、搜索、patch/apply、测试执行等关键工具。
4. 引入高级上下文工程，包括工作区索引、摘要压缩和任务相关检索。
5. 在已有 loop 之上接入 planner / executor / reviewer 的受控工作流。
6. 整理 CLI 体验、文档、演示命令与 milestone tag。

## Open Questions

- 第三条 change 的会话恢复是否需要精确 checkpoint resume，还是先支持“从持久化状态重建并继续”？
- 第三条 change 的 `watch/poll` 第一版是固定时间间隔，还是支持更显式的单次 `check-and-resume` 模式？
- 工具 registry 第一版是静态注册，还是要提前保留插件化扩展接口？
- reviewer 角色第一版是否只做规则化验证，还是允许模型参与审查反馈？
