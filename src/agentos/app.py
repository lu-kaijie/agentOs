"""Top-level application bootstrap."""

from __future__ import annotations

import time
from dataclasses import dataclass
from collections.abc import Iterator

from langchain_core.messages import AIMessage, HumanMessage

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
        execution_mode: str = "",
        approval_response: str = "",
        state_override: dict[str, object] | None = None,
    ) -> dict[str, object]:
        state = self.runtime.run_task(
            task,
            session_id=session_id,
            approved=approve,
            max_iterations=max_iterations,
            execution_mode=execution_mode,
            approval_response=approval_response,
            state_override=state_override,
        )
        self.session_manager.record_turn(
            session_id=session_id,
            user_task=task,
            state=state,
            workspace_dir=str(self.settings.workspace_dir),
        )
        self._record_context_messages(session_id=session_id, user_task=task, state=state)
        return state

    def _record_context_messages(
        self,
        *,
        session_id: str,
        user_task: str,
        state: dict[str, object],
    ) -> None:
        try:
            messages = self.context_manager.load_session(session_id)
        except FileNotFoundError:
            messages = []
        final_output = self._context_assistant_output(state)
        if not final_output:
            final_output = str(state.get("last_result", "")).strip()
        messages = [
            *messages,
            HumanMessage(content=user_task),
            AIMessage(content=final_output or "(no response)"),
        ]
        self.context_manager.compact_messages(
            session_id,
            messages,
            max_chars=24000,
            keep_last=24,
        )

    def _context_assistant_output(self, state: dict[str, object]) -> str:
        step_outputs = [
            str(item).strip()
            for item in state.get("step_outputs", [])
            if str(item).strip()
        ]
        if step_outputs:
            return step_outputs[-1]
        return str(state.get("final_output", "")).strip()

    def run_graph_model_session_task(
        self,
        task: str,
        *,
        session_id: str,
        approve: bool = False,
        max_iterations: int = 5,
        state_override: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Run a model-backed task through the shared LangGraph loop."""

        return self.run_session_task(
            task,
            session_id=session_id,
            approve=approve,
            max_iterations=max_iterations,
            execution_mode="model",
            state_override=state_override,
        )

    def run_model_session_task(
        self,
        task: str,
        *,
        session_id: str,
        approve: bool = False,
        max_iterations: int = 5,
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
        state = {
            **prior_state,
            "user_task": task,
            "session_id": session_id,
            "pending_tasks": [task],
            "active_task": task,
            "background_results": list(prior_state.get("background_results", [])),
            "consumed_background_jobs": list(prior_state.get("consumed_background_jobs", [])),
            "next_pending_tasks": [],
            "approval_policy": {},
            "tool_results": list(prior_state.get("tool_results", [])),
            "context_bundle": {},
            "memory_state": dict(prior_state.get("memory_state", {})),
            "context_policy_records": list(prior_state.get("context_policy_records", [])),
            "context_audit_records": list(prior_state.get("context_audit_records", [])),
            "current_role": "",
            "role_records": list(prior_state.get("role_records", [])),
            "role_handoffs": list(prior_state.get("role_handoffs", [])),
            "last_result": "",
            "final_output": "",
            "loaded_knowledge": str(prior_state.get("loaded_knowledge", "")),
            "execution_trace": list(prior_state.get("execution_trace", [])),
            "approved": approve,
            "iteration_count": 0,
            "max_iterations": max_iterations,
            "loop_status": "initialized",
            "decision": {"action": "model_backed_turn", "mode": "langgraph-react"},
        }

        reviewer_bundle: dict[str, object] = {}
        memory = None
        follow_up_needed = False
        stagnant_iterations = 0
        last_planner_steps: list[str] = []
        last_executor_output = ""
        last_reviewer_summary = ""
        for iteration_index in range(1, max_iterations + 1):
            planner_bundle, planner_record, memory, planner_audit = self.context_manager.prepare_role_context(
                session_id=session_id,
                role="planner",
                task=task,
                state=state,
                workspace_dir=self.settings.workspace_dir,
                skill_mode="catalog",
                trigger_reason=(
                    "session_resume"
                    if iteration_index == 1 and prior_state.get("completed_tasks")
                    else "prepare_context"
                    if iteration_index == 1
                    else "role_handoff"
                ),
            )
            prepared_state = {
                **state,
                "memory_state": memory.to_dict(),
                "context_audit_records": state["context_audit_records"] + [planner_audit.to_dict()],
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
                "context_audit_records": prepared_state["context_audit_records"] + [executor_audit.to_dict()],
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
                tool_results=list(state.get("tool_results", [])),
                approved=approve,
            )
            used_model_name = str(result.get("model_name", self.settings.model_medium_name))

            iteration_role_records = [
                {
                    "role": "planner",
                    "task": task,
                    "summary": result["planner_summary"],
                    "status": "ok",
                    "metadata": {
                        "iteration": iteration_index,
                        "planned_steps": result["planner_steps"],
                    },
                },
                {
                    "role": "executor",
                    "task": task,
                    "summary": result["executor_output"],
                    "status": "ok",
                    "metadata": {
                        "iteration": iteration_index,
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
                        "iteration": iteration_index,
                        "follow_up_needed": result["reviewer_follow_up_needed"],
                    },
                },
            ]
            iteration_role_handoffs = [
                {
                    "source_role": "planner",
                    "target_role": "executor",
                    "task": task,
                    "summary": "Planner routed the real-model coding turn to executor tools.",
                    "context_sources": planner_bundle.get("sources", []),
                    "tool_result_refs": [],
                    "iteration": iteration_index,
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
                    "iteration": iteration_index,
                },
            ]
            final_output = result["executor_output"].strip()
            if result["reviewer_summary"]:
                final_output = (
                    f"{final_output}\n\n[reviewer]\n{result['reviewer_summary']}".strip()
                )

            follow_up_needed = bool(result["reviewer_follow_up_needed"])
            planner_steps = [str(item) for item in result["planner_steps"]]
            executor_output = str(result["executor_output"]).strip()
            reviewer_summary = str(result["reviewer_summary"]).strip()
            new_tool_results = list(result["tool_results"])
            made_progress = bool(new_tool_results) or any(
                (
                    planner_steps != last_planner_steps,
                    executor_output != last_executor_output,
                    reviewer_summary != last_reviewer_summary,
                )
            )
            stagnant_iterations = 0 if made_progress else stagnant_iterations + 1

            loop_status = "continue" if follow_up_needed and iteration_index < max_iterations else "completed"
            if follow_up_needed and iteration_index >= max_iterations:
                loop_status = "stopped:max_iterations"
            elif follow_up_needed and stagnant_iterations >= 1:
                loop_status = "stopped:no_progress"

            state = {
                **state,
                "pending_tasks": (
                    [task]
                    if follow_up_needed and loop_status == "continue"
                    else ([task] if loop_status == "stopped:max_iterations" else [])
                ),
                "active_task": task,
                "completed_tasks": state["completed_tasks"]
                + [
                    f"iteration:{iteration_index}:role:planner:{task}",
                    f"iteration:{iteration_index}:role:executor:{task}",
                    f"iteration:{iteration_index}:role:reviewer:{task}",
                ],
                "step_outputs": state["step_outputs"]
                + [
                    result["planner_summary"],
                    result["executor_output"],
                    result["reviewer_summary"],
                ],
                "tool_results": state["tool_results"] + list(result["tool_results"]),
                "context_bundle": reviewer_bundle,
                "memory_state": memory.to_dict(),
                "context_policy_records": state["context_policy_records"]
                + [
                    planner_record.to_dict(),
                    executor_record.to_dict(),
                    reviewer_record.to_dict(),
                ],
                "context_audit_records": state["context_audit_records"]
                + [
                    planner_audit.to_dict(),
                    executor_audit.to_dict(),
                    reviewer_audit.to_dict(),
                ],
                "current_role": "reviewer",
                "role_records": state["role_records"] + iteration_role_records,
                "role_handoffs": state["role_handoffs"] + iteration_role_handoffs,
                "last_result": result["reviewer_summary"],
                "final_output": final_output,
                "execution_trace": state["execution_trace"]
                + [
                    f"model_iteration={iteration_index}",
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
                    f"reviewer_follow_up={str(follow_up_needed).lower()}",
                    f"iteration_progress={str(made_progress).lower()}",
                    f"stagnant_iterations={stagnant_iterations}",
                    f"loop_status={loop_status}",
                ],
                "approved": approve,
                "iteration_count": iteration_index,
                "max_iterations": max_iterations,
                "loop_status": loop_status,
            }
            last_planner_steps = planner_steps
            last_executor_output = executor_output
            last_reviewer_summary = reviewer_summary
            if loop_status != "continue":
                break
        if state["loop_status"] == "completed":
            state["execution_trace"] = state["execution_trace"] + ["model_backed_completed"]
        elif state["loop_status"] == "stopped:max_iterations":
            state["execution_trace"] = state["execution_trace"] + ["model_backed_stopped:max_iterations"]
        elif state["loop_status"] == "stopped:no_progress":
            state["execution_trace"] = state["execution_trace"] + ["model_backed_stopped:no_progress"]
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
        execution_mode: str = "deterministic",
        approval_response: str = "",
        state_override: dict[str, object] | None = None,
    ) -> Iterator[dict[str, object]]:
        final_state: dict[str, object] | None = None
        for state in self.runtime.stream_task(
            task,
            session_id=session_id,
            approved=approve,
            max_iterations=max_iterations,
            execution_mode=execution_mode,
            approval_response=approval_response,
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
        execution_mode: str = "deterministic",
        approval_response: str = "",
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
        selected_execution_mode = execution_mode or str(state_override.get("execution_mode", "deterministic"))
        state = self.run_session_task(
            next_task,
            session_id=session_id,
            approve=approve,
            max_iterations=max_iterations,
            execution_mode=selected_execution_mode,
            approval_response=approval_response,
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

    def approve_pending_approval(self, session_id: str, *, max_iterations: int = 5) -> dict[str, object]:
        """Approve a persisted pending approval and resume execution."""

        state_override, previous_task = self.session_manager.build_resume_state(session_id)
        if not state_override.get("pending_approval"):
            raise ValueError(f"Session '{session_id}' has no pending approval")
        execution_mode = str(state_override.get("execution_mode", "deterministic"))
        return self.run_session_task(
            previous_task or "describe current status",
            session_id=session_id,
            approve=True,
            max_iterations=max_iterations,
            execution_mode=execution_mode,
            approval_response="approve",
            state_override=state_override,
        )

    def reject_pending_approval(self, session_id: str, *, max_iterations: int = 5) -> dict[str, object]:
        """Reject a persisted pending approval and resume execution."""

        state_override, previous_task = self.session_manager.build_resume_state(session_id)
        if not state_override.get("pending_approval"):
            raise ValueError(f"Session '{session_id}' has no pending approval")
        execution_mode = str(state_override.get("execution_mode", "deterministic"))
        return self.run_session_task(
            previous_task or "describe current status",
            session_id=session_id,
            approve=False,
            max_iterations=max_iterations,
            execution_mode=execution_mode,
            approval_response="reject",
            state_override=state_override,
        )
