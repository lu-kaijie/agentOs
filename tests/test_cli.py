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
    assert payload["background_jobs_dir"].endswith(".agentos/background")
    assert payload["workspaces_dir"].endswith(".agentos/workspaces")


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
