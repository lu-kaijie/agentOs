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
from agentos.harness.execution import CommandExecutor, ExecutionRequest
from agentos.knowledge import KnowledgeLoader


class RuntimeDecision(BaseModel):
    """Structured runtime decision for graph routing."""

    action: Literal["run_command", "load_knowledge", "respond"] = Field(
        description="What the runtime should do next."
    )
    command: list[str] = Field(default_factory=list)
    topic: str = Field(default="")
    response: str = Field(default="")
    requires_approval: bool = Field(default=False)


class AgentGraphState(TypedDict):
    """Graph state for the advanced runtime.

    Fields:
    - user_task: the task given to the runtime
    - decision: structured routing result
    - last_result: summarized tool execution result for the current run
    - final_output: the final assistant-facing text
    - loaded_knowledge: knowledge content loaded on demand
    - execution_trace: ordered trace of visited runtime stages
    - approved: whether command execution has been approved
    """

    user_task: str
    decision: dict[str, object]
    last_result: str
    final_output: str
    loaded_knowledge: str
    execution_trace: list[str]
    approved: bool


@dataclass(slots=True)
class RuntimeBootstrap:
    """A LangGraph runtime shell with structured decisions and branching."""

    settings: Settings
    executor: CommandExecutor
    knowledge_loader: KnowledgeLoader
    graph: object

    def summary(self) -> dict[str, str]:
        """Expose runtime bootstrap information for CLI and tests."""

        return {
            "workspace_dir": str(self.settings.workspace_dir),
            "tasks_dir": str(self.settings.tasks_dir),
            "knowledge_dir": str(self.settings.knowledge_dir),
            "context_dir": str(self.settings.context_dir),
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
    ) -> AgentGraphState:
        """Execute a task through the LangGraph workflow."""

        initial_state: AgentGraphState = {
            "user_task": user_task,
            "decision": {},
            "last_result": "",
            "final_output": "",
            "loaded_knowledge": "",
            "execution_trace": [],
            "approved": approved,
        }
        return self.graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": session_id}},
        )


def _build_graph(
    settings: Settings,
    executor: CommandExecutor,
    knowledge_loader: KnowledgeLoader,
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

    def model_decide(state: AgentGraphState) -> AgentGraphState:
        prompt_messages = decision_prompt.format_messages(
            task=state["user_task"],
            format_instructions=decision_parser.get_format_instructions(),
        )
        raw_decision = _decide_from_task(state["user_task"])
        decision = decision_parser.parse(json.dumps(raw_decision))
        return {
            **state,
            "decision": decision.model_dump(),
            "final_output": "",
            "execution_trace": state["execution_trace"]
            + [
                "model_decide",
                f"prompt_messages={len(prompt_messages)}",
                f"action={decision.action}",
            ],
        }

    def approval_gate(state: AgentGraphState) -> AgentGraphState:
        decision = RuntimeDecision.model_validate(state["decision"])
        return {
            **state,
            "final_output": (
                f"Approval required before executing command: {decision.command}. "
                "Re-run with --approve to continue."
            ),
            "execution_trace": state["execution_trace"] + ["approval_gate"],
        }

    def tool_execute(state: AgentGraphState) -> AgentGraphState:
        decision = RuntimeDecision.model_validate(state["decision"])
        request = ExecutionRequest(
            command=decision.command,
            cwd=str(settings.workspace_dir),
        )
        result = executor.run(request)
        last_result = (
            f"command={result.command} exit_code={result.exit_code} "
            f"timed_out={result.timed_out}"
        )
        final_output = result.stdout.strip() or result.stderr.strip() or "(no output)"
        return {
            **state,
            "last_result": last_result,
            "final_output": final_output,
            "execution_trace": state["execution_trace"] + ["tool_execute"],
        }

    def knowledge_execute(state: AgentGraphState) -> AgentGraphState:
        decision = RuntimeDecision.model_validate(state["decision"])
        message = knowledge_loader.load_topic(decision.topic)
        return {
            **state,
            "loaded_knowledge": message.content,
            "final_output": message.content,
            "execution_trace": state["execution_trace"] + ["knowledge_execute"],
        }

    def respond_directly(state: AgentGraphState) -> AgentGraphState:
        decision = RuntimeDecision.model_validate(state["decision"])
        return {
            **state,
            "final_output": decision.response,
            "execution_trace": state["execution_trace"] + ["respond_directly"],
        }

    def route_after_model(state: AgentGraphState) -> str:
        decision = RuntimeDecision.model_validate(state["decision"])
        if decision.action == "load_knowledge":
            return "knowledge_execute"
        if decision.action == "run_command":
            if decision.requires_approval and not state["approved"]:
                return "approval_gate"
            return "tool_execute"
        return "respond_directly"

    graph_builder = StateGraph(AgentGraphState)
    graph_builder.add_node("model_decide", model_decide)
    graph_builder.add_node("approval_gate", approval_gate)
    graph_builder.add_node("tool_execute", tool_execute)
    graph_builder.add_node("knowledge_execute", knowledge_execute)
    graph_builder.add_node("respond_directly", respond_directly)
    graph_builder.add_edge(START, "model_decide")
    graph_builder.add_conditional_edges("model_decide", route_after_model)
    graph_builder.add_edge("approval_gate", END)
    graph_builder.add_edge("tool_execute", END)
    graph_builder.add_edge("knowledge_execute", END)
    graph_builder.add_edge("respond_directly", END)
    return graph_builder.compile(checkpointer=MemorySaver())


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
        dangerous = any(token in {"rm", "mv", "sudo"} for token in command)
        return {
            "action": "run_command",
            "topic": "",
            "response": "",
            "command": command,
            "requires_approval": dangerous,
        }

    return {
        "action": "respond",
        "topic": "",
        "response": (
            "No tool or knowledge action selected. "
            "Use `run: <command>` or `knowledge: <topic>`."
        ),
        "command": [],
        "requires_approval": False,
    }


def build_runtime(
    settings: Settings,
    executor: CommandExecutor,
    knowledge_loader: KnowledgeLoader,
) -> RuntimeBootstrap:
    """Build the advanced LangGraph runtime shell."""

    graph = _build_graph(settings, executor, knowledge_loader)
    return RuntimeBootstrap(
        settings=settings,
        executor=executor,
        knowledge_loader=knowledge_loader,
        graph=graph,
    )
