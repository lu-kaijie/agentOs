"""Background execution management."""

from __future__ import annotations

import json
import shlex
import uuid
from dataclasses import dataclass
from pathlib import Path
from subprocess import Popen


@dataclass(slots=True)
class BackgroundJob:
    """Persistent metadata for a background job."""

    id: str
    command: list[str]
    cwd: str
    status: str
    pid: int
    stdout_path: str
    stderr_path: str
    exit_code: int | None
    consumed_by_runtime: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "command": self.command,
            "cwd": self.cwd,
            "status": self.status,
            "pid": self.pid,
            "stdout_path": self.stdout_path,
            "stderr_path": self.stderr_path,
            "exit_code": self.exit_code,
            "consumed_by_runtime": self.consumed_by_runtime,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "BackgroundJob":
        return cls(
            id=str(payload["id"]),
            command=[str(item) for item in payload["command"]],
            cwd=str(payload["cwd"]),
            status=str(payload["status"]),
            pid=int(payload["pid"]),
            stdout_path=str(payload["stdout_path"]),
            stderr_path=str(payload["stderr_path"]),
            exit_code=int(payload["exit_code"]) if payload.get("exit_code") is not None else None,
            consumed_by_runtime=bool(payload.get("consumed_by_runtime", False)),
        )


@dataclass(slots=True)
class BackgroundResult:
    """Structured background result for runtime re-entry."""

    job_id: str
    command: list[str]
    cwd: str
    exit_code: int
    stdout: str
    stderr: str

    def to_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "command": self.command,
            "cwd": self.cwd,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


class BackgroundExecutionManager:
    """Launch and inspect background jobs with persistent metadata."""

    def __init__(self, jobs_dir: Path):
        self.jobs_dir = Path(jobs_dir)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.jobs_dir / "events.jsonl"

    def run(self, command: list[str], cwd: str) -> BackgroundJob:
        job_id = uuid.uuid4().hex[:8]
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        stdout_path = job_dir / "stdout.log"
        stderr_path = job_dir / "stderr.log"
        exit_code_path = job_dir / "exit_code.txt"
        shell_command = (
            f"cd {shlex.quote(cwd)} && "
            f"{shlex.join(command)} > {shlex.quote(str(stdout_path))} "
            f"2> {shlex.quote(str(stderr_path))}; "
            f"printf '%s' $? > {shlex.quote(str(exit_code_path))}"
        )
        process = Popen(
            ["/bin/bash", "-lc", shell_command],
            start_new_session=True,
        )
        job = BackgroundJob(
            id=job_id,
            command=command,
            cwd=cwd,
            status="running",
            pid=process.pid,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            exit_code=None,
        )
        self._save(job)
        self._emit_event("job.started", job)
        return job

    def get(self, job_id: str) -> BackgroundJob:
        path = self.jobs_dir / job_id / "job.json"
        if not path.exists():
            raise FileNotFoundError(f"Background job '{job_id}' does not exist")
        job = BackgroundJob.from_dict(json.loads(path.read_text(encoding="utf-8")))
        return self._refresh(job)

    def list(self) -> dict[str, object]:
        jobs = []
        for path in sorted(self.jobs_dir.glob("*/job.json")):
            job = BackgroundJob.from_dict(json.loads(path.read_text(encoding="utf-8")))
            jobs.append(self._refresh(job).to_dict())
        return {
            "jobs_dir": str(self.jobs_dir),
            "jobs": jobs,
        }

    def consume_completed(self) -> list[BackgroundResult]:
        """Return completed background results that have not yet re-entered runtime."""

        results: list[BackgroundResult] = []
        for path in sorted(self.jobs_dir.glob("*/job.json")):
            job = BackgroundJob.from_dict(json.loads(path.read_text(encoding="utf-8")))
            job = self._refresh(job)
            if job.status != "completed" or job.consumed_by_runtime or job.exit_code is None:
                continue
            result = BackgroundResult(
                job_id=job.id,
                command=job.command,
                cwd=job.cwd,
                exit_code=job.exit_code,
                stdout=Path(job.stdout_path).read_text(encoding="utf-8"),
                stderr=Path(job.stderr_path).read_text(encoding="utf-8"),
            )
            job.consumed_by_runtime = True
            self._save(job)
            self._emit_event("job.reentered", job)
            results.append(result)
        return results

    def _refresh(self, job: BackgroundJob) -> BackgroundJob:
        exit_code_path = self.jobs_dir / job.id / "exit_code.txt"
        if exit_code_path.exists():
            exit_code = int(exit_code_path.read_text(encoding="utf-8").strip())
            if job.status != "completed":
                job.status = "completed"
                job.exit_code = exit_code
                self._save(job)
                self._emit_event("job.completed", job)
        return job

    def _save(self, job: BackgroundJob) -> None:
        path = self.jobs_dir / job.id / "job.json"
        path.write_text(json.dumps(job.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _emit_event(self, event_type: str, job: BackgroundJob) -> None:
        event = {
            "event": event_type,
            "job": job.to_dict(),
        }
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
