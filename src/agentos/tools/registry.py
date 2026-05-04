"""Structured tool registry and built-in coding tools."""

from __future__ import annotations

import json
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

from agentos.harness.execution import CommandExecutor, ExecutionRequest
from agentos.knowledge import KnowledgeLoader
from agentos.tools.base import AgentTool
from agentos.tools.models import ToolInvocation, ToolResult


@dataclass(slots=True)
class ToolContext:
    """Context shared by registry-backed tools."""

    workspace_dir: Path
    executor: CommandExecutor
    knowledge_loader: KnowledgeLoader


class ToolRegistry:
    """Register and invoke structured coding-agent tools."""

    def __init__(self, tools: list[AgentTool]):
        self._tools = {tool.name: tool for tool in tools}

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {"name": tool.name, "description": tool.description}
            for tool in sorted(self._tools.values(), key=lambda item: item.name)
        ]

    def invoke(self, invocation: ToolInvocation) -> ToolResult:
        if invocation.tool_name not in self._tools:
            raise KeyError(f"Tool '{invocation.tool_name}' is not registered")
        return self._tools[invocation.tool_name].run(invocation)


class ShellCommandTool(AgentTool):
    name = "shell_command"
    description = "Run a shell-like command through the harness executor."

    def __init__(self, context: ToolContext):
        self.context = context

    def run(self, invocation: ToolInvocation) -> ToolResult:
        command = [str(item) for item in invocation.arguments.get("command", [])]
        cwd = str(invocation.arguments.get("cwd", str(self.context.workspace_dir)))
        result = self.context.executor.run(ExecutionRequest(command=command, cwd=cwd))
        summary = f"exit_code={result.exit_code} timed_out={result.timed_out}"
        payload = {
            "command": result.command,
            "cwd": result.cwd,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": result.timed_out,
        }
        return ToolResult(tool_name=self.name, status="ok", summary=summary, payload=payload)


class KnowledgeLoadTool(AgentTool):
    name = "knowledge_load"
    description = "Load a knowledge topic from the knowledge directory."

    def __init__(self, context: ToolContext):
        self.context = context

    def run(self, invocation: ToolInvocation) -> ToolResult:
        topic = str(invocation.arguments.get("topic", ""))
        message = self.context.knowledge_loader.load_topic(topic)
        payload = {
            "topic": message.additional_kwargs.get("topic", topic),
            "source": message.additional_kwargs.get("source", ""),
            "content": message.content,
        }
        return ToolResult(
            tool_name=self.name,
            status="ok",
            summary=f"loaded topic '{topic}'",
            payload=payload,
        )


class RepoSearchTool(AgentTool):
    name = "repo_search"
    description = "Search the repository with ripgrep."

    def __init__(self, context: ToolContext):
        self.context = context

    def run(self, invocation: ToolInvocation) -> ToolResult:
        pattern = str(invocation.arguments.get("pattern", ""))
        if not pattern:
            raise ValueError("repo_search requires a non-empty pattern")
        try:
            result = self.context.executor.run(
                ExecutionRequest(command=["rg", "-n", pattern, "."], cwd=str(self.context.workspace_dir))
            )
            payload = {
                "pattern": pattern,
                "engine": "rg",
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timed_out": result.timed_out,
            }
            summary = f"search pattern='{pattern}' exit_code={result.exit_code}"
        except FileNotFoundError:
            stdout = _search_workspace_without_rg(self.context.workspace_dir, pattern)
            payload = {
                "pattern": pattern,
                "engine": "python",
                "exit_code": 0 if stdout else 1,
                "stdout": stdout,
                "stderr": "",
                "timed_out": False,
            }
            summary = f"search pattern='{pattern}' exit_code={payload['exit_code']}"
        return ToolResult(tool_name=self.name, status="ok", summary=summary, payload=payload)


class FileReadTool(AgentTool):
    name = "file_read"
    description = "Read one workspace file."

    def __init__(self, context: ToolContext):
        self.context = context

    def run(self, invocation: ToolInvocation) -> ToolResult:
        path = _resolve_workspace_path(self.context.workspace_dir, str(invocation.arguments.get("path", "")))
        content = path.read_text(encoding="utf-8")
        payload = {"path": str(path), "content": content}
        return ToolResult(tool_name=self.name, status="ok", summary=f"read '{path.name}'", payload=payload)


