# 第三个 Change 里程碑说明

本文对应 OpenSpec change `build-agentos-basic-usable-agent`，用于记录第三阶段每个稳定子阶段完成了什么、怎么体验、重点学什么。

## 总览

第三个 change 的目标不是一次性把 `agentOs` 做成完整成品，而是在第二阶段真实 runtime 原型的基础上，补齐 session persistence、structured tools、context engineering、role workflow 和 interactive CLI，使系统进入“基本可用 agent 原型”阶段。

这一阶段完成后，你已经可以体验到：
- 可恢复和可回放的 runtime session
- 标准化 coding-agent tool registry
- task-aware context bundle 与可检查 context trace
- bounded planner / executor / reviewer role workflow
- 更连续的 CLI 体验，包括 `watch` 和 `unit-watch`

## M15: Session Persistence

对应 tag：`v0.15.0`

这一步完成了什么：
- runtime session、turn state 和 loop progress 持久化到 `.agentos/sessions`
- session summary 可用于后续 inspect / resume

怎么体验：

```bash
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli run "steps: say hello | say again" --session-id demo-session --max-iterations 1
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli sessions
```

学习重点：
- session state schema
- 为什么 runtime 必须先可恢复，才能谈可用

## M16: Session Inspect And Resume

对应 tag：`v0.16.0`

这一步完成了什么：
- 增加 `session-show`
- 增加 `resume`

怎么体验：

```bash
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli session-show demo-session
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli resume demo-session
```

学习重点：
- persisted runtime model
- replay 与继续执行的区别

## M17: Bounded Continuation And Replay

对应 tag：`v0.17.0`

这一步完成了什么：
- resume 可以消费新出现的后台结果
- interrupted session 的 replay 变得可检查

怎么体验：

```bash
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli bg-run "python -c \"print('knowledge: langgraph-runtime', end='')\"" --session-id replay-demo
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli resume replay-demo --poll-iterations 10 --poll-interval 0.2
```

学习重点：
- bounded continuation
- background result re-entry 和 persisted session 的结合

## M18: Structured Tool Registry

对应 tag：`v0.18.0`

这一步完成了什么：
- 建立 `ToolRegistry`
- 增加 `repo_search / file_read / file_write / file_patch / test_run`
- tool results 回写到 runtime state

怎么体验：

```bash
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli tool-list
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli tool-run file_read --arg path=README.md
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli run "steps: search: Tool registry | read: README.md | write: notes.txt => alpha beta | patch: notes.txt => beta >> gamma | test: python -c print(456)" --session-id tool-demo --max-iterations 5
```

学习重点：
- tool registry 为什么先自建骨架
- tool result 如何进入 LangGraph state

## M19: Task-Aware Context Bundles

对应 tag：`v0.19.0`

这一步完成了什么：
- 引入 `prepare_context`
- runtime 每轮先构造 `context_bundle`
- 历史、工具结果、工作区信号可合并并压缩

怎么体验：

```bash
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli run "steps: read: README.md | search: agentOs | say hello | say again | say once more" --session-id context-demo --max-iterations 5
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli session-show context-demo
```

学习重点：
- context engineering 作为显式图节点
- 为什么 context 不能只是 message history

## M20: Bounded Role Workflow

对应 tag：`v0.20.0`

这一步完成了什么：
- 引入 `code:` role workflow
- `planner / executor / reviewer` record
- reviewer 直接消费 tool results

怎么体验：

```bash
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli run "code: steps: read: README.md | write: notes.txt => role workflow | test: python -c print(321)" --session-id role-demo --max-iterations 5
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli session-show role-demo
```

学习重点：
- role state 如何进入 runtime graph
- 为什么现在的 role 还是 workflow stage，而不是完整独立 agent

## M21: Interactive CLI

对应 tag：`待完成`

这一步会完成什么：
- 中文可读 CLI 输出
- `watch` 与 `unit-watch`
- 更适合长期使用和调试的 staged output

怎么体验：

```bash
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli watch role-demo --poll-count 5 --poll-interval 0.5
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli unit-watch --poll-count 5 --poll-interval 0.5
```

学习重点：
- 为什么当前先做轮询，不先做主动推送
- CLI presentation 如何影响 agent 的可用性
