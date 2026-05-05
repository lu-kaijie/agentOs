## ADDED Requirements

### Requirement: Different context types must use different compression strategies
The system SHALL apply type-aware compression strategies instead of compressing all context through one generic textual reducer.

#### Scenario: Runtime compresses mixed session context
- **WHEN** the system reduces a session containing conversation history, tool outputs, task plans, user constraints, and failure records
- **THEN** it uses different reducers or extractors for those types rather than flattening them into one undifferentiated summary

### Requirement: User constraints and decisions must be preserved with higher priority
The system SHALL preserve user requirements, accepted constraints, rejected approaches, and current task decisions with higher priority than ordinary conversational phrasing.

#### Scenario: Long discussion contains both constraints and casual discussion
- **WHEN** the system compresses a long session that includes user constraints and general explanatory dialog
- **THEN** the resulting memory retains the constraints and active decisions even if less critical discussion is aggressively reduced

### Requirement: Tool outputs must be reduced into structured facts
The system SHALL reduce large tool outputs into structured facts that capture key outcomes, related files or commands, and success or failure state.

#### Scenario: Large test output enters session context
- **WHEN** a test or shell tool returns a long output payload
- **THEN** the system stores a structured tool fact that retains the key result and impact on follow-up work without requiring the full raw output in future prompts

### Requirement: Compression must support hybrid extraction and summarization
The system SHALL support a hybrid compression path in which structured hard facts are extracted programmatically, semantic memory is compressed through model-backed summarization when needed, and final context assembly remains system-controlled.

#### Scenario: Runtime compacts a mixed coding session
- **WHEN** the session contains both machine-readable execution facts and long natural-language discussion
- **THEN** the system extracts the hard facts programmatically, summarizes the semantic discussion through a dedicated semantic compressor, and keeps final budget allocation under explicit runtime control
