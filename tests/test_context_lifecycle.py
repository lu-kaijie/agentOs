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
