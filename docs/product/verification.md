# agentOs 体验与验收

## 安装验证

```bash
python3 -m venv .venv-agentos
source .venv-agentos/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
agentos --help
agentos status
```

## 产品主路径验证

```bash
agentos
```

验证点：

- 默认进入常驻 shell
- 可以直接输入自然语言
- `/status` 和 `/exit` 可用

## One-shot 验证

```bash
agentos run "请读取 README.md，并告诉我这个项目当前是什么"
agentos run "请读取 README.md，并告诉我这个项目当前是什么" --model
```

## Session 验证

```bash
agentos session-show shell
agentos watch shell
```

## 长会话上下文验证

```bash
agentos shell --plain --session-id context-demo
```

连续输入多轮任务后，再执行：

```bash
agentos session-show context-demo
```

重点观察：

- `memory_state`
- `working_memory`
- `tool_facts`
- `failure_memory`
- `lifecycle_audits`

## 回归验证

```bash
make test
```
