## ADDED Requirements

### Requirement: Legacy model runtime must be removed from product execution
The system SHALL use the graph-native LangGraph runtime as the only product path for real-model execution.

#### Scenario: Model shell input uses graph-native runtime
- **WHEN** a model-configured shell receives natural-language input
- **THEN** the task is executed through `RuntimeBootstrap` and graph-native model decisions
- **AND** the old hand-written `ModelBackedAgentRuntime` path is not invoked

#### Scenario: Model run command uses graph-native runtime
- **WHEN** `agentos run --model` is executed
- **THEN** the task is executed through the graph-native model path
- **AND** model decisions route through approval, tool execution, and finalization graph nodes

### Requirement: Deterministic fallback must remain supported
The system SHALL preserve deterministic execution for explicit DSL tasks and no-model environments.

#### Scenario: Explicit DSL task remains deterministic
- **WHEN** a user runs a task with a deterministic prefix such as `read:`, `run:`, `write:`, `patch:`, `test:`, `steps:`, or `code:`
- **THEN** the deterministic strategy handles the task unless the user explicitly changes that behavior

#### Scenario: No model credentials are configured
- **WHEN** model credentials are unavailable
- **THEN** deterministic fallback execution remains available
- **AND** tests do not require live model access for deterministic behavior

### Requirement: Cleanup must remove obsolete tests and docs
The system SHALL update tests and documentation so they describe only supported runtime paths.

#### Scenario: Documentation references model path
- **WHEN** architecture or product docs describe real-model execution
- **THEN** they describe the graph-native model path
- **AND** they do not present `ModelBackedAgentRuntime` as the active model route

#### Scenario: Tests reference legacy model runtime
- **WHEN** tests validate model-backed execution
- **THEN** they validate graph-native model behavior or deterministic fallback behavior
- **AND** they do not depend on the deleted legacy runtime implementation
