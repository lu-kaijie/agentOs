"""Bounded role-agent abstractions for the agent runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


RoleName = Literal["planner", "executor", "reviewer"]


@dataclass(slots=True)
class RoleInput:
    """Structured input delivered to one role agent."""

    session_id: str
    role: RoleName
    task: str
    user_task: str
    context_bundle: dict[str, object]
    tool_results: list[dict[str, object]] = field(default_factory=list)
    task_state: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class RoleOutput:
    """Structured output emitted by one role agent."""

    role: RoleName
    task: str
    summary: str
    status: str = "ok"
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class RoleHandoff:
    """Persistent explanation for role transitions."""

    source_role: RoleName
    target_role: RoleName
    task: str
    summary: str
    context_sources: list[str] = field(default_factory=list)
    tool_result_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class RoleAgent:
    """Shared protocol for bounded built-in role agents."""

    role: RoleName

    def run(self, role_input: RoleInput) -> RoleOutput:
        raise NotImplementedError

    def handoff_to(
        self,
        target_role: RoleName,
        role_input: RoleInput,
        *,
        summary: str,
    ) -> RoleHandoff:
        refs = [
            str(item.get("tool_name", "unknown"))
            for item in role_input.tool_results[-3:]
            if isinstance(item, dict)
        ]
        return RoleHandoff(
            source_role=self.role,
            target_role=target_role,
            task=role_input.task,
            summary=summary,
            context_sources=[
                str(item) for item in role_input.context_bundle.get("sources", [])
            ],
            tool_result_refs=refs,
        )


class PlannerRoleAgent(RoleAgent):
    role: RoleName = "planner"

    def run(self, role_input: RoleInput) -> RoleOutput:
        pending_steps = [
            str(item) for item in role_input.task_state.get("pending_tasks", [])
        ]
        planned_steps = [
            step
            for step in pending_steps
            if not step.startswith("role:planner:")
            and not step.startswith("role:reviewer:")
        ]
        summary = (
            f"Planner prepared {len(planned_steps)} executor step(s): "
            + ", ".join(planned_steps[:4])
        )
        return RoleOutput(
            role=self.role,
            task=role_input.task,
            summary=summary,
            metadata={
                "planned_steps": planned_steps,
                "context_sources": role_input.context_bundle.get("sources", []),
                "tool_result_count": len(role_input.tool_results),
            },
        )


class ExecutorRoleAgent(RoleAgent):
    role: RoleName = "executor"

    def run(self, role_input: RoleInput) -> RoleOutput:
        return RoleOutput(
            role=self.role,
            task=role_input.task,
            summary=f"Executor processed `{role_input.task}`.",
            metadata={
                "context_sources": role_input.context_bundle.get("sources", []),
                "tool_result_count": len(role_input.tool_results),
            },
        )

    def emit_result(
        self,
        role_input: RoleInput,
        *,
        summary: str,
        tool_name: str = "",
        extra: dict[str, object] | None = None,
    ) -> RoleOutput:
        metadata = {
            "context_sources": role_input.context_bundle.get("sources", []),
            "tool_result_count": len(role_input.tool_results),
        }
        if tool_name:
            metadata["tool_name"] = tool_name
        if extra:
            metadata.update(extra)
        return RoleOutput(
            role=self.role,
            task=role_input.task,
            summary=summary,
            metadata=metadata,
        )


class ReviewerRoleAgent(RoleAgent):
    role: RoleName = "reviewer"

    def run(self, role_input: RoleInput) -> RoleOutput:
        relevant_results = role_input.tool_results[-5:]
        failed_tools = [
            str(result.get("tool_name", "unknown"))
            for result in relevant_results
            if isinstance(result, dict)
            and isinstance(result.get("payload"), dict)
            and result["payload"].get("exit_code") not in (None, 0)
        ]
        if failed_tools:
            verdict = f"Reviewer found issues in tool results: {', '.join(failed_tools)}."
        else:
            verdict = "Reviewer accepted the executor outputs."
        summary = (
            f"{verdict} Reviewed {len(relevant_results)} recent tool result(s) "
            f"for task `{role_input.task}`."
        )
        return RoleOutput(
            role=self.role,
            task=role_input.task,
            summary=summary,
            metadata={
                "reviewed_tool_count": len(relevant_results),
                "failed_tools": failed_tools,
                "context_sources": role_input.context_bundle.get("sources", []),
            },
        )
