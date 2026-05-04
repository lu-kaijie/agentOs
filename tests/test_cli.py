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
    assert payload["model_configured"] in {"true", "false"}


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
    assert payload["payload"]["exit_code"] == 0
    assert payload["payload"]["timed_out"] is False
    assert payload["payload"]["command"] == ["pwd"]


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


def test_tool_list_and_tool_run(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    (tmp_path / "sample.txt").write_text("中文 tool registry", encoding="utf-8")

    listing = runner.invoke(app, ["tool-list"])
    assert listing.exit_code == 0
    listing_payload = json.loads(listing.stdout)
    names = [item["name"] for item in listing_payload["tools"]]
    assert "file_read" in names
    assert "file_patch" in names
    assert "repo_search" in names

    result = runner.invoke(app, ["tool-run", "file_read", "--arg", "path=sample.txt"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["payload"]["content"] == "中文 tool registry"
    assert "\\u4e2d\\u6587" not in result.stdout


def test_resume_polls_and_consumes_background_result(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTOS_SESSIONS_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("AGENTOS_BACKGROUND_DIR", str(tmp_path / "background"))
    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("AGENTOS_KNOWLEDGE_DIR", str(tmp_path / "knowledge"))
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    (knowledge_dir / "langgraph-runtime.md").write_text("# Runtime from watch", encoding="utf-8")

    first = runner.invoke(app, ["run", "say hello", "--session-id", "poll-session"])
    assert first.exit_code == 0

    started = runner.invoke(
        app,
        [
            "bg-run",
            "python -c \"import time; time.sleep(0.2); print('knowledge: langgraph-runtime', end='')\"",
            "--session-id",
            "poll-session",
        ],
    )
    assert started.exit_code == 0

    resumed = runner.invoke(
        app,
        [
            "resume",
            "poll-session",
            "--poll-iterations",
            "20",
            "--poll-interval",
            "0.1",
        ],
    )

    assert resumed.exit_code == 0
    assert "agentOs resumed session." in resumed.stdout
    assert "background_reentry" in resumed.stdout
    assert "tool_execute:knowledge_load" in resumed.stdout


def test_watch_command_reuses_resume_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTOS_SESSIONS_DIR", str(tmp_path / "sessions"))

    first = runner.invoke(
        app,
        ["run", "steps: say hello | say again", "--session-id", "watch-session", "--max-iterations", "1"],
    )
    assert first.exit_code == 0

    watched = runner.invoke(
        app,
        [
            "watch",
            "watch-session",
            "--poll-count",
            "2",
            "--poll-interval",
            "0.1",
        ],
    )

    assert watched.exit_code == 0
    assert "agentOs watching session `watch-session`." in watched.stdout
    assert "watch cycle 1/2" in watched.stdout
    assert "loop_status: completed" in watched.stdout


def test_shell_reuses_one_session_across_multiple_turns(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTOS_SESSIONS_DIR", str(tmp_path / "sessions"))

    result = runner.invoke(
        app,
        ["shell", "--session-id", "shell-demo", "--max-iterations", "3"],
        input="say hello\n/status\nsay again\n/exit\n",
    )

    assert result.exit_code == 0
    assert "agentOs interactive shell started for session `shell-demo`." in result.stdout
    assert "assistant>" in result.stdout
    assert '"id": "shell-demo"' in result.stdout

    session_result = runner.invoke(app, ["session-show", "shell-demo"])
    assert session_result.exit_code == 0
    payload = json.loads(session_result.stdout)
    assert payload["session"]["turn_count"] == 2


def test_runtime_multi_tool_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("AGENTOS_KNOWLEDGE_DIR", str(tmp_path / "knowledge"))
    (tmp_path / "README.md").write_text("Tool registry demo\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "run",
            "steps: search: Tool registry | read: README.md | write: notes.txt => alpha beta | patch: notes.txt => beta >> gamma | test: python -c print(456)",
            "--session-id",
            "tool-demo",
            "--max-iterations",
            "5",
        ],
    )

    assert result.exit_code == 0
    assert '"tool_name": "repo_search"' in result.stdout
    assert '"tool_name": "file_read"' in result.stdout
    assert '"tool_name": "file_write"' in result.stdout
    assert '"tool_name": "file_patch"' in result.stdout
    assert '"tool_name": "test_run"' in result.stdout
    assert '"stdout": "456\\n"' in result.stdout


def test_runtime_role_based_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    (tmp_path / "README.md").write_text("role cli demo\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "run",
            "code: steps: read: README.md | write: notes.txt => role cli | test: python -c print(321)",
            "--session-id",
            "role-demo",
            "--max-iterations",
            "5",
        ],
    )

    assert result.exit_code == 0
    assert '"role": "planner"' in result.stdout
    assert '"role": "executor"' in result.stdout
    assert '"role": "reviewer"' in result.stdout
    assert '"reviewed_tool_count"' in result.stdout


def test_run_command_supports_model_backed_path(monkeypatch):
    from agentos.runtime.model_backed import ModelBackedAgentRuntime

    monkeypatch.setattr(ModelBackedAgentRuntime, "is_configured", lambda self: True)
    monkeypatch.setattr(
        ModelBackedAgentRuntime,
        "run_turn",
        lambda self, **kwargs: {
            "planner_summary": "plan",
            "planner_steps": ["read code", "run tests"],
            "executor_output": "model executor output",
            "reviewer_summary": "model reviewer summary",
            "reviewer_follow_up_needed": False,
            "tool_results": [{"tool_name": "file_read", "summary": "read", "payload": {}}],
            "message_count": 2,
        },
    )

    result = runner.invoke(app, ["run", "inspect README and summarize", "--model", "--session-id", "model-run"])

    assert result.exit_code == 0
    assert '"action": "model_backed_turn"' in result.stdout
    assert "model executor output" in result.stdout


def test_shell_uses_model_backed_mode_for_natural_language(monkeypatch):
    from agentos.runtime.model_backed import ModelBackedAgentRuntime

    monkeypatch.setattr(ModelBackedAgentRuntime, "is_configured", lambda self: True)
    monkeypatch.setattr(
        ModelBackedAgentRuntime,
        "run_turn",
        lambda self, **kwargs: {
            "planner_summary": "plan",
            "planner_steps": ["inspect", "edit"],
            "executor_output": "model shell output",
            "reviewer_summary": "looks good",
            "reviewer_follow_up_needed": False,
            "tool_results": [],
            "message_count": 2,
        },
    )

    result = runner.invoke(
        app,
        ["shell", "--session-id", "model-shell"],
        input="please inspect the repo\n/exit\n",
    )

    assert result.exit_code == 0
    assert "[mode] model-backed" in result.stdout
    assert "model shell output" in result.stdout


def test_session_show_reflects_replayed_progress_after_resume(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTOS_SESSIONS_DIR", str(tmp_path / "sessions"))

    first = runner.invoke(
        app,
        ["run", "steps: say hello | say again", "--session-id", "replay-session", "--max-iterations", "1"],
    )
    assert first.exit_code == 0

    before = runner.invoke(app, ["session-show", "replay-session"])
    assert before.exit_code == 0
    before_payload = json.loads(before.stdout)
    assert before_payload["session"]["turn_count"] == 1
    assert before_payload["latest_turn"]["state"]["pending_tasks"] == ["say again"]

    resumed = runner.invoke(app, ["resume", "replay-session"])
    assert resumed.exit_code == 0

    after = runner.invoke(app, ["session-show", "replay-session"])
    assert after.exit_code == 0
    after_payload = json.loads(after.stdout)
    assert after_payload["session"]["turn_count"] == 2
    assert after_payload["latest_turn"]["state"]["loop_status"] == "completed"
    assert after_payload["latest_turn"]["state"]["completed_tasks"] == ["say hello", "say again"]