class FileWriteTool(AgentTool):
    name = "file_write"
    description = "Write one workspace file."

    def __init__(self, context: ToolContext):
        self.context = context

    def run(self, invocation: ToolInvocation) -> ToolResult:
        path = _resolve_workspace_path(self.context.workspace_dir, str(invocation.arguments.get("path", "")))
        content = str(invocation.arguments.get("content", ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        payload = {"path": str(path), "bytes_written": len(content.encode("utf-8"))}
        return ToolResult(tool_name=self.name, status="ok", summary=f"wrote '{path.name}'", payload=payload)


class FilePatchTool(AgentTool):
    name = "file_patch"
    description = "Apply one bounded text replacement inside a workspace file."

    def __init__(self, context: ToolContext):
        self.context = context

    def run(self, invocation: ToolInvocation) -> ToolResult:
        path = _resolve_workspace_path(self.context.workspace_dir, str(invocation.arguments.get("path", "")))
        target = str(invocation.arguments.get("target", ""))
        replacement = str(invocation.arguments.get("replacement", ""))
        if not target:
            raise ValueError("file_patch requires a non-empty target string")
        content = path.read_text(encoding="utf-8")
        replacement_count = content.count(target)
        if replacement_count == 0:
            raise ValueError(f"target text not found in '{path.name}'")
        updated = content.replace(target, replacement, 1)
        path.write_text(updated, encoding="utf-8")
        payload = {
            "path": str(path),
            "target": target,
            "replacement": replacement,
            "replacement_count": replacement_count,
        }
        return ToolResult(
            tool_name=self.name,
            status="ok",
            summary=f"patched '{path.name}'",
            payload=payload,
        )


class TestRunTool(AgentTool):
    name = "test_run"
    description = "Run a bounded test command in the workspace."

    def __init__(self, context: ToolContext):
        self.context = context

    def run(self, invocation: ToolInvocation) -> ToolResult:
        command_text = str(invocation.arguments.get("command", "")).strip()
        if not command_text:
            raise ValueError("test_run requires a command string")
        command = shlex.split(command_text)
        if command and command[0] == "python":
            command[0] = sys.executable
        result = self.context.executor.run(
            ExecutionRequest(command=command, cwd=str(self.context.workspace_dir))
        )
        payload = {
            "command": command,
            "cwd": result.cwd,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": result.timed_out,
        }
        summary = f"test command exit_code={result.exit_code}"
        return ToolResult(tool_name=self.name, status="ok", summary=summary, payload=payload)


def build_default_tool_registry(
    *,
    workspace_dir: Path,
    executor: CommandExecutor,
    knowledge_loader: KnowledgeLoader,
) -> ToolRegistry:
    """Create the built-in structured tool registry for this milestone."""

    context = ToolContext(
        workspace_dir=Path(workspace_dir).resolve(),
        executor=executor,
        knowledge_loader=knowledge_loader,
    )
    return ToolRegistry(
        [
            ShellCommandTool(context),
            KnowledgeLoadTool(context),
            RepoSearchTool(context),
            FileReadTool(context),
            FileWriteTool(context),
            FilePatchTool(context),
            TestRunTool(context),
        ]
    )


def _resolve_workspace_path(workspace_dir: Path, raw_path: str) -> Path:
    if not raw_path:
        raise ValueError("tool path must not be empty")
    workspace_dir = Path(workspace_dir).resolve()
    candidate = (workspace_dir / raw_path).resolve()
    if not str(candidate).startswith(str(workspace_dir)):
        raise ValueError("tool path must stay within the workspace")
    return candidate


def _search_workspace_without_rg(workspace_dir: Path, pattern: str) -> str:
    """Fallback repository search when ripgrep is unavailable."""

    matches: list[str] = []
    for path in sorted(workspace_dir.rglob("*")):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            if pattern in line:
                rel_path = path.relative_to(workspace_dir)
                matches.append(f"./{rel_path}:{line_number}:{line}")
    return "\n".join(matches) + ("\n" if matches else "")
