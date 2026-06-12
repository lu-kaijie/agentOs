# AgentOS

AgentOS 是一个面向本地研发场景的终端 AI Coding Agent 运行时。它提供交互式 TUI、非交互式 Prompt 执行、工具调用、权限控制、MCP 接入、项目记忆、Skills、Hooks、Worktree 隔离和多 Agent 任务协作能力。

当前版本在早期原型基础上重新梳理了运行时边界，将模型调用、工具执行、权限判断、上下文管理和扩展机制拆成更清晰的 Python 模块。

## 核心能力

- 基于 Textual 的交互式终端编码助手
- 支持 `agentos -p "..."` 的一次性 Prompt 执行模式
- 支持 Anthropic、OpenAI 和 OpenAI-compatible 模型服务
- 内置 Shell、文件、搜索、任务、Skill、团队协作等工具层
- 支持权限模式、危险命令检测和路径沙箱
- 支持 stdio / HTTP 形式的 MCP Server 接入
- 支持 `AGENTOS.md`、`.agentos/` 和用户级配置维护项目记忆
- 支持项目内置 Skill 和用户全局 Skill 加载
- 支持后台子 Agent、teammate 模式和基于 worktree 的隔离开发
- 支持命令、Prompt、HTTP 和 Agent 行为相关 Hooks

## 安装

AgentOS 需要 Python 3.11 或更高版本。

```bash
cd /home/mi/agentOs
/home/mi/.local/bin/python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

如果已经确认当前默认 Python 是 3.11+，也可以直接使用 `python -m venv .venv`。

## 配置

AgentOS 支持项目级配置和用户级配置：

- 项目级配置：`.agentos/config.yaml`
- 用户级配置：`~/.agentos/config.yaml`
- 本地覆盖配置：`.agentos/config.local.yaml`

推荐把通用模型配置放到 `~/.agentos/config.yaml`，这样可以在任意项目目录直接运行 AgentOS。

```bash
mkdir -p ~/.agentos
cp /home/mi/agentOs/config.example.yaml ~/.agentos/config.yaml
```

示例配置：

```yaml
providers:
  - name: anthropic-official
    protocol: anthropic
    base_url: https://api.anthropic.com
    api_key: "${ANTHROPIC_API_KEY}"
    model: claude-sonnet-4-20250514
    thinking: true

permission_mode: default

mcp_servers:
  - name: context7
    command: npx
    args: ["-y", "@upstash/context7-mcp"]
```

运行前设置对应的 API Key：

```bash
export ANTHROPIC_API_KEY="你的 key"
```

配置加载顺序如下，后加载的配置可以覆盖前面的配置：

1. `~/.agentos/config.yaml`
2. `.agentos/config.yaml`
3. `.agentos/config.local.yaml`

## 脱离项目目录运行

如果已经在 `/home/mi/agentOs` 中通过 `pip install -e .` 安装过 AgentOS，可以在任意代码仓库中直接运行：

```bash
cd /path/to/your/project
agentos
```

也可以用一次性 Prompt 模式：

```bash
cd /path/to/your/project
agentos -p "总结一下当前项目结构"
```

如果当前 shell 找不到 `agentos` 命令，可以直接使用虚拟环境里的可执行文件：

```bash
/home/mi/agentOs/.venv/bin/agentos
/home/mi/agentOs/.venv/bin/agentos -p "检查当前 git diff"
```

也可以添加 alias：

```bash
alias agentos='/home/mi/agentOs/.venv/bin/agentos'
```

需要长期生效时，把 alias 写入 `~/.bashrc` 或 `~/.zshrc`。

## 常用命令

启动交互式 TUI：

```bash
agentos
```

执行单条 Prompt：

```bash
agentos -p "Review the current git diff and suggest fixes"
```

指定权限模式：

```bash
agentos --mode plan
agentos --mode default
agentos --mode acceptEdits
agentos --mode bypassPermissions
```

TUI 内部提供斜杠命令，用于查看帮助、运行状态、会话管理、记忆、Skills、任务、MCP、Review、Trace、Worktree 和权限控制。

## 项目结构

```text
agentos/
  __main__.py          CLI 入口
  app.py              Textual 应用
  agent.py            主 Agent 循环
  client.py           模型 Provider 客户端
  tools/              工具定义和注册中心
  permissions/        权限策略和沙箱判断
  commands/           斜杠命令解析和处理
  memory/             项目指令、会话记忆和召回
  context/            上下文压缩和大结果替换
  skills/             Skill 解析、加载和执行
  mcp/                MCP 客户端和工具封装
  agents/             子 Agent 定义和任务管理
  teams/              teammate 和 coordinator 运行时
  worktree/           基于 git worktree 的隔离会话
  hooks/              Hook 引擎和动作执行
tests/                单元测试
docs/                 架构、使用和项目说明
```

## 文档

- [使用说明](docs/usage.md)
- [架构说明](docs/architecture.md)
- [项目演进说明](docs/evolution.md)
- [Roadmap](docs/roadmap.md)

## 开发

运行测试：

```bash
pytest
```

运行指定测试文件：

```bash
pytest tests/test_agent.py
```

## 当前状态

AgentOS 是一个本地实验型 Coding Agent 运行时，适合个人研发、代码理解、代码调整和 Agent 工作流研究。它默认围绕本地可见的文件、命令和工具执行，并通过权限模式对高风险操作做显式控制。
