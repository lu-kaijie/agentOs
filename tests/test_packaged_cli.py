from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from agentos.cli import app


runner = CliRunner()


def test_pyproject_declares_console_script_and_runtime_dependencies():
    payload = Path("pyproject.toml").read_text(encoding="utf-8")

    assert 'agentos = "agentos.cli:main"' in payload
    assert '"langchain==0.3.26"' in payload
    assert '"langgraph==0.2.62"' in payload
    assert '"click==8.1.8"' in payload
    assert '"textual==0.89.1"' in payload


def test_root_command_defaults_to_shell(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTOS_SESSIONS_DIR", str(tmp_path / "sessions"))

    result = runner.invoke(app, [], input="/exit\n")

    assert result.exit_code == 0
    assert "agentOs interactive shell started for session `shell`." in result.stdout


def test_shell_prints_user_facing_model_guidance(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTOS_SESSIONS_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("AGENTOS_MODEL_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_BASE_URL", "")

    result = runner.invoke(app, ["shell", "--plain"], input="/exit\n")

    assert result.exit_code == 0
    assert "未检测到可用的模型配置" in result.stdout
    assert "复制 `.env.example` 为 `.env`" in result.stdout


def test_run_model_without_configuration_prints_guidance(monkeypatch):
    monkeypatch.setenv("AGENTOS_MODEL_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_BASE_URL", "")

    result = runner.invoke(app, ["run", "describe current status", "--model"])

    assert result.exit_code == 1
    assert "未检测到可用的模型配置" in result.stdout


def test_run_model_handles_provider_errors_without_traceback(monkeypatch):
    from agentos.runtime.model_backed import ModelBackedAgentRuntime

    monkeypatch.setattr(ModelBackedAgentRuntime, "is_configured", lambda self: True)
    monkeypatch.setattr(
        ModelBackedAgentRuntime,
        "run_turn",
        lambda self, **kwargs: (_ for _ in ()).throw(ValueError("tool calling unavailable")),
    )

    result = runner.invoke(app, ["run", "describe current status", "--model"])

    assert result.exit_code == 1
    assert "model-backed runtime failed: tool calling unavailable" in result.stdout


def test_shell_model_runtime_error_does_not_print_missing_config_guidance(monkeypatch):
    from agentos.app import AgentOsApp
    from agentos.runtime.model_backed import ModelBackedAgentRuntime

    monkeypatch.setattr(ModelBackedAgentRuntime, "is_configured", lambda self: True)
    monkeypatch.setattr(
        AgentOsApp,
        "run_model_session_task",
        lambda self, *args, **kwargs: (_ for _ in ()).throw(ValueError("provider rejected oversized tool output")),
    )

    result = runner.invoke(app, ["shell", "--plain"], input="这是一个什么项目代码\n/exit\n")

    assert result.exit_code == 0
    assert "model-backed runtime failed: provider rejected oversized tool output" in result.stdout
    assert "未检测到可用的模型配置" not in result.stdout
