import json
from pathlib import Path

from agentos.sessions import SessionManager


def test_session_manager_records_turn_and_lists_sessions(tmp_path: Path):
    manager = SessionManager(tmp_path)

    session = manager.record_turn(
        session_id="demo",
        user_task="run: pwd",
        state={"loop_status": "completed", "iteration_count": 1, "pending_tasks": []},
        workspace_dir="/tmp/workspace",
    )

    assert session.id == "demo"
    assert session.turn_count == 1

    latest_turn = manager.load_latest_turn("demo")
    assert latest_turn["user_task"] == "run: pwd"
    assert latest_turn["state"]["loop_status"] == "completed"
    assert "memory_state" not in latest_turn["state"] or isinstance(latest_turn["state"].get("memory_state", {}), dict)

    summary = manager.summary()
    assert summary["total"] == 1
    assert summary["sessions"][0]["id"] == "demo"

    turn_path = Path(session.latest_state_path)
    assert json.loads(turn_path.read_text(encoding="utf-8"))["turn_index"] == 1


def test_session_manager_builds_resume_state_from_latest_turn(tmp_path: Path):
    manager = SessionManager(tmp_path)
    manager.record_turn(
        session_id="resume-demo",
        user_task="steps: say hello | say again",
        state={
            "loop_status": "stopped:max_iterations",
            "iteration_count": 1,
            "pending_tasks": ["say again"],
            "completed_tasks": ["say hello"],
            "step_outputs": ["No tool or knowledge action selected. Use `run: <command>` or `knowledge: <topic>`."],
            "background_results": [],
            "consumed_background_jobs": [],
            "loaded_knowledge": "",
            "last_result": "",
        },
        workspace_dir="/tmp/workspace",
    )

    state_override, previous_task = manager.build_resume_state("resume-demo")

    assert previous_task == "steps: say hello | say again"
    assert state_override["pending_tasks"] == ["say again"]
    assert state_override["completed_tasks"] == ["say hello"]


def test_session_manager_carries_layered_memory_and_audits_on_resume(tmp_path: Path):
    manager = SessionManager(tmp_path)
    manager.record_turn(
        session_id="memory-resume",
        user_task="say hello",
        state={
            "loop_status": "completed",
            "iteration_count": 1,
            "pending_tasks": [],
            "completed_tasks": ["say hello"],
            "step_outputs": ["hello"],
            "tool_results": [],
            "context_policy_records": [],
            "memory_state": {"session_summary": "goal=say hello"},
            "context_audit_records": [{"trigger_reason": "turn_complete"}],
        },
        workspace_dir="/tmp/workspace",
    )

    state_override, _ = manager.build_resume_state("memory-resume")

    assert state_override["memory_state"] == {}
    assert state_override["context_audit_records"] == []
