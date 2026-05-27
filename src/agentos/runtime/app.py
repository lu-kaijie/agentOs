"""Runtime bootstrap and advanced LangGraph orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from agentos.config import Settings
from agentos.context import ContextManager
from agentos.execution_control import BackgroundExecutionManager
from agentos.harness.execution import CommandExecutor, ExecutionRequest
from agentos.knowledge import KnowledgeLoader
from agentos.policy import CommandApprovalPolicy
from agentos.runtime.roles import (
    ExecutorRoleAgent,
    PlannerRoleAgent,
    ReviewerRoleAgent,
    RoleInput,
)
from agentos.tools import ToolInvocation, ToolRegistry


class RuntimeDecision(BaseModel):
    """Structured runtime decision for graph routing."""

    action: Literal["run_command", "load_knowledge", "respond", "use_tool"] = Field(
        description="What the runtime should do next."
    )
    command: list[str] = Field(default_factory=list)
    topic: str = Field(default="")
    response: str = Field(default="")
    requires_approval: bool = Field(default=False)
    tool_name: str = Field(default="")
    tool_input: dict[str, object] = Field(default_factory=dict)


class GraphModelDecisionError(RuntimeError):
    """Error raised when graph-native model decisions cannot be parsed."""

    def __init__(self, message: str, *, debug_lines: list[str] | None = None):
        super().__init__(message)
        self.debug_lines = debug_lines or []


@dataclass(slots=True)
class GraphModelDecisionStrategy:
    """Produce one structured RuntimeDecision for a graph iteration."""

    settings: Settings
    tool_registry: ToolRegistry | None = None

    def decide(self, *, active_task: str, state: dict[str, object]) -> RuntimeDecision:
        if not self._is_configured():
            raise GraphModelDecisionError(
                "Graph-native model execution is not configured",
                debug_lines=[
                    "[debug] stage=graph_model_decide",
                    f"[debug] provider={self.settings.model_provider}",
                    f"[debug] model_enabled={self.settings.model_enabled}",
                    "[debug] missing=OPENAI_API_KEY",
                ],
            )
        model_name = self._model_name_for_level(self.settings.executor_model_level)
        prompt_messages = self._prompt_messages(active_task=active_task, state=state)
        model = self._build_chat_model(model_name)
        try:
            raw = model.bind_tools([RuntimeDecision], tool_choice="required").invoke(prompt_messages)
            return self._runtime_decision_from_tool_call(raw)
        except Exception as exc:
            raw_preview = self._message_content(locals().get("raw")) if "raw" in locals() else "<no model output>"
            raise GraphModelDecisionError(
                f"graph model decision failed: {exc}",
                debug_lines=[
                    "[debug] stage=graph_model_decide",
                    f"[debug] model={model_name}",
                    f"[debug] active_task={active_task}",
                    f"[debug] prompt_messages={len(prompt_messages)}",
                    f"[debug] prompt_chars={sum(len(self._message_content(message)) for message in prompt_messages)}",
                    f"[debug] raw_output={raw_preview[:600]}",
                    f"[debug] raw_type={type(locals().get('raw')).__name__ if 'raw' in locals() else 'none'}",
                    f"[debug] raw_repr={repr(locals().get('raw'))[:1000] if 'raw' in locals() else '<no model output>'}",
                    f"[debug] tool_calls={getattr(locals().get('raw'), 'tool_calls', None) if 'raw' in locals() else None}",
                    f"[debug] additional_kwargs={getattr(locals().get('raw'), 'additional_kwargs', None) if 'raw' in locals() else None}",
                    f"[debug] response_metadata={getattr(locals().get('raw'), 'response_metadata', None) if 'raw' in locals() else None}",
                ],
            ) from exc

    def _is_configured(self) -> bool:
        return bool(
            self.settings.model_enabled
            and self.settings.model_provider == "openai"
            and self.settings.openai_api_key
        )

    def _build_chat_model(self, model_name: str) -> ChatOpenAI:
        kwargs = {
            "model": model_name,
            "api_key": self.settings.openai_api_key,
            "temperature": 0,
        }
        if self.settings.openai_base_url:
            kwargs["base_url"] = self.settings.openai_base_url
        return ChatOpenAI(**kwargs)

    def _model_name_for_level(self, level: str) -> str:
        normalized = level.strip().lower()
        if normalized == "small":
            return self.settings.model_small_name
        if normalized == "large":
            return self.settings.model_large_name
        return self.settings.model_medium_name

    def _prompt_messages(self, *, active_task: str, state: dict[str, object]) -> list[object]:
        context_bundle = state.get("context_bundle", {})
        recent_tool_results = [
            item for item in state.get("tool_results", []) if isinstance(item, dict)
        ][-3:]
        tool_catalog = self._runtime_tool_catalog()
        recent_messages = self._recent_messages_preview(context_bundle)
        structured_memory = self._structured_memory_preview(context_bundle)
        return [
            SystemMessage(
                content=(
                    "You are the graph-native decision maker for agentOs. "
                    "Choose exactly one next action for the current iteration. "
                    "Call the RuntimeDecision tool exactly once; do not answer with plain text. "
                    "Prefer one tool call at a time. If enough information is available, respond. "
                    "Use action=use_tool for repository tools, action=run_command only for shell commands, "
                    "action=load_knowledge for knowledge topics, and action=respond for the final user-facing answer.\n\n"
                    "The available actions and tools are fixed by this runtime; do not infer availability from "
                    "empty history, empty prior tool results, or context text such as `tools=`. "
                    f"{tool_catalog}\n\n"
                    "Tool routing rules:\n"
                    "- To read files, call action=use_tool with tool_name=file_read and tool_input={\"path\":\"...\"}.\n"
                    "- To search the repository, call action=use_tool with tool_name=repo_search and tool_input={\"pattern\":\"...\"}.\n"
                    "- To run tests, call action=use_tool with tool_name=test_run and tool_input={\"command\":\"...\"}.\n"
                    "- To write files, call action=use_tool with tool_name=file_write.\n"
                    "- To patch files, call action=use_tool with tool_name=file_patch.\n"
                    "- To move or rename files, call action=run_command with command=[\"mv\", \"source\", \"dest\"]. "
                    "The runtime approval policy will pause before executing mutating commands.\n"
                    "- Do not use shell wrappers such as bash -c, bash -lc, sh -c, or zsh -c for file reads, searches, or tests."
                )
            ),
            HumanMessage(
                content=(
                    f"Active task:\n{active_task}\n\n"
                    f"Context bundle preview:\n{context_bundle.get('bundle_preview', '') if isinstance(context_bundle, dict) else ''}\n\n"
                    f"Structured memory:\n{structured_memory}\n\n"
                    f"Recent session messages:\n{recent_messages}\n\n"
                    f"Recent tool results:\n{json.dumps(recent_tool_results, ensure_ascii=False, sort_keys=True)}"
                )
            ),
        ]

    def _message_content(self, message: object) -> str:
        if message is None:
            return ""
        content = getattr(message, "content", message)
        return content if isinstance(content, str) else str(content)

    def _runtime_decision_from_tool_call(self, message: object) -> RuntimeDecision:
        tool_calls = getattr(message, "tool_calls", None) or []
        if not tool_calls:
            tool_calls = self._raw_openai_tool_calls(message)
        if not tool_calls:
            raise ValueError("model did not return a RuntimeDecision tool call")

        call = tool_calls[0]
        args: object
        if isinstance(call, dict):
            args = call.get("args")
            if args is None and isinstance(call.get("function"), dict):
                args = call["function"].get("arguments")
        else:
            args = getattr(call, "args", None)
        if isinstance(args, str):
            args = json.loads(args)
        if not isinstance(args, dict):
            raise ValueError("RuntimeDecision tool call arguments were not an object")
        return RuntimeDecision.model_validate(args)

    def _raw_openai_tool_calls(self, message: object) -> list[dict[str, object]]:
        additional_kwargs = getattr(message, "additional_kwargs", None)
        if not isinstance(additional_kwargs, dict):
            return []
        raw_calls = additional_kwargs.get("tool_calls")
        return raw_calls if isinstance(raw_calls, list) else []

    def _recent_messages_preview(self, context_bundle: object) -> str:
        if not isinstance(context_bundle, dict):
            return ""
        layered_memory = context_bundle.get("layered_memory", {})
        if not isinstance(layered_memory, dict):
            return ""
        messages = [
            item for item in layered_memory.get("recent_messages", []) if isinstance(item, dict)
        ][-6:]
        lines = []
        for item in messages:
            content = str(item.get("content", "")).strip().replace("\n", " ")
            if len(content) > 220:
                content = content[:217] + "..."
            lines.append(f"{item.get('type', 'message')}: {content}")
        return "\n".join(lines)

    def _structured_memory_preview(self, context_bundle: object) -> str:
        if not isinstance(context_bundle, dict):
            return ""
        layered_memory = context_bundle.get("layered_memory", {})
        if not isinstance(layered_memory, dict):
            return ""
        user_profile = self._dict_from_bundle(context_bundle, layered_memory, "user_profile")
        task_state = self._dict_from_bundle(context_bundle, layered_memory, "task_state")
        remembered_facts = self._list_from_bundle(context_bundle, layered_memory, "remembered_facts")
        working_memory = layered_memory.get("working_memory", {})

        lines: list[str] = []
        if user_profile:
            preferred_language = str(user_profile.get("preferred_language", "")).strip()
            response_style = [
                str(item).strip()
                for item in user_profile.get("response_style", [])
                if str(item).strip()
            ][:4]
            stable_preferences = [
                str(item).strip().replace("\n", " ")
                for item in user_profile.get("stable_preferences", [])
                if str(item).strip()
            ][-4:]
            profile_parts = []
            if preferred_language:
                profile_parts.append(f"preferred_language={preferred_language}")
            if response_style:
                profile_parts.append("response_style=" + ", ".join(response_style))
            if stable_preferences:
                profile_parts.append("stable_preferences=" + " | ".join(stable_preferences))
            if profile_parts:
                lines.append("User profile: " + "; ".join(profile_parts))

        active_facts = [
            item
            for item in remembered_facts
            if isinstance(item, dict)
            and str(item.get("status", "active")) == "active"
            and str(item.get("key", "")).strip()
            and str(item.get("value", "")).strip()
        ][-12:]
        if active_facts:
            lines.append("Remembered facts:")
            for item in active_facts:
                source = str(item.get("source_text") or item.get("source") or "").strip().replace("\n", " ")
                source_suffix = f" source={source[:160]}" if source else ""
                lines.append(f"- {item.get('key')}={item.get('value')}{source_suffix}")

        if task_state:
            current_goal = str(task_state.get("current_goal", "")).strip()
            open_questions = [
                str(item).strip().replace("\n", " ")
                for item in task_state.get("open_questions", [])
                if str(item).strip()
            ][-4:]
            completed = [
                str(item).strip().replace("\n", " ")
                for item in task_state.get("completed_actions", [])
                if str(item).strip()
            ][-4:]
            task_parts = []
            if current_goal:
                task_parts.append(f"current_goal={current_goal}")
            if completed:
                task_parts.append("completed=" + " | ".join(completed))
            if open_questions:
                task_parts.append("open_questions=" + " | ".join(open_questions))
            if task_parts:
                lines.append("Task state: " + "; ".join(task_parts))

        if not isinstance(working_memory, dict):
            return "\n".join(lines)
        constraints = [
            str(item).strip().replace("\n", " ")
            for item in working_memory.get("accepted_constraints", [])
            if str(item).strip()
        ][-12:]
        if constraints:
            lines.append("Legacy constraints:")
            lines.extend(f"- {fact}" for fact in constraints)
        return "\n".join(lines)

    def _dict_from_bundle(
        self,
        context_bundle: dict[str, object],
        layered_memory: dict[str, object],
        key: str,
    ) -> dict[str, object]:
        direct = context_bundle.get(key, {})
        if isinstance(direct, dict):
            return direct
        layered = layered_memory.get(key, {})
        return layered if isinstance(layered, dict) else {}

    def _list_from_bundle(
        self,
        context_bundle: dict[str, object],
        layered_memory: dict[str, object],
        key: str,
    ) -> list[object]:
        direct = context_bundle.get(key, [])
        if isinstance(direct, list):
            return direct
        layered = layered_memory.get(key, [])
        return layered if isinstance(layered, list) else []

    def _runtime_tool_catalog(self) -> str:
        if self.tool_registry is None:
            return "Available use_tool tool_name values: none. Available shell command action: run_command."

        tools = self.tool_registry.list_tools()
        use_tool_names = [
            item["name"]
            for item in tools
            if item["name"] not in {"shell_command", "knowledge_load"}
        ]
        lines = [
            "Registered ToolRegistry tools:",
            *[
                f"- {item['name']}: {item['description']}"
                for item in tools
            ],
            f"Available use_tool tool_name values: {', '.join(use_tool_names) or 'none'}.",
            "Use action=run_command for shell_command semantics.",
            "Use action=load_knowledge for knowledge_load semantics.",
        ]
        return "\n".join(lines)


class AgentGraphState(TypedDict):
    """Graph state for the advanced runtime.

    Fields:
    - user_task: the task given to the runtime
    - session_id: the persisted session id for this run
    - pending_tasks: queued runtime steps to process
    - active_task: the current step being processed
    - completed_tasks: ordered list of completed steps
    - step_outputs: ordered list of outputs emitted by each completed step
    - decision: structured routing result
    - execution_mode: deterministic or model-backed graph-native mode
    - background_results: completed async results waiting to influence runtime
    - consumed_background_jobs: background jobs already consumed in this session
    - next_pending_tasks: optional queue override produced by a node before finalize
    - approval_policy: inspectable approval policy output for command execution
    - pending_approval: resumable approval request for a blocked command
    - approval_response: optional user response for a pending approval
    - approval_outcome: last approval result for audit and session inspection
    - tool_results: structured tool results accumulated across loop steps
    - context_bundle: structured context prepared for the current decision step
    - memory_state: structured layered memory restored and maintained for the session
    - context_audit_records: inspectable lifecycle maintenance and budget audit records
    - current_role: active workflow role for the current step
    - role_records: inspectable planner / executor / reviewer records
    - last_result: summarized tool execution result for the current run
    - final_output: the final assistant-facing text
    - loaded_knowledge: knowledge content loaded on demand
    - execution_trace: ordered trace of visited runtime stages
    - approved: whether command execution has been approved
    - iteration_count: number of completed loop iterations
    - max_iterations: bounded loop limit
    - loop_status: human-readable loop state
    """

    user_task: str
    session_id: str
    pending_tasks: list[str]
    active_task: str
    completed_tasks: list[str]
    step_outputs: list[str]
    decision: dict[str, object]
    execution_mode: str
    background_results: list[dict[str, object]]
    consumed_background_jobs: list[str]
    next_pending_tasks: list[str]
    approval_policy: dict[str, object]
    pending_approval: dict[str, object]
    approval_response: str
    approval_outcome: dict[str, object]
    tool_results: list[dict[str, object]]
    context_bundle: dict[str, object]
    memory_state: dict[str, object]
    context_policy_records: list[dict[str, object]]
    context_audit_records: list[dict[str, object]]
    current_role: str
    role_records: list[dict[str, object]]
    role_handoffs: list[dict[str, object]]
    last_result: str
    final_output: str
    loaded_knowledge: str
    execution_trace: list[str]
    approved: bool
    iteration_count: int
    max_iterations: int
    loop_status: str


@dataclass(slots=True)
class RuntimeBootstrap:
    """A LangGraph runtime shell with structured decisions and branching."""

    settings: Settings
    executor: CommandExecutor
    knowledge_loader: KnowledgeLoader
    background_manager: BackgroundExecutionManager
    approval_policy: CommandApprovalPolicy
    tool_registry: ToolRegistry
    context_manager: ContextManager
    graph: object

    def summary(self) -> dict[str, str]:
        """Expose runtime bootstrap information for CLI and tests."""

        return {
            "workspace_dir": str(self.settings.workspace_dir),
            "tasks_dir": str(self.settings.tasks_dir),
            "knowledge_dir": str(self.settings.knowledge_dir),
            "context_dir": str(self.settings.context_dir),
            "sessions_dir": str(self.settings.sessions_dir),
            "background_jobs_dir": str(self.settings.background_jobs_dir),
            "workspaces_dir": str(self.settings.workspaces_dir),
            "coordination_dir": str(self.settings.coordination_dir),
            "model_provider": self.settings.model_provider,
            "default_model_level": "medium",
            "runtime_status": "langgraph-advanced-ready",
            "executor": self.executor.__class__.__name__,
        }

    def run_task(
        self,
        user_task: str,
        *,
        session_id: str = "default",
        approved: bool = False,
        max_iterations: int = 5,
        execution_mode: str = "deterministic",
        approval_response: str = "",
        state_override: dict[str, object] | None = None,
    ) -> AgentGraphState:
        """Execute a task through the LangGraph workflow."""

        initial_state: AgentGraphState = {
            "user_task": user_task,
            "session_id": session_id,
            "pending_tasks": [],
            "active_task": "",
            "completed_tasks": [],
            "step_outputs": [],
            "decision": {},
            "execution_mode": execution_mode,
            "background_results": [],
            "consumed_background_jobs": [],
            "next_pending_tasks": [],
            "approval_policy": {},
            "pending_approval": {},
            "approval_response": approval_response,
            "approval_outcome": {},
            "last_result": "",
            "final_output": "",
            "loaded_knowledge": "",
            "execution_trace": [],
            "approved": approved,
            "tool_results": [],
            "context_bundle": {},
            "memory_state": {},
            "context_policy_records": [],
            "context_audit_records": [],
            "current_role": "",
            "role_records": [],
            "role_handoffs": [],
            "iteration_count": 0,
            "max_iterations": max_iterations,
            "loop_status": "initialized",
        }
        if state_override:
            initial_state.update(state_override)
            initial_state["session_id"] = session_id
            initial_state["user_task"] = user_task
            initial_state["approved"] = approved
            initial_state["max_iterations"] = max_iterations
            initial_state["execution_mode"] = execution_mode
            initial_state["approval_response"] = approval_response
        return self.graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": session_id}},
        )

    def stream_task(
        self,
        user_task: str,
        *,
        session_id: str = "default",
        approved: bool = False,
        max_iterations: int = 5,
        execution_mode: str = "deterministic",
        approval_response: str = "",
        state_override: dict[str, object] | None = None,
    ):
        """Stream state updates for one task through the LangGraph workflow."""

        initial_state: AgentGraphState = {
            "user_task": user_task,
            "session_id": session_id,
            "pending_tasks": [],
            "active_task": "",
            "completed_tasks": [],
            "step_outputs": [],
            "decision": {},
            "execution_mode": execution_mode,
            "background_results": [],
            "consumed_background_jobs": [],
            "next_pending_tasks": [],
            "approval_policy": {},
            "pending_approval": {},
            "approval_response": approval_response,
            "approval_outcome": {},
            "last_result": "",
            "final_output": "",
            "loaded_knowledge": "",
            "execution_trace": [],
            "approved": approved,
            "tool_results": [],
            "context_bundle": {},
            "memory_state": {},
            "context_policy_records": [],
            "context_audit_records": [],
            "current_role": "",
            "role_records": [],
            "role_handoffs": [],
            "iteration_count": 0,
            "max_iterations": max_iterations,
            "loop_status": "initialized",
        }
        if state_override:
            initial_state.update(state_override)
            initial_state["session_id"] = session_id
            initial_state["user_task"] = user_task
            initial_state["approved"] = approved
            initial_state["max_iterations"] = max_iterations
            initial_state["execution_mode"] = execution_mode
            initial_state["approval_response"] = approval_response
        yield from self.graph.stream(
            initial_state,
            config={"configurable": {"thread_id": session_id}},
            stream_mode="values",
        )


def _build_graph(
    settings: Settings,
    executor: CommandExecutor,
    knowledge_loader: KnowledgeLoader,
    background_manager: BackgroundExecutionManager,
    approval_policy: CommandApprovalPolicy,
    tool_registry: ToolRegistry,
    context_manager: ContextManager,
):
    """Build the advanced LangGraph runtime."""

    decision_parser = PydanticOutputParser(pydantic_object=RuntimeDecision)
    decision_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a routing planner for agentOs.\n"
                "Return one structured decision.\n"
                "{format_instructions}",
            ),
            ("human", "{task}"),
        ]
    )
    graph_model_strategy = GraphModelDecisionStrategy(settings=settings, tool_registry=tool_registry)
    planner_agent = PlannerRoleAgent()
    executor_agent = ExecutorRoleAgent()
    reviewer_agent = ReviewerRoleAgent()

    def _role_input(state: AgentGraphState) -> RoleInput:
        return RoleInput(
            session_id=state["session_id"],
            role=(state["current_role"] or "executor"),  # type: ignore[arg-type]
            task=_unwrap_role_task(state["active_task"]),
            user_task=state["user_task"],
            context_bundle=state["context_bundle"],
            tool_results=[
                item for item in state.get("tool_results", []) if isinstance(item, dict)
            ],
            task_state={
                "pending_tasks": list(state.get("pending_tasks", [])),
                "completed_tasks": list(state.get("completed_tasks", [])),
                "iteration_count": int(state.get("iteration_count", 0)),
            },
        )

    def prepare_context(state: AgentGraphState) -> AgentGraphState:
        active_task = state["pending_tasks"][0]
        current_role = _role_for_task(active_task)
        bundle, policy_record, memory, audit = context_manager.prepare_role_context(
            session_id=state["session_id"],
            task=active_task,
            role=current_role,
            state=state,
            workspace_dir=settings.workspace_dir,
            trigger_reason="prepare_context" if state.get("iteration_count", 0) == 0 else "role_handoff",
        )
        return {
            **state,
            "active_task": active_task,
            "current_role": current_role,
            "context_bundle": bundle,
            "memory_state": memory.to_dict(),
            "context_policy_records": state["context_policy_records"] + [policy_record.to_dict()],
            "context_audit_records": state["context_audit_records"] + [audit.to_dict()],
            "execution_trace": state["execution_trace"]
            + [
                "prepare_context",
                f"role={current_role}",
                f"context_sources={','.join(bundle.get('sources', [])) or 'none'}",
                f"context_role_view={bundle.get('role_view', {}).get('focus', 'none')}",
                f"context_memory={bundle.get('memory_summary', '')}",
                f"context_task={active_task}",
            ],
            "loop_status": "context_ready",
        }

    def planner_role(state: AgentGraphState) -> AgentGraphState:
        role_input = _role_input(state)
        output = planner_agent.run(role_input)
        handoff = planner_agent.handoff_to(
            "executor",
            role_input,
            summary="Planner finished scoping executor work for the current coding turn.",
        )
        return {
            **state,
            "final_output": output.summary,
            "role_records": state["role_records"] + [output.to_dict()],
            "role_handoffs": state["role_handoffs"] + [handoff.to_dict()],
            "execution_trace": state["execution_trace"] + ["planner_role"],
            "loop_status": "step_executed",
        }

    def model_decide(state: AgentGraphState) -> AgentGraphState:
        active_task = state["pending_tasks"][0]
        prompt_messages = decision_prompt.format_messages(
            task=_render_task_with_context(active_task, state["context_bundle"]),
            format_instructions=decision_parser.get_format_instructions(),
        )
        used_model = _should_use_model_decision(state, active_task)
        if used_model:
            decision = graph_model_strategy.decide(active_task=active_task, state=state)
            raw_decision = decision.model_dump()
        else:
            raw_decision = _decide_from_task(active_task)
        policy_output: dict[str, object] = {}
        if raw_decision["action"] == "run_command":
            policy_decision = approval_policy.evaluate(list(raw_decision["command"]))
            raw_decision["requires_approval"] = policy_decision.requires_approval
            policy_output = policy_decision.to_dict()
        decision = decision_parser.parse(json.dumps(raw_decision))
        return {
            **state,
            "active_task": active_task,
            "decision": decision.model_dump(),
            "approval_policy": policy_output,
            "final_output": "",
            "execution_trace": state["execution_trace"]
            + [
                "model_decide",
                f"iteration={state['iteration_count'] + 1}",
                f"active_task={active_task}",
                f"prompt_messages={len(prompt_messages)}",
                f"decision_strategy={'model' if used_model else 'deterministic'}",
                f"action={decision.action}",
                (
                    f"approval_rule={policy_output.get('matched_rule', 'n/a')}"
                    if policy_output
                    else "approval_rule=n/a"
                ),
            ],
            "loop_status": "decision_ready",
        }

    def background_reentry(state: AgentGraphState) -> AgentGraphState:
        active_task = state["pending_tasks"][0]
        job_id = active_task.split(":", 1)[1]
        result = next(
            item for item in state["background_results"] if str(item["job_id"]) == job_id
        )
        follow_up_task = _background_follow_up(result)
        final_output = (
            f"Background job {job_id} completed with exit_code={result['exit_code']}."
        )
        if follow_up_task:
            final_output += f" Queued follow-up step: {follow_up_task}"
        next_pending_tasks = state["pending_tasks"][1:]
        if follow_up_task:
            next_pending_tasks = [follow_up_task, *next_pending_tasks]
        return {
            **state,
            "active_task": active_task,
            "next_pending_tasks": next_pending_tasks,
            "consumed_background_jobs": state["consumed_background_jobs"] + [job_id],
            "final_output": final_output,
            "execution_trace": state["execution_trace"]
            + [
                "background_reentry",
                f"job_id={job_id}",
                f"follow_up={follow_up_task or 'none'}",
            ],
            "loop_status": "background_reentered",
        }

    def approval_gate(state: AgentGraphState) -> AgentGraphState:
        decision = RuntimeDecision.model_validate(state["decision"])
        pending_approval = {
            "status": "waiting",
            "active_task": state["active_task"],
            "pending_tasks": list(state["pending_tasks"]),
            "decision": decision.model_dump(),
            "command": list(decision.command),
            "approval_policy": dict(state["approval_policy"]),
            "execution_mode": state.get("execution_mode", "deterministic"),
            "iteration_count": state.get("iteration_count", 0),
        }
        return {
            **state,
            "pending_approval": pending_approval,
            "approval_outcome": {},
            "final_output": (
                f"Approval required before executing command for step "
                f"`{state['active_task']}`: {decision.command}. "
                f"Policy reason: {state['approval_policy'].get('reason', 'unknown')}. "
                "Approve or reject the pending approval request to continue."
            ),
            "execution_trace": state["execution_trace"]
            + [
                "approval_gate",
                f"pending_approval_command={' '.join(decision.command)}",
                f"loop_stop=approval_required iteration={state['iteration_count'] + 1}",
            ],
            "loop_status": "waiting_approval",
        }

    def approve_pending(state: AgentGraphState) -> AgentGraphState:
        pending = dict(state.get("pending_approval", {}))
        if not pending:
            return {
                **state,
                "final_output": "No pending approval request exists.",
                "approval_outcome": {"status": "missing"},
                "execution_trace": state["execution_trace"] + ["approval_resume:missing"],
                "loop_status": "completed",
            }
        decision = dict(pending.get("decision", {}))
        pending_tasks = [str(item) for item in pending.get("pending_tasks", [])]
        active_task = str(pending.get("active_task", pending_tasks[0] if pending_tasks else state["user_task"]))
        return {
            **state,
            "pending_tasks": pending_tasks or [active_task],
            "active_task": active_task,
            "decision": decision,
            "approval_policy": dict(pending.get("approval_policy", {})),
            "pending_approval": {},
            "approval_response": "",
            "approval_outcome": {
                "status": "approved",
                "active_task": active_task,
                "command": list(pending.get("command", [])),
            },
            "approved": True,
            "execution_mode": str(pending.get("execution_mode", state.get("execution_mode", "deterministic"))),
            "execution_trace": state["execution_trace"] + ["approval_resume:approved"],
            "loop_status": "approval_approved",
        }

    def reject_pending(state: AgentGraphState) -> AgentGraphState:
        pending = dict(state.get("pending_approval", {}))
        if not pending:
            return {
                **state,
                "final_output": "No pending approval request exists.",
                "approval_outcome": {"status": "missing"},
                "execution_trace": state["execution_trace"] + ["approval_resume:missing"],
                "loop_status": "completed",
            }
        pending_tasks = [str(item) for item in pending.get("pending_tasks", [])]
        active_task = str(pending.get("active_task", pending_tasks[0] if pending_tasks else state["user_task"]))
        command = [str(item) for item in pending.get("command", [])]
        return {
            **state,
            "pending_tasks": pending_tasks or [active_task],
            "active_task": active_task,
            "decision": dict(pending.get("decision", {})),
            "approval_policy": dict(pending.get("approval_policy", {})),
            "pending_approval": {},
            "approval_response": "",
            "approval_outcome": {
                "status": "rejected",
                "active_task": active_task,
                "command": command,
            },
            "next_pending_tasks": pending_tasks[1:] if pending_tasks else [],
            "final_output": f"Approval rejected for command: {command}. Command was not executed.",
            "execution_trace": state["execution_trace"] + ["approval_resume:rejected"],
            "loop_status": "approval_rejected",
        }

    def tool_execute(state: AgentGraphState) -> AgentGraphState:
        role_input = _role_input(state)
        decision = RuntimeDecision.model_validate(state["decision"])
        if decision.action == "run_command":
            invocation = ToolInvocation(
                tool_name="shell_command",
                arguments={
                    "command": decision.command,
                    "cwd": str(settings.workspace_dir),
                    "_approved": state["approved"],
                },
            )
        elif decision.action == "load_knowledge":
            invocation = ToolInvocation(
                tool_name="knowledge_load",
                arguments={"topic": decision.topic},
            )
        else:
            invocation = ToolInvocation(
                tool_name=decision.tool_name,
                arguments={**decision.tool_input, "_approved": state["approved"]},
            )
        tool_result = tool_registry.invoke(invocation)
        payload = tool_result.payload
        if decision.action == "run_command":
            last_result = (
                f"command={payload.get('command', [])} exit_code={payload.get('exit_code')} "
                f"timed_out={payload.get('timed_out')}"
            )
            final_output = str(payload.get("stdout") or payload.get("stderr") or "(no output)")
        elif decision.action == "load_knowledge":
            last_result = tool_result.summary
            final_output = str(payload.get("content", ""))
        else:
            last_result = tool_result.summary
            final_output = _format_tool_payload(tool_result.to_dict())
        role_output = executor_agent.emit_result(
            role_input,
            summary=last_result,
            tool_name=tool_result.tool_name,
        )
        return {
            **state,
            "last_result": last_result,
            "final_output": final_output,
            "loaded_knowledge": (
                str(payload.get("content", state["loaded_knowledge"]))
                if decision.action == "load_knowledge" or tool_result.tool_name == "skill_load"
                else state["loaded_knowledge"]
            ),
            "tool_results": state["tool_results"] + [tool_result.to_dict()],
            "role_records": state["role_records"] + [role_output.to_dict()],
            "execution_trace": state["execution_trace"] + [f"tool_execute:{tool_result.tool_name}"],
            "pending_approval": {},
            "approved": False if state.get("approval_outcome", {}).get("status") == "approved" else state["approved"],
            "loop_status": "step_executed",
        }

    def respond_directly(state: AgentGraphState) -> AgentGraphState:
        role_input = _role_input(state)
        decision = RuntimeDecision.model_validate(state["decision"])
        role_output = executor_agent.emit_result(
            role_input,
            summary=decision.response,
        )
        return {
            **state,
            "final_output": decision.response,
            "role_records": state["role_records"] + [role_output.to_dict()],
            "execution_trace": state["execution_trace"] + ["respond_directly"],
            "loop_status": "step_executed",
        }

    def reviewer_role(state: AgentGraphState) -> AgentGraphState:
        role_input = _role_input(state)
        output = reviewer_agent.run(role_input)
        return {
            **state,
            "final_output": output.summary,
            "role_records": state["role_records"] + [output.to_dict()],
            "execution_trace": state["execution_trace"] + ["reviewer_role"],
            "loop_status": "step_executed",
        }

    def route_after_model(state: AgentGraphState) -> str:
        decision = RuntimeDecision.model_validate(state["decision"])
        if decision.action == "load_knowledge":
            return "tool_execute"
        if decision.action == "run_command":
            if decision.requires_approval and not state["approved"]:
                return "approval_gate"
            return "tool_execute"
        if decision.action == "use_tool":
            return "tool_execute"
        return "respond_directly"

    def route_after_prepare_context(state: AgentGraphState) -> str:
        if state["current_role"] == "planner":
            return "planner_role"
        if state["current_role"] == "reviewer":
            return "reviewer_role"
        return "model_decide"

    def initialize_loop(state: AgentGraphState) -> AgentGraphState:
        if state.get("pending_approval") and state.get("approval_response") in {"approve", "reject"}:
            return {
                **state,
                "execution_trace": state["execution_trace"]
                + [
                    "initialize_loop",
                    f"approval_response={state.get('approval_response')}",
                ],
                "loop_status": "approval_resume_ready",
            }
        if state.get("pending_approval"):
            return {
                **state,
                "execution_trace": state["execution_trace"]
                + [
                    "initialize_loop",
                    "pending_approval_waiting",
                ],
                "loop_status": "waiting_approval",
            }
        background_results = state["background_results"] or [
            result.to_dict() for result in background_manager.consume_completed(state["session_id"])
        ]
        reentry_tasks = [
            _background_task_name(str(result["job_id"])) for result in background_results
        ]
        if state["pending_tasks"]:
            pending_tasks = state["pending_tasks"]
        else:
            pending_tasks = [
                *reentry_tasks,
                *_skill_task_names(knowledge_loader, state["user_task"]),
                *_expand_user_task(state["user_task"]),
            ]
        return {
            **state,
            "background_results": background_results,
            "pending_tasks": pending_tasks,
            "execution_trace": state["execution_trace"]
            + [
                "initialize_loop",
                f"background_results_detected={len(background_results)}",
                f"planned_steps={len(pending_tasks)}",
                f"max_iterations={state['max_iterations']}",
            ],
            "loop_status": "ready",
        }

    def finalize_iteration(state: AgentGraphState) -> AgentGraphState:
        remaining_tasks = state["next_pending_tasks"] or state["pending_tasks"][1:]
        decision = RuntimeDecision.model_validate(state["decision"]) if state.get("decision") else None
        if (
            state.get("execution_mode") == "model"
            and not state.get("next_pending_tasks")
            and not state.get("approval_outcome", {}).get("status") == "rejected"
            and decision is not None
            and decision.action != "respond"
        ):
            remaining_tasks = [state["active_task"]]
        step_outputs = state["step_outputs"] + [state["final_output"]]
        completed_tasks = state["completed_tasks"] + [state["active_task"]]
        iteration_count = state["iteration_count"] + 1
        final_output = _compose_final_output(step_outputs)
        loop_status = _derive_loop_status(
            remaining_tasks=remaining_tasks,
            iteration_count=iteration_count,
            max_iterations=state["max_iterations"],
        )
        return {
            **state,
            "pending_tasks": remaining_tasks,
            "next_pending_tasks": [],
            "completed_tasks": completed_tasks,
            "step_outputs": step_outputs,
            "final_output": final_output,
            "iteration_count": iteration_count,
            "execution_trace": state["execution_trace"]
            + [
                "finalize_iteration",
                f"completed={state['active_task']}",
                f"remaining_steps={len(remaining_tasks)}",
                f"loop_status={loop_status}",
            ],
            "loop_status": loop_status,
        }

    def route_after_initialize(state: AgentGraphState) -> str:
        if state.get("pending_approval") and state.get("approval_response") == "approve":
            return "approve_pending"
        if state.get("pending_approval") and state.get("approval_response") == "reject":
            return "reject_pending"
        if state.get("pending_approval"):
            return END
        if not state["pending_tasks"]:
            return END
        if state["pending_tasks"][0].startswith("background_result:"):
            return "background_reentry"
        return "prepare_context"

    def route_after_finalize(state: AgentGraphState) -> str:
        if state["pending_tasks"] and state["iteration_count"] < state["max_iterations"]:
            if state["pending_tasks"][0].startswith("background_result:"):
                return "background_reentry"
            return "prepare_context"
        return END

    graph_builder = StateGraph(AgentGraphState)
    graph_builder.add_node("initialize_loop", initialize_loop)
    graph_builder.add_node("prepare_context", prepare_context)
    graph_builder.add_node("planner_role", planner_role)
    graph_builder.add_node("model_decide", model_decide)
    graph_builder.add_node("background_reentry", background_reentry)
    graph_builder.add_node("approval_gate", approval_gate)
    graph_builder.add_node("approve_pending", approve_pending)
    graph_builder.add_node("reject_pending", reject_pending)
    graph_builder.add_node("reviewer_role", reviewer_role)
    graph_builder.add_node("tool_execute", tool_execute)
    graph_builder.add_node("respond_directly", respond_directly)
    graph_builder.add_node("finalize_iteration", finalize_iteration)
    graph_builder.add_edge(START, "initialize_loop")
    graph_builder.add_conditional_edges("initialize_loop", route_after_initialize)
    graph_builder.add_conditional_edges("prepare_context", route_after_prepare_context)
    graph_builder.add_conditional_edges("model_decide", route_after_model)
    graph_builder.add_edge("approval_gate", END)
    graph_builder.add_edge("approve_pending", "tool_execute")
    graph_builder.add_edge("reject_pending", "finalize_iteration")
    graph_builder.add_edge("background_reentry", "finalize_iteration")
    graph_builder.add_edge("planner_role", "finalize_iteration")
    graph_builder.add_edge("reviewer_role", "finalize_iteration")
    graph_builder.add_edge("tool_execute", "finalize_iteration")
    graph_builder.add_edge("respond_directly", "finalize_iteration")
    graph_builder.add_conditional_edges("finalize_iteration", route_after_finalize)
    return graph_builder.compile(checkpointer=MemorySaver())


def _expand_user_task(user_task: str) -> list[str]:
    """Expand a user task into explicit loop steps when requested."""

    if user_task.startswith("code:"):
        raw_task = user_task.split(":", 1)[1].strip()
        executor_steps = _expand_coding_executor_steps(raw_task)
        return [
            _role_task_name("planner", raw_task),
            *executor_steps,
            _role_task_name("reviewer", raw_task),
        ]

    if user_task.startswith("steps:"):
        raw_steps = user_task.split(":", 1)[1]
        steps = [item.strip() for item in raw_steps.split("|") if item.strip()]
        if steps:
            return steps
    return [user_task]


def _background_task_name(job_id: str) -> str:
    """Build the synthetic task name used for background re-entry."""

    return f"background_result:{job_id}"


def _role_task_name(role: str, task: str) -> str:
    return f"role:{role}:{task}"


def _role_for_task(task: str) -> str:
    if task.startswith("role:planner:"):
        return "planner"
    if task.startswith("role:reviewer:"):
        return "reviewer"
    return "executor"


def _unwrap_role_task(task: str) -> str:
    if task.startswith("role:planner:"):
        return task.split(":", 2)[2].strip()
    if task.startswith("role:reviewer:"):
        return task.split(":", 2)[2].strip()
    return task


def _expand_coding_executor_steps(raw_task: str) -> list[str]:
    if raw_task.startswith("steps:"):
        raw_steps = raw_task.split(":", 1)[1]
        steps = [item.strip() for item in raw_steps.split("|") if item.strip()]
        if steps:
            return steps
    return [raw_task]


def _executor_steps_for_review(tasks: list[str]) -> list[str]:
    return [task for task in tasks if not task.startswith("role:")]


def _should_use_model_decision(state: dict[str, object], active_task: str) -> bool:
    return str(state.get("execution_mode", "deterministic")) == "model" and not _is_legacy_task(active_task)


def _is_legacy_task(task: str) -> bool:
    return task.strip().startswith(
        (
            "run:",
            "knowledge:",
            "search:",
            "read:",
            "write:",
            "patch:",
            "test:",
            "steps:",
            "code:",
            "skill:",
        )
    )


def _background_follow_up(result: dict[str, object]) -> str:
    """Translate a background result into a follow-up runtime step when possible."""

    stdout = str(result.get("stdout", "")).strip()
    if stdout.startswith("knowledge:"):
        topic = stdout.split(":", 1)[1].strip()
        if topic:
            return f"knowledge: {topic}"
    if stdout.startswith("run:"):
        command_text = stdout.split(":", 1)[1].strip()
        if command_text:
            return f"run: {command_text}"
    return ""


def _skill_task_names(knowledge_loader: KnowledgeLoader, user_task: str) -> list[str]:
    task = user_task.strip()
    if not task or task.startswith("skill:"):
        return []
    matches = knowledge_loader.match_skills(task)
    if not matches:
        return []
    return [f"skill: {match.name}" for match in matches[:2]]


def _compose_final_output(step_outputs: list[str]) -> str:
    """Build a stable user-facing output across loop iterations."""

    if not step_outputs:
        return ""
    if len(step_outputs) == 1:
        return step_outputs[0]
    return "\n\n".join(
        f"[step {index}] {output}" for index, output in enumerate(step_outputs, start=1)
    )


def _derive_loop_status(*, remaining_tasks: list[str], iteration_count: int, max_iterations: int) -> str:
    """Return an inspectable loop status string."""

    if remaining_tasks and iteration_count >= max_iterations:
        return "stopped:max_iterations"
    if remaining_tasks:
        return "continue"
    return "completed"


def _decide_from_task(user_task: str) -> dict[str, object]:
    """Create a deterministic structured decision for this milestone."""

    if user_task.startswith("knowledge:"):
        topic = user_task.split(":", 1)[1].strip()
        return {
            "action": "load_knowledge",
            "topic": topic,
            "response": "",
            "command": [],
            "requires_approval": False,
        }

    if user_task.startswith("run:"):
        command_text = user_task.split(":", 1)[1].strip()
        command = command_text.split() if command_text else []
        return {
            "action": "run_command",
            "topic": "",
            "response": "",
            "command": command,
            "requires_approval": False,
            "tool_name": "",
            "tool_input": {},
        }

    if user_task.startswith("search:"):
        pattern = user_task.split(":", 1)[1].strip()
        return {
            "action": "use_tool",
            "topic": "",
            "response": "",
            "command": [],
            "requires_approval": False,
            "tool_name": "repo_search",
            "tool_input": {"pattern": pattern},
        }

    if user_task.startswith("skill:"):
        payload = user_task.split(":", 1)[1].strip()
        name, _, remainder = payload.partition("#")
        level = "summary"
        target = ""
        if remainder == "full":
            level = "full"
        elif remainder.startswith("ref:"):
            level = "reference"
            target = remainder.split(":", 1)[1].strip()
        elif remainder.startswith("script:"):
            level = "script"
            target = remainder.split(":", 1)[1].strip()
        return {
            "action": "use_tool",
            "topic": "",
            "response": "",
            "command": [],
            "requires_approval": False,
            "tool_name": "skill_load",
            "tool_input": {"name": name.strip(), "level": level, "target": target},
        }

    if user_task.startswith("read:"):
        path = user_task.split(":", 1)[1].strip()
        return {
            "action": "use_tool",
            "topic": "",
            "response": "",
            "command": [],
            "requires_approval": False,
            "tool_name": "file_read",
            "tool_input": {"path": path},
        }

    if user_task.startswith("write:"):
        raw_payload = user_task.split(":", 1)[1].strip()
        path, _, content = raw_payload.partition("=>")
        return {
            "action": "use_tool",
            "topic": "",
            "response": "",
            "command": [],
            "requires_approval": False,
            "tool_name": "file_write",
            "tool_input": {"path": path.strip(), "content": content.lstrip()},
        }

    if user_task.startswith("patch:"):
        raw_payload = user_task.split(":", 1)[1].strip()
        path, _, remainder = raw_payload.partition("=>")
        target, _, replacement = remainder.partition(">>")
        return {
            "action": "use_tool",
            "topic": "",
            "response": "",
            "command": [],
            "requires_approval": False,
            "tool_name": "file_patch",
            "tool_input": {
                "path": path.strip(),
                "target": target.strip(),
                "replacement": replacement.lstrip(),
            },
        }

    if user_task.startswith("test:"):
        command_text = user_task.split(":", 1)[1].strip()
        return {
            "action": "use_tool",
            "topic": "",
            "response": "",
            "command": [],
            "requires_approval": False,
            "tool_name": "test_run",
            "tool_input": {"command": command_text},
        }

    return {
        "action": "respond",
        "topic": "",
        "response": (
            "No tool or knowledge action selected. "
            "Use `run:`, `knowledge:`, `search:`, `read:`, `write:`, `patch:`, or `test:`."
        ),
        "command": [],
        "requires_approval": False,
        "tool_name": "",
        "tool_input": {},
    }


def build_runtime(
    settings: Settings,
    executor: CommandExecutor,
    knowledge_loader: KnowledgeLoader,
    background_manager: BackgroundExecutionManager,
    approval_policy: CommandApprovalPolicy,
    tool_registry: ToolRegistry,
    context_manager: ContextManager,
) -> RuntimeBootstrap:
    """Build the advanced LangGraph runtime shell."""

    graph = _build_graph(
        settings,
        executor,
        knowledge_loader,
        background_manager,
        approval_policy,
        tool_registry,
        context_manager,
    )
    return RuntimeBootstrap(
        settings=settings,
        executor=executor,
        knowledge_loader=knowledge_loader,
        background_manager=background_manager,
        approval_policy=approval_policy,
        tool_registry=tool_registry,
        context_manager=context_manager,
        graph=graph,
    )


def _format_tool_payload(tool_result: dict[str, object]) -> str:
    """Render a tool result payload into a compact readable string."""

    payload = tool_result.get("payload", {})
    return json.dumps(payload, indent=2, sort_keys=True)


def _render_task_with_context(task: str, context_bundle: dict[str, object]) -> str:
    """Inject a compact context preview into the model-facing task content."""

    if not context_bundle:
        return task
    preview = str(context_bundle.get("bundle_preview", "")).strip()
    if not preview:
        return task
    return f"{task}\n\nContext bundle:\n{preview}"
