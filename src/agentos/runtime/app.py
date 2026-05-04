"""Runtime bootstrap and LangGraph v1 orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from agentos.config import Settings
from agentos.harness.execution import CommandExecutor, ExecutionRequest


class AgentGraphState(TypedDict):
    """Minimal graph state for the first runtime.

    Fields:
    - user_task: the task given to the runtime
    - pending_command: the command selected by the model step, if any
    - last_result: summarized tool execution result for the current run
    - final_output: the final assistant-facing text
    """

    user_task: str
    pending_command: list[str]
    last_result: str
    final_output: str


@dataclass(slots=True)
class RuntimeBootstrap:
    """A thin runtime shell backed by a minimal LangGraph workflow."""

    settings: Settings
    executor: CommandExecutor
    graph: object

    def summary(self) -> dict[str, str]:
        """Expose runtime bootstrap information for CLI and tests."""

        return {
            "workspace_dir": str(self.settings.workspace_dir),
            "tasks_dir": str(self.settings.tasks_dir),
            "knowledge_dir": str(self.settings.knowledge_dir),
            "context_dir": str(self.settings.context_dir),
            "model_provider": self.settings.model_provider,
            "model_name": self.settings.model_name,
            "runtime_status": "langgraph-v1-ready",
            "executor": self.executor.__class__.__name__,
        }

    def run_task(self, user_task: str) -> AgentGraphState:
        """Execute a task through the LangGraph workflow."""

        initial_state: AgentGraphState = {
            "user_task": user_task,
            "pending_command": [],
            "last_result": "",
            "final_output": "",
        }
        return self.graph.invoke(initial_state)


def _parse_command(user_task: str) -> list[str]:
    """Convert a minimal task string into a command list.

    Supported form:
    - `run: pwd`
    - `run: ls -al`
    """

    if not user_task.startswith("run:"):
        return []

    command_text = user_task.split(":", 1)[1].strip()
    if not command_text:
        return []
    return command_text.split()


def _build_graph(settings: Settings, executor: CommandExecutor):
    """Build the first LangGraph runtime.

    The graph has two explicit runtime stages:
    - `model_decide`: decide whether to call a tool
    - `tool_execute`: call the harness executor
    """

    def model_decide(state: AgentGraphState) -> AgentGraphState:
        pending_command = _parse_command(state["user_task"])
        if pending_command:
            return {
                **state,
                "pending_command": pending_command,
                "final_output": "",
            }

        return {
            **state,
            "pending_command": [],
            "final_output": (
                "No tool call selected. Use the format `run: <command>` "
                "to execute a command through the harness."
            ),
        }

    def tool_execute(state: AgentGraphState) -> AgentGraphState:
        request = ExecutionRequest(
            command=state["pending_command"],
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
            "pending_command": [],
        }

    def route_after_model(state: AgentGraphState) -> str:
        return "tool_execute" if state["pending_command"] else END

    graph_builder = StateGraph(AgentGraphState)
    graph_builder.add_node("model_decide", model_decide)
    graph_builder.add_node("tool_execute", tool_execute)
    graph_builder.add_edge(START, "model_decide")
    graph_builder.add_conditional_edges("model_decide", route_after_model)
    graph_builder.add_edge("tool_execute", END)
    return graph_builder.compile()


def build_runtime(settings: Settings, executor: CommandExecutor) -> RuntimeBootstrap:
    """Build the LangGraph v1 runtime shell."""

    graph = _build_graph(settings, executor)
    return RuntimeBootstrap(settings=settings, executor=executor, graph=graph)
