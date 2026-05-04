"""Configurable context-policy runtime built with LangChain runnables."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from langchain_core.runnables import RunnableLambda, RunnableParallel


@dataclass(slots=True)
class ContextPolicyRecord:
    """Inspectable record of one context selection step."""

    session_id: str
    role: str
    task: str
    selectors: list[str]
    reducers: list[str]
    retrievers: list[str]
    sources: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class ContextPolicyRuntime:
    """Assemble bounded runtime context through a configurable pipeline."""

    def __init__(self) -> None:
        self._pipeline = RunnableParallel(
            task_hints=RunnableLambda(self._task_hints),
            history_entries=RunnableLambda(self._history_entries),
            tool_results=RunnableLambda(self._tool_results),
            execution_trace=RunnableLambda(self._execution_trace),
            workspace_signals=RunnableLambda(self._workspace_signals),
            role_name=RunnableLambda(lambda data: str(data.get("role", "executor"))),
            session_id=RunnableLambda(lambda data: str(data.get("session_id", ""))),
            task=RunnableLambda(lambda data: str(data.get("task", ""))),
        ) | RunnableLambda(self._assemble_bundle)

    def build_bundle(
        self,
        *,
        session_id: str,
        role: str,
        task: str,
        state: dict[str, object],
        workspace_dir: Path,
        max_chars: int = 600,
    ) -> tuple[dict[str, object], ContextPolicyRecord]:
        payload = self._pipeline.invoke(
            {
                "session_id": session_id,
                "role": role,
                "task": task,
                "state": state,
                "workspace_dir": Path(workspace_dir),
                "max_chars": max_chars,
            }
        )
        record = ContextPolicyRecord(
            session_id=session_id,
            role=role,
            task=task,
            selectors=["task_hints", "history_entries", "tool_results"],
            reducers=["history_summary", "tool_summary", "trace_summary"],
            retrievers=["workspace_signals", "role_view"],
            sources=[str(item) for item in payload.get("sources", [])],
        )
        return payload, record

    def _task_hints(self, data: dict[str, object]) -> dict[str, str]:
        task = str(data.get("task", "")).strip()
        if ":" not in task:
            return {"action": "respond", "raw": task}
        prefix, remainder = task.split(":", 1)
        action = prefix.strip()
        content = remainder.strip()
        hints = {"action": action, "raw": content}
        if action in {"read", "write", "patch"}:
            path = content.split("=>", 1)[0].strip()
            hints["path"] = path
        elif action == "search":
            hints["pattern"] = content
        elif action == "knowledge":
            hints["topic"] = content
        elif action in {"run", "test"}:
            hints["command"] = content
        return hints

    def _history_entries(self, data: dict[str, object]) -> list[dict[str, str]]:
        state = data["state"]
        completed_tasks = [str(item) for item in state.get("completed_tasks", [])]
        step_outputs = [str(item) for item in state.get("step_outputs", [])]
        entries: list[dict[str, str]] = []
        for task, output in zip(completed_tasks, step_outputs):
            preview = output.strip().replace("\n", " ")
            entries.append({"task": task, "output_preview": preview[:120]})
        return entries

    def _tool_results(self, data: dict[str, object]) -> list[dict[str, object]]:
        state = data["state"]
        return [item for item in state.get("tool_results", []) if isinstance(item, dict)]

    def _execution_trace(self, data: dict[str, object]) -> list[str]:
        state = data["state"]
        return [str(item) for item in state.get("execution_trace", [])]

    def _workspace_signals(self, data: dict[str, object]) -> list[dict[str, object]]:
        workspace_dir = Path(data["workspace_dir"])
        hints = self._task_hints(data)
        signals: list[dict[str, object]] = []
        path_hint = hints.get("path", "")
        if path_hint:
            path = (workspace_dir / path_hint).resolve()
            signal: dict[str, object] = {
                "kind": "file",
                "path": path_hint,
                "exists": path.exists(),
            }
            if path.exists() and path.is_file():
                try:
                    signal["preview"] = path.read_text(encoding="utf-8")[:200]
                except UnicodeDecodeError:
                    signal["preview"] = "<binary>"
            signals.append(signal)
        pattern_hint = hints.get("pattern", "")
        if pattern_hint:
            matches: list[str] = []
            for path in sorted(workspace_dir.rglob("*")):
                if len(matches) >= 5:
                    break
                if not path.is_file():
                    continue
                try:
                    content = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                if pattern_hint in content:
                    matches.append(str(path.relative_to(workspace_dir)))
            signals.append({"kind": "search", "pattern": pattern_hint, "matches": matches})
        top_level = sorted(path.name for path in workspace_dir.iterdir())[:8] if workspace_dir.exists() else []
        signals.append({"kind": "workspace", "top_level_entries": top_level})
        return signals

    def _assemble_bundle(self, data: dict[str, object]) -> dict[str, object]:
        history_entries = [
            item for item in data.get("history_entries", []) if isinstance(item, dict)
        ]
        tool_results = [
            item for item in data.get("tool_results", []) if isinstance(item, dict)
        ]
        execution_trace = [str(item) for item in data.get("execution_trace", [])]
        workspace_signals = [
            item for item in data.get("workspace_signals", []) if isinstance(item, dict)
        ]
        task_hints = dict(data.get("task_hints", {}))
        max_chars = int(data.get("max_chars", 600))
        role_name = str(data.get("role_name", "executor"))

        bundle = {
            "session_id": str(data.get("session_id", "")),
            "task": str(data.get("task", "")),
            "role": role_name,
            "task_hints": task_hints,
            "history_summary": self._compress_lines(
                [f"{entry['task']} => {entry['output_preview']}" for entry in history_entries],
                max_chars=max_chars // 3,
            ),
            "recent_history": history_entries[-3:],
            "tool_summary": self._compress_lines(
                [self._tool_summary(item) for item in tool_results],
                max_chars=max_chars // 3,
            ),
            "recent_tool_results": tool_results[-3:],
            "trace_summary": self._compress_lines(execution_trace, max_chars=max_chars // 4),
            "workspace_signals": workspace_signals,
            "sources": self._bundle_sources(history_entries, tool_results, workspace_signals),
        }
        bundle["role_view"] = self._role_view(role_name, bundle)
        bundle["bundle_preview"] = self.render_bundle(bundle, max_chars=max_chars)
        return bundle

    def render_bundle(self, bundle: dict[str, object], *, max_chars: int = 600) -> str:
        lines = [
            f"role={bundle.get('role', '')}",
            f"task={bundle.get('task', '')}",
            f"hints={bundle.get('task_hints', {})}",
            f"history={bundle.get('history_summary', '')}",
            f"tools={bundle.get('tool_summary', '')}",
            f"trace={bundle.get('trace_summary', '')}",
            f"role_view={bundle.get('role_view', {})}",
            f"workspace={self._workspace_preview(bundle.get('workspace_signals', []))}",
        ]
        rendered = "\n".join(line for line in lines if line.strip())
        if len(rendered) <= max_chars:
            return rendered
        return rendered[: max_chars - 3] + "..."

    def _role_view(self, role_name: str, bundle: dict[str, object]) -> dict[str, object]:
        if role_name == "planner":
            return {
                "focus": "task-scoping",
                "history": bundle.get("recent_history", [])[-2:],
                "workspace": bundle.get("workspace_signals", [])[:1],
            }
        if role_name == "reviewer":
            return {
                "focus": "verification",
                "tool_results": bundle.get("recent_tool_results", [])[-3:],
                "history": bundle.get("recent_history", [])[-1:],
            }
        return {
            "focus": "execution",
            "history": bundle.get("recent_history", [])[-2:],
            "tool_results": bundle.get("recent_tool_results", [])[-2:],
            "workspace": bundle.get("workspace_signals", [])[:2],
        }

    def _compress_lines(self, lines: list[str], *, max_chars: int) -> str:
        if not lines:
            return ""
        cleaned = [line.strip().replace("\n", " ") for line in lines if line.strip()]
        if not cleaned:
            return ""
        rendered = " | ".join(cleaned)
        if len(rendered) <= max_chars:
            return rendered
        head = cleaned[:2]
        tail = cleaned[-2:] if len(cleaned) > 2 else []
        compact = " | ".join([*head, "...", *tail])
        if len(compact) <= max_chars:
            return compact
        return compact[: max_chars - 3] + "..."

    def _tool_summary(self, item: dict[str, object]) -> str:
        tool_name = str(item.get("tool_name", "unknown"))
        summary = str(item.get("summary", ""))
        return f"{tool_name}: {summary}"

    def _bundle_sources(
        self,
        history_entries: list[dict[str, str]],
        tool_results: list[dict[str, object]],
        workspace_signals: list[dict[str, object]],
    ) -> list[str]:
        sources: list[str] = []
        if history_entries:
            sources.append("history")
        if tool_results:
            sources.append("tool_results")
        if workspace_signals:
            sources.append("workspace")
        return sources

    def _workspace_preview(self, signals: object) -> str:
        if not isinstance(signals, list):
            return ""
        previews: list[str] = []
        for signal in signals:
            if not isinstance(signal, dict):
                continue
            kind = str(signal.get("kind", ""))
            if kind == "file":
                previews.append(f"file:{signal.get('path')} exists={signal.get('exists')}")
            elif kind == "search":
                previews.append(
                    f"search:{signal.get('pattern')} matches={len(signal.get('matches', []))}"
                )
            elif kind == "workspace":
                previews.append(
                    "top=" + ",".join(str(item) for item in signal.get("top_level_entries", []))
                )
        return " | ".join(previews)
