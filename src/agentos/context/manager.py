"""Long-session context management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from agentos.context.lifecycle import ContextLifecycleManager
from agentos.context.models import LayeredMemory
from agentos.context.policy import ContextPolicyRuntime


class ContextManager:
    """Persist and compact message history."""

    def __init__(self, context_dir: Path):
        self.context_dir = Path(context_dir)
        self.context_dir.mkdir(parents=True, exist_ok=True)
        self.policy_runtime = ContextPolicyRuntime()
        self.lifecycle_manager = ContextLifecycleManager(self)

    def save_session(self, session_id: str, messages: list[BaseMessage]) -> Path:
        path = self._session_path(session_id)
        payload = [self._serialize_message(message) for message in messages]
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def load_session(self, session_id: str) -> list[BaseMessage]:
        path = self._session_path(session_id)
        if not path.exists():
            raise FileNotFoundError(f"Session '{session_id}' does not exist")
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [self._deserialize_message(item) for item in payload]

    def save_memory(self, session_id: str, memory: LayeredMemory) -> Path:
        path = self._memory_path(session_id)
        path.write_text(json.dumps(memory.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def load_memory(self, session_id: str, *, default: LayeredMemory | None = None) -> LayeredMemory:
        path = self._memory_path(session_id)
        if not path.exists():
            if default is not None:
                return default
            raise FileNotFoundError(f"Memory for session '{session_id}' does not exist")
        payload = json.loads(path.read_text(encoding="utf-8"))
        return LayeredMemory.from_dict(payload)

    def compact_messages(
        self,
        session_id: str,
        messages: list[BaseMessage],
        *,
        max_chars: int = 400,
        keep_last: int = 2,
    ) -> tuple[list[BaseMessage], Path]:
        total_chars = self.total_chars(messages)
        if total_chars <= max_chars:
            path = self.save_session(session_id, messages)
            return messages, path

        preserved = messages[-keep_last:] if keep_last else []
        older = messages[:-keep_last] if keep_last else messages
        summary_lines = [self._summarize_message(message) for message in older]
        compacted: list[BaseMessage] = [
            SystemMessage(content="Compacted history:\n" + "\n".join(summary_lines))
        ] + preserved
        path = self.save_session(session_id, compacted)
        return compacted, path

    def build_context_bundle(
        self,
        *,
        session_id: str,
        task: str,
        state: dict[str, object],
        workspace_dir: Path,
        role: str = "executor",
        max_chars: int = 600,
    ) -> dict[str, object]:
        """Build an inspectable task-aware context bundle through policy runtime."""

        bundle, _record = self.policy_runtime.build_bundle(
            session_id=session_id,
            role=role,
            task=task,
            state=state,
            workspace_dir=Path(workspace_dir),
            max_chars=max_chars,
        )
        return bundle

    def prepare_role_context(
        self,
        *,
        session_id: str,
        task: str,
        role: str,
        state: dict[str, object],
        workspace_dir: Path,
        max_chars: int = 600,
        trigger_reason: str = "prepare_context",
    ) -> tuple[dict[str, object], object, LayeredMemory, object]:
        try:
            messages = self.load_session(session_id)
        except FileNotFoundError:
            messages = []
        memory, audit = self.lifecycle_manager.maintain(
            session_id=session_id,
            task=task,
            role=role,
            state=state,
            workspace_dir=Path(workspace_dir),
            messages=messages,
            trigger_reason=trigger_reason,
        )
        enriched_state = {
            **state,
            "memory_state": memory.to_dict(),
            "context_audit_records": [
                *[item for item in state.get("context_audit_records", []) if isinstance(item, dict)],
                audit.to_dict(),
            ],
        }
        bundle, record = self.policy_runtime.build_bundle(
            session_id=session_id,
            role=role,
            task=task,
            state=enriched_state,
            workspace_dir=Path(workspace_dir),
            max_chars=max_chars,
        )
        return bundle, record, memory, audit

    @staticmethod
    def total_chars(messages: Iterable[BaseMessage]) -> int:
        return sum(len(ContextManager._string_content(message)) for message in messages)

    def _session_path(self, session_id: str) -> Path:
        return self.context_dir / f"{session_id}.json"

    def _memory_path(self, session_id: str) -> Path:
        return self.context_dir / f"{session_id}.memory.json"

    @staticmethod
    def _string_content(message: BaseMessage) -> str:
        if isinstance(message.content, str):
            return message.content
        return str(message.content)

    @staticmethod
    def string_content(message: BaseMessage) -> str:
        return ContextManager._string_content(message)

    def serialize_message(self, message: BaseMessage) -> dict[str, str]:
        return self._serialize_message(message)

    def deserialize_message(self, payload: dict[str, str]) -> BaseMessage:
        return self._deserialize_message(payload)

    def _summarize_message(self, message: BaseMessage) -> str:
        content = self._string_content(message).strip().replace("\n", " ")
        content = content[:100]
        return f"- {message.type}: {content}"

    def render_bundle(self, bundle: dict[str, object], *, max_chars: int = 600) -> str:
        """Render a compact text preview of a structured context bundle."""

        lines = [
            f"task={bundle.get('task', '')}",
            f"hints={json.dumps(bundle.get('task_hints', {}), ensure_ascii=False, sort_keys=True)}",
            f"history={bundle.get('history_summary', '')}",
            f"tools={bundle.get('tool_summary', '')}",
            f"trace={bundle.get('trace_summary', '')}",
            f"workspace={self._workspace_preview(bundle.get('workspace_signals', []))}",
        ]
        rendered = "\n".join(line for line in lines if line.strip())
        if len(rendered) <= max_chars:
            return rendered
        return rendered[: max_chars - 3] + "..."

    def _history_entries(
        self,
        completed_tasks: list[str],
        step_outputs: list[str],
    ) -> list[dict[str, str]]:
        entries: list[dict[str, str]] = []
        for task, output in zip(completed_tasks, step_outputs):
            preview = output.strip().replace("\n", " ")
            entries.append({"task": task, "output_preview": preview[:120]})
        return entries

    def _workspace_signals(
        self,
        *,
        workspace_dir: Path,
        hints: dict[str, str],
    ) -> list[dict[str, object]]:
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

    def _task_hints(self, task: str) -> dict[str, str]:
        task = task.strip()
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

    def _serialize_message(self, message: BaseMessage) -> dict[str, str]:
        payload = {
            "type": message.type,
            "content": self._string_content(message),
        }
        topic = message.additional_kwargs.get("topic") if hasattr(message, "additional_kwargs") else None
        source = message.additional_kwargs.get("source") if hasattr(message, "additional_kwargs") else None
        if topic:
            payload["topic"] = str(topic)
        if source:
            payload["source"] = str(source)
        if isinstance(message, ToolMessage):
            payload["tool_call_id"] = message.tool_call_id
        return payload

    def _deserialize_message(self, payload: dict[str, str]) -> BaseMessage:
        message_type = payload["type"]
        content = payload["content"]
        if message_type == "human":
            return HumanMessage(content=content)
        if message_type == "ai":
            return AIMessage(content=content)
        if message_type == "tool":
            return ToolMessage(content=content, tool_call_id=payload.get("tool_call_id", "restored-tool"))
        return SystemMessage(content=content)
