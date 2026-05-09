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
            memory_state=RunnableLambda(self._memory_state),
            active_skills=RunnableLambda(
                lambda data: [
                    item for item in data["state"].get("active_skills", []) if isinstance(item, dict)
                ]
            ),
            matched_skills=RunnableLambda(
                lambda data: [
                    item for item in data["state"].get("matched_skills", []) if isinstance(item, dict)
                ]
            ),
            skills_catalog=RunnableLambda(
                lambda data: [
                    item for item in data["state"].get("skills_catalog", []) if isinstance(item, dict)
                ]
            ),
            skills_available=RunnableLambda(lambda data: bool(data["state"].get("skills_available", False))),
            skills_count=RunnableLambda(lambda data: int(data["state"].get("skills_count", 0))),
            skills_hint=RunnableLambda(lambda data: str(data["state"].get("skills_hint", ""))),
            context_audit_records=RunnableLambda(
                lambda data: [
                    item for item in data["state"].get("context_audit_records", []) if isinstance(item, dict)
                ]
            ),
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
            selectors=["task_hints", "history_entries", "tool_results", "memory_state"],
            reducers=["history_summary", "tool_summary", "trace_summary", "memory_summary"],
            retrievers=["workspace_signals", "role_view", "budget_allocations"],
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

    def _memory_state(self, data: dict[str, object]) -> dict[str, object]:
        memory = data["state"].get("memory_state", {})
        if isinstance(memory, dict):
            return memory
        return {}

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
        memory_state = dict(data.get("memory_state", {}))
        task_hints = dict(data.get("task_hints", {}))
        max_chars = int(data.get("max_chars", 600))
        role_name = str(data.get("role_name", "executor"))
        recent_messages = [
            item for item in memory_state.get("recent_messages", []) if isinstance(item, dict)
        ]
        working_memory = dict(memory_state.get("working_memory", {}))
        user_preferences = dict(memory_state.get("user_preferences", {}))
        tool_facts = [
            item for item in memory_state.get("tool_facts", []) if isinstance(item, dict)
        ]
        workspace_memory = dict(memory_state.get("workspace_state", {}))
        failure_memory = [
            item for item in memory_state.get("failure_memory", []) if isinstance(item, dict)
        ]
        session_summary = str(memory_state.get("session_summary", ""))
        budget_allocations = self._budget_allocations(role_name)
        context_audits = [
            item for item in data.get("context_audit_records", []) if isinstance(item, dict)
        ]

        bundle = {
            "session_id": str(data.get("session_id", "")),
            "task": str(data.get("task", "")),
            "role": role_name,
            "task_hints": task_hints,
            "active_skills": [item for item in data.get("active_skills", []) if isinstance(item, dict)],
            "matched_skills": [item for item in data.get("matched_skills", []) if isinstance(item, dict)],
            "skills_catalog": [item for item in data.get("skills_catalog", []) if isinstance(item, dict)],
            "skills_available": bool(data.get("skills_available", False)),
            "skills_count": int(data.get("skills_count", 0)),
            "skills_hint": str(data.get("skills_hint", "")),
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
            "tool_facts": tool_facts[-3:],
            "trace_summary": self._compress_lines(execution_trace, max_chars=max_chars // 4),
            "workspace_signals": workspace_signals,
            "sources": self._bundle_sources(history_entries, tool_results, workspace_signals, memory_state),
            "memory_summary": self._memory_summary(
                working_memory=working_memory,
                user_preferences=user_preferences,
                tool_facts=tool_facts,
                failure_memory=failure_memory,
                session_summary=session_summary,
                max_chars=max_chars // 2,
            ),
            "layered_memory": {
                "recent_messages": recent_messages[-4:],
                "working_memory": working_memory,
                "user_preferences": user_preferences,
                "tool_facts": tool_facts[-3:],
                "workspace_state": workspace_memory,
                "failure_memory": failure_memory[-3:],
                "session_summary": session_summary,
            },
            "budget_allocations": budget_allocations,
            "context_audit_records": context_audits[-3:],
        }
        bundle["skills_hint"] = self._skill_summary(
            skills_catalog=bundle.get("skills_catalog", []),
            matched_skills=bundle.get("matched_skills", []),
            role_name=role_name,
        )
        bundle["role_view"] = self._role_view(role_name, bundle)
        bundle["bundle_preview"] = self.render_bundle(bundle, max_chars=max_chars)
        return bundle

    def render_bundle(self, bundle: dict[str, object], *, max_chars: int = 600) -> str:
        lines = [
            f"role={bundle.get('role', '')}",
            f"task={bundle.get('task', '')}",
            f"hints={bundle.get('task_hints', {})}",
            f"skills={bundle.get('skills_hint', '')}",
            f"history={bundle.get('history_summary', '')}",
            f"memory={bundle.get('memory_summary', '')}",
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
                "skills": self._skill_names(bundle.get("skills_catalog", []), limit=4),
                "working_memory": bundle.get("layered_memory", {}).get("working_memory", {}),
                "workspace": bundle.get("workspace_signals", [])[:1],
                "budget": bundle.get("budget_allocations", {}),
            }
        if role_name == "reviewer":
            return {
                "focus": "verification",
                "tool_results": bundle.get("recent_tool_results", [])[-3:],
                "tool_facts": bundle.get("tool_facts", [])[-3:],
                "matched_skills": self._skill_names(bundle.get("matched_skills", []), limit=2),
                "failure_memory": bundle.get("layered_memory", {}).get("failure_memory", [])[-3:],
                "history": bundle.get("recent_history", [])[-1:],
                "budget": bundle.get("budget_allocations", {}),
            }
        return {
            "focus": "execution",
            "history": bundle.get("recent_history", [])[-2:],
            "tool_results": bundle.get("recent_tool_results", [])[-2:],
            "skills": self._skill_names(bundle.get("skills_catalog", []), limit=4),
            "matched_skills": self._skill_names(bundle.get("matched_skills", []), limit=2),
            "working_memory": bundle.get("layered_memory", {}).get("working_memory", {}),
            "workspace": bundle.get("workspace_signals", [])[:2],
            "workspace_state": bundle.get("layered_memory", {}).get("workspace_state", {}),
            "budget": bundle.get("budget_allocations", {}),
        }

    def _skill_summary(
        self,
        skills_catalog: object,
        matched_skills: object,
        role_name: str,
    ) -> str:
        if not isinstance(skills_catalog, list) or not skills_catalog:
            return ""
        lines = [f"skills({role_name})"]
        available_names = [
            str(skill.get("name", "")) for skill in skills_catalog[:6] if isinstance(skill, dict)
        ]
        if available_names:
            lines.append("available=" + ", ".join(name for name in available_names if name))
        if isinstance(matched_skills, list) and matched_skills:
            matched_names = [
                str(skill.get("name", "")) for skill in matched_skills[:3] if isinstance(skill, dict)
            ]
            if matched_names:
                lines.append("matched_hint=" + ", ".join(name for name in matched_names if name))
        for skill in skills_catalog[:3]:
            if not isinstance(skill, dict):
                continue
            line = str(skill.get("name", ""))
            description = str(skill.get("description", "")).strip()
            role_hint = str(skill.get("when_to_use", "")).strip()
            if description:
                line += f": {description}"
            if role_hint:
                line += f" | hint={role_hint}"
            lines.append(line)
        return self._compress_lines(lines, max_chars=220)

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

    def _skill_names(self, skills: object, *, limit: int) -> list[str]:
        if not isinstance(skills, list):
            return []
        names: list[str] = []
        for skill in skills[:limit]:
            if not isinstance(skill, dict):
                continue
            name = str(skill.get("name", "")).strip()
            if name:
                names.append(name)
        return names

    def _tool_summary(self, item: dict[str, object]) -> str:
        tool_name = str(item.get("tool_name", "unknown"))
        summary = str(item.get("summary", ""))
        return f"{tool_name}: {summary}"

    def _bundle_sources(
        self,
        history_entries: list[dict[str, str]],
        tool_results: list[dict[str, object]],
        workspace_signals: list[dict[str, object]],
        memory_state: dict[str, object],
    ) -> list[str]:
        sources: list[str] = []
        if history_entries:
            sources.append("history")
        if tool_results:
            sources.append("tool_results")
        if workspace_signals:
            sources.append("workspace")
        if memory_state:
            sources.append("layered_memory")
        return sources

    def _memory_summary(
        self,
        *,
        working_memory: dict[str, object],
        user_preferences: dict[str, object],
        tool_facts: list[dict[str, object]],
        failure_memory: list[dict[str, object]],
        session_summary: str,
        max_chars: int,
    ) -> str:
        lines = [session_summary]
        if working_memory.get("current_goal"):
            lines.append(f"goal={working_memory.get('current_goal')}")
        constraints = [str(item) for item in working_memory.get("accepted_constraints", [])]
        if constraints:
            lines.append("constraints=" + ", ".join(constraints[:3]))
        if user_preferences.get("preferred_language"):
            lines.append(f"language={user_preferences.get('preferred_language')}")
        if tool_facts:
            lines.append(f"tool_facts={len(tool_facts)}")
        if failure_memory:
            lines.append(f"failures={len(failure_memory)}")
        return self._compress_lines(lines, max_chars=max_chars)

    def _budget_allocations(self, role_name: str) -> dict[str, int]:
        if role_name == "planner":
            return {"working_memory": 260, "user_preferences": 80, "recent_messages": 120, "workspace_state": 100}
        if role_name == "reviewer":
            return {"working_memory": 180, "tool_facts": 220, "failure_memory": 120, "recent_messages": 80}
        return {"working_memory": 180, "tool_facts": 180, "workspace_state": 160, "recent_messages": 80}

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
