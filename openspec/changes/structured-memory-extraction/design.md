## Context

agentOs already has a layered memory model and a context lifecycle manager, but the current memory extraction path is mostly heuristic. Explicit user facts such as "please remember the first test code: blue kite" are currently preserved as raw accepted constraints, while user profile fields and remembered facts are not first-class structured data. Recent-message compression can hide these facts from the model even when they remain in persisted memory.

The graph-native model runtime now prepares context before each model decision and routes tools through LangGraph. This gives a natural place to update memory at turn boundaries and inject structured memory into model prompts. The change should preserve deterministic fallback behavior and avoid making tool stdout part of long-lived conversation memory.

## Goals / Non-Goals

**Goals:**

- Add explicit structured memory layers for user profile, remembered facts, task state, tool facts, workspace state, and failure memory.
- Use a model-backed structured extractor when configured to produce memory deltas from each completed turn.
- Keep deterministic rule-based extraction as fallback when model extraction is unavailable or fails.
- Merge memory deltas field-by-field so stable layers are not rebuilt or lost when volatile layers change.
- Inject structured memory into graph-native model decisions as first-class context.
- Keep full tool output available for audit/debug while feeding the model bounded tool summaries and facts.

**Non-Goals:**

- Building a vector database or semantic retrieval service.
- Persisting cross-project global user profiles outside the current project/session storage.
- Replacing graph runtime state (`AgentGraphState`) with memory storage.
- Reintroducing hidden ReAct loops inside the graph-native model path.
- Guaranteeing perfect long-term memory beyond the configured persisted memory budget.

## Decisions

1. **Introduce `MemoryDelta` rather than rewriting `LayeredMemory` directly.**

   The extractor will produce a structured delta with optional sections such as `user_profile_delta`, `remembered_facts_delta`, `task_state_delta`, and `failure_memory_delta`. A merge function will apply the delta to the existing memory. This avoids overwriting stable fields when only one layer changes.

   Alternative considered: let the extractor output a full replacement memory object. That is simpler, but it risks losing unrelated fields and makes deterministic fallback harder to reason about.

2. **Use model-backed function/tool calling for extraction when available.**

   The model path should bind a structured extraction schema and require a tool/function response, similar to graph-native `RuntimeDecision`. This is more robust than asking for prompt-only JSON and makes extractor failures easier to diagnose.

   Alternative considered: keep heuristic extraction only. That is fast and deterministic, but it cannot reliably identify user profile, key-value facts, or corrections.

3. **Keep deterministic extraction as a required fallback.**

   The fallback will continue to identify obvious Chinese/English preference phrases and explicit "remember" facts. It should populate the same `MemoryDelta` shape as the model extractor so merge and prompt injection do not care which extractor ran.

   Alternative considered: require model configuration for structured memory. That would break offline/deterministic execution and existing tests.

4. **Store remembered facts as structured records.**

   Remembered facts should have fields such as `key`, `value`, `scope`, `source`, `confidence`, `created_at`, `updated_at`, and `status`. The system should support updates by key and allow newer corrections to supersede older values.

   Alternative considered: store raw remembered sentences only. This preserves source text but makes later lookup brittle and forces the model to infer structure every turn.

5. **Separate model-visible context from audit storage.**

   Full tool payloads remain in session state and tool results. The model receives bounded summaries, extracted tool facts, and recent relevant tool results. Conversation history stores user and final assistant messages, not full intermediate tool stdout.

   Alternative considered: keep all tool output in conversation messages. This caused compression pressure and pushed out user facts in longer shell sessions.

6. **Prompt injection reads structured memory layers directly.**

   Graph-native model decisions should receive a bounded "User profile", "Remembered facts", "Task state", and "Recent tool facts" section. These sections should be built from structured memory fields, not inferred from a compressed `bundle_preview` alone.

## Risks / Trade-offs

- **Extractor model returns incorrect facts** -> Validate schema, keep source snippets, track confidence, and prefer explicit user statements over assistant guesses.
- **Memory grows without bound** -> Keep per-layer budgets, dedupe by key/source, and archive/summarize older low-priority facts.
- **Model extractor latency slows every turn** -> Make extraction bounded, use a smaller configured model level where appropriate, and fall back to deterministic extraction on failure.
- **Privacy or accidental over-retention** -> Store only project/session memory by default and support scoped facts with status fields so later deletion/archive work can target records.
- **Prompt bloat from structured memory** -> Inject only high-confidence profile fields, active session facts, recent task state, and bounded tool facts.
- **Merge bugs corrupt memory** -> Add focused tests for field-level merge, correction, dedupe, compression, and fallback behavior.

## Migration Plan

1. Extend memory models with new fields while preserving existing fields for compatibility.
2. Implement merge so old memory files can be loaded with empty defaults for new layers.
3. Route lifecycle extraction through the new delta path.
4. Update context bundle construction and graph prompt injection to consume structured fields.
5. Keep `accepted_constraints` populated during migration for backwards compatibility, but stop relying on it as the primary remembered-fact source.
6. Add tests for existing memory files, multi-turn shell memory, and compression retention.
