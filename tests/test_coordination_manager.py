from pathlib import Path

from agentos.coordination import CoordinationManager
from agentos.coordination.models import WorkUnitStatus


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
