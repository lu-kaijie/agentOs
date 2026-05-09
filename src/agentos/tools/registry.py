"""LangChain-native structured tool runtime and registry."""

from __future__ import annotations

import shlex
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from agentos.harness.execution import CommandExecutor, ExecutionRequest
from agentos.knowledge import KnowledgeLoader
from agentos.policy import CommandApprovalPolicy
from agentos.tools.models import ToolInvocation, ToolResult

_TOOL_RUNTIME_OPTIONS: ContextVar[dict[str, object]] = ContextVar(
    "tool_runtime_options",
    default={"approved": False, "collector": None},
)


@dataclass(slots=True)
class ToolContext:
    """Context shared by LangChain-bound coding tools."""

    workspace_dir: Path
    executor: CommandExecutor
    knowledge_loader: KnowledgeLoader
    approval_policy: CommandApprovalPolicy


class ShellCommandArgs(BaseModel):
    command: list[str] = Field(description="Command and argv list to execute.")
    cwd: str = Field(description="Working directory for command execution.")


class KnowledgeLoadArgs(BaseModel):
    topic: str = Field(description="Knowledge topic to load from the knowledge directory.")


class SkillListArgs(BaseModel):
    role: str = Field(default="", description="Optional role hint for compact skill catalog rendering.")


class SkillLoadArgs(BaseModel):
    name: str = Field(description="Skill name to load from the skills directory.")
    level: str = Field(default="summary", description="One of: summary, full, reference, script.")
    target: str = Field(default="", description="Optional reference/script target path for deeper disclosure.")


class RepoSearchArgs(BaseModel):
    pattern: str = Field(description="Plain-text pattern to search inside the workspace.")


class FileReadArgs(BaseModel):
    path: str = Field(description="Relative workspace path to read.")


class FileWriteArgs(BaseModel):
    path: str = Field(description="Relative workspace path to write.")
    content: str = Field(description="Full file content to write.")


class FilePatchArgs(BaseModel):
    path: str = Field(description="Relative workspace path to patch.")
    target: str = Field(description="Existing text to replace once.")
    replacement: str = Field(description="Replacement text.")


class TestRunArgs(BaseModel):
    command: str = Field(description="Bounded test command string.")


class ToolRegistry:
    """Register and invoke LangChain-native coding tools."""

    def __init__(self, tools: list[BaseTool]):
        self._tools = {tool.name: tool for tool in tools}

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {"name": tool.name, "description": tool.description}
            for tool in sorted(self._tools.values(), key=lambda item: item.name)
        ]

    def get_tool(self, tool_name: str) -> BaseTool:
        if tool_name not in self._tools:
            raise KeyError(f"Tool '{tool_name}' is not registered")
        return self._tools[tool_name]

    def as_langchain_tools(self) -> list[BaseTool]:
        return [self._tools[name] for name in sorted(self._tools)]

    def invoke(self, invocation: ToolInvocation) -> ToolResult:
        arguments = dict(invocation.arguments)
        approved = bool(arguments.pop("_approved", False))
        existing = _TOOL_RUNTIME_OPTIONS.get({})
        collector = existing.get("collector")
        tool = self.get_tool(invocation.tool_name)
        with tool_runtime_context(approved=approved, collector=collector):
            payload = tool.invoke(arguments)
        if not isinstance(payload, dict):
            payload = {"content": payload}
        status = str(payload.pop("_status", "ok"))
        summary = str(payload.pop("_summary", f"{tool.name} completed"))
        return ToolResult(tool_name=tool.name, status=status, summary=summary, payload=payload)


