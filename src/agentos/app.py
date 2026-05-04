"""Top-level application bootstrap."""

from __future__ import annotations

from dataclasses import dataclass

from agentos.config import Settings
from agentos.runtime.app import RuntimeBootstrap, build_runtime


@dataclass(slots=True)
class AgentOsApp:
    """Application wrapper that wires config into the runtime shell."""

    settings: Settings
    runtime: RuntimeBootstrap

    @classmethod
    def bootstrap(cls) -> "AgentOsApp":
        """Load settings and prepare the runtime shell."""

        settings = Settings.load()
        runtime = build_runtime(settings)
        return cls(settings=settings, runtime=runtime)

    def status(self) -> dict[str, str]:
        """Return a small status payload for CLI and tests."""

        return self.runtime.summary()
