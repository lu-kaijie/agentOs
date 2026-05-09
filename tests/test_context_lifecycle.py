from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agentos.context import ContextManager


def test_prepare_role_context_persists_layered_memory_and_audit(tmp_path: Path):
    manager = ContextManager(tmp_path)
    messages = [
        HumanMessage(content="请用中文，总结当前计划，不要删文件。"),
        ToolMessage(content=("pytest output " * 60).strip(), tool_call_id="tool-1"),
        AIMessage(content="我会先检查测试失败原因。"),
    ]
    manager.save_session("memory-demo", messages)

    bundle, record, memory, audit = manager.prepare_role_context(
        session_id="memory-demo",
        task="test: pytest -q",
        role="reviewer",
        state={
            "completed_tasks": ["read: README.md"],
            "step_outputs": ["reviewed read output"],
            "tool_results": [
                {
                    "tool_name": "test_run",
                    "summary": "pytest failed on tests/test_cli.py",
                    "payload": {"command": ["pytest", "-q"], "exit_code": 1, "stdout": "tests/test_cli.py::test_a FAILED"},
                }
            ],
            "execution_trace": ["prepare_context", "tool_execute:test_run"],
        },
        workspace_dir=tmp_path,
        trigger_reason="large_tool_output",
    )

    assert record.sources
    assert memory.working_memory.accepted_constraints
    assert memory.user_preferences.preferred_language == "zh-CN"
    assert memory.tool_facts[0].tool_name == "test_run"
    assert memory.failure_memory[0].tool_name == "test_run"
    assert audit.trigger_reason == "large_tool_output"
    assert audit.compression_mode == "hybrid"
    assert "layered_memory" in bundle["sources"]
    assert bundle["layered_memory"]["working_memory"]["accepted_constraints"]
    assert bundle["context_audit_records"]


def test_prepare_role_context_restores_existing_memory(tmp_path: Path):
    manager = ContextManager(tmp_path)
    first_bundle, _, first_memory, _ = manager.prepare_role_context(
        session_id="restore-demo",
        task="read: README.md",
        role="executor",
        state={
            "completed_tasks": ["read: README.md"],
            "step_outputs": ["read ok"],
            "tool_results": [{"tool_name": "file_read", "summary": "read ok", "payload": {"path": "README.md"}}],
            "execution_trace": ["prepare_context"],
        },
        workspace_dir=tmp_path,
    )

    second_bundle, _, second_memory, _ = manager.prepare_role_context(
        session_id="restore-demo",
        task="say hello",
        role="planner",
        state={
            "completed_tasks": ["read: README.md", "say hello"],
            "step_outputs": ["read ok", "hello"],
            "tool_results": [{"tool_name": "file_read", "summary": "read ok", "payload": {"path": "README.md"}}],
            "execution_trace": ["prepare_context", "planner_role"],
            "memory_state": first_memory.to_dict(),
        },
        workspace_dir=tmp_path,
        trigger_reason="session_resume",
    )

    assert first_bundle["layered_memory"]["workspace_state"]["recent_reads"] == ["README.md"]
    assert second_memory.workspace_state.recent_reads == ["README.md"]
    assert second_bundle["layered_memory"]["working_memory"]["current_goal"] == "say hello"


def test_prepare_role_context_exposes_compact_skill_catalog_for_model_path(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    skill_dir = skills_dir / "code-review"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: code-review
description: Review code changes for bugs and regressions.
triggers:
  - code review
roles:
  reviewer:
    hint: Focus on regressions and missing tests.
---

# Code Review

Prioritize correctness over style.
""",
        encoding="utf-8",
    )

    from agentos.knowledge import KnowledgeLoader

    loader = KnowledgeLoader(tmp_path / "knowledge", skills_dir)
    manager = ContextManager(tmp_path / "context", knowledge_loader=loader)

    bundle, _, _, _ = manager.prepare_role_context(
        session_id="skill-demo",
        task="请做 code review",
        role="reviewer",
        skill_mode="catalog",
        state={
            "completed_tasks": [],
            "step_outputs": [],
            "tool_results": [],
            "execution_trace": [],
        },
        workspace_dir=tmp_path,
    )

    assert bundle["skills_catalog"]
    assert bundle["skills_catalog"][0]["name"] == "code-review"
    assert bundle["skills_catalog"][0]["when_to_use"] == "Focus on regressions and missing tests."
    assert bundle["matched_skills"] == []
    assert bundle["active_skills"] == []
    assert bundle["skills_available"] is True
    assert bundle["skills_count"] == 1
    assert "catalog: code-review" in bundle["skills_hint"]


def test_prepare_role_context_keeps_compact_skill_catalog_without_match(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    skill_dir = skills_dir / "repo-explore"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: repo-explore
description: Explore repository structure and entry points.
triggers:
  - repo explore
roles:
  executor:
    hint: Start from entry points and top-level directories.
---

# Repo Explore

Explore the repository before editing.
""",
        encoding="utf-8",
    )

    from agentos.knowledge import KnowledgeLoader

    loader = KnowledgeLoader(tmp_path / "knowledge", skills_dir)
    manager = ContextManager(tmp_path / "context", knowledge_loader=loader)

    bundle, _, _, _ = manager.prepare_role_context(
        session_id="skill-index-demo",
        task="请读取 README 并总结项目",
        role="executor",
        skill_mode="catalog",
        state={
            "completed_tasks": [],
            "step_outputs": [],
            "tool_results": [],
            "execution_trace": [],
        },
        workspace_dir=tmp_path,
    )

    assert bundle["skills_catalog"]
    assert bundle["skills_catalog"][0]["name"] == "repo-explore"
    assert bundle["matched_skills"] == []
    assert "repo-explore" in bundle["skills_hint"]


def test_prepare_role_context_keeps_matched_skills_for_fallback_path(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    skill_dir = skills_dir / "code-review"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: code-review
description: Review code changes for bugs and regressions.
triggers:
  - code review
---
""",
        encoding="utf-8",
    )

    from agentos.knowledge import KnowledgeLoader

    loader = KnowledgeLoader(tmp_path / "knowledge", skills_dir)
    manager = ContextManager(tmp_path / "context", knowledge_loader=loader)

    bundle, _, _, _ = manager.prepare_role_context(
        session_id="fallback-skill-demo",
        task="请做 code review",
        role="executor",
        state={
            "completed_tasks": [],
            "step_outputs": [],
            "tool_results": [],
            "execution_trace": [],
        },
        workspace_dir=tmp_path,
    )

    assert bundle["matched_skills"]
    assert bundle["matched_skills"][0]["name"] == "code-review"
    assert bundle["active_skills"] == bundle["matched_skills"]
