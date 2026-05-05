# 一步一步构建历程

## 阶段 1：先把底座做出来

这一阶段解决的是“先让项目能站住”：

- 仓库基础文件
- Python 环境与依赖锁定
- 初始包结构
- harness 执行边界
- 第一个 LangGraph runtime

这一步的关键不是炫技，而是把后面所有 agent 能力的落脚点准备好。

## 阶段 2：从静态流程变成真实 runtime

这一阶段开始引入：

- loop
- background result re-entry
- delegated execution
- approval / safety 边界

核心变化是：系统不再只是“一次跑完”，而是开始像 agent 一样持续推进任务。

## 阶段 3：补 session、tool、context、role

这一阶段让系统开始“基本可用”：

- session persistence
- session resume
- structured tools
- task-aware context
- role workflow
- interactive CLI

这一步之后，系统已经不只是图结构实验，而是具备真正的 agent 产品骨架。

## 阶段 4：变成模型驱动的交互式 shell

这一阶段完成：

- 常驻 shell
- structured role agent
- context policy runtime
- LangChain-native tool runtime
- model-backed runtime

这一步是从“agent runtime 工程”走向“agent 产品形态”的关键转折点。

## 阶段 5：做产品化收尾

最后两步重点是：

- 安装后直接 `agentos`
- production context engine

到这里，仓库已经从学习型项目变成一个能拿出来演示和继续迭代的产品原型。
