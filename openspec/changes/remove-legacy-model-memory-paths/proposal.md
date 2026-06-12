## Why

The graph-native model path and structured memory extraction are now the primary runtime architecture, but transitional code from the old hand-written model loop and pre-structured memory layers still remains. Keeping both paths active increases maintenance cost, makes docs confusing, and risks future behavior drifting between duplicated implementations.

## What Changes

- Remove or fully de-route the old `ModelBackedAgentRuntime` hand-written planner/executor/reviewer loop from product entry points.
- Keep deterministic fallback and explicit legacy DSL commands such as `run:`, `read:`, `write:`, `patch:`, `test:`, `steps:`, and `code:`.
- Remove unused graph decision prompt/parser scaffolding that no longer participates in model-backed decisions.
- Downgrade overlapping old memory fields such as `accepted_constraints` and `user_preferences` to compatibility projections, or remove their primary-path use where structured `user_profile`, `remembered_facts`, and `task_state` now own the behavior.
- Update tests and documentation so the supported model path is clearly `RuntimeBootstrap` + LangGraph + `GraphModelDecisionStrategy`.
- Archive completed OpenSpec changes after cleanup is implemented and verified.

## Capabilities

### New Capabilities

- `legacy-path-cleanup`: Covers removal of obsolete model runtime paths, cleanup of transitional memory compatibility paths, and verification that supported graph-native model and deterministic fallback behavior remain intact.

### Modified Capabilities

- `graph-native-model-agent-loop`: The model-backed path shall no longer expose or depend on the old `ModelBackedAgentRuntime` transition path.
- `structured-memory-extraction`: Structured memory layers shall be the primary prompt-facing memory source; legacy memory fields shall not drive remembered facts or user profile behavior.

## Impact

- Affected code:
  - `src/agentos/app.py`
  - `src/agentos/cli.py`
  - `src/agentos/shell_tui.py`
  - `src/agentos/runtime/app.py`
  - `src/agentos/runtime/model_backed.py`
  - `src/agentos/context/lifecycle.py`
  - `src/agentos/context/models.py`
  - `src/agentos/context/policy.py`
  - tests for CLI, graph runtime, context lifecycle, and packaged CLI behavior
- Affected docs:
  - architecture docs that still describe `ModelBackedAgentRuntime` as the real model path
  - product/configuration docs if any model-path references change
- Compatibility:
  - deterministic DSL fallback remains supported
  - existing persisted memory should load without crashing during the cleanup
  - old completed OpenSpec changes may be archived after implementation
