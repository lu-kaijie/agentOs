## MODIFIED Requirements

### Requirement: Runtime context must be selected through a configurable policy runtime
The system SHALL prepare runtime context through a configurable policy runtime instead of relying only on hardcoded bundle-construction rules, and that policy runtime SHALL be able to combine task hints, layered memory, workspace retrieval, type-aware reducers, and budget policies.

#### Scenario: Executor prepares context for a file-editing step
- **WHEN** the executor role needs context for a coding step
- **THEN** the runtime selects context through a configurable policy that can combine task hints, layered memory, workspace retrieval, type-aware reduction, and role-specific needs

### Requirement: Different roles must receive different bounded context views
The system SHALL allow planner, executor, and reviewer to receive different bounded context views derived from the same persisted runtime and layered memory state.

#### Scenario: Reviewer prepares its context
- **WHEN** the reviewer role prepares its context
- **THEN** it can receive a context view prioritizing tool results, verification signals, unresolved risks, and handoff data over raw workspace exploration

### Requirement: Context policy decisions must remain inspectable
The system SHALL preserve inspectable records of which context selectors, reducers, memory layers, retrieval sources, and budget decisions were used for each role step.

#### Scenario: Contributor audits a context decision
- **WHEN** a contributor inspects how one role step assembled its prompt context
- **THEN** they can determine which context policy components selected, compressed, retrieved, retained, or dropped the final context payload

### Requirement: Final context assembly must remain runtime-controlled
The system SHALL keep final context assembly under explicit runtime policy control rather than delegating end-to-end retention and selection decisions to a model summarizer.

#### Scenario: Runtime builds a bounded executor bundle
- **WHEN** the executor role receives compressed memory plus structured facts
- **THEN** the runtime policy still decides which layers, facts, and summaries fit inside the final budget instead of relying on a model to choose the entire final bundle alone
