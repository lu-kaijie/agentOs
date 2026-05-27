from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agentos.context import ContextManager
from agentos.context.lifecycle import StructuredMemoryExtractor
from agentos.context.models import LayeredMemory, RememberedFact, TaskState, ToolFact, UserProfile


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


def test_prepare_role_context_preserves_remembered_facts_after_compression(tmp_path: Path):
    manager = ContextManager(tmp_path)
    manager.save_session(
        "fact-demo",
        [
            HumanMessage(content="请记住第一个测试代号：蓝色风筝。"),
            AIMessage(content="记住了：蓝色风筝。"),
        ],
    )
    _, _, first_memory, _ = manager.prepare_role_context(
        session_id="fact-demo",
        task="请记住第一个测试代号：蓝色风筝。",
        role="executor",
        state={"completed_tasks": [], "step_outputs": [], "tool_results": [], "execution_trace": []},
        workspace_dir=tmp_path,
    )
    manager.save_session(
        "fact-demo",
        [
            HumanMessage(content=f"普通对话 {index}")
            for index in range(12)
        ],
    )

    bundle, _, second_memory, _ = manager.prepare_role_context(
        session_id="fact-demo",
        task="刚才第一个测试代号是什么？",
        role="executor",
        state={
            "completed_tasks": [],
            "step_outputs": [],
            "tool_results": [],
            "execution_trace": [],
            "memory_state": first_memory.to_dict(),
        },
        workspace_dir=tmp_path,
        trigger_reason="role_handoff",
    )

    remembered = {fact.key: fact.value for fact in second_memory.remembered_facts}
    assert remembered["test_code_1"] == "蓝色风筝"
    assert "蓝色风筝" in bundle["memory_summary"]
    assert bundle["remembered_facts"][0]["value"] == "蓝色风筝"
    assert bundle["layered_memory"]["remembered_facts"][0]["value"] == "蓝色风筝"


def test_deterministic_memory_extraction_extracts_profile_and_facts(tmp_path: Path):
    manager = ContextManager(tmp_path)
    extractor = StructuredMemoryExtractor(manager)

    delta = extractor.extract_deterministic(
        task="记忆测试",
        state={"completed_tasks": [], "pending_tasks": []},
        recent_messages=[
            HumanMessage(content="从现在开始，请记住：我偏好中文回答，回答要短一点。"),
            HumanMessage(content="请记住第一个测试代号：蓝色风筝。"),
            HumanMessage(content="请记住第二个测试代号：银色钥匙。"),
        ],
        tool_facts=[],
    )

    assert delta.user_profile_delta.preferred_language == "zh-CN"
    assert "brief" in delta.user_profile_delta.response_style
    facts = {fact.key: fact.value for fact in delta.remembered_facts_delta}
    assert facts == {"test_code_1": "蓝色风筝", "test_code_2": "银色钥匙"}


def test_memory_merge_updates_fact_by_key_and_preserves_other_layers(tmp_path: Path):
    manager = ContextManager(tmp_path)
    lifecycle = manager.lifecycle_manager

    existing_profile = UserProfile(preferred_language="zh-CN", stable_preferences=["短回答"])
    merged_profile = lifecycle._merge_user_profile(
        existing_profile,
        UserProfile(response_style=["brief"]),
    )
    assert merged_profile.preferred_language == "zh-CN"
    assert merged_profile.stable_preferences == ["短回答"]
    assert merged_profile.response_style == ["brief"]

    old_fact = RememberedFact(
        key="test_code_1",
        value="蓝色风筝",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        source_text="旧事实",
    )
    new_fact = RememberedFact(
        key="test_code_1",
        value="红色风筝",
        updated_at="2026-01-02T00:00:00+00:00",
        source_text="纠正后的事实",
    )
    untouched_fact = RememberedFact(key="test_code_2", value="银色钥匙")

    merged_facts = lifecycle._merge_remembered_facts([old_fact, untouched_fact], [new_fact])
    by_key = {fact.key: fact for fact in merged_facts}
    assert by_key["test_code_1"].value == "红色风筝"
    assert by_key["test_code_1"].created_at == old_fact.created_at
    assert by_key["test_code_2"].value == "银色钥匙"

    merged_task = lifecycle._merge_task_state(
        TaskState(current_goal="旧目标", completed_actions=["a"]),
        TaskState(open_questions=["还要做什么？"]),
        working_memory=LayeredMemory().working_memory,
    )
    assert merged_task.current_goal == "旧目标"
    assert merged_task.completed_actions == ["a"]
    assert merged_task.open_questions == ["还要做什么？"]


