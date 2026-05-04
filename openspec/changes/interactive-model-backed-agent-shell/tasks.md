## 1. Persistent Interactive Shell

- [x] 1.1 Add a persistent interactive CLI shell that holds one session open across consecutive user turns
- [x] 1.2 Add shell streaming output, interrupt handling, and session-bound turn history so the shell behaves like a real long-lived agent console
- [x] 1.3 Add a first bounded shell demo or test that proves a contributor can work across multiple turns without one-shot command re-entry

## 2. Agent-Role Runtime Abstraction

- [x] 2.1 Introduce a bounded `RoleAgent` abstraction for planner, executor, and reviewer with explicit role input / output structures
- [x] 2.2 Refactor the current hardcoded planner / executor / reviewer functions to run through the shared role-agent protocol
- [x] 2.3 Persist structured role handoff records so session inspection can explain why control moved between roles

## 3. Context Policy Runtime

- [x] 3.1 Replace the current hardcoded context-bundle selection rules with a configurable context policy pipeline
- [x] 3.2 Add role-specific context views that can combine task hints, history reduction, workspace retrieval, and tool-result prioritization
- [x] 3.3 Persist inspectable records of which context selectors, reducers, and retrieval sources were used per role step

## 4. LangChain Tool Runtime

- [ ] 4.1 Move the main coding tools to LangChain-native tool definitions and bindings
- [ ] 4.2 Preserve harness boundaries, approval policy, workspace constraints, and structured persistence around the LangChain tool runtime
- [ ] 4.3 Keep deterministic fallback execution only where necessary and cover that compatibility with tests

## 5. Real Model Runtime Integration

- [ ] 5.1 Add a real model-backed runtime path that can call the configured provider with valid API credentials
- [ ] 5.2 Connect the persistent shell plus at least one bounded planner/executor/reviewer workflow to real model reasoning and tool usage
- [ ] 5.3 Add explicit configuration, fallback, and integration tests or demos for model-enabled runs

## 6. Integrated Agent Experience

- [ ] 6.1 Update runtime integration so the shell can drive role agents, context-policy outputs, and LangChain-native tools without losing harness observability
- [ ] 6.2 Ensure the shell can autonomously reuse existing session, tool, context, coordination, and role capabilities from one continuous workspace conversation
- [ ] 6.3 Update repository docs and milestone notes so the acceptance standard is clearly “open one persistent window and keep working with the agent”
