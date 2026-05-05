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

## 5. 非模型路径

如果未配置 `OPENAI_API_KEY`，启动时会给出明确引导，并退回到 deterministic / legacy 路径。这条路径仍然可以运行已有的显式 task DSL，例如：

```bash
agentos run "code: steps: read: README.md | write: notes.txt => demo | test: python -c print(321)"
```

## 6. 调试和开发

如果你要调试源码仓库本身，而不是只把它当产品来用，继续使用 `make` 命令即可，例如：

```bash
make shell
make shell-model
make test
```
