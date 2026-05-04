"""Top-level application bootstrap."""

from __future__ import annotations

from dataclasses import dataclass

from agentos.config import Settings
from agentos.context import ContextManager
from agentos.harness.execution import LocalCommandExecutor
from agentos.knowledge import KnowledgeLoader
from agentos.runtime.app import RuntimeBootstrap, build_runtime
from agentos.tasks import TaskManager


@dataclass(slots=True)
class AgentOsApp:
    """Application wrapper that wires config into the runtime shell."""

    settings: Settings
    runtime: RuntimeBootstrap
    task_manager: TaskManager
    knowledge_loader: KnowledgeLoader
    context_manager: ContextManager

    @classmethod
    def bootstrap(cls) -> "AgentOsApp":
        """Load settings and prepare the runtime shell."""

        settings = Settings.load()
        executor = LocalCommandExecutor()
        knowledge_loader = KnowledgeLoader(settings.knowledge_dir)
        context_manager = ContextManager(settings.context_dir)
        runtime = build_runtime(settings, executor=executor, knowledge_loader=knowledge_loader)
        task_manager = TaskManager(settings.tasks_dir)
        return cls(
            settings=settings,
            runtime=runtime,
            task_manager=task_manager,
            knowledge_loader=knowledge_loader,
            context_manager=context_manager,
        )

    def status(self) -> dict[str, str]:
        """Return a small status payload for CLI and tests."""

        return self.runtime.summary()
