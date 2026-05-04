## 1. Session Persistence And Replay

- [x] 1.1 Persist runtime session state, step history, and task linkage in a stable on-disk structure
- [ ] 1.2 Add commands or APIs to list sessions, inspect one session, and resume prior work
- [ ] 1.3 Add bounded session continuation flows so resumed sessions can consume newly available background results
- [ ] 1.4 Add tests or demos that show an interrupted session being resumed and replayed

## 2. Structured Tool Registry

- [ ] 2.1 Define a standard tool registry interface and migrate existing execution paths onto it
- [ ] 2.2 Add a first coding-oriented tool set covering repository search, file read, patch or write, and test execution
- [ ] 2.3 Connect structured tool results back into runtime state for later role or loop steps
- [ ] 2.4 Add tests or demos that show a coding task using multiple registered tools end-to-end

## 3. Advanced Context Engineering

- [ ] 3.1 Extend context management with task-aware selection and context bundle construction
- [ ] 3.2 Add long-history compression or summarization for runtime and tool traces
- [ ] 3.3 Introduce repository or workspace context signals that can be merged with message history
- [ ] 3.4 Add tests or demos that show context selection changing based on task and history size

## 4. Role-Based Coding Workflow

- [ ] 4.1 Add bounded planner / executor / reviewer role records to the runtime workflow
- [ ] 4.2 Connect role transitions to tool results, task state, and loop continuation rules
- [ ] 4.3 Add tests or demos that show a multi-role coding task progressing through planning, execution, and review

## 5. Interactive CLI

- [ ] 5.1 Add CLI flows for session listing, resume, and historical inspection
- [ ] 5.2 Add a bounded `watch` or `poll` style CLI flow for continued session progress
- [ ] 5.3 Improve runtime output presentation for longer sessions or streamed progress
- [ ] 5.4 Update repository docs and milestone notes so the third change remains teachable and taggable
