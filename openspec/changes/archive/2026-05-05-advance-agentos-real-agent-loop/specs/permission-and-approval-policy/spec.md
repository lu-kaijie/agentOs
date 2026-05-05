## ADDED Requirements

### Requirement: Tool execution approval must be driven by explicit policy
The system SHALL define tool-execution approval through an explicit policy layer rather than scattering ad hoc rules across runtime nodes.

#### Scenario: Runtime evaluates a risky command
- **WHEN** the runtime considers executing a command that matches a risky policy case
- **THEN** the approval requirement is determined through the policy layer

### Requirement: Policy decisions must be inspectable
The system SHALL make it possible to understand why a command required approval or was allowed automatically.

#### Scenario: Contributor inspects an approval decision
- **WHEN** a contributor reviews runtime output for a guarded execution
- **THEN** they can determine which policy condition caused the approval outcome

### Requirement: Approval policy must be extensible
The system SHALL keep the initial permission system structured so new rule categories can be added without rewriting runtime routing logic.

#### Scenario: Project adds a new approval category
- **WHEN** the project needs to add another rule category for tool execution
- **THEN** that category can be introduced by extending the policy layer rather than rewriting unrelated runtime nodes
