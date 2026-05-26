## Context

`agentOs` currently has two runtime shapes:

- The fallback runtime is a LangGraph `StateGraph` in `src/agentos/runtime/app.py`. It owns loop initialization, context preparation, deterministic decision parsing, approval routing, tool execution, background re-entry, finalization, and session persistence through `AgentOsApp.run_session_task()`.
- The real model-backed runtime is a separate path in `AgentOsApp.run_model_session_task()` and `ModelBackedAgentRuntime.run_turn()`. It prepares role contexts outside the model executor, then runs a planner model, a ReAct executor, and a reviewer model inside a hand-written bounded loop.

This creates a mismatch: the fallback path has stronger graph-level orchestration, while the real model path has stronger reasoning but hides the executor's multi-step tool loop inside `create_react_agent()`. Context management is applied before entering the ReAct executor, not before every model decision inside that executor.

The fallback graph also owns most harness-adjacent behavior today: `ToolRegistry` invokes tools through the `CommandExecutor` boundary, command execution passes through `CommandApprovalPolicy`, background jobs can re-enter the loop, workspaces can be resolved for execution, and delegated work units/tasks are persisted through their managers. The unified model path must not regress those capabilities.

The desired architecture is a graph-native model path: the LangGraph runtime remains the owner of the agent loop, and the model is used as a decision strategy inside the graph.

## Goals / Non-Goals

**Goals:**

- Route model-backed execution through the existing LangGraph loop.
- Keep `prepare_context` as the required context-management step before each real model decision.
- Make each model-backed graph iteration produce at most one `RuntimeDecision`.
- Reuse existing `tool_execute`, `approval_gate`, `background_reentry`, `finalize_iteration`, session persistence, and context audit behavior.
- Reuse existing harness capabilities, including local command execution through `CommandExecutor`, approval policy evaluation, workspace resolution, background jobs, task state, and delegated work-unit coordination.
- Support resumable interactive approval for dangerous model-selected commands, so the graph can pause, wait for user approval or rejection, and resume from the pending decision.
- Preserve deterministic fallback behavior for non-model mode, test environments, and explicit legacy DSL tasks.
- Keep the first implementation narrow enough that current tests and CLI behavior can migrate without a broad product rewrite.

**Non-Goals:**

- Do not build a full multi-agent delegation system in this change.
- Do not remove the old `ModelBackedAgentRuntime` immediately.
- Do not add vector search, semantic repo indexing, or a new memory backend.
- Do not make the model call multiple tools inside a hidden ReAct loop for the graph-native path.
- Do not redesign the shell UI or permission UX beyond preserving existing behavior.

## Decisions

### 1. Use the existing fallback graph as the unified agent-loop foundation

The existing `RuntimeBootstrap` graph already expresses the lifecycle the project wants:

```text
initialize_loop
  -> prepare_context
  -> decision / role node
  -> approval_gate / tool_execute / respond_directly
  -> finalize_iteration
  -> next step or END
```

Model-backed execution should enter this graph instead of maintaining a separate outer loop.

Alternative considered: keep the current model path and improve context inside `ModelBackedAgentRuntime`. That would preserve the split runtime and still leave approval, finalization, and background behavior duplicated or only partially integrated.

### 2. Treat model-backed reasoning as a decision strategy, not a separate runtime

The graph decision node should select between two strategies:

- deterministic strategy: existing `_decide_from_task(active_task)`
- model strategy: call a configured chat model and parse a `RuntimeDecision`

The strategy can be selected by explicit state, CLI option, and task shape. Legacy DSL tasks can continue using deterministic decisions even when the model is configured.

Alternative considered: replace `_decide_from_task()` entirely with model calls. That would make tests brittle, remove offline behavior, and make simple deterministic DSL workflows slower and less predictable.

### 3. One model decision per graph iteration

The model strategy must output a single `RuntimeDecision` per iteration. The graph then executes one tool or response and finalizes the iteration. If more work is needed, the next graph iteration prepares fresh context and asks the model again.

This intentionally avoids a hidden ReAct loop in the graph-native path. The current ReAct executor can remain temporarily for compatibility, but the target behavior is graph-native observe-decide-act:

```text
prepare_context -> model_decide -> tool_execute -> finalize_iteration
prepare_context -> model_decide -> tool_execute -> finalize_iteration
prepare_context -> model_decide -> respond_directly -> finalize_iteration
```

Alternative considered: put `create_react_agent()` inside a graph node. That would still hide multiple tool calls behind one graph step and would not let `ContextManager` run between tool observations.

### 4. Keep context management in `prepare_context`

`prepare_context` remains the only place that calls `ContextManager.prepare_role_context()` for a step. The model decision strategy must consume `state["context_bundle"]` and write observable decision metadata back to `state`.

