"""Base classes for structured tool execution."""

from __future__ import annotations

from abc import ABC, abstractmethod

from agentos.tools.models import ToolInvocation, ToolResult


class AgentTool(ABC):
    """Abstract base class for coding-agent tools."""

    name: str
    description: str

    @abstractmethod
    def run(self, invocation: ToolInvocation) -> ToolResult:
        """Execute one structured tool invocation."""
