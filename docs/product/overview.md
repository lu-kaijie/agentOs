# agentOs 产品概览

## 这是什么

`agentOs` 是一个用 `LangChain` 和 `LangGraph` 实现的 coding-agent shell。目标不是做教学 demo，而是做一个接近真实产品形态的终端 agent。

它的核心形态是：

- 安装后通过 `agentos` 启动
- 进入常驻交互式 shell
- 围绕代码阅读、搜索、文件修改、测试执行、会话恢复和状态观察来工作

## 当前能做什么

- 连续多轮自然语言交互
- 真实模型驱动的 planner / executor / reviewer 工作流
- LangChain-native tools 执行文件读取、搜索、写入、patch、测试等操作
- 持久化 session，并支持 `session-show`、`resume`、`watch`
- 对长会话做主动上下文整理，保留用户画像、显式事实、任务状态、工具事实、失败记忆和生命周期审计
- 可选使用模型结构化抽取记忆，并在失败时回退到确定性抽取

## 当前不能做什么

- 还不是完整商业级的 Claude Code 替代品
- 还没有复杂的多 subagent 常驻编排与主动推送 UI
- 还没有仓库语义检索、向量检索或更强的 repo-level understanding
- 上下文压缩和结构化记忆已经可用于长会话测试，但文件内容强制重读、同一路径工具调用去重等策略还需要继续增强

## 适合谁

- 想做自己的 coding-agent 产品原型的人
- 想看一个 LangChain / LangGraph 在真实 CLI agent 里的组合方式的人
- 想把项目作为工程展示、面试项目或后续创业原型的人
