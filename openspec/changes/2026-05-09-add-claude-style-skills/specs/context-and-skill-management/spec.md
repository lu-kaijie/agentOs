## ADDED Requirements

### Requirement: The project must support user-defined local skills

The project SHALL support user-defined local skills under `skills/<name>/SKILL.md`, with optional `references/` and `scripts/` subdirectories.

#### Scenario: Contributor adds a custom skill

- **WHEN** a contributor creates `skills/repo-explore/SKILL.md`
- **THEN** the runtime can discover that skill without code changes
- **AND** the CLI can list or show it

### Requirement: The project must expose a compact skill catalog separately from matched hints

The project SHALL expose a compact skill catalog for the current repository and SHALL treat trigger-based matches as a separate hint channel.

#### Scenario: Context bundle is prepared for a model-backed turn

- **WHEN** the runtime prepares a role-specific context bundle
- **THEN** the bundle includes `skills_catalog`
- **AND** any trigger-based matches are stored separately as `matched_skills`
- **AND** trigger-based matches do not replace the compact skill catalog

### Requirement: The model-backed path must support proactive skill loading

The project SHALL allow the model-backed runtime to decide whether to load a skill, rather than requiring deterministic trigger routing first.

#### Scenario: Model sees a relevant compact skill catalog entry

- **WHEN** the model-backed executor receives a task whose context bundle shows a relevant compact skill catalog entry
- **THEN** it can call `skill_list` or `skill_load`
- **AND** it can first use summary information before progressively loading fuller skill content and deeper references

### Requirement: The fallback path must retain deterministic skill preloading

The project SHALL retain a deterministic fallback path that can pre-match a skill and preload it without model reasoning.

#### Scenario: Fallback runtime handles a matching task

- **WHEN** the fallback runtime receives a task whose text matches a skill trigger
- **THEN** it may enqueue a `skill:` preload step before subsequent task execution
- **AND** later steps can consume the loaded skill output
