"""Long-session context management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage


class ContextManager:
    """Persist and compact message history."""

    def __init__(self, context_dir: Path):
        self.context_dir = Path(context_dir)
        self.context_dir.mkdir(parents=True, exist_ok=True)

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

    @staticmethod
    def total_chars(messages: Iterable[BaseMessage]) -> int:
        return sum(len(ContextManager._string_content(message)) for message in messages)

    def _session_path(self, session_id: str) -> Path:
        return self.context_dir / f"{session_id}.json"

    @staticmethod
    def _string_content(message: BaseMessage) -> str:
        if isinstance(message.content, str):
            return message.content
        return str(message.content)

    def _summarize_message(self, message: BaseMessage) -> str:
        content = self._string_content(message).strip().replace("\n", " ")
        content = content[:100]
        return f"- {message.type}: {content}"

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
