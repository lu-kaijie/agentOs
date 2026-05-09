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
from agentos.runtime.model_backed import ModelBackedAgentRuntime
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
    model_runtime: ModelBackedAgentRuntime

    @classmethod
    def bootstrap(cls) -> "AgentOsApp":
        """Load settings and prepare the runtime shell."""

        settings = Settings.load()
        executor = LocalCommandExecutor()
        knowledge_loader = KnowledgeLoader(settings.knowledge_dir, settings.skills_dir)
        context_manager = ContextManager(settings.context_dir, knowledge_loader=knowledge_loader)
        session_manager = SessionManager(settings.sessions_dir)
        background_manager = BackgroundExecutionManager(settings.background_jobs_dir)
        workspace_manager = WorkspaceManager(settings.workspaces_dir)
        coordination_manager = CoordinationManager(settings.coordination_dir)
        approval_policy = CommandApprovalPolicy()
        tool_registry = build_default_tool_registry(
            workspace_dir=settings.workspace_dir,
            executor=executor,
            knowledge_loader=knowledge_loader,
            approval_policy=approval_policy,
        )
        model_runtime = ModelBackedAgentRuntime(
            settings=settings,
            tool_registry=tool_registry,
            context_manager=context_manager,
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
            model_runtime=model_runtime,
        )

    def status(self) -> dict[str, str]:
        """Return a small status payload for CLI and tests."""

        payload = self.runtime.summary()
        payload["model_configured"] = "true" if self.model_runtime.is_configured() else "false"
        payload["model_small_name"] = self.settings.model_small_name
        payload["model_medium_name"] = self.settings.model_medium_name
        payload["model_large_name"] = self.settings.model_large_name
        payload["planner_model_level"] = self.settings.planner_model_level
        payload["executor_model_level"] = self.settings.executor_model_level
        payload["reviewer_model_level"] = self.settings.reviewer_model_level
        return payload

    def model_setup_guidance(self) -> list[str]:
        """Return user-facing setup guidance for the model-backed product path."""

        lines = [
            "未检测到可用的模型配置，当前只能稳定使用非模型路径。",
            "如需启用常驻真实模型 agent shell，请准备以下配置：",
            "1. 复制 `.env.example` 为 `.env`",
            "2. 填写 `OPENAI_API_KEY`",
            "3. 如使用兼容网关，可额外填写 `OPENAI_BASE_URL`",
            "   同时确认该网关兼容当前模型路径所需的 tool calling / agent loop 能力",
            "4. 按需调整三挡模型：`AGENTOS_MODEL_SMALL`、`AGENTOS_MODEL_MEDIUM`、`AGENTOS_MODEL_LARGE`",
            "5. 按需调整 role 映射：`AGENTOS_PLANNER_MODEL_LEVEL`、`AGENTOS_EXECUTOR_MODEL_LEVEL`、`AGENTOS_REVIEWER_MODEL_LEVEL`",
        ]
        return lines

    def shell_banner_lines(self, *, session_id: str) -> list[str]:
        """Return product-oriented shell banner lines."""

        model_state = "ready" if self.model_runtime.is_configured() else "not-configured"
        return [
            f"agentOs shell session: {session_id}",
            f"workspace: {self.settings.workspace_dir}",
            (
                "models: "
                f"small={self.settings.model_small_name} "
                f"medium={self.settings.model_medium_name} "
                f"large={self.settings.model_large_name}"
            ),
            (
                "roles: "
                f"planner={self.settings.planner_model_level} "
                f"executor={self.settings.executor_model_level} "
                f"reviewer={self.settings.reviewer_model_level}"
            ),
            f"model_runtime: {model_state}",
        ]

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

    def run_model_session_task(
        self,
        task: str,
        *,
        session_id: str,
        approve: bool = False,
    ) -> dict[str, object]:
        try:
            latest_turn = self.session_manager.load_latest_turn(session_id)
            prior_state = dict(latest_turn["state"])
        except FileNotFoundError:
            prior_state = {
                "completed_tasks": [],
                "step_outputs": [],
                "tool_results": [],
                "execution_trace": [],
                "context_audit_records": [],
                "memory_state": {},
            }

        planner_bundle, planner_record, memory, planner_audit = self.context_manager.prepare_role_context(
            session_id=session_id,
            role="planner",
            task=task,
            state=prior_state,
            workspace_dir=self.settings.workspace_dir,
            skill_mode="catalog",
            trigger_reason="session_resume" if prior_state.get("completed_tasks") else "prepare_context",
        )
        prepared_state = {
            **prior_state,
            "memory_state": memory.to_dict(),
            "context_audit_records": [planner_audit.to_dict()],
        }
        executor_bundle, executor_record, memory, executor_audit = self.context_manager.prepare_role_context(
            session_id=session_id,
            role="executor",
            task=task,
            state=prepared_state,
            workspace_dir=self.settings.workspace_dir,
            skill_mode="catalog",
            trigger_reason="role_handoff",
        )
        prepared_state = {
            **prepared_state,
            "memory_state": memory.to_dict(),
            "context_audit_records": [planner_audit.to_dict(), executor_audit.to_dict()],
        }
        reviewer_bundle, reviewer_record, memory, reviewer_audit = self.context_manager.prepare_role_context(
            session_id=session_id,
            role="reviewer",
            task=task,
            state=prepared_state,
            workspace_dir=self.settings.workspace_dir,
            skill_mode="catalog",
            trigger_reason="role_handoff",
        )

        result = self.model_runtime.run_turn(
            session_id=session_id,
            user_task=task,
            context_bundles={
                "planner": planner_bundle,
                "executor": executor_bundle,
                "reviewer": reviewer_bundle,
            },
            tool_results=list(prior_state.get("tool_results", [])),
            approved=approve,
        )
        used_model_name = str(result.get("model_name", self.settings.model_medium_name))

        role_records = [
            {
                "role": "planner",
                "task": task,
                "summary": result["planner_summary"],
                "status": "ok",
                "metadata": {"planned_steps": result["planner_steps"]},
            },
            {
                "role": "executor",
                "task": task,
                "summary": result["executor_output"],
                "status": "ok",
                "metadata": {
                    "tool_result_count": len(result["tool_results"]),
                    "message_count": result["message_count"],
                },
            },
            {
                "role": "reviewer",
                "task": task,
                "summary": result["reviewer_summary"],
                "status": "ok",
                "metadata": {
                    "follow_up_needed": result["reviewer_follow_up_needed"],
                },
            },
        ]
        role_handoffs = [
            {
                "source_role": "planner",
                "target_role": "executor",
                "task": task,
                "summary": "Planner routed the real-model coding turn to executor tools.",
                "context_sources": planner_bundle.get("sources", []),
                "tool_result_refs": [],
            },
            {
                "source_role": "executor",
                "target_role": "reviewer",
                "task": task,
                "summary": "Executor completed a bounded model-backed turn and handed results to reviewer.",
                "context_sources": executor_bundle.get("sources", []),
                "tool_result_refs": [
                    str(item.get("tool_name", "unknown"))
                    for item in result["tool_results"][-3:]
                    if isinstance(item, dict)
                ],
            },
        ]
        final_output = result["executor_output"].strip()
        if result["reviewer_summary"]:
            final_output = (
                f"{final_output}\n\n[reviewer]\n{result['reviewer_summary']}".strip()
            )
        state = {
            "user_task": task,
            "session_id": session_id,
            "pending_tasks": [],
            "active_task": task,
            "completed_tasks": [
                f"role:planner:{task}",
                f"role:executor:{task}",
                f"role:reviewer:{task}",
            ],
            "step_outputs": [
                result["planner_summary"],
                result["executor_output"],
                result["reviewer_summary"],
            ],
            "decision": {"action": "model_backed_turn", "mode": "langgraph-react"},
            "background_results": [],
            "consumed_background_jobs": [],
            "next_pending_tasks": [],
            "approval_policy": {},
            "tool_results": result["tool_results"],
            "context_bundle": reviewer_bundle,
            "memory_state": memory.to_dict(),
            "context_policy_records": [
                planner_record.to_dict(),
                executor_record.to_dict(),
                reviewer_record.to_dict(),
            ],
            "context_audit_records": [
                planner_audit.to_dict(),
                executor_audit.to_dict(),
                reviewer_audit.to_dict(),
            ],
            "current_role": "reviewer",
            "role_records": role_records,
            "role_handoffs": role_handoffs,
            "last_result": result["reviewer_summary"],
            "final_output": final_output,
            "loaded_knowledge": "",
            "execution_trace": [
                "prepare_context",
                f"model_selected={used_model_name}",
                f"planner_model={result.get('planner_model_name', used_model_name)}",
                "planner_model",
                f"planner_steps={len(result['planner_steps'])}",
                f"executor_model={result.get('executor_model_name', used_model_name)}",
                "executor_model",
                f"executor_tools={len(result['tool_results'])}",
                f"reviewer_model={result.get('reviewer_model_name', used_model_name)}",
                "reviewer_model",
                "model_backed_completed",
            ],
            "approved": approve,
            "iteration_count": 3,
            "max_iterations": 3,
            "loop_status": "completed",
        }
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
        try:
            memory = self.context_manager.load_memory(session_id)
            state["memory_state"] = memory.to_dict()
            state["context_audit_records"] = [item.to_dict() for item in memory.lifecycle_audits[-5:]]
        except FileNotFoundError:
            pass
        state["resume_poll_iterations"] = poll_iterations
        state["resume_from_loop_status"] = last_session.latest_loop_status
        return state