This keeps the invariant clear:

- tool results are appended during `tool_execute`
- completed step state is updated during `finalize_iteration`
- the next `prepare_context` absorbs those facts into memory, audit records, and role views

### 5. Make approval resumable instead of only flag-based

The current approval path is flag-based: if a command requires approval and `approved` is false, `approval_gate` stops and tells the user to re-run with `--approve`. The graph-native model path should support a stronger stateful flow:

```text
model_decide -> approval_gate
  -> persist pending_approval
  -> loop_status=waiting_approval
  -> user approves/rejects
  -> resume graph from pending decision
```

`pending_approval` should include the active task, structured decision, approval policy result, command/tool metadata, and enough context to resume without asking the model to regenerate the same dangerous command.

Approval outcomes should be explicit:

- approved: resume at `tool_execute` for the pending decision
- rejected: persist the rejection, append an observable result, and either finalize with a rejection message or allow a later model decision to choose a safer path

Alternative considered: keep only `--approve`. That is simpler, but it does not match interactive agent expectations and makes shell/model sessions clumsy because users must restart execution instead of approving the paused action.

### 6. Migrate CLI behavior without changing user-facing commands

`agentos run --model` should use the graph-native model path. `agentos run` should remain deterministic. Shell routing should continue to prefer model mode for natural-language input when model configuration is available, while legacy DSL prefixes remain deterministic unless explicitly forced later.

The internal API can add a mode flag or state field such as `execution_mode: "deterministic" | "model"` to `RuntimeBootstrap.run_task()`.

### 7. Treat harness behavior as part of the graph contract

The graph-native model path must preserve the same harness contract as deterministic execution:

- command actions are represented as `RuntimeDecision(action="run_command")`
- command execution still flows through `approval_gate` and `ToolRegistry.invoke("shell_command")`
- `shell_command` and `test_run` still execute through `CommandExecutor`
- background results are consumed by `initialize_loop` and handled by `background_reentry`
- workspace-aware execution remains available through existing workspace and coordination managers
- delegated work-unit execution remains a CLI/manager capability and must not be bypassed by model mode

This means the model should select actions, but the graph and harness still enforce execution boundaries.

Alternative considered: let the model executor directly run commands or background work inside a ReAct tool loop. That would bypass the existing harness surfaces and make approval, workspace, and task state harder to audit consistently.

## Risks / Trade-offs

- Model output may fail to parse as `RuntimeDecision` -> Mitigation: use the existing `PydanticOutputParser`, include format instructions, and fall back to a clear runtime error with debug lines.
- One-tool-per-iteration can be slower than ReAct's internal loop -> Mitigation: this is an intentional trade-off to gain context control, auditability, and approval consistency.
- Existing model-backed tests may depend on planner/executor/reviewer records -> Mitigation: preserve role records where useful, but define new graph-native observability around model decisions and tool results.
- Model mode may accidentally bypass harness managers if implemented as direct model tools -> Mitigation: require all model-selected actions to route through graph decisions and existing `tool_execute`/manager paths.
- Pending approval state can become stale after files change -> Mitigation: persist the command, active task, and policy metadata; on resume, execute only the exact approved decision or force a fresh model decision if the pending state is invalid.
- `runtime/app.py` may become too large -> Mitigation: extract model decision strategy helpers into a small module if implementation grows.
- Shell behavior may become surprising for explicit DSL tasks in model-enabled sessions -> Mitigation: keep legacy prefix detection and deterministic routing for those tasks.

## Migration Plan

1. Add graph execution mode state while preserving the deterministic default.
2. Add a model decision strategy that produces `RuntimeDecision` from `state["context_bundle"]`.
3. Route `agentos run --model` and model-enabled natural-language shell input into `RuntimeBootstrap.run_task(..., execution_mode="model")`.
4. Add pending approval state and resume handling for approved or rejected dangerous commands.
5. Verify graph-native model decisions route through the existing harness boundary for shell commands, tests, approval, background re-entry, workspaces, and coordination/task managers.
6. Keep old `ModelBackedAgentRuntime` available until graph-native model behavior is covered by tests.
7. Update tests to verify that model mode goes through `prepare_context`, `tool_execute`, and `finalize_iteration`.
8. After parity is proven in a later change, remove or simplify the old hand-written model path.

## Open Questions

- Should model mode still use planner and reviewer role calls in the first implementation, or should it initially focus on graph-native executor decisions only?
- Should natural-language shell tasks always use graph-native model mode when configured, or should there be a command-level override to force deterministic mode?
- What is the minimum mocked model interface needed to test model decisions without API credentials?
- Should rejected approvals immediately finalize the turn, or should the next model decision receive the rejection and attempt an alternate path?
