# 核心功能与取舍

## 核心功能

- 可安装的 `agentos` CLI
- 常驻交互式 shell
- LangGraph runtime 编排
- LangChain-native tools
- 真实模型主路径
- session persistence / resume / watch
- 主动上下文整理

## 关键取舍

### 为什么不是直接做大而全的多 agent 系统

因为先把单 session、单工作流、单 shell 做稳定，产品价值更高，也更容易验证。

### 为什么 tool 层保留自有 harness

因为 LangChain 适合做工具抽象和组合，但文件系统边界、命令执行边界和工作区隔离仍然需要产品自己控制。

### 为什么 context engine 没完全依赖框架 memory

因为产品级上下文整理通常要显式控制：

- 触发时机
- 预算
- 生命周期
- 审计记录

这些内容仅靠框架内置 memory 往往不够。
