# agentOs 产品使用说明

## 1. 安装

推荐在项目虚拟环境中安装：

```bash
python3 -m venv .venv-agentos
source .venv-agentos/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

如果你只是想把它当成命令行产品来用，核心是安装后可以直接执行 `agentos`，不再依赖 `PYTHONPATH=src`。

## 2. 准备配置

```bash
cp .env.example .env
```

至少填写：

```env
OPENAI_API_KEY=...
OPENAI_BASE_URL=...
AGENTOS_CONTEXT_MODEL_COMPRESSION=0
```

模型采用三挡配置：

```env
AGENTOS_MODEL_SMALL=gpt-5.4
AGENTOS_MODEL_MEDIUM=gpt-5.4
AGENTOS_MODEL_LARGE=gpt-5.4

AGENTOS_PLANNER_MODEL_LEVEL=medium
AGENTOS_EXECUTOR_MODEL_LEVEL=medium
AGENTOS_REVIEWER_MODEL_LEVEL=medium
```

含义是：

- 先定义三挡模型池
- 再让 planner / executor / reviewer 选择使用哪一挡
- 默认三个 role 都走 `medium`
- `AGENTOS_CONTEXT_MODEL_COMPRESSION=1` 时，长语义记忆允许使用模型做额外压缩；默认 `0`，即只用启发式回退，避免开发和测试时意外触发外部请求

## 3. 主要命令

```bash
agentos
agentos shell
agentos run "阅读 README.md 并总结当前项目状态" --model
agentos status
agentos session-show shell
agentos watch shell
```

命令说明：

- `agentos`
  默认进入常驻交互式 shell
- `agentos shell`
  显式进入 shell；等价于主入口
- `agentos run`
  适合单轮执行、脚本化调用、快速验证
- `agentos status`
  查看当前工作区、模型配置和 runtime 状态
- `agentos session-show`
  查看指定 session 的最新持久化状态
- `agentos watch`
  持续观察 session 状态变化

## 4. 交互式 shell

启动：

```bash
agentos
```

进入后可以直接输入自然语言任务，例如：

```text
请先阅读 README.md，然后总结当前项目状态
搜索 tests 里和 context policy 相关的测试
运行测试并汇报结果
```

内置命令：

- `/status`
  查看当前 shell session 的持久化状态
- `/exit`
  退出 shell

如果检测到终端支持并且安装了 `textual`，默认会进入更稳定的 TUI 风格界面；否则会自动退回 plain shell。

## 5. 长会话与上下文整理

当前版本已经加入了主动上下文维护机制。会话在以下场景会自动整理上下文：

- 会话内容增长到活跃阈值附近
- 工具输出过长
- role 切换
- session resume
- 一轮任务结束后的后续组装

整理策略不是单一摘要，而是混合式：

- 结构化硬事实由程序抽取
  - 例如最近工具结果、失败记录、已读已改文件、工作区状态
- 语义性信息进入工作记忆
  - 例如当前目标、用户约束、最近决策、阶段总结
- 最终进入 prompt 的内容仍由 runtime 按 budget 显式控制

你可以这样验证：

```bash
agentos shell --plain --session-id context-demo
```

然后连续输入多轮任务，例如：

```text
请先阅读 README.md，总结项目状态，并记住后续都用中文回复
搜索 tests 里所有和 context 相关的测试
运行一个不会通过的测试命令，并告诉我失败原因
现在总结一下刚才已经做过什么、哪些文件看过、哪些尝试失败过
```

之后执行：

```bash
agentos session-show context-demo
```

重点看这些字段：

- `memory_state`
- `memory_state.working_memory`
- `memory_state.tool_facts`
- `memory_state.failure_memory`
- `memory_state.lifecycle_audits`

如果这些字段随着长会话推进而持续更新，说明上下文整理链路已经在工作。

## 6. 非模型路径

如果未配置 `OPENAI_API_KEY`，启动时会给出明确引导，并退回到 deterministic / legacy 路径。这条路径仍然可以运行已有的显式 task DSL，例如：

```bash
agentos run "code: steps: read: README.md | write: notes.txt => demo | test: python -c print(321)"
```

## 7. 调试和开发

如果你要调试源码仓库本身，而不是只把它当产品来用，继续使用 `make` 命令即可，例如：

```bash
make shell
make shell-model
make test
```
