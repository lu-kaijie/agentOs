# AgentOS 使用说明

## 安装为本地 CLI

进入 AgentOS 仓库并安装：

```bash
cd /home/mi/agentOs
/home/mi/.local/bin/python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

安装后，`agentos` 会作为 CLI 命令注册到当前虚拟环境中。

## 配置模型服务

推荐使用用户级配置，这样可以在任意项目目录复用同一份模型配置：

```bash
mkdir -p ~/.agentos
cp /home/mi/agentOs/config.example.yaml ~/.agentos/config.yaml
```

然后设置 API Key：

```bash
export ANTHROPIC_API_KEY="你的 key"
```

也可以在具体项目中创建 `.agentos/config.yaml`，用于覆盖或补充全局配置。

## 在任意项目中运行

完成安装和用户级配置后，可以离开 AgentOS 仓库，在任意代码项目中运行：

```bash
cd /path/to/your/project
agentos
```

一次性 Prompt 模式：

```bash
agentos -p "总结一下当前仓库结构"
agentos -p "检查当前 git diff 并给出修改建议"
```

如果 shell 找不到 `agentos`，直接使用虚拟环境路径：

```bash
/home/mi/agentOs/.venv/bin/agentos
/home/mi/agentOs/.venv/bin/agentos -p "解释这个项目如何启动"
```

也可以配置 alias：

```bash
alias agentos='/home/mi/agentOs/.venv/bin/agentos'
```

## 权限模式

AgentOS 支持多种权限模式：

```bash
agentos --mode plan
agentos --mode default
agentos --mode acceptEdits
agentos --mode bypassPermissions
```

建议：

- 陌生仓库使用 `plan` 或 `default`。
- 熟悉的本地实验项目可以使用 `acceptEdits`。
- `bypassPermissions` 只适合完全可信的本地临时环境。

## 项目指令

在项目根目录添加 `AGENTOS.md`，可以给 AgentOS 提供项目级说明，例如：

- 技术栈
- 启动方式
- 测试方式
- 编码规范
- 不允许修改的目录
- 常用命令

AgentOS 会把这些内容加载进运行上下文，作为当前项目的行为约束。

## Skills

项目级 Skills 放在：

```text
.agentos/skills/
```

用户级 Skills 放在：

```text
~/.agentos/skills/
```

每个 Skill 可以包含 `SKILL.md` 和可选的脚本、模板、参考资料。AgentOS 会在需要时加载对应 Skill，让复杂任务可以复用稳定流程。

## MCP Servers

AgentOS 可以从配置文件加载 stdio 或 HTTP 形式的 MCP Server：

```yaml
mcp_servers:
  - name: context7
    command: npx
    args: ["-y", "@upstash/context7-mcp"]
```

加载后的 MCP 能力会被封装成 AgentOS 工具，供 Agent 在工具调用阶段使用。

## Hooks

Hooks 可用于在命令执行、Prompt 处理、HTTP 请求或 Agent 行为前后触发额外动作。适合做本地自动化和安全约束，例如：

- 命令执行前检查
- Prompt 注入项目上下文
- 调用外部 HTTP 服务
- 记录 Agent 行为日志

Hooks 不应该用于隐藏破坏性行为。

## Worktree

Worktree 能力用于把较大的改动隔离到独立 git worktree 中执行。适合：

- 多 Agent 并行修改
- 实验性代码调整
- 需要单独 review 的大改动

这样可以避免直接污染主工作区，便于后续合并和回滚。
