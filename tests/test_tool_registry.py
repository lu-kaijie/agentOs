from pathlib import Path

import pytest

from agentos.harness.execution import LocalCommandExecutor
from agentos.knowledge import KnowledgeLoader
from agentos.tools import ToolInvocation, build_default_tool_registry


def test_tool_registry_lists_builtin_tools(tmp_path: Path):
    registry = build_default_tool_registry(
        workspace_dir=tmp_path,
        executor=LocalCommandExecutor(),
        knowledge_loader=KnowledgeLoader(tmp_path / "knowledge"),
    )

    names = [item["name"] for item in registry.list_tools()]
    assert names == [
        "file_patch",
        "file_read",
        "file_write",
        "knowledge_load",
        "repo_search",
        "shell_command",
        "test_run",
    ]


def test_tool_registry_runs_coding_tools(tmp_path: Path):
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "notes.txt").write_text("alpha beta\n", encoding="utf-8")
    registry = build_default_tool_registry(
        workspace_dir=tmp_path,
        executor=LocalCommandExecutor(),
        knowledge_loader=KnowledgeLoader(knowledge_dir),
    )

    search_result = registry.invoke(ToolInvocation(tool_name="repo_search", arguments={"pattern": "alpha"}))
    read_result = registry.invoke(ToolInvocation(tool_name="file_read", arguments={"path": "notes.txt"}))
    write_result = registry.invoke(
        ToolInvocation(tool_name="file_write", arguments={"path": "written.txt", "content": "written"})
    )
    patch_result = registry.invoke(
        ToolInvocation(
            tool_name="file_patch",
            arguments={"path": "notes.txt", "target": "beta", "replacement": "gamma"},
        )
    )
    test_result = registry.invoke(ToolInvocation(tool_name="test_run", arguments={"command": "python -c print(123)"}))

    assert "alpha" in search_result.payload["stdout"]
    assert read_result.payload["content"] == "alpha beta\n"
    assert write_result.payload["bytes_written"] == len("written".encode("utf-8"))
    assert patch_result.payload["replacement_count"] == 1
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "alpha gamma\n"
    assert test_result.payload["stdout"].strip() == "123"


def test_repo_search_falls_back_when_rg_is_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "notes.txt").write_text("alpha beta\n", encoding="utf-8")
    registry = build_default_tool_registry(
        workspace_dir=tmp_path,
        executor=LocalCommandExecutor(),
        knowledge_loader=KnowledgeLoader(knowledge_dir),
    )

    original_run = LocalCommandExecutor.run

    def failing_run(self, request):
        if request.command and request.command[0] == "rg":
            raise FileNotFoundError("rg not found")
        return original_run(self, request)

    monkeypatch.setattr(LocalCommandExecutor, "run", failing_run)

    result = registry.invoke(ToolInvocation(tool_name="repo_search", arguments={"pattern": "alpha"}))

    assert result.payload["engine"] == "python"
    assert "./notes.txt:1:alpha beta" in result.payload["stdout"]
