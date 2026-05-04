import json

from typer.testing import CliRunner

from agentos.cli import app


runner = CliRunner()


def test_status_command_outputs_bootstrap_payload():
    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["runtime_status"] == "skeleton-ready"
    assert payload["model_provider"] == "openai"


def test_run_command_announces_runtime_shell():
    result = runner.invoke(app, ["run"])

    assert result.exit_code == 0
    assert "agentOs runtime skeleton is ready." in result.stdout
