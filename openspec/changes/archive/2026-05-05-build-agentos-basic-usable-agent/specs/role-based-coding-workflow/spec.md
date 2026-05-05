## ADDED Requirements

### Requirement: The runtime must support a bounded role-based coding workflow
The system SHALL define a bounded coding workflow with explicit roles such as planner, executor, and reviewer.

#### Scenario: Runtime handles a non-trivial coding task
- **WHEN** the runtime must inspect, change, and verify code
- **THEN** it can assign distinct responsibilities across explicit roles rather than treating the task as a single opaque step

### Requirement: Role transitions must remain inspectable
The system SHALL preserve records showing which role produced a plan, executed work, or reviewed results.

#### Scenario: Contributor reviews a role-based session
- **WHEN** a contributor inspects a completed coding workflow
- **THEN** they can determine which role handled each major stage and what output it produced

### Requirement: Role-based workflow must integrate with tool and task state
The system SHALL allow role-specific workflow steps to consume tool results, task records, and workspace state.

#### Scenario: Reviewer validates executor output
- **WHEN** the reviewer stage inspects an earlier execution
- **THEN** it can access the relevant tool outputs and task context without reconstructing them from free-form memory
