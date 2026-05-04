import time
from pathlib import Path

from agentos.execution_control import BackgroundExecutionManager


def test_background_job_completes_and_persists(tmp_path: Path):
    manager = BackgroundExecutionManager(tmp_path)

    job = manager.run(["bash", "-lc", "printf 'done'"], cwd=str(tmp_path))
    assert job.status == "running"

    deadline = time.time() + 5
    refreshed = job
    while time.time() < deadline:
        refreshed = manager.get(job.id)
        if refreshed.status == "completed":
            break
        time.sleep(0.1)

    assert refreshed.status == "completed"
    assert refreshed.exit_code == 0
    assert Path(refreshed.stdout_path).read_text(encoding="utf-8") == "done"


def test_background_list_reports_jobs(tmp_path: Path):
    manager = BackgroundExecutionManager(tmp_path)
    manager.run(["bash", "-lc", "printf 'x'"], cwd=str(tmp_path))

    listing = manager.list()

    assert listing["jobs_dir"] == str(tmp_path)
    assert len(listing["jobs"]) == 1
