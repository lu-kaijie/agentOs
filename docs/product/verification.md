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

## 本次修复与已知问题

本轮针对 model-backed shell 的错误提示链路做了收敛，当前已确认：

- 已修复：
  - shell 中如果 model-backed 任务执行失败，CLI 现在优先输出真实错误，不再错误追加“未检测到可用的模型配置”提示。
  - model-backed 会话持久化时不再复用原始 ReAct tool-calling 协议消息，避免后续 turn 误把历史 tool protocol 当成新输入。
  - provider/runtime 异常现在会附带更明确的 stage 级调试信息，便于定位 planner、executor、reviewer 哪一层失败。

- 仍未修复：
  - 某些工具结果中混入 `bytes` 时，`tool_results` 或 turn state 在 JSON 序列化阶段仍会报 `Object of type bytes is not JSON serializable`。
  - 某些宽泛查询会让工具返回过大的文本结果，再回灌给模型时可能触发 provider 400，例如 `input[x].output string too long`。

- 建议后续优化：
  - 为 CLI 输出、session 落盘和状态持久化增加统一的 JSON-safe serializer，递归处理 `bytes`。
  - 为 `repo_search`、`shell_command`、`test_run` 等工具增加 stdout/stderr 截断和结果条数上限。
  - 为搜索路径增加二进制/产物目录跳过策略，降低大输出和二进制污染的概率。
