## 1. Repository Bootstrap

- [x] 1.1 Add baseline GitHub-facing files such as `README.md`, `.gitignore`, and contribution/setup notes appropriate for an early public project
- [x] 1.2 Define the first milestone map in repository documentation, including the learning objective and expected output for each step
- [x] 1.3 Decide and document the Git tag naming convention for milestone checkpoints

## 2. Python Environment Foundation

- [x] 2.1 Add local virtual environment setup instructions using a project-local `.venv-agentos`
- [x] 2.2 Create pinned `requirements.txt` for runtime dependencies and pinned dev requirements if separate tooling is needed
- [x] 2.3 Add a basic verification step that confirms the environment installs successfully from the pinned requirements

## 3. Project Skeleton

- [x] 3.1 Create the initial Python package layout for runtime, harness, CLI entrypoint, and shared configuration
- [x] 3.2 Add a minimal CLI command that loads configuration and starts the project entrypoint without implementing full agent behavior
- [x] 3.3 Add tests or smoke checks that validate the skeleton imports and entrypoint wiring

## 4. Harness Foundation

- [x] 4.1 Define the harness interfaces for command execution, execution results, and future approval hooks
- [x] 4.2 Implement a first local command runner that is intentionally narrow and easy to inspect
- [x] 4.3 Add tests that verify harness execution boundaries and result handling

## 5. LangGraph Runtime

- [x] 5.1 Add the initial LangGraph state model and document the meaning of each state field
- [x] 5.2 Implement a minimal graph with separate model-decision and tool-execution stages
- [x] 5.3 Connect the graph runtime to the harness executor through a narrow adapter layer
- [x] 5.4 Add tests or demos that show at least one task flowing through the graph and tool loop

## 6. Task Control Plane

- [ ] 6.1 Design a persistent task model with statuses, identifiers, and on-disk storage
- [ ] 6.2 Add explicit task dependency support so the system can distinguish ready and blocked work
- [ ] 6.3 Connect task state to the runtime so multi-step work can continue across sessions
- [ ] 6.4 Add tests that verify persistence, dependency transitions, and reload behavior

## 7. Context And Skill Management

- [ ] 7.1 Define a mechanism for loading task-specific knowledge or skills on demand
- [ ] 7.2 Add a context-management strategy for long-running sessions and large tool outputs
- [ ] 7.3 Keep critical execution state outside transient chat history where continuation requires durability
- [ ] 7.4 Add tests or demos that show controlled knowledge loading and context reduction behavior

## 8. Advanced Framework Coverage

- [ ] 8.1 Add a milestone plan for advanced LangChain/LangGraph topics to be covered in the project, tied to concrete runtime goals
- [ ] 8.2 Extend the runtime with structured output or schema-driven model responses
- [ ] 8.3 Add conditional routing or multi-step branching in the LangGraph workflow
- [ ] 8.4 Add state persistence, checkpointing, or memory features appropriate for the project stage
- [ ] 8.5 Add a human-in-the-loop approval or interruption point in the graph or harness flow
- [ ] 8.6 Add tracing, evaluation, or runtime observability hooks so framework behavior can be studied during execution

## 9. Async And Isolated Execution

- [ ] 9.1 Add a background execution path for long-running commands or tool operations
- [ ] 9.2 Add result notification or polling so background work can re-enter the main runtime cleanly
- [ ] 9.3 Design isolated execution contexts for tasks that should not always share one mutable workspace
- [ ] 9.4 Add lifecycle records for background and isolated execution state transitions

## 10. Multi-Agent Coordination

- [ ] 10.1 Define a delegation model for splitting large work into inspectable sub-work units
- [ ] 10.2 Add coordination state that tracks pending, active, and completed delegated work
- [ ] 10.3 Add a first bounded multi-agent or role-based execution flow tied to the task system
- [ ] 10.4 Add tests or demos that show delegated work being coordinated and reconciled

## 11. Milestone Discipline

- [ ] 11.1 Document the expected completion criteria for each milestone so work can stop cleanly between steps
- [ ] 11.2 Add a lightweight release checklist for tagging and publishing each stable checkpoint
- [ ] 11.3 Review the repository documentation to ensure it accurately reflects current scope and limitations at every milestone
