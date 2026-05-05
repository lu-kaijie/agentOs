## ADDED Requirements

### Requirement: Runtime must proactively trigger context lifecycle actions
The system SHALL monitor session context growth and proactively trigger context lifecycle actions when configured thresholds or lifecycle events are reached, instead of relying only on manual compaction calls.

#### Scenario: Session history exceeds the active threshold
- **WHEN** recent conversation, tool output, or accumulated working state grows beyond the configured active threshold for a session
- **THEN** the runtime triggers a context lifecycle action that reduces context pressure before the next model-facing step is assembled

#### Scenario: Lifecycle event forces context maintenance
- **WHEN** a role handoff, turn completion, session resume, or large tool result occurs
- **THEN** the system can trigger lifecycle maintenance even if the raw size threshold has not yet been exceeded

### Requirement: Context lifecycle actions must record trigger metadata
The system SHALL persist inspectable metadata for each lifecycle action so contributors can determine why context maintenance occurred.

#### Scenario: Contributor inspects an automatic context reduction
- **WHEN** a context lifecycle action has been triggered
- **THEN** the system stores the trigger reason, pre-reduction size, post-reduction size, and affected memory layers in an inspectable record
