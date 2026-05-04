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

    summary = manager.summary()
    assert summary["total"] == 1
    assert summary["sessions"][0]["id"] == "demo"

    turn_path = Path(session.latest_state_path)
    assert json.loads(turn_path.read_text(encoding="utf-8"))["turn_index"] == 1
