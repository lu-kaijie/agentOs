# AgentOS 项目演进说明

AgentOS 最初是一个 Coding Agent 原型，用来验证终端交互、工具调用和本地代码修改流程。随着功能增加，早期结构中的交互逻辑、工具执行、工作区状态、上下文处理和扩展点逐渐耦合，继续迭代会比较吃力。

当前版本在早期原型基础上重新整理了实现，重点是把项目收敛成更清晰的 Python 运行时。

## 演进目标

- 提供更实用的终端 Coding Agent 体验。
- 将 Agent 主循环和 TUI 展示解耦。
- 让工具执行变成显式、可测试、可拦截的结构化流程。
- 给高风险 shell 和文件操作增加权限控制。
- 支持 MCP 工具，同时不把 MCP 逻辑硬耦合到核心运行时。
- 增加项目指令、记忆和上下文压缩机制。
- 支持子 Agent、teammate 和基于 worktree 的任务隔离。
- 将运行配置集中到 `.agentos/` 和 `~/.agentos/`，保持本地透明。

## 主要变化

- 运行时包名统一为 `agentos`。
- CLI 入口统一为 `agentos`。
- 项目状态统一放到 `.agentos/`。
- 项目指令文件统一使用 `AGENTOS.md`。
- 工具调用统一经过工具注册中心和权限检查器。
- Provider 配置支持 Anthropic、OpenAI 和 OpenAI-compatible API。
- Skills、Hooks、MCP、Memory、Teams、Worktrees 都作为一等模块维护。
- 支持从任意项目目录启动 AgentOS，而不是绑定在 AgentOS 仓库内运行。

## 兼容性说明

当前版本不是早期原型的原地兼容升级。它保留了“本地 Coding Agent 运行时”的项目目标，但围绕新的模块边界、配置方式和 CLI 体验重新整理了实现和文档。

如果旧项目中存在早期配置或脚本，建议迁移到：

- `AGENTOS.md`
- `.agentos/config.yaml`
- `.agentos/skills/`
- `.agentos/permissions.yaml`

用户级通用配置建议放在 `~/.agentos/config.yaml`。
