"""Top-level application bootstrap."""

from __future__ import annotations

import time
from dataclasses import dataclass
from collections.abc import Iterator

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
from agentos.tools import ToolRegistry, build_default_tool_registry


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
    tool_registry: ToolRegistry

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
        tool_registry = build_default_tool_registry(
            workspace_dir=settings.workspace_dir,
            executor=executor,
            knowledge_loader=knowledge_loader,
        )
        runtime = build_runtime(
            settings,
            executor=executor,
            knowledge_loader=knowledge_loader,
            background_manager=background_manager,
            approval_policy=approval_policy,
            tool_registry=tool_registry,
            context_manager=context_manager,
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
            tool_registry=tool_registry,
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

    def stream_session_task(
        self,
        task: str,
        *,
        session_id: str,
        approve: bool = False,
        max_iterations: int = 5,
        state_override: dict[str, object] | None = None,
    ) -> Iterator[dict[str, object]]:
        final_state: dict[str, object] | None = None
        for state in self.runtime.stream_task(
            task,
            session_id=session_id,
            approved=approve,
            max_iterations=max_iterations,
            state_override=state_override,
        ):
            final_state = state
            yield state
        if final_state is None:
            return
        self.session_manager.record_turn(
            session_id=session_id,
            user_task=task,
            state=final_state,
            workspace_dir=str(self.settings.workspace_dir),
        )

    def resume_session(
        self,
        session_id: str,
        *,
        task: str = "",
        approve: bool = False,
        max_iterations: int = 5,
        poll_iterations: int = 1,
        poll_interval: float = 0.2,
    ) -> dict[str, object]:
        last_session = self.session_manager.get_session(session_id)
        if poll_iterations > 1:
            for poll_index in range(poll_iterations):
                if self.background_manager.has_unconsumed_completed(session_id):
                    break
                if poll_index < poll_iterations - 1:
                    time.sleep(poll_interval)
        state_override, previous_task = self.session_manager.build_resume_state(session_id)
        next_task = task or previous_task or "describe current status"
        state = self.run_session_task(
            next_task,
            session_id=session_id,
            approve=approve,
            max_iterations=max_iterations,
            state_override=state_override,
        )
        state["resume_poll_iterations"] = poll_iterations
        state["resume_from_loop_status"] = last_session.latest_loop_status
        return state
