## ADDED Requirements

### Requirement: Runtime must expose explicit agent-role abstractions
The system SHALL expose bounded agent-role abstractions for planner, executor, and reviewer so each role has a defined input contract, output contract, and inspectable state contribution.

#### Scenario: Runtime enters planner role
- **WHEN** a coding session begins a non-trivial task
- **THEN** the planner role receives explicit task, context, prior state, and model-runtime inputs and emits a structured planning output rather than relying on a hardcoded stage-only function

### Requirement: Role handoff records must be persisted and inspectable
The system SHALL persist explicit handoff records between roles so contributors can inspect why control moved from one role to another.

#### Scenario: Executor takes over after planning
- **WHEN** the planner finishes preparing work for the executor
- **THEN** the runtime persists a handoff record that identifies the source role, target role, summary of the handoff, and relevant context or tool references

### Requirement: Role agents must consume bounded runtime state
The system SHALL provide each role agent a bounded, role-appropriate view of runtime state including context bundle, relevant tool results, and task status.

#### Scenario: Reviewer validates executor work
- **WHEN** the reviewer role inspects executor output
- **THEN** it receives the relevant tool results, context bundle, and task progress as structured inputs without reconstructing them from free-form text alone
