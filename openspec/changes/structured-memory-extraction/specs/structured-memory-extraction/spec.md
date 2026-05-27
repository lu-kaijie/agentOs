## ADDED Requirements

### Requirement: Memory extraction must produce structured deltas
The system SHALL extract turn-level memory updates into a structured memory delta rather than relying only on recent-message compression or raw accepted-constraint strings.

#### Scenario: Explicit user fact is extracted
- **WHEN** a user says to remember a named fact such as a test code
- **THEN** the memory extraction result includes a remembered fact record with a key, value, source, scope, confidence, and timestamp metadata
- **AND** the remembered fact remains available after recent messages are compressed

#### Scenario: User preference is extracted
- **WHEN** a user states a stable preference such as preferred language or answer length
- **THEN** the memory extraction result includes a user profile delta for that preference
- **AND** later prompts can inject the preference without scanning recent messages

### Requirement: Model-backed extraction must use structured model output
The system SHALL use structured model output for memory extraction when model-backed execution is configured.

#### Scenario: Model extractor is available
- **WHEN** a model-backed turn completes
- **AND** model-backed memory extraction is configured
- **THEN** the system calls the configured model with a structured memory extraction schema
- **AND** the extractor output is parsed as a memory delta

#### Scenario: Model extractor fails
- **WHEN** the model extractor returns invalid output or raises a provider error
- **THEN** the system records extractor diagnostics
- **AND** falls back to deterministic memory extraction for the turn
- **AND** the user-facing task result is not failed solely because memory extraction failed

### Requirement: Deterministic extraction must remain available
The system SHALL provide deterministic memory extraction for offline mode, tests, and model extraction fallback.

#### Scenario: Model execution is disabled
- **WHEN** a turn completes without model-backed memory extraction
- **THEN** deterministic extraction identifies obvious user preferences and explicit remembered facts
- **AND** emits the same memory delta shape used by model-backed extraction

### Requirement: Memory merge must be field-level
The system SHALL merge extracted memory deltas into existing layered memory without replacing unrelated layers.

#### Scenario: User profile changes
- **WHEN** a memory delta updates the preferred language or response style
- **THEN** only the corresponding user profile fields are updated
- **AND** remembered facts, tool facts, workspace state, and failure memory remain intact

#### Scenario: Remembered fact is corrected
- **WHEN** a later memory delta provides a remembered fact with the same key and a newer source statement
- **THEN** the existing fact is updated or superseded according to the merge policy
- **AND** the older value remains auditable through source metadata or history

### Requirement: Memory layers must have distinct lifecycles
The system SHALL maintain separate retention and injection behavior for stable profile data, remembered facts, task state, tool facts, workspace state, failure memory, and recent messages.

#### Scenario: Recent messages are compressed
- **WHEN** recent messages exceed their compression budget
- **THEN** stable user profile fields and remembered facts remain available through their structured layers
- **AND** the system may drop or summarize old recent messages without losing those structured facts

#### Scenario: Tool output is large
- **WHEN** a tool produces large stdout or payload content
- **THEN** the complete tool result remains available in persisted session state
- **AND** model-visible memory receives only bounded summaries, tool facts, and selected recent tool results

### Requirement: Structured memory must be inspectable
The system SHALL persist structured memory layers in an inspectable format.

#### Scenario: Contributor inspects a session
- **WHEN** a contributor runs a session inspection command
- **THEN** the persisted memory state exposes user profile fields, remembered facts, task state, tool facts, workspace state, failure memory, and lifecycle audit records
- **AND** each extracted fact includes enough source metadata to explain why it exists
