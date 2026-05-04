"""Local command execution for the current milestone."""

from __future__ import annotations

import subprocess
from pathlib import Path

from agentos.harness.execution.base import CommandExecutor
from agentos.harness.execution.models import ExecutionRequest, ExecutionResult


class LocalCommandExecutor(CommandExecutor):
    """A minimal local executor with explicit process boundaries."""

    def run(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a command in a specific working directory."""

        cwd = Path(request.cwd).resolve()
        try:
            completed = subprocess.run(
                request.command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                check=False,
            )
            return ExecutionResult(
                command=request.command,
                cwd=str(cwd),
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            return ExecutionResult(
                command=request.command,
                cwd=str(cwd),
                exit_code=124,
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                timed_out=True,
            )
