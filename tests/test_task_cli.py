import json
from pathlib import Path

from typer.testing import CliRunner

from agentos.cli import app


runner = CliRunner()


def test_task_cli_persists_and_lists_tasks(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENTOS_TASKS_DIR", str(tmp_path))

    create_result = runner.invoke(app, ["task-create", "Setup project"])
    assert create_result.exit_code == 0
    created = json.loads(create_result.stdout)
    assert created["title"] == "Setup project"

    list_result = runner.invoke(app, ["task-list"])
    assert list_result.exit_code == 0
    listing = json.loads(list_result.stdout)
    assert listing["total"] == 1
    assert listing["ready"][0]["title"] == "Setup project"


def test_task_complete_unblocks_dependents(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENTOS_TASKS_DIR", str(tmp_path))

    first = json.loads(runner.invoke(app, ["task-create", "Task 1"]).stdout)
    second = json.loads(
        runner.invoke(app, ["task-create", "Task 2", "--blocked-by", str(first["id"])]).stdout
    )

    complete_result = runner.invoke(app, ["task-complete", str(first["id"])])
    assert complete_result.exit_code == 0

    list_result = runner.invoke(app, ["task-list"])
    listing = json.loads(list_result.stdout)
    ready_titles = [task["title"] for task in listing["ready"]]
    assert "Task 2" in ready_titles
    assert second["id"] == 2
