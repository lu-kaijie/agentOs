"""Real model-backed bounded agent workflow built on LangChain/LangGraph."""

from __future__ import annotations

from dataclasses import dataclass
import re

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from agentos.config import Settings
from agentos.context import ContextManager
from agentos.runtime.roles import PlannerRoleAgent, ReviewerRoleAgent, RoleInput
from agentos.tools import ToolRegistry
from agentos.tools.registry import tool_runtime_context


class ModelBackedRuntimeError(RuntimeError):
    """Runtime error that carries model-facing debug context."""

    def __init__(self, message: str, *, debug_lines: list[str] | None = None):
        super().__init__(message)
        self.debug_lines = debug_lines or []


class PlannerPlan(BaseModel):
    summary: str = Field(description="Short plan summary for this coding turn.")
    steps: list[str] = Field(default_factory=list, description="High-level execution steps.")


class ReviewerVerdict(BaseModel):
    summary: str = Field(description="Short reviewer verdict.")
    follow_up_needed: bool = Field(description="Whether more work appears necessary.")


@dataclass(slots=True)
class ModelBackedAgentRuntime:
    """Bounded real-model workflow for shell and one-shot runs."""

    settings: Settings
    tool_registry: ToolRegistry
    context_manager: ContextManager

    def is_configured(self) -> bool:
        return bool(
            self.settings.model_enabled
            and self.settings.model_provider == "openai"
            and self.settings.openai_api_key
        )

    def build_chat_model(self) -> ChatOpenAI:
        return self.build_chat_model_for(self.settings.model_medium_name)

    def build_chat_model_for(self, model_name: str) -> ChatOpenAI:
        kwargs = {
            "model": model_name,
            "api_key": self.settings.openai_api_key,
            "temperature": 0,
        }
        if self.settings.openai_base_url:
            kwargs["base_url"] = self.settings.openai_base_url
        return ChatOpenAI(**kwargs)

    def model_name_for_level(self, level: str) -> str:
        normalized = level.strip().lower()
        if normalized == "small":
            return self.settings.model_small_name
        if normalized == "large":
            return self.settings.model_large_name
        return self.settings.model_medium_name

    def model_name_for_role(self, role: str) -> str:
        normalized = role.strip().lower()
        if normalized == "planner":
            return self.model_name_for_level(self.settings.planner_model_level)
        if normalized == "reviewer":
            return self.model_name_for_level(self.settings.reviewer_model_level)
        return self.model_name_for_level(self.settings.executor_model_level)

    def run_turn(
        self,
        *,
        session_id: str,
        user_task: str,
        context_bundles: dict[str, dict[str, object]],
        tool_results: list[dict[str, object]] | None = None,
        approved: bool = False,
    ) -> dict[str, object]:
        if not self.is_configured():
            raise RuntimeError("Model-backed runtime is not configured")

        prior_messages = self._load_prior_messages(session_id)
        planner_input = RoleInput(
            session_id=session_id,
            role="planner",
            task=user_task,
            user_task=user_task,
            context_bundle=context_bundles["planner"],
            tool_results=tool_results or [],
            task_state={},
        )
        planner_agent = PlannerRoleAgent()
        planner_fallback = planner_agent.run(planner_input)
        planner_parser = PydanticOutputParser(pydantic_object=PlannerPlan)
        planner_model_name = self.model_name_for_role("planner")
        planner_model = self.build_chat_model_for(planner_model_name)
        planner_prompt = [
            SystemMessage(
                content=(
                    "You are the planner for agentOs. Produce a short scoped plan for one bounded coding turn. "
                    "Prefer repository search, file read/write/patch, and test execution tools when needed. "
                    "The context may include a compact skills catalog. Use it only to decide whether a skill may help. "
                    "Do not assume a skill's full contents until it is loaded. "
                    "Return JSON only."
                )
            ),
            HumanMessage(
                content=(
                    f"User task:\n{user_task}\n\n"
                    f"Context bundle:\n{context_bundles['planner'].get('bundle_preview', '')}\n\n"
                    f"{planner_parser.get_format_instructions()}"
                )
            ),
        ]
        try:
            planner_raw = planner_model.invoke(planner_prompt)
            planner_plan = self._parse_structured_response(planner_parser, planner_raw)
        except Exception as exc:
            planner_raw_text = self._safe_message_content(locals().get("planner_raw"))
            raise ModelBackedRuntimeError(
                f"planner stage failed: {exc}",
                debug_lines=[
                    "[debug] stage=planner",
                    f"[debug] model={planner_model_name}",
                    f"[debug] prompt_messages={len(planner_prompt)}",
                    f"[debug] raw_output={planner_raw_text}",
                ],
            ) from exc

        executor_model_name = self.model_name_for_role("executor")
        executor_model = self.build_chat_model_for(executor_model_name)
        executor_agent = create_react_agent(
            executor_model,
            self.tool_registry.as_langchain_tools(),
            state_modifier=(
                "You are the executor for agentOs. Work inside the repository. "
                "Use tools when helpful. Prefer bounded file operations and test execution. "
                "The context may include only a compact skills catalog because context is scarce. "
                "If a skill seems useful, first inspect the catalog or call `skill_list`, then call `skill_load` progressively: "
                "start with `level=summary`, then `level=full`, and only then specific `reference` or `script` targets if needed. "
                "Do not claim work you did not verify."
            ),
        )
        observed_tool_results: list[dict[str, object]] = []
        executor_messages = [
            *prior_messages,
            HumanMessage(
                content=(
                    f"User task:\n{user_task}\n\n"
                    f"Planner summary:\n{planner_plan.summary}\n\n"
                    f"Planner steps:\n- "
                    + "\n- ".join(planner_plan.steps or [planner_fallback.summary])
                    + "\n\n"
                    + f"Context bundle:\n{context_bundles['executor'].get('bundle_preview', '')}"
                )
            ),
        ]
        try:
            with tool_runtime_context(approved=approved, collector=observed_tool_results):
                executor_state = executor_agent.invoke({"messages": executor_messages})
        except Exception as exc:
            raise ModelBackedRuntimeError(
                f"executor stage failed: {exc}",
                debug_lines=[
                    "[debug] stage=executor",
                    f"[debug] model={executor_model_name}",
                    f"[debug] tool_names={','.join(tool.name for tool in self.tool_registry.as_langchain_tools())}",
                    f"[debug] prior_messages={len(prior_messages)}",
                    f"[debug] executor_messages={len(executor_messages)}",
                    f"[debug] user_task={user_task}",
                    f"[debug] planner_summary={planner_plan.summary}",
                    f"[debug] planner_steps={planner_plan.steps}",
                    f"[debug] executor_context_preview={context_bundles['executor'].get('bundle_preview', '')}",
                    f"[debug] exception_type={exc.__class__.__name__}",
                ],
            ) from exc
        executor_output = self._last_ai_content(executor_state.get("messages", []))

        reviewer_input = RoleInput(
            session_id=session_id,
            role="reviewer",
            task=user_task,
            user_task=user_task,
            context_bundle=context_bundles["reviewer"],
            tool_results=observed_tool_results,
            task_state={},
        )
        reviewer_agent = ReviewerRoleAgent()
        reviewer_fallback = reviewer_agent.run(reviewer_input)
        reviewer_parser = PydanticOutputParser(pydantic_object=ReviewerVerdict)
        reviewer_model_name = self.model_name_for_role("reviewer")
        reviewer_model = self.build_chat_model_for(reviewer_model_name)
        reviewer_prompt = [
            SystemMessage(
                content=(
                    "You are the reviewer for agentOs. Judge whether the executor result appears grounded "
                    "in tool output and summarize the current state for the user. "
                    "If the context or tool results show that a skill was used, apply it only to the extent that it was actually loaded. "
                    "Return JSON only."
                )
            ),
            HumanMessage(
                content=(
                    f"User task:\n{user_task}\n\n"
                    f"Executor final answer:\n{executor_output}\n\n"
                    f"Observed tool results:\n{observed_tool_results}\n\n"
                    f"Context bundle:\n{context_bundles['reviewer'].get('bundle_preview', '')}\n\n"
                    f"{reviewer_parser.get_format_instructions()}"
                )
            ),
        ]
        try:
            reviewer_raw = reviewer_model.invoke(reviewer_prompt)
            reviewer_verdict = self._parse_structured_response(reviewer_parser, reviewer_raw)
        except Exception as exc:
            reviewer_raw_text = self._safe_message_content(locals().get("reviewer_raw"))
            raise ModelBackedRuntimeError(
                f"reviewer stage failed: {exc}",
                debug_lines=[
                    "[debug] stage=reviewer",
                    f"[debug] model={reviewer_model_name}",
                    f"[debug] prompt_messages={len(reviewer_prompt)}",
                    f"[debug] executor_output={executor_output}",
                    f"[debug] observed_tool_results={observed_tool_results}",
                    f"[debug] raw_output={reviewer_raw_text}",
                ],
            ) from exc

        persisted_messages = self._build_persisted_messages(
            prior_messages=prior_messages,
            user_task=user_task,
            executor_output=executor_output,
            reviewer_summary=reviewer_verdict.summary or reviewer_fallback.summary,
        )
        self.context_manager.save_session(session_id, persisted_messages)

        return {
            "model_name": executor_model_name,
            "planner_model_name": planner_model_name,
            "executor_model_name": executor_model_name,
            "reviewer_model_name": reviewer_model_name,
            "planner_summary": planner_plan.summary or planner_fallback.summary,
            "planner_steps": planner_plan.steps or [],
            "executor_output": executor_output,
            "reviewer_summary": reviewer_verdict.summary or reviewer_fallback.summary,
            "reviewer_follow_up_needed": reviewer_verdict.follow_up_needed,
            "tool_results": observed_tool_results,
            "message_count": len(persisted_messages),
        }

    def _load_prior_messages(self, session_id: str) -> list[BaseMessage]:
        try:
            messages = self.context_manager.load_session(session_id)
        except FileNotFoundError:
            return []
        return self._sanitize_reusable_messages(messages)

    def _normalize_messages(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        normalized: list[BaseMessage] = []
        for message in messages:
            if isinstance(message, SystemMessage):
                continue
            normalized.append(message)
        return normalized[-12:]

    def _sanitize_reusable_messages(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        """Keep only safe replayable messages for the next model-backed turn."""

        sanitized: list[BaseMessage] = []
        for message in messages:
            if isinstance(message, SystemMessage):
                continue
            if isinstance(message, ToolMessage):
                continue
            if isinstance(message, AIMessage) and getattr(message, "tool_calls", None):
                content = self._string_content(message).strip()
                if content:
                    sanitized.append(AIMessage(content=content))
                continue
            sanitized.append(message)
        return sanitized[-8:]

    def _build_persisted_messages(
        self,
        *,
        prior_messages: list[BaseMessage],
        user_task: str,
        executor_output: str,
        reviewer_summary: str,
    ) -> list[BaseMessage]:
        """Persist a compact transcript instead of raw ReAct protocol messages."""

        messages: list[BaseMessage] = [
            *prior_messages,
            HumanMessage(content=user_task),
            AIMessage(content=executor_output.strip()),
        ]
        if reviewer_summary.strip():
            messages.append(AIMessage(content=f"[reviewer] {reviewer_summary.strip()}"))
        return self._sanitize_reusable_messages(messages)

    def _last_ai_content(self, messages: list[BaseMessage]) -> str:
        for message in reversed(messages):
            if isinstance(message, AIMessage):
                return self._string_content(message)
        return ""

    def _string_content(self, message: BaseMessage) -> str:
        if isinstance(message.content, str):
            return message.content
        return str(message.content)

    def _safe_message_content(self, message: BaseMessage | None) -> str:
        if message is None:
            return "<no message captured>"
        try:
            return self._string_content(message)
        except Exception as exc:  # pragma: no cover - defensive formatting
            return f"<failed to decode message: {exc}>"

    def _parse_structured_response(self, parser: PydanticOutputParser, message: BaseMessage):
        content = self._string_content(message).strip()
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", content)
            content = re.sub(r"\n```$", "", content)
        return parser.parse(content)
