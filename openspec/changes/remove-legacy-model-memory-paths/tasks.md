## 1. Inventory And Safety

- [ ] 1.1 Inventory all imports, tests, docs, and CLI/shell references to `ModelBackedAgentRuntime` and `src/agentos/runtime/model_backed.py`.
- [ ] 1.2 Inventory active uses of `PydanticOutputParser`, `decision_prompt`, and prompt-only model decision scaffolding in the graph runtime.
- [ ] 1.3 Inventory active uses of `accepted_constraints` and `user_preferences`, classifying each as primary behavior, compatibility projection, or removable test/doc expectation.
- [ ] 1.4 Confirm deterministic DSL fallback commands and no-model execution paths that must remain supported.

## 2. Remove Legacy Model Runtime Path

- [ ] 2.1 Route all model-backed product entry points through graph-native execution and remove fallback calls to the old hand-written model runtime.
- [ ] 2.2 Delete `src/agentos/runtime/model_backed.py` if no supported entry point requires it.
- [ ] 2.3 Remove `ModelBackedAgentRuntime` from `AgentOsApp` bootstrap state and status surfaces, replacing configuration checks with graph-native model readiness where needed.
- [ ] 2.4 Update CLI and TUI routing tests so model-configured natural-language input uses graph-native execution.
- [ ] 2.5 Keep explicit legacy DSL tasks on deterministic graph execution and preserve tests for that behavior.

## 3. Clean Graph Decision Scaffolding

- [ ] 3.1 Remove unused `decision_prompt` and `PydanticOutputParser` scaffolding from `src/agentos/runtime/app.py` when graph-native model decisions use `RuntimeDecision` tool/function calls.
- [ ] 3.2 Keep deterministic `_decide_from_task()` for fallback and legacy DSL behavior.
- [ ] 3.3 Ensure graph execution traces still record enough decision metadata after removing unused prompt/parser code.
- [ ] 3.4 Run graph runtime tests covering model decisions, tool calls, approval pause/resume, and deterministic fallback.

## 4. Narrow Legacy Memory Fields

- [ ] 4.1 Update prompt and bundle construction so `user_profile`, `remembered_facts`, and `task_state` are the authoritative model-visible memory layers.
- [ ] 4.2 Keep `accepted_constraints` only as bounded legacy context or migration data, not as the primary remembered-fact source.
- [ ] 4.3 Keep `user_preferences` only as compatibility or derived projection data where needed, not as the primary user-profile source.
- [ ] 4.4 Preserve backwards-compatible loading for old memory files that lack structured memory layers.
- [ ] 4.5 Update lifecycle and policy tests to prove structured memory overrides or supersedes legacy compatibility fields.

## 5. Documentation And OpenSpec Cleanup

- [ ] 5.1 Update architecture docs that still describe `ModelBackedAgentRuntime` or the old hand-written model loop as the real model path.
- [ ] 5.2 Update product and configuration docs to describe graph-native model execution as the supported path.
- [ ] 5.3 Archive completed OpenSpec changes once cleanup implementation is verified.

## 6. Verification

- [ ] 6.1 Run focused tests for CLI, packaged CLI, graph runtime, context lifecycle, approval policy, and tool registry.
- [ ] 6.2 Run full test suite.
- [ ] 6.3 Manually smoke-test a model-backed shell session with natural language, deterministic DSL input, approval, file read/write, remembered facts, and context recall.
