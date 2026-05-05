## ADDED Requirements

### Requirement: Context assembly must produce inspectable audit records
The system SHALL produce inspectable audit records for context assembly, reduction, and selection decisions.

#### Scenario: Contributor audits one role turn
- **WHEN** a planner, executor, or reviewer turn assembles model-facing context
- **THEN** the system records which layers, reducers, retrieval sources, and budget allocations contributed to the final bundle

### Requirement: Context audit output must expose retained and dropped information classes
The system SHALL expose which information classes were retained, compressed, or dropped during lifecycle management.

#### Scenario: Contributor inspects why the agent forgot older detail
- **WHEN** an older detail is no longer present in the active bundle
- **THEN** the audit record shows whether that detail class was retained in another layer, compressed into structured memory, or dropped by budget policy
