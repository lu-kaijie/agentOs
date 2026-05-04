"""Execution interfaces for the harness layer."""

from __future__ import annotations

from abc import ABC, abstractmethod

from agentos.harness.execution.models import ExecutionRequest, ExecutionResult


class CommandExecutor(ABC):
    """Abstract execution boundary for shell-like commands."""

    @abstractmethod
    def run(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a command request and return a structured result."""
