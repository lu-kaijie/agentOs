# Session 与记忆

## Session

session 是这个项目走向“可用产品”的关键层。

它负责：

- 保存一轮轮对话状态
- 支持 `session-show`
- 支持 `resume`
- 支持 `watch`

如果没有 session，agent 每次都是一次性脚本，很难接近 Claude Code 这类产品体验。

## Memory

记忆并不等于完整历史回放。

当前记忆更像是：

- 用户画像，例如偏好语言、回答长度和协作风格
- 用户明确要求记住的事实
- 当前任务状态
- 当前目标摘要
- 用户约束
- 最近工具事实
- 最近失败
- 生命周期审计

结构化记忆不是只靠压缩后的聊天历史。每轮 context lifecycle 会生成或合并这些层：

- `user_profile`
- `remembered_facts`
- `task_state`
- `working_memory`
- `tool_facts`
- `workspace_state`
- `failure_memory`
- `recent_messages`

如果开启 `AGENTOS_MEMORY_MODEL_EXTRACTION=1`，显式事实和用户画像会优先通过模型 tool/function output 形成 `MemoryDelta`；模型不可用或失败时，系统会回退到确定性抽取。

当前预算已经按真实模型测试调大：session 消息默认保留更长窗口，context bundle 默认约 `8000` 字符，memory lifecycle 在压缩后仍保留最近消息和工具事实的较大窗口。

## 为什么需要两者分开

- session 负责“完整状态可恢复”
- memory 负责“上下文可持续”

一个系统可以有 session，但 memory 很弱；也可以有 memory 摘要，但没有可恢复 session。`agentOs` 现在两者都已经具备基础骨架。

当前已知限制：

- 文件内容类问题最好由模型重新调用 `file_read` 确认当前内容，不能只依赖历史记忆
- 同一轮重复读取同一路径仍可能发生，后续需要在工具策略或运行时层去重
- 长期记忆仍是结构化提炼与数量裁剪，不是向量检索系统
