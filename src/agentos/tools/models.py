"""Structured tool invocation and result models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class ToolInvocation:
    """A structured request for one registered tool."""

    tool_name: str
    arguments: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    """A structured result returned by one registered tool."""

    tool_name: str
    status: str
    summary: str
    payload: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
