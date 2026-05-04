"""Execution data models for the harness layer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ExecutionRequest:
    """A narrow command execution request."""

    command: list[str]
    cwd: str
    timeout_seconds: int = 30


@dataclass(slots=True)
class ExecutionResult:
    """The result of a command execution."""

    command: list[str]
    cwd: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
