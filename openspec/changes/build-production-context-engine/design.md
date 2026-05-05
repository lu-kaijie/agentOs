## Context

当前 `agentOs` 的上下文链路已经有三块基础能力：

- `ContextManager` 负责消息落盘与简单压缩
- `ContextPolicyRuntime` 负责按任务、role、workspace 组装 context bundle
- runtime / model runtime 会在每个 role 步骤前调用 context bundle，并把 bundle preview 送进模型

但这条链路目前仍然是原型级实现：

- 压缩不是自动触发，而是一个显式函数
- 长历史压缩几乎等于字符串截断
- 用户约束、计划、工具事实、失败记录、工作区状态没有分层记忆
- 恢复时主要恢复消息历史和简单 state，而不是恢复结构化工作上下文
- 没有清晰的预算控制，也没有可审计的压缩记录

要让产品真正支持长时间连续协作，这次 change 需要把“上下文管理”升级成“上下文生命周期系统”。

## Goals / Non-Goals

**Goals:**
- 让系统在上下文达到阈值后主动触发整理，而不是只在手动调用时压缩。
- 引入结构化记忆层，把不同类型的信息分开存储和压缩。
- 支持按内容类型采用不同压缩策略，而不是统一文本摘要。
- 让 planner / executor / reviewer 在同一份底层记忆上拿到不同视角的上下文。
- 增加上下文预算与来源审计信息，使每轮模型输入可解释。
- 让 session resume 恢复结构化上下文，而不是只恢复原始消息。
- 明确区分“程序化事实抽取”“模型语义压缩”“系统预算装配”三类职责，避免把上下文工程退化成纯 summary prompt。

**Non-Goals:**
- 这条 change 不做向量数据库或外部知识库服务接入。
- 不在这一条 change 中引入复杂的跨仓库长期用户画像系统。
- 不追求一次性覆盖全部高级检索算法，先在本地文件与会话状态范围内实现可用版本。
- 不重写现有 runtime / role 架构，重点是升级 context engine 并接入现有 runtime。

## Decisions

### 1. 引入 `ContextLifecycleManager`，负责自动触发而不是把压缩逻辑散落在调用点

新增一个生命周期管理层，位于 `ContextManager` 与 runtime 之间，职责包括：

- 检查当前上下文大小、消息数、工具输出大小、role 切换点
- 决定是否触发压缩
- 触发对应压缩器
- 更新结构化记忆层
- 产出审计记录

理由：
- 这样可以把“何时压缩”与“如何压缩”分开。
- runtime 不需要自己判断所有上下文阈值。

备选方案：
- 继续只在 `ContextManager` 里加几个 if。放弃，因为会把生命周期判断和压缩实现继续耦合在一起。

### 2. 采用分层记忆模型，而不是把所有内容都压成一段文本

引入统一的结构化记忆对象，例如：

- `recent_messages`
- `working_memory`
- `user_preferences`
- `tool_facts`
- `workspace_state`
- `failure_memory`
- `session_summary`

其中：
- `recent_messages` 保留最近原始对话
- `working_memory` 保存当前目标、约束、计划、待办、最近关键事实
- `user_preferences` 保存用户语言、输出风格、协作偏好
- `tool_facts` 保存工具输出中的关键事实，不保存全部原始噪声
- `workspace_state` 保存已读/已改文件、工作区信号、关键路径
- `failure_memory` 保存失败命令、失败原因、已否决方案

理由：
- 实际产品里，不同信息的生命周期和重要性完全不同。
- 分层后才能做类型化压缩和 resume 恢复。

### 3. 使用类型化压缩器，而不是统一 reducer

至少定义以下压缩策略：

- `conversation_compressor`
  - 压缩普通对话，保留决策、问题、未完成项
- `constraint_extractor`
  - 提取用户要求、限制、偏好
- `tool_result_compressor`
  - 针对工具输出提取关键事实、关联文件、成功/失败、是否影响后续
- `workspace_state_compressor`
  - 提取已读文件、已改文件、关键工作区线索
- `failure_compressor`
  - 提取失败尝试与原因，避免重复试错

理由：
- 不同类型的信息语义完全不同。
- 工具日志不能和人类对话用同一套压缩方法。

备选方案：
- 只加一个更复杂的 summary prompt。放弃，因为仍然会把所有信息混成一锅。

