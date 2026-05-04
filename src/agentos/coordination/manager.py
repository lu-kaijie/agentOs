"""Delegated work coordination."""

from __future__ import annotations

import json
from pathlib import Path

from agentos.coordination.models import WorkUnitRecord, WorkUnitStatus


class CoordinationManager:
    """Manage delegated work units with explicit coordination state."""

    def __init__(self, coordination_dir: Path):
        self.coordination_dir = Path(coordination_dir)
        self.coordination_dir.mkdir(parents=True, exist_ok=True)

    def create_unit(
        self,
        *,
        title: str,
        role: str,
        task_id: int | None = None,
        workspace: str = "",
        depends_on: list[int] | None = None,
    ) -> WorkUnitRecord:
        unit = WorkUnitRecord(
            id=self._next_id(),
            title=title,
            role=role,
            task_id=task_id,
            workspace=workspace,
            depends_on=list(depends_on or []),
        )
        self._save(unit)
        return unit

    def list_units(self) -> list[WorkUnitRecord]:
        units = [self._load(path) for path in sorted(self.coordination_dir.glob("unit_*.json"))]
        return sorted(units, key=lambda item: item.id)

    def get_unit(self, unit_id: int) -> WorkUnitRecord:
        path = self._unit_path(unit_id)
        if not path.exists():
            raise FileNotFoundError(f"Work unit {unit_id} does not exist")
        return self._load(path)

    def update_status(
        self,
        unit_id: int,
        *,
        status: WorkUnitStatus,
        result: str | None = None,
    ) -> WorkUnitRecord:
        unit = self.get_unit(unit_id)
        unit.status = status
        if result is not None:
            unit.result = result
        self._save(unit)
        return unit

    def ready_units(self) -> list[WorkUnitRecord]:
        completed = {unit.id for unit in self.list_units() if unit.status == WorkUnitStatus.COMPLETED}
        ready: list[WorkUnitRecord] = []
        for unit in self.list_units():
            if unit.status != WorkUnitStatus.PENDING:
                continue
            if all(dep in completed for dep in unit.depends_on):
                ready.append(unit)
        return ready

    def summary(self) -> dict[str, object]:
        units = self.list_units()
        return {
            "coordination_dir": str(self.coordination_dir),
            "total": len(units),
            "ready": [unit.to_dict() for unit in self.ready_units()],
            "units": [unit.to_dict() for unit in units],
        }

    def _next_id(self) -> int:
        ids = [unit.id for unit in self.list_units()]
        return max(ids, default=0) + 1

    def _unit_path(self, unit_id: int) -> Path:
        return self.coordination_dir / f"unit_{unit_id}.json"

    def _save(self, unit: WorkUnitRecord) -> None:
        self._unit_path(unit.id).write_text(
            json.dumps(unit.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _load(self, path: Path) -> WorkUnitRecord:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return WorkUnitRecord.from_dict(payload)
