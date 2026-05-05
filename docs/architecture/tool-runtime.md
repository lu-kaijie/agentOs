# 工具运行时

## 当前形态

`agentOs` 的工具层已经不是手写函数直接硬调，而是切到了 LangChain-native tool runtime。

核心构成：

- `ToolRegistry`
- LangChain `StructuredTool`
- 本地 harness 边界
- 工作区 / 文件系统访问规则

## 典型工具

- `repo_search`
- `file_read`
- `file_write`
- `file_patch`
- `test_run`

## 执行链路

1. runtime 决定要调用哪个工具
2. 通过 registry 取出对应 LangChain tool
3. 由 tool 执行底层文件或命令操作
4. 把结构化结果回写到 runtime state
5. reviewer 可以直接消费这些工具结果

## 为什么这样做

这样做的好处是：

- tool schema 更规范
- 与 LangChain runnable / agent 体系更兼容
- 后续继续增加工具更自然
- 仍然保留自己的 harness 与安全边界
