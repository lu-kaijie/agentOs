import json
from pathlib import Path

from typer.testing import CliRunner

from agentos.cli import app


runner = CliRunner()


def test_coordination_cli_creates_and_lists_units(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENTOS_COORDINATION_DIR", str(tmp_path))

    create_one = runner.invoke(app, ["unit-create", "Inspect backend", "--role", "researcher"])
    assert create_one.exit_code == 0
    one = json.loads(create_one.stdout)

    create_two = runner.invoke(
        app,
        ["unit-create", "Write patch", "--role", "builder", "--depends-on", str(one["id"])],
    )
    assert create_two.exit_code == 0

    listing = runner.invoke(app, ["unit-list"])
    assert listing.exit_code == 0
    payload = json.loads(listing.stdout)
    assert payload["ready"][0]["title"] == "Inspect backend"


def test_coordination_cli_completes_and_unblocks(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENTOS_COORDINATION_DIR", str(tmp_path))

    one = json.loads(runner.invoke(app, ["unit-create", "Inspect backend", "--role", "researcher"]).stdout)
    two = json.loads(
        runner.invoke(
            app,
            ["unit-create", "Write patch", "--role", "builder", "--depends-on", str(one["id"])],
        ).stdout
    )

    complete = runner.invoke(app, ["unit-complete", str(one["id"]), "--result", "inspection done"])
    assert complete.exit_code == 0

    listing = json.loads(runner.invoke(app, ["unit-list"]).stdout)
    ready_titles = [unit["title"] for unit in listing["ready"]]
    assert "Write patch" in ready_titles
    assert two["id"] == 2


def test_coordination_cli_executes_unit(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENTOS_COORDINATION_DIR", str(tmp_path / "coordination"))
    monkeypatch.setenv("AGENTOS_TASKS_DIR", str(tmp_path / "tasks"))
    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("AGENTOS_WORKSPACES_DIR", str(tmp_path / "workspaces"))

    runner.invoke(app, ["workspace-create", "unit-a"])
    task = json.loads(runner.invoke(app, ["task-create", "Delegated task"]).stdout)
    unit = json.loads(
        runner.invoke(
            app,
            [
                "unit-create",
                "Inspect backend",
                "--role",
                "researcher",
                "--task-id",
                str(task["id"]),
                "--workspace",
                "unit-a",
                "--command",
                "python",
                "--command",
                "-c",
                "--command",
                "print('delegated-cli', end='')",
            ],
        ).stdout
    )

    executed = runner.invoke(app, ["unit-exec", str(unit["id"])])

    assert executed.exit_code == 0
    payload = json.loads(executed.stdout)
    assert payload["status"] == "completed"
    assert payload["result"] == "delegated-cli"
    assert payload["execution_context"].endswith("unit-a")
