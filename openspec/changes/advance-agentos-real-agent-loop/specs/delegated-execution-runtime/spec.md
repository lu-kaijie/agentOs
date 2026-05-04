## ADDED Requirements

### Requirement: Work units must support execution-oriented delegation
The system SHALL define a path for work units to move from coordination records into actual delegated execution flows.

#### Scenario: Coordinator delegates a task
- **WHEN** the coordinator assigns a bounded role-specific unit of work
- **THEN** the system can represent that unit as executable delegated work rather than only passive metadata

### Requirement: Delegated execution must preserve role boundaries
The system SHALL keep role-specific delegated flows inspectable so contributors can tell which role handled which work.

#### Scenario: Contributor reviews delegated execution
- **WHEN** delegated work has been executed
- **THEN** the recorded state makes clear which role executed which unit and what result was returned

### Requirement: Delegated execution must integrate with task and workspace state
The system SHALL allow delegated work units to reference task records or isolated workspaces when needed.

#### Scenario: Delegated unit targets isolated work
- **WHEN** a delegated work unit is intended to operate in a particular execution context
- **THEN** the system can associate that unit with the relevant task or workspace state
