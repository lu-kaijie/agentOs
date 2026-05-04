import json
import time
from pathlib import Path

from typer.testing import CliRunner

from agentos.cli import app


runner = CliRunner()


def test_workspace_cli_creates_workspace(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENTOS_WORKSPACES_DIR", str(tmp_path))

    result = runner.invoke(app, ["workspace-create", "task-a"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "task-a"
    assert Path(payload["path"]).exists()


def test_background_cli_runs_job(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENTOS_BACKGROUND_DIR", str(tmp_path / "background"))
    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))

    start = runner.invoke(app, ["bg-run", "bash -lc 'printf done'"])
    assert start.exit_code == 0
    started = json.loads(start.stdout)

    deadline = time.time() + 5
    status_payload = started
    while time.time() < deadline:
        result = runner.invoke(app, ["bg-status", started["id"]])
        assert result.exit_code == 0
        status_payload = json.loads(result.stdout)
        if status_payload["status"] == "completed":
            break
        time.sleep(0.1)

    assert status_payload["status"] == "completed"
