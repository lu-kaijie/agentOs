# Release Checklist

This checklist is used before creating a milestone tag.

## Required Checks

- `make test` passes in `.venv-agentos`
- The milestone's documented demo commands still work
- `README.md` reflects the repository's actual current stage
- `CONTRIBUTING.md` still matches the working process used in the repo
- `openspec/changes/.../tasks.md` checkboxes match implementation reality
- Generated local state such as `.agentos/` is not included in the commit

## Milestone Completion Standard

A milestone is ready to tag only when all of the following are true:

- The milestone's primary learning goal is implemented, not just sketched
- The repository can stop at this point without hidden follow-up work
- At least one concrete CLI or test path demonstrates the new capability
- New persistent files and directories are intentionally placed and documented
- The change does not break previously documented flows unless explicitly called out

## Tagging Flow

1. Run the milestone verification commands.
2. Review `git status` and confirm only intentional files are included.
3. Commit the milestone with a focused message.
4. Create the milestone tag `v0.<milestone>.<revision>`.
5. Push `main`.
6. Push the tag.

## Current Stable Tags

- `v0.1.0` Environment foundation
- `v0.2.0` Project skeleton
- `v0.3.0` Harness foundation
- `v0.4.0` LangGraph runtime v1
- `v0.5.0` Task control plane
- `v0.6.0` Context and knowledge management
- `v0.7.0` Advanced LangChain/LangGraph routing
- `v0.8.0` Async and isolated execution
- `v0.9.0` Multi-agent coordination control plane
- `v0.10.0` First change wrap-up
- `v0.11.0` Resumable runtime loop
- `v0.12.0` Background result re-entry
- `v0.13.0` Delegated execution runtime
- `v0.14.0` Permission and approval policy
- `v0.15.0` Session persistence
- `v0.16.0` Session inspect / resume
- `v0.17.0` Bounded continuation and replay
- `v0.18.0` Structured tool registry
- `v0.19.0` Task-aware context bundles
- `v0.20.0` Bounded role workflow
