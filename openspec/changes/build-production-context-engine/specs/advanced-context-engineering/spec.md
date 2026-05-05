## MODIFIED Requirements

### Requirement: Context selection must be task-aware
The system SHALL select or compose context based on the current task, session state, workspace signals, layered memory state, budget policy, and role-specific policy components rather than relying only on raw chronological history or hardcoded bundle-selection rules.

#### Scenario: Runtime prepares context for a coding step
- **WHEN** the runtime prepares model input for a specific coding subtask
- **THEN** it can prioritize the most relevant files, summaries, prior results, structured memory layers, and role-specific signals through a configurable context policy runtime

### Requirement: Long context must support compression or summarization
The system SHALL provide proactive, inspectable, type-aware compression for long interaction or tool history while preserving important working information, and the compression path SHALL be exposed as explicit lifecycle and reduction components rather than only inline hardcoded logic.

#### Scenario: Session history grows beyond a practical limit
- **WHEN** runtime history or tool output becomes too large to include directly
- **THEN** the system automatically preserves the important information through compacted structured memory and lifecycle records before the next model-facing step

### Requirement: Multiple context sources must be mergeable
The system SHALL support merging context from messages, persisted summaries, layered memory, file or repository signals, prior tool outputs, failure memory, and policy-driven retrieval sources.

#### Scenario: Runtime combines several context sources
- **WHEN** the runtime needs both recent conversation state and repository-specific knowledge
- **THEN** it can combine those sources into a coherent, inspectable context bundle through a configurable policy runtime