def test_layered_memory_loads_old_payload_with_structured_defaults():
    memory = LayeredMemory.from_dict(
        {
            "working_memory": {"current_goal": "old"},
            "tool_facts": [{"tool_name": "file_read", "summary": "read README"}],
        }
    )

    assert memory.user_profile == UserProfile()
    assert memory.remembered_facts == []
    assert memory.task_state == TaskState()
    assert memory.working_memory.current_goal == "old"
    assert memory.tool_facts[0].tool_name == "file_read"


def test_model_memory_extraction_parses_tool_call(monkeypatch, tmp_path: Path):
    manager = ContextManager(tmp_path)
    monkeypatch.setenv("AGENTOS_MEMORY_MODEL_EXTRACTION", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class BoundModel:
        def invoke(self, messages):
            return type(
                "Message",
                (),
                {
                    "tool_calls": [
                        {
                            "name": "MemoryDeltaPayload",
                            "args": {
                                "user_profile_delta": {"preferred_language": "zh-CN", "response_style": ["brief"]},
                                "remembered_facts_delta": [
                                    {
                                        "key": "test_code_3",
                                        "value": "绿色罗盘",
                                        "source_text": "请记住第三个测试代号：绿色罗盘。",
                                    }
                                ],
                                "task_state_delta": {"current_goal": "测试记忆"},
                            },
                        }
                    ]
                },
            )()

    class FakeModel:
        def bind_tools(self, tools, *, tool_choice=None, **kwargs):
            return BoundModel()

    monkeypatch.setattr("agentos.context.lifecycle.ChatOpenAI", lambda **kwargs: FakeModel())
    extractor = StructuredMemoryExtractor(manager)

    delta = extractor.extract(
        session_id="model-memory",
        task="测试记忆",
        state={},
        recent_messages=[HumanMessage(content="请记住第三个测试代号：绿色罗盘。")],
        tool_facts=[ToolFact(tool_name="file_read", summary="read ok", related_paths=["README.md"])],
    )

    assert delta.user_profile_delta.preferred_language == "zh-CN"
    assert delta.remembered_facts_delta[0].key == "test_code_3"
    assert delta.remembered_facts_delta[0].value == "绿色罗盘"


def test_model_memory_extraction_falls_back_on_failure(monkeypatch, tmp_path: Path):
    manager = ContextManager(tmp_path)
    monkeypatch.setenv("AGENTOS_MEMORY_MODEL_EXTRACTION", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FailingModel:
        def bind_tools(self, tools, *, tool_choice=None, **kwargs):
            raise RuntimeError("provider failed")

    monkeypatch.setattr("agentos.context.lifecycle.ChatOpenAI", lambda **kwargs: FailingModel())
    extractor = StructuredMemoryExtractor(manager)

    delta = extractor.extract(
        session_id="fallback-memory",
        task="测试记忆",
        state={},
        recent_messages=[HumanMessage(content="请记住第一个测试代号：蓝色风筝。")],
        tool_facts=[],
    )

    assert delta.remembered_facts_delta[0].value == "蓝色风筝"
    assert delta.diagnostics
    assert delta.diagnostics[0].startswith("model_memory_extraction_failed:")


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
