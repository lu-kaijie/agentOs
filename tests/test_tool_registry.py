from langchain_core.tools import BaseTool

from agentos.app import AgentOsApp


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
        "test_run",
    }
