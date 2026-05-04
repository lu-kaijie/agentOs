## MODIFIED Requirements

### Requirement: Context selection must be task-aware
The system SHALL select or compose context based on the current task, session state, workspace signals, and role-specific policy components rather than relying only on raw chronological history or hardcoded bundle-selection rules.

#### Scenario: Runtime prepares context for a coding step
- **WHEN** the runtime prepares model input for a specific coding subtask
- **THEN** it can prioritize the most relevant files, summaries, prior results, and role-specific signals through a configurable context policy runtime

### Requirement: Long context must support compression or summarization
The system SHALL provide a way to compress or summarize long interaction or tool history while preserving important working information, and the compression path SHALL be exposed as an inspectable reducer or compressor component rather than only inline hardcoded logic.

#### Scenario: Session history grows beyond a practical limit
- **WHEN** runtime history or tool output becomes too large to include directly
- **THEN** the system can preserve the important information through a compacted representation produced by an explicit context reduction component

### Requirement: Multiple context sources must be mergeable
The system SHALL support merging context from messages, persisted summaries, file or repository signals, prior tool outputs, and policy-driven retrieval sources.

#### Scenario: Runtime combines several context sources
- **WHEN** the runtime needs both recent conversation state and repository-specific knowledge
- **THEN** it can combine those sources into a coherent, inspectable context bundle through a configurable policy runtime
