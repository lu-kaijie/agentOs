"""Session persistence and replay support."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agentos.sessions.models import SessionRecord


class SessionManager:
    """Persist runtime sessions, states, and replayable turn history."""

    def __init__(self, sessions_dir: Path):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def record_turn(
        self,
        *,
        session_id: str,
        user_task: str,
        state: dict[str, object],
        workspace_dir: str,
        linked_task_ids: list[int] | None = None,
        linked_work_unit_ids: list[int] | None = None,
    ) -> SessionRecord:
        session = self._load_or_create(session_id, workspace_dir=workspace_dir)
        turn_index = session.turn_count + 1
        timestamp = self._now()
        turn_path = self._session_dir(session_id) / f"turn_{turn_index:04d}.json"
        payload = {
            "session_id": session_id,
            "turn_index": turn_index,
            "recorded_at": timestamp,
            "user_task": user_task,
            "state": state,
        }
        turn_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        session.turn_count = turn_index
        session.updated_at = timestamp
        session.latest_user_task = user_task
        session.latest_state_path = str(turn_path)
        session.latest_loop_status = str(state.get("loop_status", ""))
        session.latest_iteration_count = int(state.get("iteration_count", 0))
        session.workspace_dir = workspace_dir
        session.linked_task_ids = linked_task_ids or session.linked_task_ids
        session.linked_work_unit_ids = linked_work_unit_ids or session.linked_work_unit_ids
        self._save(session)
        return session

    def list_sessions(self) -> list[SessionRecord]:
        sessions = []
        for path in sorted(self.sessions_dir.glob("*/session.json")):
            sessions.append(self._load(path.parent.name))
        return sorted(sessions, key=lambda item: item.updated_at, reverse=True)

    def get_session(self, session_id: str) -> SessionRecord:
        return self._load(session_id)

    def load_latest_turn(self, session_id: str) -> dict[str, object]:
        session = self.get_session(session_id)
        if not session.latest_state_path:
            raise FileNotFoundError(f"Session '{session_id}' has no recorded turns")
        return json.loads(Path(session.latest_state_path).read_text(encoding="utf-8"))

    def build_resume_state(self, session_id: str) -> tuple[dict[str, object], str]:
        turn = self.load_latest_turn(session_id)
        state = dict(turn["state"])
        user_task = str(turn["user_task"])
        carryover = {
            "pending_tasks": list(state.get("pending_tasks", [])),
            "completed_tasks": list(state.get("completed_tasks", [])),
            "step_outputs": list(state.get("step_outputs", [])),
            "background_results": list(state.get("background_results", [])),
            "consumed_background_jobs": list(state.get("consumed_background_jobs", [])),
            "iteration_count": int(state.get("iteration_count", 0)),
            "loop_status": str(state.get("loop_status", "initialized")),
            "loaded_knowledge": str(state.get("loaded_knowledge", "")),
            "last_result": str(state.get("last_result", "")),
            "role_records": list(state.get("role_records", [])),
            "role_handoffs": list(state.get("role_handoffs", [])),
            "tool_results": list(state.get("tool_results", [])),
            "context_policy_records": list(state.get("context_policy_records", [])),
        }
        if not carryover["pending_tasks"]:
            carryover.update(
                {
                    "completed_tasks": [],
                    "step_outputs": [],
                    "background_results": [],
                    "consumed_background_jobs": [],
                    "iteration_count": 0,
                    "loop_status": "initialized",
                    "loaded_knowledge": "",
                    "last_result": "",
                    "role_records": [],
                    "role_handoffs": [],
                    "tool_results": [],
                    "context_policy_records": [],
                }
            )
        return carryover, user_task

    def summary(self) -> dict[str, object]:
        sessions = self.list_sessions()
        return {
            "sessions_dir": str(self.sessions_dir),
            "total": len(sessions),
            "sessions": [session.to_dict() for session in sessions],
        }

    def _load_or_create(self, session_id: str, *, workspace_dir: str) -> SessionRecord:
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        session_file = self._session_file(session_id)
        if session_file.exists():
            return self._load(session_id)
        now = self._now()
        session = SessionRecord(id=session_id, created_at=now, updated_at=now, workspace_dir=workspace_dir)
        self._save(session)
        return session

    def _load(self, session_id: str) -> SessionRecord:
        path = self._session_file(session_id)
        if not path.exists():
            raise FileNotFoundError(f"Session '{session_id}' does not exist")
        return SessionRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def _save(self, session: SessionRecord) -> None:
        self._session_file(session.id).write_text(
            json.dumps(session.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _session_dir(self, session_id: str) -> Path:
        return self.sessions_dir / session_id

    def _session_file(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "session.json"

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
