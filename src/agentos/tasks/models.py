"""Persistent task data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass(slots=True)
class TaskRecord:
    """A durable task model for the control plane."""

    id: int
    title: str
    status: TaskStatus = TaskStatus.PENDING
    blocked_by: list[int] = field(default_factory=list)
    blocks: list[int] = field(default_factory=list)
    owner: str = ""
    execution_context: str = ""

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "TaskRecord":
        return cls(
            id=int(payload["id"]),
            title=str(payload["title"]),
            status=TaskStatus(str(payload.get("status", TaskStatus.PENDING.value))),
            blocked_by=[int(item) for item in payload.get("blocked_by", [])],
            blocks=[int(item) for item in payload.get("blocks", [])],
            owner=str(payload.get("owner", "")),
            execution_context=str(payload.get("execution_context", "")),
        )
