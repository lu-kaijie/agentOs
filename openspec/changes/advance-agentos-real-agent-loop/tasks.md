## 1. Resumable Loop

- [x] 1.1 Refactor the runtime graph so it can continue processing new state instead of always ending after one directed pass
- [x] 1.2 Add explicit loop control and trace output so repeated iterations remain inspectable
- [x] 1.3 Add tests or demos that show the runtime continuing beyond a single one-shot flow

## 2. Background Result Re-entry

- [x] 2.1 Connect completed background job state back into runtime input handling
- [x] 2.2 Add a path for the runtime to detect and consume completed background results in later decision steps
- [x] 2.3 Add tests or demos that show a background task completing and then influencing subsequent runtime behavior

## 3. Delegated Execution

- [x] 3.1 Extend coordination records so work units can move into a bounded execution flow
- [x] 3.2 Add a first role-based delegated execution path tied to work units
- [x] 3.3 Connect delegated execution to task state or workspace state where appropriate
- [x] 3.4 Add tests or demos that show delegated work being created, executed, and reconciled

## 4. Permission Policy

- [ ] 4.1 Extract command approval logic into an explicit policy layer
- [ ] 4.2 Add inspectable policy outputs so approval decisions explain why a command was gated or allowed
- [ ] 4.3 Add tests that verify policy-driven approval behavior

## 5. Documentation And Release Flow

- [ ] 5.1 Add milestone notes and demo commands for the second change so each sub-stage remains teachable
- [ ] 5.2 Update repository docs so the project status reflects the new phase after each stable checkpoint
- [ ] 5.3 Tag and publish each stable checkpoint as the second change progresses
