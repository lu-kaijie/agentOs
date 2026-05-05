## ADDED Requirements

### Requirement: CLI usage must support session-oriented workflows
The system SHALL provide CLI commands or flows for listing sessions, resuming prior work, and inspecting saved runtime state.

#### Scenario: Contributor returns to earlier work
- **WHEN** a contributor wants to continue a previous agent session
- **THEN** the CLI exposes a direct way to locate and resume that session

### Requirement: CLI must support bounded watch or poll flows for continued sessions
The system SHALL provide a bounded CLI flow for watching or polling a saved session so newly available runtime events can trigger continued progress without requiring a manual full restart every time.

#### Scenario: Contributor watches a session waiting on background work
- **WHEN** a contributor wants a saved session to continue after background work completes
- **THEN** the CLI provides a bounded watch or poll mode that can detect the new state and resume that session

### Requirement: CLI execution must remain observable during longer runs
The system SHALL provide a more readable execution view for longer agent runs than a single large JSON dump.

#### Scenario: Contributor watches a longer coding run
- **WHEN** a runtime session performs multiple steps and tool calls
- **THEN** the CLI exposes an inspectable live or staged view of progress, trace, and major state changes

#### Scenario: Contributor reads Chinese content in CLI output
- **WHEN** a CLI command prints persisted content, tool payloads, or runtime state that contains Chinese text
- **THEN** the CLI renders readable UTF-8 text directly rather than JSON Unicode escape sequences such as `\u4e2d\u6587`

### Requirement: CLI commands must align with the persisted runtime model
The system SHALL keep CLI session and log commands aligned with persisted runtime state rather than relying only on transient in-memory values.

#### Scenario: Contributor inspects runtime logs after the fact
- **WHEN** a contributor runs a CLI command to inspect prior work
- **THEN** the displayed information is sourced from persisted runtime records that match the session being examined
