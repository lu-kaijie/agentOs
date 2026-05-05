## 1. Memory Model Foundation

- [x] 1.1 Define structured memory models for recent messages, working memory, user preferences, tool facts, workspace state, and failure memory
- [x] 1.2 Add persistent storage and load paths for layered memory alongside the existing session context files
- [x] 1.3 Keep backward-compatible loading so existing sessions without layered memory can still resume

## 2. Adaptive Lifecycle Triggers

- [x] 2.1 Add a context lifecycle manager that evaluates thresholds and lifecycle events before model-facing context assembly
- [x] 2.2 Implement trigger rules for size growth, large tool output, role handoff, turn completion, and session resume
- [x] 2.3 Persist lifecycle trigger records including before or after sizes, trigger reasons, and affected memory layers

## 3. Type-Aware Compression Pipeline

- [x] 3.1 Replace the current generic long-history compaction path with dedicated reducers for conversation, constraints, tool results, workspace state, and failure memory
- [x] 3.2 Preserve user requirements, accepted constraints, rejected approaches, and active task decisions with higher priority than casual dialog
- [x] 3.3 Convert large tool outputs into structured tool facts that retain key outcomes, related files or commands, and success or failure state
- [x] 3.4 Implement the hybrid compression split so hard facts are programmatically extracted, semantic memory is model-compressed, and these outputs remain separately inspectable

## 4. Context Policy Runtime Upgrade

- [x] 4.1 Upgrade the context policy runtime to assemble bundles from layered memory instead of relying mainly on recent history summaries
- [x] 4.2 Add role-specific budget allocation across memory layers and context sources
- [x] 4.3 Ensure planner, executor, and reviewer each receive a different bounded role view derived from the same layered memory state

## 5. Runtime And Resume Integration

- [x] 5.1 Integrate adaptive lifecycle maintenance into interactive shell turns and model-backed runtime turns
- [x] 5.2 Upgrade session resume to restore structured memory, recent tool facts, failure memory, and workspace state
- [x] 5.3 Expose inspectable context audit output through runtime state, shell status, or session inspection commands

## 6. Verification And Product Validation

- [x] 6.1 Add tests for automatic lifecycle triggering and type-aware compression behavior
- [x] 6.2 Add tests for layered memory resume and role-specific bundle assembly
- [x] 6.3 Add a documented long-session verification flow showing proactive compression and audit visibility in product usage docs
