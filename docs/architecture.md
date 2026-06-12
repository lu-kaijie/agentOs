# AgentOS 架构说明

AgentOS 的核心定位是本地 Coding Agent 运行时，而不是一组脚本集合。整体设计将用户交互、模型调用、工具执行、权限检查、项目状态和多 Agent 协作拆分为独立模块，便于扩展和测试。

## 分层结构

```text
用户入口层
  Textual TUI
  非交互式 CLI Prompt 模式

Agent 运行层
  会话管理
  Agent 主循环
  上下文窗口管理
  Provider 客户端

工具层
  文件工具
  Shell 工具
  搜索工具
  任务工具
  Skill 工具
  MCP 工具
  Team 工具

安全层
  权限模式
  危险命令检测
  路径沙箱
  用户级规则
  项目级规则

状态层
  .agentos 配置
  项目指令
  会话记忆
  文件历史
  worktree 会话

扩展层
  Skills
  Hooks
  Subagents
  Teammates
  MCP Servers
```

## 主流程

```text
用户输入
  -> 命令解析器或 Agent 主循环
  -> Provider 客户端流式调用模型
  -> 解析模型返回的工具调用
  -> 权限检查器判断是否允许执行
  -> 工具执行结果写回会话上下文
  -> 上下文管理器在必要时压缩或替换大结果
  -> 最终结果输出到 TUI 或 stdout
```

## 工具运行机制

工具通过统一注册中心管理。每个工具定义参数 schema 和异步执行方法，模型不会直接操作 shell 或文件，而是生成结构化工具调用请求，再由注册中心和权限层负责实际执行。

内置工具包括：

- 文件读取和写入
- grep / glob 搜索
- Shell 命令执行
- 任务状态管理
- Skill 加载
- Plan 模式退出
- 用户提问
- 子 Agent 消息通信
- Team 创建和协作

这种设计的好处是工具边界清晰，权限控制可以集中处理，也方便给工具补充日志、审计和测试。

## 权限机制

AgentOS 支持多种权限模式。权限检查器会综合以下信息做判断：

- 当前权限模式
- 危险命令检测结果
- 路径沙箱规则
- 用户级规则
- 项目级规则
- 本地临时覆盖规则

常规编码任务可以保持较少打断，高风险命令和越权路径访问则需要显式确认。

## 记忆和上下文

AgentOS 使用多种状态来源维护上下文：

- `AGENTOS.md`：项目级指令
- `.agentos/config.yaml`：项目级运行配置
- `.agentos/permissions.yaml`：项目级权限规则
- `.agentos/sessions/`：会话元数据
- `.agentos/session/tool-results/`：大工具结果替换状态
- `.agentos/memories.md`：项目级记忆
- `~/.agentos/config.yaml`：用户级通用配置
- `~/.agentos/skills/`：用户级 Skills

上下文管理器负责控制活跃会话不要超过模型上下文窗口，并在工具结果过大时用紧凑引用替换原始内容。

## 多 Agent 协作

Subagents 和 teammates 用于把边界清晰的任务拆出去执行。主会话可以创建子任务、发送消息、等待结果，并通过任务管理器追踪进度。

Worktree 模块可以为并行任务创建隔离的 git worktree，使实验性修改和主工作区解耦，便于后续 review、合并或丢弃。
