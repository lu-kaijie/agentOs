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
