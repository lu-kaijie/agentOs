## 1. Runtime Mode Plumbing

- [ ] 1.1 Add an execution mode field or parameter to `RuntimeBootstrap.run_task()` and `stream_task()` to distinguish deterministic and model-backed graph execution.
- [ ] 1.2 Update `AgentOsApp.run_session_task()` or add a graph-native model wrapper so model mode can enter `RuntimeBootstrap` instead of the hand-written model loop.
- [ ] 1.3 Preserve existing deterministic defaults for `agentos run`, legacy DSL tasks, tests, and no-model environments.

## 2. Graph-Native Model Decision Strategy

- [ ] 2.1 Implement a model decision strategy that builds a prompt from `state["active_task"]`, `state["context_bundle"]`, recent tool results, and `RuntimeDecision` format instructions.
- [ ] 2.2 Parse model output into `RuntimeDecision` and record model decision metadata in `execution_trace` or role records.
- [ ] 2.3 Keep `_decide_from_task()` as the deterministic strategy and route legacy DSL tasks to it.
- [ ] 2.4 Add clear error handling for malformed model decisions, including debug context for model name, prompt size, and raw output preview.

## 3. LangGraph Loop Integration

- [ ] 3.1 Modify the graph decision node so model mode uses the model decision strategy after `prepare_context`.
- [ ] 3.2 Ensure model decisions route through existing `approval_gate`, `tool_execute`, and `respond_directly` paths.
- [ ] 3.3 Ensure each model-backed tool call finalizes one iteration and returns to `prepare_context` before the next model decision.
- [ ] 3.4 Preserve background result re-entry and pending-task behavior in both deterministic and model modes.

## 4. CLI And Shell Routing

- [ ] 4.1 Route `agentos run --model` to graph-native model execution.
- [ ] 4.2 Route model-configured natural-language shell input to graph-native model execution.
- [ ] 4.3 Keep explicit legacy prefixes such as `run:`, `read:`, `write:`, `patch:`, `test:`, `steps:`, and `code:` on deterministic graph execution unless explicitly changed later.
- [ ] 4.4 Keep the old `ModelBackedAgentRuntime` available during transition without making it the primary `--model` path.

## 5. Tests And Verification

- [ ] 5.1 Add unit tests for model decision strategy using a fake or mocked model response.
- [ ] 5.2 Add integration coverage proving model mode trace includes `prepare_context`, model decision, action handling, and `finalize_iteration`.
- [ ] 5.3 Add coverage proving a multi-tool model-backed task performs separate graph iterations with context preparation before each decision.
- [ ] 5.4 Verify deterministic fallback tests still pass without API credentials.
- [ ] 5.5 Update product or architecture docs to describe the unified LangGraph agent loop and the location of context management.
