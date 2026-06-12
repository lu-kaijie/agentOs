## MODIFIED Requirements

### Requirement: Model-backed execution uses the LangGraph agent loop
The system SHALL route real model-backed task execution through the same LangGraph loop used by deterministic fallback execution, and SHALL NOT expose the old hand-written model runtime as a product execution path.

#### Scenario: Model mode is enabled
- **WHEN** a user runs a natural-language task in model mode
- **THEN** the task enters the LangGraph loop
- **AND** `prepare_context` runs before model decision
- **AND** `model_decide` uses structured `RuntimeDecision` tool/function output
- **AND** the resulting decision routes through graph nodes such as `approval_gate`, `tool_execute`, `respond_directly`, and `finalize_iteration`
- **AND** `ModelBackedAgentRuntime` is not called

#### Scenario: Deterministic mode remains available
- **WHEN** a user runs deterministic fallback tasks or explicit legacy DSL tasks
- **THEN** the graph uses the deterministic decision strategy
- **AND** existing tool, approval, background, and finalization graph behavior remains available

### Requirement: Model decisions use graph-native structured output
The system SHALL keep graph-native model decisions based on structured `RuntimeDecision` tool/function calls rather than prompt-only JSON parsing.

#### Scenario: Model returns a decision
- **WHEN** the graph-native decision strategy calls a configured model
- **THEN** it requires a `RuntimeDecision` tool/function call
- **AND** it validates the tool-call arguments into a `RuntimeDecision`
- **AND** obsolete prompt-only decision parser scaffolding is not used as the active model decision mechanism