### 3.1 压缩采用混合式路线，而不是全模型或全规则路线

压缩与记忆整理明确分成三层职责：

- 程序化事实抽取
  - 负责提取结构化硬事实
  - 例如：修改过的文件、工具名、命令、退出码、失败记录、测试通过与否、工作区状态
- 模型语义压缩
  - 负责提取自然语言语义信息
  - 例如：用户真实目标、约束、已确认方案、已否决方案、阶段计划、长对话摘要
- 系统预算与装配
  - 负责决定每层进 prompt 的预算、优先级和裁剪顺序
  - 不把“保留什么”和“丢弃什么”的最终权力交给模型

理由：
- 全部交给模型会带来成本高、速度慢、事实漂移和不稳定的问题。
- 全部手写规则则无法稳定提取复杂语义。
- 混合式路线最接近真实产品工程。

第一版的拆分原则：
- `workspace_state`、`tool_facts`、`failure_memory`、`session_metrics` 优先程序抽取
- `working_memory`、`user_preferences`、`decision_summary`、`conversation_summary` 优先模型压缩
- 所有角色最终看到的 bundle 仍由 policy runtime 按预算显式装配

### 4. 预算控制按 role 和 source 双维度进行

上下文预算不再只看 `max_chars`，而是要有：

- role budget：planner / executor / reviewer 各自预算
- source budget：recent messages / working memory / tool facts / workspace state / summaries 各自预算
- trigger threshold：什么时候触发压缩

第一版可以仍用近似字符预算，但设计上保留向 token budget 迁移的接口。

理由：
- 产品级系统必须控制上下文成本和稳定性。
- 即使短期先不用 tokenizer，也要先把预算系统建出来。

### 5. 上下文选择走“相关性 + 分层 + role view”组合

当前 `ContextPolicyRuntime` 需要升级，不再只拼接已有 summary，而是：

- 从分层记忆里选取相关字段
- 结合当前任务 hint 和 role
- 限制预算
- 生成 role-specific bundle
- 记录用了哪些 source、哪些 reducer、哪些 budget decision

理由：
- 这样才能从“被动拼 context”升级到“主动选 context”。
- 也能确保模型只是参与语义归纳，而不是反向主导整个上下文系统。

### 6. resume 恢复结构化上下文状态

session resume 时需要恢复：

- working memory
- failure memory
- workspace state
- recent tool facts
- recent messages
- last compression records

而不只是恢复原始 turn state。

理由：
- 产品的连续性不应该依赖“重新读完历史”。

### 7. 审计记录作为一等输出

新增 inspectable context audit，例如记录：

- `trigger_reason`
- `before_size`
- `after_size`
- `compressed_layers`
- `retained_layers`
- `dropped_items`
- `budget_allocations`
- `bundle_sources`

理由：
- 如果没有审计记录，后面很难解释 agent 为什么忘了某件事。
- 这对调试产品行为很重要。

## Risks / Trade-offs

- [结构化记忆层引入更多状态复杂度] → Mitigation：先限定记忆层数量，并把持久化模型保持简单、可读。
- [类型化压缩器过多会导致实现分散] → Mitigation：统一通过 lifecycle manager 调度，压缩器只负责单一类型。
- [预算控制如果过于复杂会拖慢交付] → Mitigation：第一版先用字符预算抽象接口，后续再替换为精确 token budget。
- [自动压缩可能过早触发，损失有用原始信息] → Mitigation：保留最近原始消息层，并把压缩触发记录下来以便回溯。
- [resume 结构化恢复会改变当前 session 文件格式] → Mitigation：采用向后兼容字段，保留旧字段读取路径。

## Migration Plan

1. 新增结构化记忆模型与持久化格式。
2. 引入 lifecycle manager 和触发策略。
3. 实现类型化压缩器并接入现有 context manager。
4. 升级 context policy runtime，使其从分层记忆构建 role bundle。
5. 接入 shell / runtime / resume 主链路。
6. 增加审计输出与测试。
7. 用长会话与 resume 场景做回归验证。

## Open Questions

- 第一版是否要直接做精确 token 统计，还是先保留字符预算接口？
- 用户长期偏好记忆是否和 session 记忆分文件保存？
- 是否在 shell 中暴露一个显式命令查看当前 memory / context audit？
