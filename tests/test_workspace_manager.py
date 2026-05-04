from pathlib import Path

from agentos.execution_control import WorkspaceManager


def test_workspace_manager_creates_and_resolves(tmp_path: Path):
    manager = WorkspaceManager(tmp_path)

    workspace = manager.create("task-a")

    assert workspace["name"] == "task-a"
    assert Path(workspace["path"]).exists()
    assert manager.resolve("task-a", "/tmp/fallback") == workspace["path"]


def test_workspace_list_reports_created_workspaces(tmp_path: Path):
    manager = WorkspaceManager(tmp_path)
    manager.create("task-a")

    listing = manager.list()

    assert "task-a" in listing["workspaces"]
