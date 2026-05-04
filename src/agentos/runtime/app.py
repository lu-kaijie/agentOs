"""Runtime bootstrap for the current milestone."""

from __future__ import annotations

from dataclasses import dataclass

from agentos.config import Settings


@dataclass(slots=True)
class RuntimeBootstrap:
    """A thin runtime shell before LangGraph is introduced."""

    settings: Settings

    def summary(self) -> dict[str, str]:
        """Expose runtime bootstrap information for CLI and tests."""

        return {
            "workspace_dir": str(self.settings.workspace_dir),
            "model_provider": self.settings.model_provider,
            "model_name": self.settings.model_name,
            "runtime_status": "skeleton-ready",
        }


def build_runtime(settings: Settings) -> RuntimeBootstrap:
    """Build the runtime shell for the current milestone."""

    return RuntimeBootstrap(settings=settings)
