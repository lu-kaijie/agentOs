## ADDED Requirements

### Requirement: Runtime must maintain layered structured memory
The system SHALL maintain structured memory layers for active sessions instead of relying only on raw chronological message history or one flattened summary.

#### Scenario: Runtime persists session working state
- **WHEN** a session advances through multiple turns
- **THEN** the system stores at least recent messages, working memory, tool facts, workspace state, and failure or decision memory as distinct layers

### Requirement: Resume must restore layered memory state
The system SHALL restore layered memory state during session resume so the agent can continue work from structured context rather than reconstructing everything from raw turns.

#### Scenario: Contributor resumes an interrupted coding session
- **WHEN** a persisted session is resumed
- **THEN** the runtime restores the structured memory layers needed to continue the current goal, recent decisions, recent failures, and relevant workspace state

### Requirement: Layered memory must support role-specific views
The system SHALL allow planner, executor, and reviewer to consume different bounded views derived from the same layered memory state.

#### Scenario: Reviewer prepares a verification turn
- **WHEN** the reviewer role requests context from a session with layered memory
- **THEN** the reviewer can prioritize verification facts, recent tool outcomes, and unresolved risks over unrelated workspace exploration
