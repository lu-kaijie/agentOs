from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agentos.context import ContextManager


def test_context_manager_compacts_long_history(tmp_path: Path):
    manager = ContextManager(tmp_path)
    messages = [
        HumanMessage(content="Inspect repository"),
        ToolMessage(content=("very long output " * 50).strip(), tool_call_id="tool-1"),
        AIMessage(content="Done"),
        HumanMessage(content="Summarize"),
    ]

    compacted, path = manager.compact_messages("demo", messages, max_chars=120)

    assert path.exists()
    assert compacted[0].type == "system"
    assert manager.total_chars(compacted) < manager.total_chars(messages)


def test_context_manager_restores_saved_session(tmp_path: Path):
    manager = ContextManager(tmp_path)
    messages = [HumanMessage(content="hello"), AIMessage(content="world")]
    manager.save_session("session-a", messages)

    restored = manager.load_session("session-a")

    assert [message.type for message in restored] == ["human", "ai"]


def test_context_manager_builds_task_aware_bundle(tmp_path: Path):
    manager = ContextManager(tmp_path)
    (tmp_path / "README.md").write_text("Tool registry demo\n", encoding="utf-8")

    bundle = manager.build_context_bundle(
        session_id="bundle-a",
        task="read: README.md",
        state={
            "completed_tasks": ["search: Tool registry"],
            "step_outputs": ["./README.md:1:Tool registry demo"],
            "tool_results": [{"tool_name": "repo_search", "summary": "search ok"}],
            "execution_trace": ["initialize_loop", "prepare_context", "model_decide"],
        },
        workspace_dir=tmp_path,
    )

    assert bundle["task_hints"]["action"] == "read"
    assert bundle["task_hints"]["path"] == "README.md"
    assert "history" in bundle["sources"]
    assert "tool_results" in bundle["sources"]
    assert bundle["workspace_signals"][0]["path"] == "README.md"
    assert "Tool registry demo" in bundle["workspace_signals"][0]["preview"]


def test_context_manager_compresses_long_trace_and_tool_history(tmp_path: Path):
    manager = ContextManager(tmp_path)

    bundle = manager.build_context_bundle(
        session_id="bundle-b",
        task="search: alpha",
        state={
            "completed_tasks": [f"step {index}" for index in range(6)],
            "step_outputs": [f"output {index} " * 10 for index in range(6)],
            "tool_results": [
                {"tool_name": "file_read", "summary": f"summary {index} " * 8}
                for index in range(6)
            ],
            "execution_trace": [f"trace-{index}" for index in range(20)],
        },
        workspace_dir=tmp_path,
        max_chars=180,
    )

    assert "..." in bundle["history_summary"]
    assert "..." in bundle["tool_summary"]
    assert "..." in bundle["trace_summary"]
