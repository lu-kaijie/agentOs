"""Structured memory and lifecycle models for product-grade context management."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class WorkingMemory:
    current_goal: str = ""
    accepted_constraints: list[str] = field(default_factory=list)
    rejected_approaches: list[str] = field(default_factory=list)
    active_plan: list[str] = field(default_factory=list)
    completed_actions: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    conversation_summary: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "WorkingMemory":
        return cls(
            current_goal=str(payload.get("current_goal", "")),
            accepted_constraints=[str(item) for item in payload.get("accepted_constraints", [])],
            rejected_approaches=[str(item) for item in payload.get("rejected_approaches", [])],
            active_plan=[str(item) for item in payload.get("active_plan", [])],
            completed_actions=[str(item) for item in payload.get("completed_actions", [])],
            open_questions=[str(item) for item in payload.get("open_questions", [])],
            conversation_summary=str(payload.get("conversation_summary", "")),
        )


@dataclass(slots=True)
class UserPreferences:
    preferred_language: str = ""
    output_preferences: list[str] = field(default_factory=list)
    collaboration_preferences: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "UserPreferences":
        return cls(
            preferred_language=str(payload.get("preferred_language", "")),
            output_preferences=[str(item) for item in payload.get("output_preferences", [])],
            collaboration_preferences=[str(item) for item in payload.get("collaboration_preferences", [])],
        )


@dataclass(slots=True)
class ToolFact:
    tool_name: str
    summary: str
    related_paths: list[str] = field(default_factory=list)
    command: str = ""
    success: bool = True
    exit_code: int | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ToolFact":
        exit_code = payload.get("exit_code")
        return cls(
            tool_name=str(payload.get("tool_name", "")),
            summary=str(payload.get("summary", "")),
            related_paths=[str(item) for item in payload.get("related_paths", [])],
            command=str(payload.get("command", "")),
            success=bool(payload.get("success", True)),
            exit_code=int(exit_code) if exit_code is not None else None,
        )


@dataclass(slots=True)
class WorkspaceState:
    top_level_entries: list[str] = field(default_factory=list)
    touched_files: list[str] = field(default_factory=list)
    recent_reads: list[str] = field(default_factory=list)
    recent_writes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "WorkspaceState":
        return cls(
            top_level_entries=[str(item) for item in payload.get("top_level_entries", [])],
            touched_files=[str(item) for item in payload.get("touched_files", [])],
            recent_reads=[str(item) for item in payload.get("recent_reads", [])],
            recent_writes=[str(item) for item in payload.get("recent_writes", [])],
        )


@dataclass(slots=True)
class FailureFact:
    summary: str
    tool_name: str = ""
    command: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "FailureFact":
        return cls(
            summary=str(payload.get("summary", "")),
            tool_name=str(payload.get("tool_name", "")),
            command=str(payload.get("command", "")),
            reason=str(payload.get("reason", "")),
        )


@dataclass(slots=True)
class LifecycleAuditRecord:
    trigger_reason: str
    before_size: int
    after_size: int
    compressed_layers: list[str] = field(default_factory=list)
    retained_layers: list[str] = field(default_factory=list)
    dropped_classes: list[str] = field(default_factory=list)
    budget_allocations: dict[str, int] = field(default_factory=dict)
    compression_mode: str = "hybrid"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "LifecycleAuditRecord":
        return cls(
            trigger_reason=str(payload.get("trigger_reason", "")),
            before_size=int(payload.get("before_size", 0)),
            after_size=int(payload.get("after_size", 0)),
            compressed_layers=[str(item) for item in payload.get("compressed_layers", [])],
            retained_layers=[str(item) for item in payload.get("retained_layers", [])],
            dropped_classes=[str(item) for item in payload.get("dropped_classes", [])],
            budget_allocations={str(key): int(value) for key, value in dict(payload.get("budget_allocations", {})).items()},
            compression_mode=str(payload.get("compression_mode", "hybrid")),
        )


@dataclass(slots=True)
class LayeredMemory:
    recent_messages: list[dict[str, object]] = field(default_factory=list)
    working_memory: WorkingMemory = field(default_factory=WorkingMemory)
    user_preferences: UserPreferences = field(default_factory=UserPreferences)
    tool_facts: list[ToolFact] = field(default_factory=list)
    workspace_state: WorkspaceState = field(default_factory=WorkspaceState)
    failure_memory: list[FailureFact] = field(default_factory=list)
    session_summary: str = ""
    lifecycle_audits: list[LifecycleAuditRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "recent_messages": self.recent_messages,
            "working_memory": self.working_memory.to_dict(),
            "user_preferences": self.user_preferences.to_dict(),
            "tool_facts": [item.to_dict() for item in self.tool_facts],
            "workspace_state": self.workspace_state.to_dict(),
            "failure_memory": [item.to_dict() for item in self.failure_memory],
            "session_summary": self.session_summary,
            "lifecycle_audits": [item.to_dict() for item in self.lifecycle_audits],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "LayeredMemory":
        return cls(
            recent_messages=[
                item for item in payload.get("recent_messages", []) if isinstance(item, dict)
            ],
            working_memory=WorkingMemory.from_dict(
                dict(payload.get("working_memory", {}))
            ),
            user_preferences=UserPreferences.from_dict(
                dict(payload.get("user_preferences", {}))
            ),
            tool_facts=[
                ToolFact.from_dict(item)
                for item in payload.get("tool_facts", [])
                if isinstance(item, dict)
            ],
            workspace_state=WorkspaceState.from_dict(
                dict(payload.get("workspace_state", {}))
            ),
            failure_memory=[
                FailureFact.from_dict(item)
                for item in payload.get("failure_memory", [])
                if isinstance(item, dict)
            ],
            session_summary=str(payload.get("session_summary", "")),
            lifecycle_audits=[
                LifecycleAuditRecord.from_dict(item)
                for item in payload.get("lifecycle_audits", [])
                if isinstance(item, dict)
            ],
        )
