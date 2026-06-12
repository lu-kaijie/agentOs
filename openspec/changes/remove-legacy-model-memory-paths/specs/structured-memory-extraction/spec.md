## MODIFIED Requirements

### Requirement: Structured memory layers are primary model-visible memory
The system SHALL use structured memory layers as the primary model-visible memory source for user profile, remembered facts, and task state.

#### Scenario: Prompt memory is assembled
- **WHEN** a graph-native model decision prompt is prepared
- **THEN** user profile data comes from `user_profile`
- **AND** explicit remembered facts come from `remembered_facts`
- **AND** current task state comes from `task_state`
- **AND** legacy `accepted_constraints` or `user_preferences` fields do not serve as the primary source for remembered facts or user profile behavior

#### Scenario: Old memory files are loaded
- **WHEN** persisted memory lacks newer structured fields
- **THEN** loading memory succeeds with backwards-compatible defaults
- **AND** compatibility fields may still be projected into structured views where safe

### Requirement: Legacy memory compatibility is bounded
The system SHALL keep legacy memory fields only where they are needed for migration, old memory loading, or bounded prompt compatibility.

#### Scenario: Legacy constraints exist
- **WHEN** old memory contains `accepted_constraints`
- **THEN** the system may expose them as bounded legacy context
- **AND** they do not override structured `remembered_facts` or `user_profile`

#### Scenario: User preference fields overlap
- **WHEN** both `user_preferences` and `user_profile` contain language or output-style information
- **THEN** `user_profile` is the authoritative model-visible layer
- **AND** `user_preferences` is treated as compatibility or derived projection data
