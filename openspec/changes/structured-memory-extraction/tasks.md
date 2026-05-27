## 1. Memory Data Model

- [x] 1.1 Add structured memory model classes for user profile, remembered facts, task state, and memory deltas.
- [x] 1.2 Extend `LayeredMemory` serialization/deserialization with backwards-compatible defaults for new fields.
- [x] 1.3 Add fact metadata fields for key, value, scope, source, confidence, status, created timestamp, and updated timestamp.

## 2. Extraction Pipeline

- [x] 2.1 Implement deterministic memory extraction that emits `MemoryDelta` for explicit remembered facts and user preferences.
- [x] 2.2 Implement model-backed memory extraction using structured tool/function output when model configuration is available.
- [x] 2.3 Add extractor fallback behavior so model extraction failures produce diagnostics and use deterministic extraction without failing the user turn.
- [x] 2.4 Ensure memory extraction uses final assistant answers and structured tool facts rather than raw multi-step tool stdout.

## 3. Field-Level Merge

- [x] 3.1 Implement merge logic for user profile fields that preserves unrelated existing profile values.
- [x] 3.2 Implement remembered-fact merge by stable key, including update/supersede behavior for corrected facts.
- [x] 3.3 Implement task-state merge for current goal, completed actions, and open questions without overwriting stable memory layers.
- [x] 3.4 Keep existing tool facts, workspace state, and failure memory merge behavior compatible with new memory layers.

## 4. Context Projection

- [x] 4.1 Update context bundle construction to expose structured `user_profile`, `remembered_facts`, and `task_state` sections.
- [x] 4.2 Update graph-native model decision prompts to inject structured memory sections directly.
- [x] 4.3 Keep large tool payloads out of long-lived conversation messages while preserving full tool results in persisted session state.
- [x] 4.4 Keep `AgentGraphState` as a runtime snapshot carrier and avoid moving memory lifecycle ownership into graph nodes.

## 5. Tests and Verification

- [x] 5.1 Add unit tests for deterministic extraction of user profile and remembered facts.
- [x] 5.2 Add unit tests for model-backed extraction parsing and fallback behavior.
- [x] 5.3 Add unit tests for field-level merge, fact correction, dedupe, and backwards-compatible memory loading.
- [x] 5.4 Add graph runtime tests proving remembered facts survive recent-message compression.
- [x] 5.5 Add shell/session-style tests for a long multi-turn conversation with preferences, multiple remembered facts, tool calls, approval, and missing-file recovery.
- [x] 5.6 Run the full test suite and update architecture documentation for the structured memory lifecycle.
