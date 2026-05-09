---
name: code-review
description: Review code changes for bugs, regressions, and missing tests.
when_to_use: Use when the task is about code review, regression analysis, or review comments.
triggers:
  - code review
  - review
  - analyze diff
  - regression
roles:
  planner:
    hint: Focus on changed scope, risky areas, and likely verification gaps.
  executor:
    hint: Read changed files first, then inspect behavior, tests, and edge cases.
  reviewer:
    hint: Prioritize correctness, regressions, and missing verification over style.
references:
  - references/checklist.md
  - references/examples.md
scripts:
  - scripts/gather_diff_context.py
allowed_tools:
  - repo_search
  - file_read
  - shell_command
  - test_run
---

# Code Review Skill

Use this skill when the task is about reviewing code changes, identifying risks, or generating review comments.

## What This Skill Emphasizes

- correctness over style
- regressions over cosmetic suggestions
- verification gaps over vague advice

## Progressive Disclosure

- default: use this file only
- when checklist is needed: load `references/checklist.md`
- when examples are needed: load `references/examples.md`
- when repository context is missing: inspect `scripts/gather_diff_context.py`