def build_default_tool_registry(
    *,
    workspace_dir: Path,
    executor: CommandExecutor,
    knowledge_loader: KnowledgeLoader,
    approval_policy: CommandApprovalPolicy,
) -> ToolRegistry:
    """Create the built-in LangChain tool runtime for this milestone."""

    context = ToolContext(
        workspace_dir=Path(workspace_dir).resolve(),
        executor=executor,
        knowledge_loader=knowledge_loader,
        approval_policy=approval_policy,
    )

    def shell_command(command: list[str], cwd: str) -> dict[str, object]:
        policy = context.approval_policy.evaluate(command)
        if policy.requires_approval and not _tool_runtime_options().get("approved", False):
            payload = {
                "_status": "blocked",
                "_summary": f"approval required for command '{command[0]}'",
                "command": command,
                "cwd": cwd,
                "policy": policy.to_dict(),
            }
            _emit_tool_record("shell_command", "blocked", payload)
            return payload
        result = context.executor.run(ExecutionRequest(command=command, cwd=cwd))
        payload = {
            "_summary": f"exit_code={result.exit_code} timed_out={result.timed_out}",
            "command": result.command,
            "cwd": result.cwd,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": result.timed_out,
        }
        _emit_tool_record("shell_command", "ok", payload)
        return payload

    def knowledge_load(topic: str) -> dict[str, object]:
        message = context.knowledge_loader.load_topic(topic)
        payload = {
            "_summary": f"loaded topic '{topic}'",
            "topic": message.additional_kwargs.get("topic", topic),
            "source": message.additional_kwargs.get("source", ""),
            "content": message.content,
        }
        _emit_tool_record("knowledge_load", "ok", payload)
        return payload

    def skill_list(role: str = "") -> dict[str, object]:
        catalog = context.knowledge_loader.skill_catalog(role=role)
        payload = {
            "_summary": f"listed {len(catalog)} skill(s)",
            "role": role,
            "skills": catalog,
        }
        _emit_tool_record("skill_list", "ok", payload)
        return payload

    def skill_load(name: str, level: str = "summary", target: str = "") -> dict[str, object]:
        topic = name if level == "summary" and not target else f"{name}#{'ref:' + target if level == 'reference' and target else 'script:' + target if level == 'script' and target else level}"
        message = context.knowledge_loader.load_skill(topic)
        payload = {
            "_summary": f"loaded skill '{name}' level={level}",
            "name": name,
            "level": level,
            "target": target,
            "content": message.content,
            "source": message.additional_kwargs.get("source", ""),
        }
        _emit_tool_record("skill_load", "ok", payload)
        return payload

    def repo_search(pattern: str) -> dict[str, object]:
        if not pattern:
            raise ValueError("repo_search requires a non-empty pattern")
        try:
            result = context.executor.run(
                ExecutionRequest(command=["rg", "-n", pattern, "."], cwd=str(context.workspace_dir))
            )
            payload = {
                "_summary": f"search pattern='{pattern}' exit_code={result.exit_code}",
                "pattern": pattern,
                "engine": "rg",
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timed_out": result.timed_out,
            }
            _emit_tool_record("repo_search", "ok", payload)
            return payload
        except FileNotFoundError:
            stdout = _search_workspace_without_rg(context.workspace_dir, pattern)
            payload = {
                "_summary": f"search pattern='{pattern}' exit_code={0 if stdout else 1}",
                "pattern": pattern,
                "engine": "python",
                "exit_code": 0 if stdout else 1,
                "stdout": stdout,
                "stderr": "",
                "timed_out": False,
            }
            _emit_tool_record("repo_search", "ok", payload)
            return payload

    def file_read(path: str) -> dict[str, object]:
        resolved = _resolve_workspace_path(context.workspace_dir, path)
        payload = {
            "_summary": f"read '{resolved.name}'",
            "path": str(resolved),
            "content": resolved.read_text(encoding="utf-8"),
        }
        _emit_tool_record("file_read", "ok", payload)
        return payload

    def file_write(path: str, content: str) -> dict[str, object]:
        resolved = _resolve_workspace_path(context.workspace_dir, path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        payload = {
            "_summary": f"wrote '{resolved.name}'",
            "path": str(resolved),
            "bytes_written": len(content.encode("utf-8")),
        }
        _emit_tool_record("file_write", "ok", payload)
        return payload

    def file_patch(path: str, target: str, replacement: str) -> dict[str, object]:
        resolved = _resolve_workspace_path(context.workspace_dir, path)
        if not target:
            raise ValueError("file_patch requires a non-empty target string")
        content = resolved.read_text(encoding="utf-8")
        replacement_count = content.count(target)
        if replacement_count == 0:
            raise ValueError(f"target text not found in '{resolved.name}'")
        updated = content.replace(target, replacement, 1)
        resolved.write_text(updated, encoding="utf-8")
        payload = {
            "_summary": f"patched '{resolved.name}'",
            "path": str(resolved),
            "target": target,
            "replacement": replacement,
            "replacement_count": replacement_count,
        }
        _emit_tool_record("file_patch", "ok", payload)
        return payload

    def test_run(command: str) -> dict[str, object]:
        command_text = command.strip()
        if not command_text:
            raise ValueError("test_run requires a command string")
        argv = shlex.split(command_text)
        if argv and argv[0] == "python":
            argv[0] = sys.executable
        policy = context.approval_policy.evaluate(argv)
        if policy.requires_approval and not _tool_runtime_options().get("approved", False):
            payload = {
                "_status": "blocked",
                "_summary": f"approval required for command '{argv[0]}'",
                "command": argv,
                "cwd": str(context.workspace_dir),
                "policy": policy.to_dict(),
            }
            _emit_tool_record("test_run", "blocked", payload)
            return payload
        result = context.executor.run(
            ExecutionRequest(command=argv, cwd=str(context.workspace_dir))
        )
        payload = {
            "_summary": f"test command exit_code={result.exit_code}",
            "command": argv,
            "cwd": result.cwd,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": result.timed_out,
        }
        _emit_tool_record("test_run", "ok", payload)
        return payload

    tools = [
        StructuredTool.from_function(
            name="shell_command",
            description="Run a shell-like command through the harness executor.",
            func=shell_command,
            args_schema=ShellCommandArgs,
        ),
        StructuredTool.from_function(
            name="knowledge_load",
            description="Load a knowledge topic from the knowledge directory.",
            func=knowledge_load,
            args_schema=KnowledgeLoadArgs,
        ),
        StructuredTool.from_function(
            name="skill_list",
            description="List the compact skill catalog with names and one-line usage hints.",
            func=skill_list,
            args_schema=SkillListArgs,
        ),
        StructuredTool.from_function(
            name="skill_load",
            description="Load a skill entry, summary, reference, or full skill content from the skills directory.",
            func=skill_load,
            args_schema=SkillLoadArgs,
        ),
        StructuredTool.from_function(
            name="repo_search",
            description="Search the repository with ripgrep or bounded fallback.",
            func=repo_search,
            args_schema=RepoSearchArgs,
        ),
        StructuredTool.from_function(
            name="file_read",
            description="Read one workspace file.",
            func=file_read,
            args_schema=FileReadArgs,
        ),
        StructuredTool.from_function(
            name="file_write",
            description="Write one workspace file.",
            func=file_write,
            args_schema=FileWriteArgs,
        ),
        StructuredTool.from_function(
            name="file_patch",
            description="Apply one bounded text replacement inside a workspace file.",
            func=file_patch,
            args_schema=FilePatchArgs,
        ),
        StructuredTool.from_function(
            name="test_run",
            description="Run a bounded test command in the workspace.",
            func=test_run,
            args_schema=TestRunArgs,
        ),
    ]
    return ToolRegistry(tools)


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


@contextmanager
def tool_runtime_context(
    *,
    approved: bool = False,
    collector: list[dict[str, object]] | None = None,
):
    """Set per-turn tool runtime options for LangChain-native invocations."""

    token = _TOOL_RUNTIME_OPTIONS.set({"approved": approved, "collector": collector})
    try:
        yield
    finally:
        _TOOL_RUNTIME_OPTIONS.reset(token)


def _tool_runtime_options() -> dict[str, object]:
    return dict(_TOOL_RUNTIME_OPTIONS.get({}))


def _emit_tool_record(tool_name: str, status: str, payload: dict[str, object]) -> None:
    options = _tool_runtime_options()
    collector = options.get("collector")
    if not isinstance(collector, list):
        return
    collector.append(
        ToolResult(
            tool_name=tool_name,
            status=status,
            summary=str(payload.get("_summary", f"{tool_name} completed")),
            payload={key: value for key, value in payload.items() if not key.startswith("_")},
        ).to_dict()
    )
