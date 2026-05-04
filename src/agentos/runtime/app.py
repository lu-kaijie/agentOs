"""Runtime bootstrap for the current milestone."""

from __future__ import annotations

from dataclasses import dataclass
from agentos.config import Settings
from agentos.harness.execution import CommandExecutor


@dataclass(slots=True)
class RuntimeBootstrap:
    """A thin runtime shell before LangGraph is introduced."""

    settings: Settings
    executor: CommandExecutor

    def summary(self) -> dict[str, str]:
        """Expose runtime bootstrap information for CLI and tests."""

        return {
            "workspace_dir": str(self.settings.workspace_dir),
            "model_provider": self.settings.model_provider,
            "model_name": self.settings.model_name,
            "runtime_status": "skeleton-ready",
            "executor": self.executor.__class__.__name__,
        }


def build_runtime(settings: Settings, executor: CommandExecutor) -> RuntimeBootstrap:
    """Build the runtime shell for the current milestone."""

    return RuntimeBootstrap(settings=settings, executor=executor)
