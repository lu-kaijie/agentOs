from pathlib import Path

from agentos.tasks import TaskManager
from agentos.tasks.models import TaskStatus


def test_task_manager_persists_and_lists_tasks(tmp_path: Path):
    manager = TaskManager(tmp_path)

    first = manager.create_task("Setup project")
    second = manager.create_task("Write tests", blocked_by=[first.id])

    summary = manager.summary()

    assert summary["total"] == 2
    assert summary["ready"][0]["title"] == "Setup project"
    assert second.id in manager.get_task(first.id).blocks


def test_completing_task_unblocks_dependents(tmp_path: Path):
    manager = TaskManager(tmp_path)

    first = manager.create_task("Parse input")
    second = manager.create_task("Render output", blocked_by=[first.id])

    manager.update_status(first.id, TaskStatus.COMPLETED)
    reloaded_second = manager.get_task(second.id)

    assert reloaded_second.blocked_by == []
    assert manager.ready_tasks()[0].id == second.id


def test_completed_dependency_does_not_block_new_task(tmp_path: Path):
    manager = TaskManager(tmp_path)

    first = manager.create_task("Completed task")
    manager.update_status(first.id, TaskStatus.COMPLETED)

    second = manager.create_task("Follow-up task", blocked_by=[first.id])

    assert second.blocked_by == []
