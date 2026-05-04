# 第二个 Change 里程碑说明

本文对应 OpenSpec change `advance-agentos-real-agent-loop`，用于记录第二阶段每个稳定子阶段完成了什么、怎么体验、重点学什么。

## 总览

第二个 change 的目标不是直接把 `agentOs` 做成完整成品，而是把第一阶段的学习型底座推进成一个更真实的 agent runtime 原型。

这一阶段完成后，你已经可以体验到：
- 可续跑的 LangGraph runtime loop
- 后台结果回流到 runtime
- 受控 delegated execution
- 显式 approval policy

## M11: Resumable Runtime Loop

对应 tag：`v0.11.0`

这一步完成了什么：
- runtime 从单次 directed pass 变成可继续的 loop
- 引入 `pending_tasks`、`completed_tasks`、`iteration_count`、`loop_status`
- 增加 `--max-iterations` 和显式 trace

怎么体验：

```bash
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli run "steps: run: pwd | knowledge: langgraph-runtime | say hello" --max-iterations 5
```

你会看到：
- 多次 `model_decide`
- 每轮的 `active_task`
- `loop_status=continue/completed`

学习重点：
- LangGraph 显式 loop
- bounded continuation
- trace 可观察性

## M12: Background Result Re-entry

对应 tag：`v0.12.0`

这一步完成了什么：
- 已完成后台任务会在下一次 runtime 启动时被扫描
- 未消费后台结果会以 `background_result:<job_id>` 的形式重新进入 loop
- 如果后台输出是 `knowledge: ...` 或 `run: ...`，会继续派生 follow-up step

怎么体验：

```bash
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli bg-run "python -c \"print('knowledge: langgraph-runtime', end='')\""
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli bg-list
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli run "say hello" --max-iterations 5
```

你会看到：
- `background_results_detected`
- `background_reentry`
- 后续 `knowledge_execute` 或 `tool_execute`

学习重点：
- 异步结果如何回流到 runtime state
- 为什么先做“启动时回收”而不是 daemon

## M13: Delegated Execution

对应 tag：`v0.13.0`

这一步完成了什么：
- work unit 从 coordination record 变成可执行单元
- 支持 `role`、`workspace`、`task_id`、`command`
- delegated execution 会回写 unit 状态与 task 状态

怎么体验：

```bash
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli workspace-create unit-a
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli task-create "Delegated task"
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli unit-create "Inspect backend" --role researcher --task-id 1 --workspace unit-a --command python --command -c --command "print('delegated-demo', end='')"
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli unit-exec 1
```

你会看到：
- `execution_context`
- `exit_code`
- `result`
- task 的 `owner` 与 `execution_context` 被更新

学习重点：
- coordination control plane 如何接成执行流
- role-bound work unit 如何保持可检查

## M14: Permission And Approval Policy

对应 tag：`v0.14.0`

这一步完成了什么：
- command approval 从 runtime 节点中抽到独立 policy layer
- 暴露 `approval_policy.matched_rule/reason/risk_level`
- `approval_gate` 输出可解释的拦截原因

怎么体验：

```bash
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli run "run: rm temp.txt"
PYTHONPATH=src .venv-agentos/bin/python -m agentos.cli run "run: pwd"
```

你会看到：
- 危险命令命中 `destructive-command`
- 安全命令命中 `safe-command`
- CLI 输出里直接包含 policy 原因

学习重点：
- harness 安全边界为什么应该独立于 runtime routing
- “为什么被拦”如何变成 inspectable state

## 第二个 Change 收尾状态

截至 `v0.14.0`：
- OpenSpec 代码任务 `1.1 ~ 4.3` 已完成
- 剩余的是文档与发布纪律任务
- 第三个 change 已经提出，但尚未实施
