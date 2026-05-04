from pathlib import Path

from agentos.coordination import CoordinationManager
from agentos.coordination.models import WorkUnitStatus
from agentos.harness.execution import LocalCommandExecutor
from agentos.tasks import TaskManager
from agentos.tasks.models import TaskStatus


def test_coordination_manager_tracks_ready_units(tmp_path: Path):
    manager = CoordinationManager(tmp_path)
    first = manager.create_unit(title="Inspect backend", role="researcher")
    second = manager.create_unit(title="Write patch", role="builder", depends_on=[first.id])

    ready_titles = [unit.title for unit in manager.ready_units()]
    assert ready_titles == ["Inspect backend"]

    manager.update_status(first.id, status=WorkUnitStatus.COMPLETED, result="inspection done")
    ready_titles = [unit.title for unit in manager.ready_units()]
    assert "Write patch" in ready_titles
    assert second.id == 2


def test_coordination_manager_persists_result(tmp_path: Path):
    manager = CoordinationManager(tmp_path)
    unit = manager.create_unit(title="Summarize findings", role="summarizer")

    updated = manager.update_status(unit.id, status=WorkUnitStatus.COMPLETED, result="done")

    assert updated.result == "done"
    assert manager.get_unit(unit.id).status == WorkUnitStatus.COMPLETED


def test_coordination_manager_executes_unit_and_updates_task(tmp_path: Path):
    coordination_dir = tmp_path / "coordination"
    tasks_dir = tmp_path / "tasks"
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    workspace_path = workspace_root / "unit-a"
    workspace_path.mkdir()

    manager = CoordinationManager(coordination_dir)
    task_manager = TaskManager(tasks_dir)
    task = task_manager.create_task("Implement delegated step")
    unit = manager.create_unit(
        title="Inspect backend",
        role="researcher",
        task_id=task.id,
        workspace="unit-a",
        command=["python", "-c", "print('delegated-ok', end='')"],
    )

    executed = manager.execute_unit(
        unit.id,
        executor=LocalCommandExecutor(),
        default_cwd=str(tmp_path),
        workspace_resolver=lambda name, default_cwd: str(workspace_root / str(name)),
        task_manager=task_manager,
    )

    assert executed.status == WorkUnitStatus.COMPLETED
    assert executed.exit_code == 0
    assert executed.execution_context == str(workspace_path)
    assert executed.result == "delegated-ok"

    reloaded_task = task_manager.get_task(task.id)
    assert reloaded_task.status == TaskStatus.COMPLETED
    assert reloaded_task.owner == "researcher"
    assert reloaded_task.execution_context == str(workspace_path)
