## Why

The current context lifecycle has layered-memory scaffolding, but user facts and profile details are still extracted mostly through heuristic keyword rules and can be hidden from model prompts after compression. This causes multi-turn conversations to forget explicit facts such as test codes even when those facts are still present somewhere in persisted memory.

## What Changes

- Introduce structured memory extraction that uses a model-backed structured decision when available and deterministic rules as fallback.
- Add explicit memory layers for user profile, remembered facts, task state, tool facts, workspace state, and failure memory.
- Add field-level merge semantics so stable fields are updated without rebuilding unrelated memory layers.
- Ensure prompts consume structured memory fields directly instead of relying on compressed recent-message snippets.
- Keep complete tool output available for audit/debug while feeding the model bounded summaries and facts.
- Preserve existing fallback behavior when model-backed extraction is unavailable.

## Capabilities

### New Capabilities

- `structured-memory-extraction`: Covers structured user-profile extraction, remembered-fact extraction, field-level memory deltas, merge semantics, and prompt injection of structured memory.

### Modified Capabilities

- `graph-native-model-agent-loop`: Model-backed graph decisions shall receive structured memory layers as first-class context rather than depending on recent-message compression alone.

## Impact

- Affected code:
  - `src/agentos/context/models.py`
  - `src/agentos/context/lifecycle.py`
  - `src/agentos/context/manager.py`
  - `src/agentos/context/policy.py`
  - `src/agentos/runtime/app.py`
  - tests for context lifecycle, graph runtime, and model-backed shell behavior
- Affected behavior:
  - Long-running shell sessions should retain explicit remembered facts and user preferences across compression.
  - Tool outputs remain in structured tool state and audit records, while model prompts receive bounded summaries and memory facts.
  - Model-backed memory extraction may call the configured chat model; deterministic extraction remains the fallback.
