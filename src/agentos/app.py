"""Top-level application bootstrap."""

from __future__ import annotations

from dataclasses import dataclass

from agentos.config import Settings
from agentos.coordination import CoordinationManager
from agentos.context import ContextManager
from agentos.execution_control import BackgroundExecutionManager, WorkspaceManager
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
    background_manager: BackgroundExecutionManager
    workspace_manager: WorkspaceManager
    coordination_manager: CoordinationManager

    @classmethod
    def bootstrap(cls) -> "AgentOsApp":
        """Load settings and prepare the runtime shell."""

        settings = Settings.load()
        executor = LocalCommandExecutor()
        knowledge_loader = KnowledgeLoader(settings.knowledge_dir)
        context_manager = ContextManager(settings.context_dir)
        background_manager = BackgroundExecutionManager(settings.background_jobs_dir)
        workspace_manager = WorkspaceManager(settings.workspaces_dir)
        coordination_manager = CoordinationManager(settings.coordination_dir)
        runtime = build_runtime(
            settings,
            executor=executor,
            knowledge_loader=knowledge_loader,
            background_manager=background_manager,
        )
        task_manager = TaskManager(settings.tasks_dir)
        return cls(
            settings=settings,
            runtime=runtime,
            task_manager=task_manager,
            knowledge_loader=knowledge_loader,
            context_manager=context_manager,
            background_manager=background_manager,
            workspace_manager=workspace_manager,
            coordination_manager=coordination_manager,
        )

    def status(self) -> dict[str, str]:
        """Return a small status payload for CLI and tests."""

        return self.runtime.summary()
