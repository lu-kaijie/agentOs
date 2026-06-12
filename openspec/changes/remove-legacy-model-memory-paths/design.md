## Context

The current runtime has two generations of model-backed implementation:

- the old `ModelBackedAgentRuntime` hand-written loop in `src/agentos/runtime/model_backed.py`
- the current graph-native model path in `src/agentos/runtime/app.py`, driven by `RuntimeBootstrap`, LangGraph nodes, `GraphModelDecisionStrategy`, `RuntimeDecision`, `ToolRegistry`, and approval gates

The current memory system also has two generations of memory fields:

- legacy working-memory fields such as `accepted_constraints` and `user_preferences`
- structured layers such as `user_profile`, `remembered_facts`, `task_state`, `tool_facts`, `workspace_state`, and `failure_memory`

The previous changes intentionally kept legacy paths during transition. The graph-native model path and structured memory extraction are now covered by tests and manual shell verification, so the transitional code should be removed or narrowed.

## Goals / Non-Goals

**Goals:**

- Make graph-native LangGraph execution the only supported real-model runtime path.
- Keep deterministic fallback and legacy DSL commands intact.
- Remove `ModelBackedAgentRuntime` from product entry points and delete its implementation if no tests or docs still require it.
- Remove unused model-decision prompt/parser scaffolding from the graph runtime if model decisions now only use tool/function calling.
- Ensure structured memory layers are the primary prompt-facing memory source.
- Keep persisted old memory loading safe during migration.
- Update docs and tests to match the cleaned architecture.

**Non-Goals:**

- Removing deterministic fallback commands.
- Removing `working_memory` entirely if it still carries useful task state or compatibility data.
- Building vector retrieval or a new long-term memory backend.
- Changing approval policy semantics.
- Changing shell UX beyond removing references to the old model path.

## Decisions

1. **Delete the old model runtime instead of keeping it dormant.**

   The old model runtime duplicates planner/executor/reviewer behavior, uses different parsing and error handling, and no longer represents the product path. Keeping it as dormant code would keep tests and docs ambiguous.

   Alternative considered: leave `ModelBackedAgentRuntime` as an emergency fallback. This preserves code but keeps two implementations alive and makes future context or approval changes harder to reason about.

2. **Keep deterministic DSL fallback.**

   Prefix commands such as `run:`, `read:`, `write:`, `patch:`, `test:`, `steps:`, and `code:` remain valuable for tests, no-model environments, and explicit command-like tasks. Cleanup should remove the legacy model path, not the deterministic runtime.

   Alternative considered: route all tasks through model decisions when model configuration exists. That would make CLI behavior slower and less predictable, and would weaken offline testability.

3. **Make legacy memory fields compatibility projections.**

   `user_profile`, `remembered_facts`, and `task_state` should drive model-visible memory. `accepted_constraints` and `user_preferences` can remain while old persisted memory or older docs/tests need them, but new prompt construction should not rely on them as the primary remembered-fact path.

   Alternative considered: remove the fields immediately from `LayeredMemory`. That could break old memory files and unrelated tests. A staged downgrade is safer.

4. **Archive completed changes after cleanup lands.**

   Completed active changes such as `unify-model-runtime-langgraph-loop` and `structured-memory-extraction` should not remain as active work once their follow-up cleanup has verified the current architecture.

   Alternative considered: archive before cleanup. That would hide transition notes while legacy code still exists.

## Risks / Trade-offs

- **Hidden dependency on `ModelBackedAgentRuntime`** -> Search imports, remove or update tests, and run packaged CLI tests.
- **Deterministic fallback regression** -> Keep `_decide_from_task()` and add explicit tests for legacy DSL tasks.
- **Persisted memory compatibility break** -> Keep tolerant `LayeredMemory.from_dict()` defaults and add backward-loading tests.
- **Prompt context loses useful constraints** -> Ensure structured memory previews include user profile, remembered facts, task state, and bounded legacy constraints during transition.
- **Docs drift** -> Update architecture docs that still describe the old model path as primary.

## Migration Plan

1. Inventory all references to `ModelBackedAgentRuntime`, prompt-only parser scaffolding, `accepted_constraints`, and `user_preferences`.
2. Replace product entry points so model mode always calls graph-native model execution.
3. Delete old model runtime files and tests that only validate the deleted path.
4. Update tests to assert graph-native model path behavior and deterministic fallback behavior.
5. Narrow legacy memory fields to compatibility behavior, preserving old memory loading.
6. Update docs to remove old hand-written loop descriptions.
7. Run focused tests, then full tests.
8. Archive completed OpenSpec changes after the cleanup is implemented and accepted.
