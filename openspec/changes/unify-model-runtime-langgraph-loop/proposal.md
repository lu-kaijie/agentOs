## Why

The current project has two execution paths: the fallback path uses a LangGraph state machine for the agent loop, while the real model-backed path uses a separate hand-written planner / executor / reviewer loop with a ReAct executor inside it. This split makes the real model path bypass the strongest parts of the runtime orchestration, especially per-step context preparation, approval gates, pending-task handling, background re-entry, and inspectable finalization.

This change makes the fallback LangGraph runtime become the shared agent-loop foundation, then adds real model decision-making into that graph so model-backed execution receives context management before every model decision.

## What Changes

- Introduce a graph-native model-backed execution mode inside the existing `RuntimeBootstrap` LangGraph loop.
- Allow the graph's decision step to call a real model when model mode is enabled, while preserving deterministic `_decide_from_task()` behavior for fallback and legacy DSL tasks.
- Move model-backed tool use from an internal executor ReAct loop to graph-level one-decision-per-iteration execution.
- Ensure each model-backed iteration follows the existing sequence: `prepare_context` -> model decision -> approval/tool/respond -> `finalize_iteration`.
- Keep `ContextManager.prepare_role_context()` as the required context boundary immediately before every model decision.
- Preserve current CLI behavior at the user level: `agentos run --model` and model-enabled shell still use real models, while non-model and explicit DSL flows remain deterministic.
- Keep the existing `ModelBackedAgentRuntime` available during transition until the graph-native model path reaches parity.

## Capabilities

### New Capabilities
- `graph-native-model-agent-loop`: Defines a unified LangGraph agent loop where real model decisions and deterministic fallback decisions share the same orchestration, context lifecycle, tool execution, and session persistence path.

### Modified Capabilities

## Impact

- Affects `src/agentos/app.py`, `src/agentos/cli.py`, `src/agentos/runtime/app.py`, and model-backed runtime integration.
- Affects tests for model mode, fallback runtime, context lifecycle, tool execution, approval behavior, and shell routing.
- May add a small model decision strategy or helper module to keep `runtime/app.py` from becoming too large.
- Does not require new external dependencies.
- Does not remove deterministic fallback behavior.
