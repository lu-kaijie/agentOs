"""Top-level application bootstrap."""

from __future__ import annotations

from dataclasses import dataclass

from agentos.config import Settings
from agentos.coordination import CoordinationManager
from agentos.context import ContextManager
from agentos.execution_control import BackgroundExecutionManager, WorkspaceManager
from agentos.harness.execution import LocalCommandExecutor
from agentos.knowledge import KnowledgeLoader
from agentos.policy import CommandApprovalPolicy
from agentos.runtime.app import RuntimeBootstrap, build_runtime
from agentos.sessions import SessionManager
from agentos.tasks import TaskManager


@dataclass(slots=True)
class AgentOsApp:
    """Application wrapper that wires config into the runtime shell."""

    settings: Settings
    runtime: RuntimeBootstrap
    task_manager: TaskManager
    knowledge_loader: KnowledgeLoader
    context_manager: ContextManager
    session_manager: SessionManager
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
        session_manager = SessionManager(settings.sessions_dir)
        background_manager = BackgroundExecutionManager(settings.background_jobs_dir)
        workspace_manager = WorkspaceManager(settings.workspaces_dir)
        coordination_manager = CoordinationManager(settings.coordination_dir)
        approval_policy = CommandApprovalPolicy()
        runtime = build_runtime(
            settings,
            executor=executor,
            knowledge_loader=knowledge_loader,
            background_manager=background_manager,
            approval_policy=approval_policy,
        )
        task_manager = TaskManager(settings.tasks_dir)
        return cls(
            settings=settings,
            runtime=runtime,
            task_manager=task_manager,
            knowledge_loader=knowledge_loader,
            context_manager=context_manager,
            session_manager=session_manager,
            background_manager=background_manager,
            workspace_manager=workspace_manager,
            coordination_manager=coordination_manager,
        )

    def status(self) -> dict[str, str]:
        """Return a small status payload for CLI and tests."""

        return self.runtime.summary()

    def run_session_task(
        self,
        task: str,
        *,
        session_id: str,
        approve: bool = False,
        max_iterations: int = 5,
        state_override: dict[str, object] | None = None,
    ) -> dict[str, object]:
        state = self.runtime.run_task(
            task,
            session_id=session_id,
            approved=approve,
            max_iterations=max_iterations,
            state_override=state_override,
        )
        self.session_manager.record_turn(
            session_id=session_id,
            user_task=task,
            state=state,
            workspace_dir=str(self.settings.workspace_dir),
        )
        return state

    def resume_session(
        self,
        session_id: str,
        *,
        task: str = "",
        approve: bool = False,
        max_iterations: int = 5,
    ) -> dict[str, object]:
        state_override, previous_task = self.session_manager.build_resume_state(session_id)
        next_task = task or previous_task or "describe current status"
        return self.run_session_task(
            next_task,
            session_id=session_id,
            approve=approve,
            max_iterations=max_iterations,
            state_override=state_override,
        )
