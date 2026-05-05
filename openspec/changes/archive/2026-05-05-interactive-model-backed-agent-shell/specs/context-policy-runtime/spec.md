## ADDED Requirements

### Requirement: Context preparation must be driven by a configurable policy runtime
The system SHALL prepare runtime context through a configurable policy runtime instead of relying only on hardcoded bundle-construction rules.

#### Scenario: Executor prepares context for a file-editing step
- **WHEN** the executor role needs context for a coding step
- **THEN** the runtime selects context through a configurable policy that can combine task hints, history reduction, workspace retrieval, and role-specific needs

### Requirement: Context policy must support role-specific views
The system SHALL allow planner, executor, and reviewer to receive different bounded context views derived from the same persisted runtime state.

#### Scenario: Reviewer inspects executor output
- **WHEN** the reviewer role prepares its context
- **THEN** it can receive a context view prioritizing tool results, verification signals, and handoff data over raw workspace exploration

### Requirement: Context compression and retrieval must remain inspectable
The system SHALL preserve inspectable records of which context selectors, reducers, and retrieval sources were used for each role step.

#### Scenario: Contributor audits a context decision
- **WHEN** a contributor inspects a role-driven session
- **THEN** they can determine which context policy components selected, compressed, and retrieved the final context payload
