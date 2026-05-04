import json

from typer.testing import CliRunner

from agentos.cli import app


runner = CliRunner()


def test_status_command_outputs_bootstrap_payload():
    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["runtime_status"] == "langgraph-advanced-ready"
    assert payload["model_provider"] == "openai"
    assert payload["tasks_dir"].endswith(".agentos/tasks")
    assert payload["knowledge_dir"].endswith("/knowledge")
    assert payload["context_dir"].endswith(".agentos/context")
    assert payload["sessions_dir"].endswith(".agentos/sessions")
    assert payload["background_jobs_dir"].endswith(".agentos/background")
    assert payload["workspaces_dir"].endswith(".agentos/workspaces")
    assert payload["coordination_dir"].endswith(".agentos/coordination")


def test_run_command_announces_runtime_shell():
    result = runner.invoke(app, ["run", "run: pwd"])

    assert result.exit_code == 0
    assert "agentOs LangGraph runtime executed." in result.stdout
    assert "user_task" in result.stdout
    assert "execution_trace" in result.stdout


def test_exec_command_uses_harness_boundary():
    result = runner.invoke(app, ["exec", "pwd"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["exit_code"] == 0
    assert payload["timed_out"] is False
    assert payload["command"] == ["pwd"]


def test_run_command_persists_session_and_lists_it(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTOS_SESSIONS_DIR", str(tmp_path / "sessions"))

    result = runner.invoke(app, ["run", "run: pwd", "--session-id", "demo-session"])
    assert result.exit_code == 0

    sessions_result = runner.invoke(app, ["sessions"])
    assert sessions_result.exit_code == 0
    payload = json.loads(sessions_result.stdout)
    assert payload["total"] == 1
    assert payload["sessions"][0]["id"] == "demo-session"


def test_session_show_returns_latest_turn(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTOS_SESSIONS_DIR", str(tmp_path / "sessions"))

    runner.invoke(app, ["run", "run: pwd", "--session-id", "demo-session"])
    result = runner.invoke(app, ["session-show", "demo-session"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["session"]["id"] == "demo-session"
    assert payload["latest_turn"]["user_task"] == "run: pwd"


def test_resume_reuses_persisted_session_state(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTOS_SESSIONS_DIR", str(tmp_path / "sessions"))

    first = runner.invoke(
        app,
        ["run", "steps: say hello | say again", "--session-id", "resume-session", "--max-iterations", "1"],
    )
    assert first.exit_code == 0

    resumed = runner.invoke(app, ["resume", "resume-session"])

    assert resumed.exit_code == 0
    assert "agentOs resumed session." in resumed.stdout
    assert "say again" in resumed.stdout
