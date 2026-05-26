## ADDED Requirements

### Requirement: Model-backed execution must use the LangGraph agent loop
The system SHALL support a model-backed execution mode that runs through the same LangGraph loop used by deterministic execution.

#### Scenario: Model run enters the graph runtime
- **WHEN** a contributor runs a model-enabled task through the CLI
- **THEN** the runtime executes through the graph lifecycle
- **AND** the recorded trace includes context preparation, model decision, action handling, and iteration finalization

#### Scenario: Deterministic fallback remains available
- **WHEN** a contributor runs without model mode or without valid model configuration
- **THEN** the runtime uses deterministic decision behavior
- **AND** existing legacy DSL tasks continue to execute without model access

### Requirement: Context must be prepared before each model decision
The system SHALL run context preparation before every graph-native model decision.

#### Scenario: Model decides after context preparation
- **WHEN** model-backed execution is about to choose the next action
- **THEN** `ContextManager.prepare_role_context()` has prepared a bounded context bundle for the active task
- **AND** the model decision uses that context bundle as its primary runtime context

#### Scenario: Tool observations are absorbed on the next iteration
- **WHEN** a model-backed iteration executes a tool and finalizes the step
- **THEN** the next iteration prepares context again
- **AND** the new context can include the prior tool result, memory update, and audit record

### Requirement: Model decisions must produce structured runtime decisions
The system SHALL require graph-native model decisions to produce a structured `RuntimeDecision`.

#### Scenario: Model selects a tool action
- **WHEN** the model decides to inspect or modify the workspace
- **THEN** it emits a structured decision identifying the action, tool name, and tool input
- **AND** the graph routes that decision through existing approval and tool execution nodes

#### Scenario: Model responds without a tool
- **WHEN** the model determines that no tool call is needed
- **THEN** it emits a structured respond decision
- **AND** the graph routes the result through the direct response path and finalizes the iteration

### Requirement: Model-backed tool use must remain graph-observable
The system SHALL record model-backed decisions, tool executions, and final iteration state in the same inspectable graph state used by deterministic execution.

#### Scenario: Contributor inspects a model-backed session
- **WHEN** a model-backed task has executed one or more steps
- **THEN** the persisted session state includes the model decision trace, tool results, context audit records, completed tasks, and final output

### Requirement: Model-backed execution must preserve harness execution boundaries
The system SHALL route model-backed command and test execution through the existing harness execution boundary.

#### Scenario: Model selects a shell command
- **WHEN** the model emits a structured decision to run a command
- **THEN** the graph evaluates the command through the existing approval policy
- **AND** approved execution uses the existing `CommandExecutor` and `ExecutionRequest` path
- **AND** the resulting `ExecutionResult` is persisted as a structured tool result

#### Scenario: Model selects a test command
- **WHEN** the model emits a structured decision to run tests
- **THEN** test execution uses the existing `test_run` tool and harness executor
- **AND** timeout, exit code, stdout, stderr, and command metadata remain inspectable

### Requirement: Model-backed execution must preserve background re-entry
The system SHALL preserve existing background job re-entry behavior in model-backed graph execution.

#### Scenario: Completed background job is waiting
- **WHEN** a model-backed graph run starts or resumes with an unconsumed completed background job
- **THEN** the graph consumes the background result through the existing background manager
- **AND** the result can enqueue the same follow-up runtime steps as deterministic execution

### Requirement: Model-backed execution must preserve workspace and delegated work coordination
The system SHALL preserve existing workspace resolution, task binding, and delegated work-unit coordination behavior when model-backed graph execution is enabled.

#### Scenario: Work unit executes in a workspace
- **WHEN** a delegated work unit is executed while model-backed graph execution is available
- **THEN** workspace resolution uses the existing workspace manager
- **AND** execution uses the existing local harness executor
- **AND** linked task state and work-unit status are persisted through their existing managers

#### Scenario: Model-backed graph does not bypass coordination state
- **WHEN** model-backed execution needs to inspect or act on delegated work state
- **THEN** it uses graph-visible manager state or structured tool results
- **AND** it does not run commands outside the existing harness and coordination boundaries

### Requirement: Hidden ReAct loops must not be required for graph-native model execution
The system SHALL NOT require a hidden multi-tool ReAct loop inside the graph-native model-backed path.

#### Scenario: Model-backed execution needs multiple tool calls
- **WHEN** a model-backed task requires multiple tool calls
- **THEN** each tool call can occur as a separate graph iteration
- **AND** context preparation runs before the model chooses each subsequent action
