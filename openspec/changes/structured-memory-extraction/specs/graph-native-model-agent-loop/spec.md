## ADDED Requirements

### Requirement: Model decisions must receive structured memory context
The system SHALL provide graph-native model decisions with structured memory layers as first-class context.

#### Scenario: Remembered facts are outside recent messages
- **WHEN** a model-backed session has remembered facts that are no longer present in the recent-message window
- **THEN** `model_decide` receives those facts from the structured remembered-facts layer
- **AND** the model can answer questions about those facts without relying on recent-message compression

#### Scenario: User profile is available to model decisions
- **WHEN** a model-backed session has extracted user profile preferences
- **THEN** `model_decide` receives bounded user profile context including preferred language and response style
- **AND** the model can apply those preferences without scanning raw conversation history

### Requirement: Model-visible tool context must be bounded and structured
The system SHALL avoid injecting large raw tool outputs as long-lived conversation messages for graph-native model decisions.

#### Scenario: Search produces large output
- **WHEN** a model-backed graph iteration executes a repository search that produces large stdout
- **THEN** the complete output remains available in persisted tool results
- **AND** subsequent model decisions receive bounded tool summaries or facts instead of the full stdout as conversation history

### Requirement: Graph state must carry memory snapshots without owning memory lifecycle
The system SHALL keep `AgentGraphState` as runtime state while structured memory lifecycle remains owned by context components.

#### Scenario: Context is prepared for a model decision
- **WHEN** `prepare_context` runs before `model_decide`
- **THEN** `AgentGraphState["memory_state"]` contains the current structured memory snapshot
- **AND** `AgentGraphState["context_bundle"]` contains the model-visible projection of that memory
- **AND** field-level memory extraction and merge are performed by context lifecycle components rather than by graph routing nodes
