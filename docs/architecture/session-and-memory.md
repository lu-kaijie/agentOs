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

- 当前目标摘要
- 用户约束
- 最近工具事实
- 最近失败
- 生命周期审计

## 为什么需要两者分开

- session 负责“完整状态可恢复”
- memory 负责“上下文可持续”

一个系统可以有 session，但 memory 很弱；也可以有 memory 摘要，但没有可恢复 session。`agentOs` 现在两者都已经具备基础骨架。
