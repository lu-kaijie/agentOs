from langchain_core.tools import BaseTool

from agentos.app import AgentOsApp
from agentos.tools import ToolInvocation


def test_default_tool_registry_exposes_langchain_tools():
    app = AgentOsApp.bootstrap()

    tools = app.tool_registry.as_langchain_tools()

    assert tools
    assert all(isinstance(tool, BaseTool) for tool in tools)
    assert {tool.name for tool in tools} >= {
        "file_read",
        "file_write",
        "file_patch",
        "repo_search",
        "skill_list",
        "skill_load",
        "test_run",
    }


def test_file_read_missing_file_returns_structured_error(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    app = AgentOsApp.bootstrap()

    result = app.tool_registry.invoke(
        ToolInvocation(tool_name="file_read", arguments={"path": "missing.txt"})
    )

    assert result.status == "error"
    assert result.summary == "file not found 'missing.txt'"
    assert result.payload["error"] == "File not found: missing.txt"


def test_tool_registry_converts_tool_exceptions_to_structured_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    (tmp_path / "sample.txt").write_text("alpha", encoding="utf-8")
    app = AgentOsApp.bootstrap()

    result = app.tool_registry.invoke(
        ToolInvocation(
            tool_name="file_patch",
            arguments={"path": "sample.txt", "target": "missing", "replacement": "beta"},
        )
    )

    assert result.status == "error"
    assert result.tool_name == "file_patch"
    assert result.payload["exception_type"] == "ValueError"
    assert "target text not found" in result.summary


def test_tool_registry_converts_unknown_tool_to_structured_error():
    app = AgentOsApp.bootstrap()

    result = app.tool_registry.invoke(ToolInvocation(tool_name="missing_tool", arguments={}))

    assert result.status == "error"
    assert result.tool_name == "missing_tool"
    assert result.payload["exception_type"] == "KeyError"
    assert "not registered" in result.summary
