"""Delegated work unit models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class WorkUnitStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class WorkUnitRecord:
    """A delegated work unit for role-based coordination."""

    id: int
    title: str
    role: str
    task_id: int | None = None
    workspace: str = ""
    status: WorkUnitStatus = WorkUnitStatus.PENDING
    result: str = ""
    depends_on: list[int] = field(default_factory=list)
    instructions: str = ""
    command: list[str] = field(default_factory=list)
    execution_context: str = ""
    exit_code: int | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "WorkUnitRecord":
        return cls(
            id=int(payload["id"]),
            title=str(payload["title"]),
            role=str(payload["role"]),
            task_id=int(payload["task_id"]) if payload.get("task_id") is not None else None,
            workspace=str(payload.get("workspace", "")),
            status=WorkUnitStatus(str(payload.get("status", WorkUnitStatus.PENDING.value))),
            result=str(payload.get("result", "")),
            depends_on=[int(item) for item in payload.get("depends_on", [])],
            instructions=str(payload.get("instructions", "")),
            command=[str(item) for item in payload.get("command", [])],
            execution_context=str(payload.get("execution_context", "")),
            exit_code=int(payload["exit_code"]) if payload.get("exit_code") is not None else None,
        )
