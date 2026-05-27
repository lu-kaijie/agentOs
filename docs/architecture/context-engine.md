# 上下文引擎

如果你想看字段级、预算级、生命周期级的完整说明，优先读：

- [上下文管理机制详解](context-management-deep-dive.md)

## 它解决什么问题

如果 agent 只是不断把完整历史塞进 prompt，很快会遇到：

- token 爆炸
- 工具输出过长
- 用户约束被淹没
- 失败历史无法稳定保留

所以 `agentOs` 做了一个产品化方向的 context engine。

## 当前结构

当前上下文不是单一摘要，而是分层整理：

- `user_profile`
  - 稳定用户画像，例如偏好语言、回答风格、长期输出偏好
- `remembered_facts`
  - 用户明确要求记住的事实，包含 key、value、scope、source、confidence、状态和时间戳
- `task_state`
  - 当前目标、已完成动作、开放问题、活跃计划
- `working_memory`
  - 当前目标、用户约束、阶段总结
- `tool_facts`
  - 最近工具调用得到的硬事实
- `failure_memory`
  - 最近失败与风险
- `lifecycle_audits`
  - 什么时候因为什么触发了整理

## 触发时机

会在这些场景主动整理：

- 会话变长
- 工具输出过大
- role 切换
- session resume
- 一轮任务完成后的后处理

## 压缩策略

当前是混合式：

- 硬事实尽量结构化抽取
- 显式用户事实和用户画像进入结构化记忆层
- 语义信息进入工作记忆
- 最终 prompt 根据 role 和预算组装为 `context_bundle`
- 可选用模型参与更强语义压缩
- 可选用模型通过结构化 tool/function output 生成 `MemoryDelta`

当前默认预算偏向真实模型上下文，而不是早期 smoke test 小窗口：

- active memory 压缩阈值约 `24000` 字符
- session 消息压缩保留最近约 `24` 条
- lifecycle 压缩后仍保留最近约 `12` 条消息和 `10` 条工具事实
- context bundle 默认约 `8000` 字符

## 与完整生产级还有什么差距

- 还没有更细的长期记忆检索策略
- 还没有更复杂的 token budget 自适应
- 还没有更丰富的记忆质量评估与清理策略
- 文件内容类请求仍需要更强的“当前轮必须读取相关文件”策略
- 同一轮同一路径工具调用还可以继续做去重
