import time
from pathlib import Path

import pytest

from agentos.app import AgentOsApp


@pytest.fixture(autouse=True)
def isolate_background_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENTOS_BACKGROUND_DIR", str(tmp_path / "background"))


def test_runtime_runs_tool_enabled_task():
    app = AgentOsApp.bootstrap()

    state = app.runtime.run_task("run: pwd")

    assert state["user_task"] == "run: pwd"
    assert state["final_output"].strip().endswith("agentOs")
    assert "exit_code=0" in state["last_result"]
    assert "tool_execute:shell_command" in state["execution_trace"]
    assert "finalize_iteration" in state["execution_trace"]
    assert state["decision"]["action"] == "run_command"
    assert state["approval_policy"]["matched_rule"] == "safe-command"
    assert state["tool_results"][0]["tool_name"] == "shell_command"
    assert state["context_bundle"]["task_hints"]["action"] == "run"
    assert "workspace" in state["context_bundle"]["sources"]
    assert state["iteration_count"] == 1
    assert state["loop_status"] == "completed"


def test_runtime_returns_guidance_without_tool_call():
    app = AgentOsApp.bootstrap()

    state = app.runtime.run_task("say hello")

    assert state["decision"]["action"] == "respond"
    assert "Use `run:`, `knowledge:`, `search:`, `read:`, `write:`, `patch:`, or `test:`." in state["final_output"]


def test_runtime_loads_knowledge_topic():
    app = AgentOsApp.bootstrap()

    state = app.runtime.run_task("knowledge: langgraph-runtime")

    assert state["decision"]["action"] == "load_knowledge"
    assert "[knowledge:langgraph-runtime]" in state["loaded_knowledge"]
    assert "tool_execute:knowledge_load" in state["execution_trace"]


def test_runtime_requires_approval_for_dangerous_command():
    app = AgentOsApp.bootstrap()

    blocked = app.runtime.run_task("run: rm temp.txt")
    approved = app.runtime.run_task("run: rm temp.txt", approved=True)

    assert "Approval required" in blocked["final_output"]
    assert "Policy reason:" in blocked["final_output"]
    assert "approval_gate" in blocked["execution_trace"]
    assert blocked["approval_policy"]["matched_rule"] == "destructive-command"
    assert blocked["approval_policy"]["risk_level"] == "high"
    assert approved["decision"]["requires_approval"] is True


def test_runtime_continues_across_multiple_explicit_steps():
    app = AgentOsApp.bootstrap()

    state = app.runtime.run_task(
        "steps: run: pwd | knowledge: langgraph-runtime | say hello",
        max_iterations=5,
    )

    assert state["iteration_count"] == 3
    assert state["completed_tasks"] == [
        "run: pwd",
        "knowledge: langgraph-runtime",
        "say hello",
    ]
    assert state["pending_tasks"] == []
    assert state["loop_status"] == "completed"
    assert "[step 1]" in state["final_output"]
    assert "[knowledge:langgraph-runtime]" in state["final_output"]
    assert state["execution_trace"].count("model_decide") == 3


def test_runtime_stops_at_max_iterations_with_remaining_steps():
    app = AgentOsApp.bootstrap()

    state = app.runtime.run_task(
        "steps: say hello | say again | say once more",
        max_iterations=2,
    )

    assert state["iteration_count"] == 2
    assert state["pending_tasks"] == ["say once more"]
    assert state["loop_status"] == "stopped:max_iterations"


def test_runtime_reenters_completed_background_results(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENTOS_BACKGROUND_DIR", str(tmp_path / "background"))
    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("AGENTOS_KNOWLEDGE_DIR", str(tmp_path / "knowledge"))
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    (knowledge_dir / "langgraph-runtime.md").write_text("# Runtime from background", encoding="utf-8")

    app = AgentOsApp.bootstrap()
    job = app.background_manager.run(
        ["bash", "-lc", "printf 'knowledge: langgraph-runtime'"],
        cwd=str(tmp_path),
    )

    deadline = time.time() + 5
    while time.time() < deadline:
        refreshed = app.background_manager.get(job.id)
        if refreshed.status == "completed":
            break
        time.sleep(0.1)

    state = app.runtime.run_task("say hello", max_iterations=5)

    assert state["consumed_background_jobs"] == [job.id]
    assert "background_reentry" in state["execution_trace"]
    assert "background_results_detected=1" in state["execution_trace"]
    assert "tool_execute:knowledge_load" in state["execution_trace"]
    assert "[knowledge:langgraph-runtime]" in state["final_output"]
    assert state["completed_tasks"][0] == f"background_result:{job.id}"


def test_runtime_context_selection_changes_with_task_and_history_size(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    (tmp_path / "README.md").write_text("alpha beta gamma\n", encoding="utf-8")

    app = AgentOsApp.bootstrap()
    state = app.runtime.run_task(
        "steps: read: README.md | search: alpha | say hello | say again | say once more",
        max_iterations=5,
    )

    bundle = state["context_bundle"]

    assert bundle["task"] == "say once more"
    assert bundle["task_hints"]["action"] == "respond"
    assert "history" in bundle["sources"]
    assert "tool_results" in bundle["sources"]
    assert "..." in bundle["history_summary"] or "..." in bundle["tool_summary"] or "..." in bundle["trace_summary"]
