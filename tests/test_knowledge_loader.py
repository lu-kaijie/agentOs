from pathlib import Path

from agentos.knowledge import KnowledgeLoader


def test_knowledge_loader_lists_and_loads_topics(tmp_path: Path):
    (tmp_path / "langgraph.md").write_text("graph notes", encoding="utf-8")
    (tmp_path / "ignore.json").write_text("{}", encoding="utf-8")

    loader = KnowledgeLoader(tmp_path)

    assert loader.list_topics() == ["langgraph"]
    message = loader.load_topic("langgraph")
    assert "[knowledge:langgraph]" in message.content
    assert message.additional_kwargs["topic"] == "langgraph"


def test_knowledge_loader_lists_matches_and_loads_skills(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    skill_dir = skills_dir / "code-review"
    (skill_dir / "references").mkdir(parents=True, exist_ok=True)
    (skill_dir / "scripts").mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: code-review
description: Review code changes for bugs and regressions.
when_to_use: Use when the task asks for code review or regression analysis.
triggers:
  - code review
  - review
roles:
  executor:
    hint: Read changed files first.
references:
  - references/checklist.md
scripts:
  - scripts/gather.py
allowed_tools:
  - repo_search
  - file_read
---

# Code Review

Focus on correctness and missing tests.
""",
        encoding="utf-8",
    )
    (skill_dir / "references" / "checklist.md").write_text("checklist body", encoding="utf-8")
    (skill_dir / "scripts" / "gather.py").write_text("print('ok')", encoding="utf-8")

    loader = KnowledgeLoader(tmp_path, skills_dir)

    assert loader.list_skills() == ["code-review"]
    assert "code-review" in loader.skill_index()
    catalog = loader.skill_catalog(role="executor")
    assert catalog[0]["when_to_use"] == "Read changed files first."
    matched = loader.match_skills("请帮我做 code review", role="executor")
    assert len(matched) == 1
    assert matched[0].name == "code-review"

    summary = loader.load_skill("code-review")
    assert "[skill:code-review]" in summary.content
    assert "Read changed files first." in summary.content
    assert "Focus on correctness and missing tests." not in summary.content

    full = loader.load_skill("code-review#full")
    assert "Focus on correctness and missing tests." in full.content
    assert "[skill:code-review:reference:references/checklist.md]" not in full.content

    reference = loader.load_skill("code-review#ref:references/checklist.md")
    assert "checklist body" in reference.content
