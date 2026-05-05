## Context

当前仓库已经完成第一条基础 change，建立了 harness 执行边界、LangGraph runtime、任务控制面、上下文管理、后台执行、隔离工作区和 coordination control plane。这个阶段的成果适合作为学习型底座，但还没有形成一个更真实的 coding-agent 运行闭环。

目前最关键的缺口有四个。第一，runtime 仍然是“单次走到 END”的图，没有真正的继续决策能力。第二，后台任务可以运行，但结果不会自动重新进入图，无法形成真正的异步 agent workflow。第三，multi-agent coordination 目前主要是控制面，还没有把 work unit 接成真实的受控执行。第四，审批逻辑还只是基础示例，没有上升为可扩展的权限策略。

这条 change 的目标不是一次性把 `agentOs` 做成完整 Claude Code 成品，而是把当前底座推进到“更接近真实 agent”的下一阶段，同时继续保持第一条 change 的学习节奏：小步实施、每阶段可体验、每阶段可打 tag、每阶段都能让你学到 LangChain / LangGraph 的新用法。

## Goals / Non-Goals

**Goals:**

- 让 runtime 从单次有向流程推进为可恢复、可继续推进的 agent loop。
- 让后台结果回流到 runtime 状态中，使异步执行真正成为 loop 的一部分。
- 把 coordination control plane 接成第一版受控 delegated execution 流程。
- 提升权限与审批能力，使工具执行边界更清晰、更可解释。
- 在实现过程中继续扩大 LangChain / LangGraph 的实践覆盖面，并保持项目的教学可读性。
- 保持第一条 change 的约束：继续分阶段实现、继续锁版本依赖、继续每步可打 tag 并适合上传 GitHub。

**Non-Goals:**

- 这一条 change 内就完整复刻 Claude Code 的全部行为。
- 一次性做完生产级权限系统、远程沙箱、复杂多进程调度或完整 UI。
- 在这一阶段引入过多真实模型调用成本，导致学习重点被 API 细节淹没。
- 让 runtime 过早走向难以解释的高复杂度自治行为。

## Decisions

### 1. 先把“可继续运行”做成明确的 loop，再扩大智能性

第二条 change 会先解决“图为什么能继续往前跑”的问题，而不是优先增加更多工具或更多角色。

理由：
- 当前最大的结构性缺口是没有 loop，而不是缺更多节点。
- 你最想学的是 agent 如何持续推进工作，这一点必须先在运行形态上成立。
- 只有 loop 建立后，后台结果回流、委派结果回流、权限审查才有统一承接面。

备选方案：
- 先扩展更多工具和角色，再回头改 loop。否决，因为会让系统复杂度增加，却仍然停留在“一次性执行”阶段。

### 2. 后台结果回流必须显式建模到 runtime 状态

后台任务完成后，不应只停留在 `.agentos/background/` 文件里，而应在下一轮 runtime 决策中作为显式输入重新进入图状态。

理由：
- 这能把“后台执行”从外部辅助能力推进为 agent loop 的一部分。
- 这也是理解真实 agent runtime 的关键教学点：外部世界的变化如何被重新感知。
- LangGraph 非常适合展示这种状态回流。

备选方案：
- 保持人工轮询 CLI，不接进图。否决，因为无法学到异步 agent loop 的核心。

### 3. delegated execution 先做受控角色流，不做黑盒自治

第二条 change 中的多 agent 扩展应先采用“coordinator + bounded role execution”的方式，而不是直接让多个独立 agent 黑盒并发。

理由：
- 这更容易调试，也更容易学习。
- 现在已有的 coordination control plane 已经提供了良好基础。
- 这能在不失控的情况下逐步把 work unit、workspace、background execution 串起来。

备选方案：
- 直接做自由并发多 agent。否决，因为当前阶段维护成本过高，且不利于教学。

### 4. 权限体系从“显式策略对象”开始

这条 change 应把当前零散的审批逻辑推进为一个可扩展的策略层，例如按命令类别、工作区、风险级别来判断是否需要批准。

理由：
- 现在的 agent 已经开始具备越来越多执行能力，必须同步提高安全边界表达能力。
- 这能把“审批”从示例逻辑升级成真正的 harness 设计问题。
- 这也让后续引入更真实模型决策时，安全层不需要推倒重来。

备选方案：
- 继续在 runtime 节点里零散写 if/else。否决，因为扩展性差，也难以教学。

### 5. LangChain 的下一步重点是“消息与结构化决策真正驱动 loop”

第一条 change 后半段已经引入了 `langchain_core.messages`、`ChatPromptTemplate` 和 `PydanticOutputParser`。第二条 change 要让这些能力不只是出现在单次 routing，而是进入 loop、回流和 delegated execution 的关键路径。

理由：
- 这更符合你“学会框架而不是只记住 demo”的目标。
- 这样 LangChain 的价值会从“辅助组织 prompt”升级到“参与整个 runtime 的状态演化”。

备选方案：
- 只用 LangGraph，不再深化 LangChain 用法。否决，因为会削弱你学习框架的广度。

## Risks / Trade-offs

- [引入真正 loop 后，状态机会明显复杂化] → 缓解：先做受控 loop，只允许少量明确回流来源。
- [后台结果回流容易让调试链路变长] → 缓解：保留 trace、checkpoint 和落盘状态，保证每一步可观察。
- [delegated execution 容易滑向不可解释的并发系统] → 缓解：先做有角色边界的受控执行，不做完全自治。
- [权限策略过早做重会拖慢推进] → 缓解：先做策略骨架与最小规则集，再逐步丰富。
- [继续扩展框架能力可能让项目偏离“可用系统”] → 缓解：每个新能力都必须绑定真实 runtime 或 harness 问题。

## Migration Plan

第二条 change 建议按以下顺序推进：

1. 将 runtime 从单次图推进为可继续执行的 loop 结构。
2. 将后台结果回流接入 runtime 状态与后续决策。
3. 将 coordination control plane 接成第一版 delegated execution 流程。
4. 将权限与审批逻辑抽象成策略层。
5. 为每一阶段补体验命令、测试、文档和 tag。

回退策略延续第一条 change：每个子阶段都在稳定停止点打 tag，如需回退，直接回退到上一个 milestone tag。

## Open Questions

- 第二条 change 中的 loop 应该优先支持“直到没有可处理事件”为止，还是支持固定步数上限？
- delegated execution 的第一版是否需要真正启动新的 runtime 进程，还是先用单进程模拟不同角色流？
- 权限策略的第一版是纯规则驱动，还是要提前预留模型辅助判断接口？
