## ADDED Requirements

### Requirement: CLI usage must support session-oriented workflows
The system SHALL provide CLI commands or flows for listing sessions, resuming prior work, and inspecting saved runtime state.

#### Scenario: Contributor returns to earlier work
- **WHEN** a contributor wants to continue a previous agent session
- **THEN** the CLI exposes a direct way to locate and resume that session

### Requirement: CLI execution must remain observable during longer runs
The system SHALL provide a more readable execution view for longer agent runs than a single large JSON dump.

#### Scenario: Contributor watches a longer coding run
- **WHEN** a runtime session performs multiple steps and tool calls
- **THEN** the CLI exposes an inspectable live or staged view of progress, trace, and major state changes

### Requirement: CLI commands must align with the persisted runtime model
The system SHALL keep CLI session and log commands aligned with persisted runtime state rather than relying only on transient in-memory values.

#### Scenario: Contributor inspects runtime logs after the fact
- **WHEN** a contributor runs a CLI command to inspect prior work
- **THEN** the displayed information is sourced from persisted runtime records that match the session being examined
