"""Adaptive lifecycle maintenance for layered context memory."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from agentos.context.models import (
    FailureFact,
    LayeredMemory,
    LifecycleAuditRecord,
    MemoryDelta,
    RememberedFact,
    TaskState,
    ToolFact,
    UserProfile,
    UserPreferences,
    WorkingMemory,
    WorkspaceState,
)

if TYPE_CHECKING:
    from agentos.context.manager import ContextManager


class ContextLifecycleManager:
    """Maintain layered memory and trigger adaptive compression."""

    ACTIVE_THRESHOLD_CHARS = 24000
    LARGE_TOOL_OUTPUT_CHARS = 6000

    def __init__(self, manager: "ContextManager"):
        self.manager = manager
        self.semantic_compressor = SemanticMemoryCompressor()
        self.memory_extractor = StructuredMemoryExtractor(manager)

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

        new_tool_facts = self._extract_tool_facts(state)
        tool_facts = self._merge_tool_facts(memory.tool_facts, new_tool_facts)
        extracted_failures = self._extract_failures(new_tool_facts)
        delta = self.memory_extractor.extract(
            session_id=session_id,
            task=task,
            state=state,
            recent_messages=recent_messages,
            tool_facts=new_tool_facts,
        )
        working_memory = self._extract_working_memory(
            task=task,
            state=state,
            recent_messages=recent_messages,
            existing=memory.working_memory,
        )
        user_profile = self._merge_user_profile(memory.user_profile, delta.user_profile_delta)
        preferences = self._extract_user_preferences(memory.user_preferences, recent_messages, user_profile)
        remembered_facts = self._merge_remembered_facts(memory.remembered_facts, delta.remembered_facts_delta)
        task_state = self._merge_task_state(memory.task_state, delta.task_state_delta, working_memory)
        failure_memory = self._merge_failures(memory.failure_memory, extracted_failures, delta.failure_memory_delta)
        workspace_state = self._merge_workspace_state(
            memory.workspace_state,
            self._extract_workspace_state(workspace_dir=workspace_dir, state=state, tool_facts=new_tool_facts),
        )

        message_dicts = [
            self.manager.serialize_message(message)
            for message in recent_messages[-24:]
        ]
        retained_layers = [
            "recent_messages",
            "user_profile",
            "remembered_facts",
            "task_state",
            "working_memory",
            "user_preferences",
            "tool_facts",
            "workspace_state",
            "failure_memory",
        ]

        memory = LayeredMemory(
            recent_messages=message_dicts,
            user_profile=user_profile,
            remembered_facts=remembered_facts[-50:],
            task_state=task_state,
            working_memory=working_memory,
            user_preferences=preferences,
            tool_facts=tool_facts[-20:],
            workspace_state=workspace_state,
            failure_memory=failure_memory[-12:],
            session_summary=self._session_summary(task_state, working_memory, tool_facts, failure_memory),
            lifecycle_audits=list(memory.lifecycle_audits),
        )

        compressed_layers: list[str] = []
        dropped_classes: list[str] = []
        if self._should_reduce(trigger_reason=trigger_reason, before_size=before_size, tool_facts=tool_facts):
            compressed_layers = ["recent_messages", "tool_facts"]
            if len(memory.recent_messages) > 12:
                memory.recent_messages = memory.recent_messages[-12:]
                dropped_classes.append("older_recent_messages")
            if len(memory.tool_facts) > 10:
                memory.tool_facts = memory.tool_facts[-10:]
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
        existing: WorkingMemory,
    ) -> WorkingMemory:
        accepted_constraints: list[str] = list(existing.accepted_constraints)
        rejected_approaches: list[str] = list(existing.rejected_approaches)
        open_questions: list[str] = list(existing.open_questions)
        preferred_language = ""

        for message in recent_messages[-12:]:
            content = self.manager.string_content(message).strip()
            lowered = content.lower()
            if any(keyword in content for keyword in ("不要", "必须", "请用", "记得", "记住", "偏好")):
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
            accepted_constraints=self._dedupe(accepted_constraints)[-12:],
            rejected_approaches=self._dedupe(rejected_approaches)[-8:],
            active_plan=active_plan,
            completed_actions=completed_actions,
            open_questions=self._dedupe(open_questions)[:4],
            conversation_summary=conversation_summary,
        )

    def _extract_user_preferences(
        self,
        existing: UserPreferences,
        recent_messages: list[BaseMessage],
        user_profile: UserProfile,
    ) -> UserPreferences:
        preferences = list(existing.output_preferences)
        collaboration = list(existing.collaboration_preferences)
        language = user_profile.preferred_language or existing.preferred_language
        preferences.extend(user_profile.response_style)
        preferences.extend(user_profile.stable_preferences)
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
        task_state: TaskState,
        working_memory: WorkingMemory,
        tool_facts: list[ToolFact],
        failure_memory: list[FailureFact],
    ) -> str:
        parts = [f"goal={task_state.current_goal or working_memory.current_goal}"]
        active_plan = task_state.active_plan or working_memory.active_plan
        if active_plan:
            parts.append("plan=" + ", ".join(active_plan[:3]))
        if tool_facts:
            parts.append(f"tool_facts={len(tool_facts)}")
        if failure_memory:
            parts.append(f"failures={len(failure_memory)}")
        return " | ".join(parts)

    def _merge_user_profile(self, existing: UserProfile, delta: UserProfile) -> UserProfile:
        return UserProfile(
            preferred_language=self._normalize_language(delta.preferred_language) or existing.preferred_language,
            response_style=self._dedupe([*existing.response_style, *delta.response_style])[-8:],
            stable_preferences=self._dedupe([*existing.stable_preferences, *delta.stable_preferences])[-12:],
        )

    def _merge_remembered_facts(
        self,
        existing: list[RememberedFact],
        delta: list[RememberedFact],
    ) -> list[RememberedFact]:
        by_key: dict[str, RememberedFact] = {
            fact.key: fact for fact in existing if fact.key and fact.status == "active"
        }
        for fact in delta:
            if not fact.key:
                continue
            old = by_key.get(fact.key)
            if old and not fact.created_at:
                fact.created_at = old.created_at
            if not fact.created_at:
                fact.created_at = fact.updated_at
            by_key[fact.key] = fact
        return list(by_key.values())

    def _merge_task_state(
        self,
        existing: TaskState,
        delta: TaskState,
        working_memory: WorkingMemory,
    ) -> TaskState:
        return TaskState(
            current_goal=delta.current_goal or working_memory.current_goal or existing.current_goal,
            completed_actions=self._dedupe(
                [*existing.completed_actions, *working_memory.completed_actions, *delta.completed_actions]
            )[-12:],
            open_questions=self._dedupe(
                [*existing.open_questions, *working_memory.open_questions, *delta.open_questions]
            )[-8:],
            active_plan=delta.active_plan or working_memory.active_plan or existing.active_plan,
        )

    def _merge_tool_facts(self, existing: list[ToolFact], new: list[ToolFact]) -> list[ToolFact]:
        merged = [*existing, *new]
        seen: set[tuple[str, str, str]] = set()
        deduped: list[ToolFact] = []
        for fact in merged:
            marker = (fact.tool_name, fact.summary, ",".join(fact.related_paths))
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(fact)
        return deduped

    def _merge_failures(
        self,
        existing: list[FailureFact],
        extracted: list[FailureFact],
        delta: list[FailureFact],
    ) -> list[FailureFact]:
        merged = [*existing, *extracted, *delta]
        seen: set[tuple[str, str, str]] = set()
        deduped: list[FailureFact] = []
        for failure in merged:
            marker = (failure.summary, failure.tool_name, failure.reason)
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(failure)
        return deduped[-8:]

    def _merge_workspace_state(self, existing: WorkspaceState, new: WorkspaceState) -> WorkspaceState:
        return WorkspaceState(
            top_level_entries=new.top_level_entries or existing.top_level_entries,
            touched_files=self._dedupe([*existing.touched_files, *new.touched_files])[-20:],
            recent_reads=self._dedupe([*existing.recent_reads, *new.recent_reads])[-12:],
            recent_writes=self._dedupe([*existing.recent_writes, *new.recent_writes])[-12:],
        )

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
            return {"working_memory": 1200, "user_preferences": 400, "recent_messages": 2400, "workspace_state": 600}
        if role == "reviewer":
            return {"working_memory": 1000, "tool_facts": 1600, "failure_memory": 600, "recent_messages": 1600}
        return {"working_memory": 1200, "tool_facts": 1600, "workspace_state": 1000, "recent_messages": 2400}

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

    def _normalize_language(self, value: str) -> str:
        normalized = value.strip().lower()
        if normalized in {"中文", "chinese", "zh", "zh-cn", "简体中文", "汉语"}:
            return "zh-CN"
        if normalized in {"english", "en", "en-us", "英文"}:
            return "en-US"
        return value.strip()


class MemoryFactPayload(BaseModel):
    key: str = Field(default="", description="Stable fact key.")
    value: str = Field(default="", description="Fact value.")
    scope: str = Field(default="session", description="Fact scope such as session or project.")
    source: str = Field(default="user_explicit", description="Source type.")
    confidence: float = Field(default=1.0, description="Confidence from 0 to 1.")
    status: str = Field(default="active", description="Fact status.")
    source_text: str = Field(default="", description="Original source text.")


class UserProfilePayload(BaseModel):
    preferred_language: str = Field(default="")
    response_style: list[str] = Field(default_factory=list)
    stable_preferences: list[str] = Field(default_factory=list)


class TaskStatePayload(BaseModel):
    current_goal: str = Field(default="")
    completed_actions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    active_plan: list[str] = Field(default_factory=list)


class MemoryDeltaPayload(BaseModel):
    user_profile_delta: UserProfilePayload = Field(default_factory=UserProfilePayload)
    remembered_facts_delta: list[MemoryFactPayload] = Field(default_factory=list)
    task_state_delta: TaskStatePayload = Field(default_factory=TaskStatePayload)
    diagnostics: list[str] = Field(default_factory=list)


class StructuredMemoryExtractor:
    """Extract structured memory deltas with model-backed and deterministic paths."""

    ORDINAL_KEYS = {
        "第一": "test_code_1",
        "第一个": "test_code_1",
        "第二": "test_code_2",
        "第二个": "test_code_2",
        "第三": "test_code_3",
        "第三个": "test_code_3",
        "第四": "test_code_4",
        "第四个": "test_code_4",
        "1": "test_code_1",
        "2": "test_code_2",
        "3": "test_code_3",
        "4": "test_code_4",
    }

    def __init__(self, manager: "ContextManager"):
        self.manager = manager
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "")
        self.model_name = os.getenv("AGENTOS_MODEL_SMALL", "gpt-5.4")
        self.model_enabled = (
            os.getenv("AGENTOS_MEMORY_MODEL_EXTRACTION", "0").lower() in {"1", "true", "yes"}
            and os.getenv("AGENTOS_MODEL_ENABLED", "1").lower() not in {"0", "false", "no"}
        )

    def extract(
        self,
        *,
        session_id: str,
        task: str,
        state: dict[str, object],
        recent_messages: list[BaseMessage],
        tool_facts: list[ToolFact],
    ) -> MemoryDelta:
        fallback = self.extract_deterministic(
            task=task,
            state=state,
            recent_messages=recent_messages,
            tool_facts=tool_facts,
        )
        if not (self.model_enabled and self.api_key):
            return fallback
        try:
            return self.extract_with_model(
                session_id=session_id,
                task=task,
                state=state,
                recent_messages=recent_messages,
                tool_facts=tool_facts,
                fallback=fallback,
            )
        except Exception as exc:
            fallback.diagnostics.append(f"model_memory_extraction_failed:{exc.__class__.__name__}:{exc}")
            return fallback

    def extract_deterministic(
        self,
        *,
        task: str,
        state: dict[str, object],
        recent_messages: list[BaseMessage],
        tool_facts: list[ToolFact],
    ) -> MemoryDelta:
        now = datetime.now(timezone.utc).isoformat()
        profile = UserProfile()
        remembered: list[RememberedFact] = []
        open_questions: list[str] = []

        for message in recent_messages[-16:]:
            if not isinstance(message, HumanMessage):
                continue
            content = self.manager.string_content(message).strip()
            if not content:
                continue
            if "中文" in content:
                profile.preferred_language = "zh-CN"
            if "短一点" in content or "简短" in content or "短" in content and "回答" in content:
                profile.response_style.append("brief")
                profile.stable_preferences.append(content[:160])
            if "偏好" in content:
                profile.stable_preferences.append(content[:160])
            remembered.extend(self._facts_from_text(content, now=now))
            if "?" in content or "？" in content:
                open_questions.append(content[:160])

        completed = [str(item) for item in state.get("completed_tasks", [])][-8:]
        active_plan = [str(item) for item in state.get("pending_tasks", [])][:6]
        task_state = TaskState(
            current_goal=task or str(state.get("user_task", "")),
            completed_actions=completed,
            open_questions=open_questions[-6:],
            active_plan=active_plan,
        )
        return MemoryDelta(
            user_profile_delta=profile,
            remembered_facts_delta=remembered,
            task_state_delta=task_state,
        )

    def extract_with_model(
        self,
        *,
        session_id: str,
        task: str,
        state: dict[str, object],
        recent_messages: list[BaseMessage],
        tool_facts: list[ToolFact],
        fallback: MemoryDelta,
    ) -> MemoryDelta:
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
                    "Extract structured memory updates for agentOs. "
                    "Prefer explicit user statements over assistant guesses. "
                    "Call MemoryDeltaPayload exactly once."
                )
            ),
            HumanMessage(
                content=json.dumps(
                    {
                        "session_id": session_id,
                        "task": task,
                        "recent_messages": [
                            {
                                "type": message.type,
                                "content": self.manager.string_content(message),
                            }
                            for message in recent_messages[-12:]
                        ],
                        "tool_facts": [fact.to_dict() for fact in tool_facts[-12:]],
                        "fallback_delta": fallback.to_dict(),
                    },
                    ensure_ascii=False,
                )
            ),
        ]
        raw = model.bind_tools([MemoryDeltaPayload], tool_choice="required").invoke(prompt)
        payload = self._payload_from_tool_call(raw)
        return self._memory_delta_from_payload(payload)

    def _facts_from_text(self, text: str, *, now: str) -> list[RememberedFact]:
        if "记住" not in text and "记得" not in text:
            return []
        facts: list[RememberedFact] = []
        patterns = [
            r"(第[一二三四]个?|[1234])测试代号[：:]\s*([^。.\n]+)",
            r"测试代号[：:]\s*([^。.\n]+)",
        ]
        ordinal_match = re.search(patterns[0], text)
        if ordinal_match:
            ordinal = ordinal_match.group(1)
            value = ordinal_match.group(2).strip()
            key = self.ORDINAL_KEYS.get(ordinal, f"remembered_fact_{len(facts) + 1}")
            facts.append(
                RememberedFact(
                    key=key,
                    value=value,
                    source="user_explicit",
                    confidence=1.0,
                    created_at=now,
                    updated_at=now,
                    source_text=text[:240],
                )
            )
            return facts
        generic_match = re.search(patterns[1], text)
        if generic_match:
            value = generic_match.group(1).strip()
            facts.append(
                RememberedFact(
                    key=self._fact_key(value),
                    value=value,
                    source="user_explicit",
                    confidence=0.9,
                    created_at=now,
                    updated_at=now,
                    source_text=text[:240],
                )
            )
        return facts

    def _fact_key(self, value: str) -> str:
        normalized = re.sub(r"\W+", "_", value.strip().lower()).strip("_")
        return f"remembered_{normalized or 'fact'}"

    def _payload_from_tool_call(self, message: object) -> MemoryDeltaPayload:
        tool_calls = getattr(message, "tool_calls", None) or []
        if not tool_calls:
            additional_kwargs = getattr(message, "additional_kwargs", None)
            if isinstance(additional_kwargs, dict):
                raw_calls = additional_kwargs.get("tool_calls")
                if isinstance(raw_calls, list):
                    tool_calls = raw_calls
        if not tool_calls:
            raise ValueError("model did not return a memory extraction tool call")
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
            raise ValueError("memory extraction tool call arguments were not an object")
        return MemoryDeltaPayload.model_validate(args)

    def _memory_delta_from_payload(self, payload: MemoryDeltaPayload) -> MemoryDelta:
        now = datetime.now(timezone.utc).isoformat()
        return MemoryDelta(
            user_profile_delta=UserProfile(
                preferred_language=self._normalize_language(payload.user_profile_delta.preferred_language),
                response_style=list(payload.user_profile_delta.response_style),
                stable_preferences=list(payload.user_profile_delta.stable_preferences),
            ),
            remembered_facts_delta=[
                RememberedFact(
                    key=item.key,
                    value=item.value,
                    scope=item.scope,
                    source=item.source,
                    confidence=item.confidence,
                    status=item.status,
                    created_at=now,
                    updated_at=now,
                    source_text=item.source_text,
                )
                for item in payload.remembered_facts_delta
                if item.key and item.value
            ],
            task_state_delta=TaskState(
                current_goal=payload.task_state_delta.current_goal,
                completed_actions=list(payload.task_state_delta.completed_actions),
                open_questions=list(payload.task_state_delta.open_questions),
                active_plan=list(payload.task_state_delta.active_plan),
            ),
            diagnostics=list(payload.diagnostics),
        )

    def _normalize_language(self, value: str) -> str:
        normalized = value.strip().lower()
        if normalized in {"中文", "chinese", "zh", "zh-cn", "简体中文", "汉语"}:
            return "zh-CN"
        if normalized in {"english", "en", "en-us", "英文"}:
            return "en-US"
        return value.strip()


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
