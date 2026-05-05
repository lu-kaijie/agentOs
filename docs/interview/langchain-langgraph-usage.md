# LangChain / LangGraph 用法

## LangGraph 用在了哪里

主要用于 runtime 编排：

- 管理状态流
- 驱动 role / tool / review 工作流
- 支持 loop、resume、context preparation 等链路

它解决的是“流程图和状态机”问题。

## LangChain 用在了哪里

主要用于：

- 模型接入
- runnable 组合
- tool 抽象
- structured tool invoke
- 部分上下文处理管线

它解决的是“模型、工具和 runnable 组件化”问题。

## 哪些地方还是偏自研

- session persistence
- context lifecycle triggers
- budget control
- audit records
- memory persistence
- harness / workspace / approval 边界

这些部分不是不能更框架化，而是当前产品形态下，自研反而更可控。

## 有没有还能继续框架化的地方

有，但不是当前必须项：

- 更深入使用 retriever 接口
- 更复杂的 memory 组合
- 更标准的 agent protocol 适配
