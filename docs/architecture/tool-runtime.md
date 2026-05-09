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
- `skill_list`
- `skill_load`

## 执行链路

1. runtime 决定要调用哪个工具
2. 通过 registry 取出对应 LangChain tool
3. 由 tool 执行底层文件或命令操作
4. 把结构化结果回写到 runtime state
5. reviewer 可以直接消费这些工具结果

## Skill 工具分层

skills 相关工具故意拆成两层，而不是一次性把 `SKILL.md` 全塞进上下文：

- `skill_list`
  只返回最小 skill catalog，包含 `name`、`description`、`when_to_use`
- `skill_load`
  按层级逐步加载 skill 内容：
  - `summary`
    只返回 skill 元信息，不加载 `SKILL.md` 主体
  - `full`
    加载 `SKILL.md` 主体
  - `reference`
    精确加载某个 `references/*.md`
  - `script`
    返回 skill 脚本路径，供后续 read/execute

这样设计的目的不是工具拆分本身，而是控制上下文成本：

1. 默认上下文只保留最小 catalog
2. executor 需要更多规则时，再主动调用 `skill_list` / `skill_load`
3. 更细的 checklist、example、script 继续按需深读

这和 `agentOs` 当前的上下文策略保持一致：默认 prompt 里只放足够做决策的信息，不预先注入整包技能知识。

## 为什么这样做

这样做的好处是：

- tool schema 更规范
- 与 LangChain runnable / agent 体系更兼容
- 后续继续增加工具更自然
- 仍然保留自己的 harness 与安全边界
