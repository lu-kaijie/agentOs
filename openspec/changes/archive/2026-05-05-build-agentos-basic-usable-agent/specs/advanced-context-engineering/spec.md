## ADDED Requirements

### Requirement: Context selection must be task-aware
The system SHALL select or compose context based on the current task, session state, and workspace signals rather than relying only on raw chronological history.

#### Scenario: Runtime prepares context for a coding step
- **WHEN** the runtime prepares model input for a specific coding subtask
- **THEN** it can prioritize the most relevant files, summaries, and prior results for that subtask

### Requirement: Long context must support compression or summarization
The system SHALL provide a way to compress or summarize long interaction or tool history while preserving important working information.

#### Scenario: Session history grows beyond a practical limit
- **WHEN** runtime history or tool output becomes too large to include directly
- **THEN** the system can preserve the important information through a compacted representation

### Requirement: Multiple context sources must be mergeable
The system SHALL support merging context from messages, persisted summaries, file or repository signals, and prior tool outputs.

#### Scenario: Runtime combines several context sources
- **WHEN** the runtime needs both recent conversation state and repository-specific knowledge
- **THEN** it can combine those sources into a coherent, inspectable context bundle
