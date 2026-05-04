"""Persistent session data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class SessionRecord:
    """A durable session model for runtime replay and resume."""

    id: str
    created_at: str
    updated_at: str
    turn_count: int = 0
    latest_user_task: str = ""
    latest_state_path: str = ""
    latest_loop_status: str = ""
    latest_iteration_count: int = 0
    linked_task_ids: list[int] = field(default_factory=list)
    linked_work_unit_ids: list[int] = field(default_factory=list)
    workspace_dir: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "SessionRecord":
        return cls(
            id=str(payload["id"]),
            created_at=str(payload["created_at"]),
            updated_at=str(payload["updated_at"]),
            turn_count=int(payload.get("turn_count", 0)),
            latest_user_task=str(payload.get("latest_user_task", "")),
            latest_state_path=str(payload.get("latest_state_path", "")),
            latest_loop_status=str(payload.get("latest_loop_status", "")),
            latest_iteration_count=int(payload.get("latest_iteration_count", 0)),
            linked_task_ids=[int(item) for item in payload.get("linked_task_ids", [])],
            linked_work_unit_ids=[int(item) for item in payload.get("linked_work_unit_ids", [])],
            workspace_dir=str(payload.get("workspace_dir", "")),
        )
