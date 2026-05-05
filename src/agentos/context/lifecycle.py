"""Adaptive lifecycle maintenance for layered context memory."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agentos.context.models import (
    FailureFact,
    LayeredMemory,
    LifecycleAuditRecord,
    ToolFact,
    UserPreferences,
    WorkingMemory,
    WorkspaceState,
)

if TYPE_CHECKING:
    from agentos.context.manager import ContextManager


class ContextLifecycleManager:
    """Maintain layered memory and trigger adaptive compression."""

    ACTIVE_THRESHOLD_CHARS = 900
    LARGE_TOOL_OUTPUT_CHARS = 500

    def __init__(self, manager: "ContextManager"):
        self.manager = manager
        self.semantic_compressor = SemanticMemoryCompressor()

    def maintain(
        self,
        *,
        session_id: str,
        task: str,
        role: str,
        state: dict[str, object],
        workspace_dir: Path,
        messages: list[BaseMessage] | None = None,
        trigger_reason: str = "prepare_context",
    ) -> tuple[LayeredMemory, LifecycleAuditRecord]:
        memory = self.manager.load_memory(session_id, default=LayeredMemory())
        recent_messages = messages or self._messages_from_memory(memory)
        before_size = self._estimate_size(memory, recent_messages, state)

        tool_facts = self._extract_tool_facts(state)
        failure_memory = self._extract_failures(tool_facts)
        working_memory = self._extract_working_memory(task=task, state=state, recent_messages=recent_messages)
        preferences = self._extract_user_preferences(memory.user_preferences, recent_messages)
        workspace_state = self._extract_workspace_state(workspace_dir=workspace_dir, state=state, tool_facts=tool_facts)

        message_dicts = [
            self.manager.serialize_message(message)
            for message in recent_messages[-6:]
        ]
        retained_layers = [
            "recent_messages",
            "working_memory",
            "user_preferences",
            "tool_facts",
            "workspace_state",
            "failure_memory",
        ]

        memory = LayeredMemory(
            recent_messages=message_dicts,
            working_memory=working_memory,
            user_preferences=preferences,
            tool_facts=tool_facts[-5:],
            workspace_state=workspace_state,
            failure_memory=failure_memory[-5:],
            session_summary=self._session_summary(working_memory, tool_facts, failure_memory),
            lifecycle_audits=list(memory.lifecycle_audits),
        )

        compressed_layers: list[str] = []
        dropped_classes: list[str] = []
        if self._should_reduce(trigger_reason=trigger_reason, before_size=before_size, tool_facts=tool_facts):
            compressed_layers = ["recent_messages", "tool_facts"]
            if len(memory.recent_messages) > 4:
                memory.recent_messages = memory.recent_messages[-4:]
                dropped_classes.append("older_recent_messages")
            if len(memory.tool_facts) > 3:
                memory.tool_facts = memory.tool_facts[-3:]
                dropped_classes.append("older_tool_facts")

        budget_allocations = self._budget_allocations_for_role(role)
        after_size = self._estimate_layered_memory_size(memory)
        audit = LifecycleAuditRecord(
            trigger_reason=trigger_reason,
            before_size=before_size,
            after_size=after_size,
            compressed_layers=compressed_layers,
            retained_layers=retained_layers,
            dropped_classes=dropped_classes,
            budget_allocations=budget_allocations,
            compression_mode="hybrid",
        )
        memory.lifecycle_audits = [*memory.lifecycle_audits[-4:], audit]
        self.manager.save_memory(session_id, memory)
        return memory, audit

    def _messages_from_memory(self, memory: LayeredMemory) -> list[BaseMessage]:
        return [
            self.manager.deserialize_message(item)
            for item in memory.recent_messages
            if isinstance(item, dict)
        ]

    def _extract_working_memory(
        self,
        *,
        task: str,
        state: dict[str, object],
        recent_messages: list[BaseMessage],
    ) -> WorkingMemory:
        accepted_constraints: list[str] = []
        rejected_approaches: list[str] = []
        open_questions: list[str] = []
        preferred_language = ""

        for message in recent_messages[-8:]:
            content = self.manager.string_content(message).strip()
            lowered = content.lower()
            if any(keyword in content for keyword in ("不要", "必须", "请用", "记得")):
                accepted_constraints.append(content[:120])
            if any(keyword in content for keyword in ("不要", "不能", "不要用")):
                rejected_approaches.append(content[:120])
            if "?" in content or "？" in content:
                open_questions.append(content[:120])
            if "中文" in content:
                preferred_language = "zh-CN"

        completed_actions = [str(item) for item in state.get("completed_tasks", [])][-5:]
        active_plan = [str(item) for item in state.get("pending_tasks", [])][:5]
        summary_candidates = [
            str(item).strip().replace("\n", " ")
            for item in state.get("step_outputs", [])[-3:]
            if str(item).strip()
        ]
        conversation_summary = self._compress_lines(summary_candidates, max_chars=220)
        current_goal = task or str(state.get("user_task", ""))
        if preferred_language and "prefers Chinese output" not in accepted_constraints:
            accepted_constraints.append("prefers Chinese output")

        semantic_summary = self.semantic_compressor.compress(
            task=current_goal,
            accepted_constraints=accepted_constraints,
            completed_actions=completed_actions,
            open_questions=open_questions,
            recent_messages=[self.manager.string_content(message) for message in recent_messages[-6:]],
            fallback_summary=conversation_summary,
        )
        conversation_summary = semantic_summary.get("conversation_summary", conversation_summary)
        accepted_constraints = semantic_summary.get("accepted_constraints", accepted_constraints)
        open_questions = semantic_summary.get("open_questions", open_questions)

        return WorkingMemory(
            current_goal=current_goal,
            accepted_constraints=self._dedupe(accepted_constraints)[:6],
            rejected_approaches=self._dedupe(rejected_approaches)[:6],
            active_plan=active_plan,
            completed_actions=completed_actions,
            open_questions=self._dedupe(open_questions)[:4],
            conversation_summary=conversation_summary,
        )

    def _extract_user_preferences(
        self,
        existing: UserPreferences,
        recent_messages: list[BaseMessage],
    ) -> UserPreferences:
        preferences = list(existing.output_preferences)
        collaboration = list(existing.collaboration_preferences)
        language = existing.preferred_language
        for message in recent_messages[-8:]:
            content = self.manager.string_content(message)
            if "中文" in content:
                language = "zh-CN"
            if "一步一步" in content:
                collaboration.append("step-by-step implementation")
            if "直接" in content and "实现" in content:
                collaboration.append("prefer direct implementation")
        return UserPreferences(
            preferred_language=language,
            output_preferences=self._dedupe(preferences)[:4],
            collaboration_preferences=self._dedupe(collaboration)[:6],
        )

    def _extract_tool_facts(self, state: dict[str, object]) -> list[ToolFact]:
        facts: list[ToolFact] = []
        for item in state.get("tool_results", []):
            if not isinstance(item, dict):
                continue
            payload = item.get("payload", {})
            related_paths = self._extract_related_paths(item, payload)
            exit_code = payload.get("exit_code") if isinstance(payload, dict) else None
            command = ""
            if isinstance(payload, dict):
                raw_command = payload.get("command")
                if isinstance(raw_command, list):
                    command = " ".join(str(part) for part in raw_command)
                elif raw_command is not None:
                    command = str(raw_command)
            facts.append(
                ToolFact(
                    tool_name=str(item.get("tool_name", "unknown")),
                    summary=str(item.get("summary", ""))[:180],
                    related_paths=related_paths,
                    command=command,
                    success=exit_code in (None, 0),
                    exit_code=int(exit_code) if exit_code is not None else None,
                )
            )
        return facts

    def _extract_failures(self, tool_facts: list[ToolFact]) -> list[FailureFact]:
        failures: list[FailureFact] = []
        for fact in tool_facts:
            if fact.success:
                continue
            reason = fact.summary or "tool execution failed"
            failures.append(
                FailureFact(
                    summary=f"{fact.tool_name} failed",
                    tool_name=fact.tool_name,
                    command=fact.command,
                    reason=reason,
                )
            )
        return failures

    def _extract_workspace_state(
        self,
        *,
        workspace_dir: Path,
        state: dict[str, object],
        tool_facts: list[ToolFact],
    ) -> WorkspaceState:
        reads: list[str] = []
        writes: list[str] = []
        touched: list[str] = []
        for fact in tool_facts:
            touched.extend(fact.related_paths)
            if fact.tool_name in {"file_read", "repo_search"}:
                reads.extend(fact.related_paths)
            if fact.tool_name in {"file_write", "file_patch"}:
                writes.extend(fact.related_paths)
        for task in state.get("completed_tasks", []):
            text = str(task)
            path = self._extract_path_hint(text)
            if path:
                touched.append(path)
        top_level = sorted(path.name for path in workspace_dir.iterdir())[:8] if workspace_dir.exists() else []
        return WorkspaceState(
            top_level_entries=top_level,
            touched_files=self._dedupe(touched)[:12],
            recent_reads=self._dedupe(reads)[:8],
            recent_writes=self._dedupe(writes)[:8],
        )

    def _session_summary(
        self,
        working_memory: WorkingMemory,
        tool_facts: list[ToolFact],
        failure_memory: list[FailureFact],
    ) -> str:
        parts = [f"goal={working_memory.current_goal}"]
        if working_memory.active_plan:
            parts.append("plan=" + ", ".join(working_memory.active_plan[:3]))
        if tool_facts:
            parts.append(f"tool_facts={len(tool_facts)}")
        if failure_memory:
            parts.append(f"failures={len(failure_memory)}")
        return " | ".join(parts)

    def _should_reduce(
        self,
        *,
        trigger_reason: str,
        before_size: int,
        tool_facts: list[ToolFact],
    ) -> bool:
        if trigger_reason in {"session_resume", "role_handoff", "turn_complete", "large_tool_output"}:
            return True
        if before_size > self.ACTIVE_THRESHOLD_CHARS:
            return True
        return any(len(fact.summary) > self.LARGE_TOOL_OUTPUT_CHARS for fact in tool_facts)

    def _estimate_size(
        self,
        memory: LayeredMemory,
        recent_messages: list[BaseMessage],
        state: dict[str, object],
    ) -> int:
        message_chars = sum(len(self.manager.string_content(message)) for message in recent_messages)
        tool_chars = sum(len(str(item)) for item in state.get("tool_results", []))
        return len(str(memory.to_dict())) + message_chars + tool_chars

    def _estimate_layered_memory_size(self, memory: LayeredMemory) -> int:
        return len(str(memory.to_dict()))

    def _budget_allocations_for_role(self, role: str) -> dict[str, int]:
        if role == "planner":
            return {"working_memory": 260, "user_preferences": 80, "recent_messages": 120, "workspace_state": 100}
        if role == "reviewer":
            return {"working_memory": 180, "tool_facts": 220, "failure_memory": 120, "recent_messages": 80}
        return {"working_memory": 180, "tool_facts": 180, "workspace_state": 160, "recent_messages": 80}

    def _extract_related_paths(self, item: dict[str, object], payload: object) -> list[str]:
        paths: list[str] = []
        for candidate in (
            item.get("path"),
            item.get("arguments", {}).get("path") if isinstance(item.get("arguments"), dict) else None,
            payload.get("path") if isinstance(payload, dict) else None,
        ):
            if candidate:
                paths.append(str(candidate))
        if isinstance(payload, dict):
            stdout = str(payload.get("stdout", ""))[:300]
            paths.extend(re.findall(r"([A-Za-z0-9_./-]+\.[A-Za-z0-9_]+)", stdout))
        return self._dedupe(paths)

    def _extract_path_hint(self, text: str) -> str:
        match = re.search(r"([A-Za-z0-9_./-]+\.[A-Za-z0-9_]+)", text)
        if not match:
            return ""
        return match.group(1)

    def _compress_lines(self, lines: list[str], *, max_chars: int) -> str:
        cleaned = [line.strip().replace("\n", " ") for line in lines if line.strip()]
        if not cleaned:
            return ""
        rendered = " | ".join(cleaned)
        if len(rendered) <= max_chars:
            return rendered
        return rendered[: max_chars - 3] + "..."

    def _dedupe(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in items:
            if not item or item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered


class SemanticMemoryCompressor:
    """Hybrid semantic compressor with model-backed path and heuristic fallback."""

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "")
        self.model_name = os.getenv("AGENTOS_MODEL_SMALL", "gpt-5.4")
        self.model_enabled = os.getenv("AGENTOS_CONTEXT_MODEL_COMPRESSION", "0").lower() in {"1", "true", "yes"}

    def compress(
        self,
        *,
        task: str,
        accepted_constraints: list[str],
        completed_actions: list[str],
        open_questions: list[str],
        recent_messages: list[str],
        fallback_summary: str,
    ) -> dict[str, list[str] | str]:
        if self.model_enabled and self.api_key and self._semantic_load(recent_messages, fallback_summary) > 240:
            try:
                return self._compress_with_model(
                    task=task,
                    accepted_constraints=accepted_constraints,
                    completed_actions=completed_actions,
                    open_questions=open_questions,
                    recent_messages=recent_messages,
                    fallback_summary=fallback_summary,
                )
            except Exception:
                pass
        return {
            "conversation_summary": fallback_summary,
            "accepted_constraints": accepted_constraints,
            "open_questions": open_questions,
        }

    def _compress_with_model(
        self,
        *,
        task: str,
        accepted_constraints: list[str],
        completed_actions: list[str],
        open_questions: list[str],
        recent_messages: list[str],
        fallback_summary: str,
    ) -> dict[str, list[str] | str]:
        kwargs = {
            "model": self.model_name,
            "api_key": self.api_key,
            "temperature": 0,
        }
        if self.base_url:
            kwargs["base_url"] = self.base_url
        model = ChatOpenAI(**kwargs)
        prompt = [
            SystemMessage(
                content=(
                    "Compress coding-session semantic memory. "
                    "Return JSON with keys conversation_summary, accepted_constraints, open_questions. "
                    "Preserve user constraints with higher priority than casual dialog."
                )
            ),
            HumanMessage(
                content=json.dumps(
                    {
                        "task": task,
                        "accepted_constraints": accepted_constraints,
                        "completed_actions": completed_actions,
                        "open_questions": open_questions,
                        "recent_messages": recent_messages,
                        "fallback_summary": fallback_summary,
                    },
                    ensure_ascii=False,
                )
            ),
        ]
        response = model.invoke(prompt)
        content = response.content if isinstance(response.content, str) else str(response.content)
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", content)
            content = re.sub(r"\n```$", "", content)
        payload = json.loads(content)
        return {
            "conversation_summary": str(payload.get("conversation_summary", fallback_summary)),
            "accepted_constraints": [str(item) for item in payload.get("accepted_constraints", accepted_constraints)],
            "open_questions": [str(item) for item in payload.get("open_questions", open_questions)],
        }

    def _semantic_load(self, recent_messages: list[str], fallback_summary: str) -> int:
        return sum(len(item) for item in recent_messages) + len(fallback_summary)
