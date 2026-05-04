"""Runtime bootstrap and advanced LangGraph orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal, TypedDict

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from agentos.config import Settings
from agentos.context import ContextManager
from agentos.execution_control import BackgroundExecutionManager
from agentos.harness.execution import CommandExecutor, ExecutionRequest
from agentos.knowledge import KnowledgeLoader
from agentos.policy import CommandApprovalPolicy
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
    - background_results: completed async results waiting to influence runtime
    - consumed_background_jobs: background jobs already consumed in this session
    - next_pending_tasks: optional queue override produced by a node before finalize
    - approval_policy: inspectable approval policy output for command execution
    - tool_results: structured tool results accumulated across loop steps
    - context_bundle: structured context prepared for the current decision step
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
    background_results: list[dict[str, object]]
    consumed_background_jobs: list[str]
    next_pending_tasks: list[str]
    approval_policy: dict[str, object]
    tool_results: list[dict[str, object]]
    context_bundle: dict[str, object]
    current_role: str
    role_records: list[dict[str, object]]
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
            "model_name": self.settings.model_name,
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
            "background_results": [],
            "consumed_background_jobs": [],
            "next_pending_tasks": [],
            "approval_policy": {},
            "last_result": "",
            "final_output": "",
            "loaded_knowledge": "",
            "execution_trace": [],
            "approved": approved,
            "tool_results": [],
            "context_bundle": {},
            "current_role": "",
            "role_records": [],
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
            "background_results": [],
            "consumed_background_jobs": [],
            "next_pending_tasks": [],
            "approval_policy": {},
            "last_result": "",
            "final_output": "",
            "loaded_knowledge": "",
            "execution_trace": [],
            "approved": approved,
            "tool_results": [],
            "context_bundle": {},
            "current_role": "",
            "role_records": [],
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

    def prepare_context(state: AgentGraphState) -> AgentGraphState:
        active_task = state["pending_tasks"][0]
        current_role = _role_for_task(active_task)
        bundle = context_manager.build_context_bundle(
            session_id=state["session_id"],
            task=active_task,
            state=state,
            workspace_dir=settings.workspace_dir,
        )
        return {
            **state,
            "active_task": active_task,
            "current_role": current_role,
            "context_bundle": bundle,
            "execution_trace": state["execution_trace"]
            + [
                "prepare_context",
                f"role={current_role}",
                f"context_sources={','.join(bundle.get('sources', [])) or 'none'}",
                f"context_task={active_task}",
            ],
            "loop_status": "context_ready",
        }

    def planner_role(state: AgentGraphState) -> AgentGraphState:
        task = _unwrap_role_task(state["active_task"])
        planned_steps = _executor_steps_for_review(state["pending_tasks"][1:])
        output = (
            f"Planner prepared {len(planned_steps)} executor step(s): "
            + ", ".join(planned_steps[:4])
        )
        record = {
            "role": "planner",
            "task": task,
            "summary": output,
            "planned_steps": planned_steps,
            "context_sources": state["context_bundle"].get("sources", []),
            "tool_result_count": len(state["tool_results"]),
        }
        return {
            **state,
            "final_output": output,
            "role_records": state["role_records"] + [record],
            "execution_trace": state["execution_trace"] + ["planner_role"],
            "loop_status": "step_executed",
        }

    def model_decide(state: AgentGraphState) -> AgentGraphState:
        active_task = state["pending_tasks"][0]
        prompt_messages = decision_prompt.format_messages(
            task=_render_task_with_context(active_task, state["context_bundle"]),
            format_instructions=decision_parser.get_format_instructions(),
        )
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
        return {
            **state,
            "final_output": (
                f"Approval required before executing command for step "
                f"`{state['active_task']}`: {decision.command}. "
                f"Policy reason: {state['approval_policy'].get('reason', 'unknown')}. "
                "Re-run with --approve to continue."
            ),
            "execution_trace": state["execution_trace"]
            + [
                "approval_gate",
                f"loop_stop=approval_required iteration={state['iteration_count'] + 1}",
            ],
            "loop_status": "waiting_approval",
        }

    def tool_execute(state: AgentGraphState) -> AgentGraphState:
        decision = RuntimeDecision.model_validate(state["decision"])
        if decision.action == "run_command":
            invocation = ToolInvocation(
                tool_name="shell_command",
                arguments={"command": decision.command, "cwd": str(settings.workspace_dir)},
            )
        elif decision.action == "load_knowledge":
            invocation = ToolInvocation(
                tool_name="knowledge_load",
                arguments={"topic": decision.topic},
            )
        else:
            invocation = ToolInvocation(
                tool_name=decision.tool_name,
                arguments=decision.tool_input,
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
        return {
            **state,
            "last_result": last_result,
            "final_output": final_output,
            "loaded_knowledge": str(payload.get("content", state["loaded_knowledge"]))
            if decision.action == "load_knowledge"
            else state["loaded_knowledge"],
            "tool_results": state["tool_results"] + [tool_result.to_dict()],
            "role_records": state["role_records"]
            + [
                {
                    "role": state["current_role"] or "executor",
                    "task": state["active_task"],
                    "summary": last_result,
                    "tool_name": tool_result.tool_name,
                    "context_sources": state["context_bundle"].get("sources", []),
                }
            ],
            "execution_trace": state["execution_trace"] + [f"tool_execute:{tool_result.tool_name}"],
            "loop_status": "step_executed",
        }

    def respond_directly(state: AgentGraphState) -> AgentGraphState:
        decision = RuntimeDecision.model_validate(state["decision"])
        return {
            **state,
            "final_output": decision.response,
            "role_records": state["role_records"]
            + [
                {
                    "role": state["current_role"] or "executor",
                    "task": state["active_task"],
                    "summary": decision.response,
                    "context_sources": state["context_bundle"].get("sources", []),
                }
            ],
            "execution_trace": state["execution_trace"] + ["respond_directly"],
            "loop_status": "step_executed",
        }

    def reviewer_role(state: AgentGraphState) -> AgentGraphState:
        task = _unwrap_role_task(state["active_task"])
        relevant_results = state["tool_results"][-5:]
        failed_tools = [
            result["tool_name"]
            for result in relevant_results
            if isinstance(result, dict)
            and isinstance(result.get("payload"), dict)
            and result["payload"].get("exit_code") not in (None, 0)
        ]
        if failed_tools:
            verdict = f"Reviewer found issues in tool results: {', '.join(failed_tools)}."
        else:
            verdict = "Reviewer accepted the executor outputs."
        output = (
            f"{verdict} "
            f"Reviewed {len(relevant_results)} recent tool result(s) for task `{task}`."
        )
        record = {
            "role": "reviewer",
            "task": task,
            "summary": output,
            "reviewed_tool_count": len(relevant_results),
            "failed_tools": failed_tools,
            "context_sources": state["context_bundle"].get("sources", []),
        }
        return {
            **state,
            "final_output": output,
            "role_records": state["role_records"] + [record],
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
        background_results = state["background_results"] or [
            result.to_dict() for result in background_manager.consume_completed(state["session_id"])
        ]
        reentry_tasks = [
            _background_task_name(str(result["job_id"])) for result in background_results
        ]
        pending_tasks = state["pending_tasks"] or [
            *reentry_tasks,
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
    graph_builder.add_node("reviewer_role", reviewer_role)
    graph_builder.add_node("tool_execute", tool_execute)
    graph_builder.add_node("respond_directly", respond_directly)
    graph_builder.add_node("finalize_iteration", finalize_iteration)
    graph_builder.add_edge(START, "initialize_loop")
    graph_builder.add_conditional_edges("initialize_loop", route_after_initialize)
    graph_builder.add_conditional_edges("prepare_context", route_after_prepare_context)
    graph_builder.add_conditional_edges("model_decide", route_after_model)
    graph_builder.add_edge("approval_gate", END)
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
