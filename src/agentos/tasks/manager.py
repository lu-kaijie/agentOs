"""Persistent task manager for the control plane."""

from __future__ import annotations

import json
from pathlib import Path

from agentos.tasks.models import TaskRecord, TaskStatus


class TaskManager:
    """Manage task state on disk."""

    def __init__(self, tasks_dir: Path):
        self.tasks_dir = Path(tasks_dir)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def create_task(self, title: str, blocked_by: list[int] | None = None) -> TaskRecord:
        normalized_blocked_by: list[int] = []
        for dependency_id in blocked_by or []:
            dependency = self.get_task(dependency_id)
            if dependency.status != TaskStatus.COMPLETED:
                normalized_blocked_by.append(dependency_id)

        task = TaskRecord(
            id=self._next_id(),
            title=title,
            blocked_by=normalized_blocked_by,
        )
        self._save(task)
        for dependency_id in normalized_blocked_by:
            dependency = self.get_task(dependency_id)
            if task.id not in dependency.blocks:
                dependency.blocks.append(task.id)
                self._save(dependency)
        return task

    def list_tasks(self) -> list[TaskRecord]:
        tasks = [self._load(path) for path in sorted(self.tasks_dir.glob("task_*.json"))]
        return sorted(tasks, key=lambda item: item.id)

    def get_task(self, task_id: int) -> TaskRecord:
        path = self._task_path(task_id)
        if not path.exists():
            raise FileNotFoundError(f"Task {task_id} does not exist")
        return self._load(path)

    def update_status(self, task_id: int, status: TaskStatus) -> TaskRecord:
        task = self.get_task(task_id)
        task.status = status
        self._save(task)
        if status == TaskStatus.COMPLETED:
            self._clear_dependency(task_id)
        return task

    def ready_tasks(self) -> list[TaskRecord]:
        return [
            task
            for task in self.list_tasks()
            if task.status == TaskStatus.PENDING and not task.blocked_by
        ]

    def summary(self) -> dict[str, object]:
        tasks = self.list_tasks()
        return {
            "tasks_dir": str(self.tasks_dir),
            "total": len(tasks),
            "ready": [task.to_dict() for task in self.ready_tasks()],
            "tasks": [task.to_dict() for task in tasks],
        }

    def _next_id(self) -> int:
        ids = [task.id for task in self.list_tasks()]
        return max(ids, default=0) + 1

    def _clear_dependency(self, completed_id: int) -> None:
        for task in self.list_tasks():
            if completed_id in task.blocked_by:
                task.blocked_by.remove(completed_id)
                self._save(task)

    def _task_path(self, task_id: int) -> Path:
        return self.tasks_dir / f"task_{task_id}.json"

    def _save(self, task: TaskRecord) -> None:
        self._task_path(task.id).write_text(
            json.dumps(task.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _load(self, path: Path) -> TaskRecord:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return TaskRecord.from_dict(payload)
