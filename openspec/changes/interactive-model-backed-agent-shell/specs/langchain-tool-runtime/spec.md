## ADDED Requirements

### Requirement: Tool runtime must use LangChain-native tool abstractions on the main path
The system SHALL execute its primary coding-tool path through LangChain-native tool abstractions so schema definition, tool binding, and invocation are framework-first wherever LangChain can fully cover the behavior.

#### Scenario: Executor binds coding tools for a model-backed turn
- **WHEN** the executor prepares tools for a model-backed coding step
- **THEN** the runtime binds the available coding tools through LangChain-native tool definitions instead of routing the main path through a custom registry-first execution layer

### Requirement: LangChain tool runtime must preserve harness boundaries
The system SHALL preserve approval policy, workspace constraints, command-execution boundaries, and structured persistence when a tool is invoked through the LangChain-native runtime.

#### Scenario: Model-backed tool invocation reaches the harness boundary
- **WHEN** a LangChain-bound tool triggers file edits, repository search, or command execution
- **THEN** the runtime still enforces the existing harness approval and workspace boundaries before the underlying action is executed

### Requirement: LangChain tool runtime must support bounded deterministic fallback
The system SHALL allow bounded deterministic fallback only where required for testing, recovery, or controlled offline execution, without making the fallback path the primary runtime architecture.

#### Scenario: Runtime executes without valid model credentials
- **WHEN** the model-backed path is unavailable or disabled
- **THEN** the runtime can use the limited deterministic fallback path while keeping the LangChain-native tool definitions and persistence contracts aligned with the primary architecture
