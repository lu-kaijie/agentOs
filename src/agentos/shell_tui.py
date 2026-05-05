"""Product-oriented terminal shell built with Textual."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

if TYPE_CHECKING:
    from agentos.app import AgentOsApp


def _json_lines(payload: object) -> list[str]:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False).splitlines()


class AgentShellApp(App[None]):
    """Textual shell for a persistent agentOs session."""

    CSS = """
    Screen {
        layout: vertical;
        background: #0e1116;
        color: #f2f2f2;
    }

    #status {
        height: 5;
        padding: 0 1;
        background: #132238;
        color: #d7e7ff;
        border: solid #406080;
    }

    #conversation {
        height: 1fr;
        margin: 1 0;
        padding: 0 1;
        background: #091018;
        color: #f6f7f9;
        border: round #2d4e73;
    }

    #input {
        dock: bottom;
        margin: 0 0 1 0;
        background: #16273b;
        color: #ffffff;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+l", "clear_log", "Clear"),
    ]

    def __init__(
        self,
        *,
        application: "AgentOsApp",
        session_id: str,
        approve: bool,
        max_iterations: int,
    ) -> None:
        super().__init__()
        self.application = application
        self.session_id = session_id
        self.approve = approve
        self.max_iterations = max_iterations
        self._busy = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield Static("", id="status")
            yield RichLog(id="conversation", wrap=True, markup=False, highlight=False)
            yield Input(
                placeholder="输入任务，或使用 /status /exit",
                id="input",
            )
        yield Footer()

    def on_mount(self) -> None:
        self.title = "agentOs"
        self.sub_title = f"session={self.session_id}"
        self._refresh_status()
        for line in self.application.shell_banner_lines(session_id=self.session_id):
            self._write("system", line)
        if not self.application.model_runtime.is_configured():
            for line in self.application.model_setup_guidance():
                self._write("hint", line)

    def action_clear_log(self) -> None:
        self.query_one(RichLog).clear()
        self._write("system", "日志已清空。")

    @on(Input.Submitted)
    def handle_submit(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        event.input.value = ""
        if not command:
            return
        if self._busy:
            self._write("status", "当前还有任务在执行，请等待本轮完成。")
            return
        if command in {"/exit", "exit", "quit", ":q"}:
            self.exit()
            return
        if command == "/status":
            self._write_json("status", self.application.status())
            return

        self._write("user", command)
        self._busy = True
        self._refresh_status(loop_status="running", active_task=command)
        self.run_turn(command)

    @work(thread=True, exclusive=True)
    def run_turn(self, command: str) -> None:
        latest_state: dict[str, object] | None = None
        try:
            if self.application.model_runtime.is_configured() and not self._looks_like_legacy_task(command):
                self.call_from_thread(self._write, "mode", "model-backed")
                latest_state = self.application.run_model_session_task(
                    command,
                    session_id=self.session_id,
                    approve=self.approve,
                )
            else:
                last_trace_len = -1
                for state in self.application.stream_session_task(
                    command,
                    session_id=self.session_id,
                    approve=self.approve,
                    max_iterations=self.max_iterations,
                ):
                    latest_state = state
                    trace = [str(item) for item in state.get("execution_trace", [])]
                    if len(trace) != last_trace_len:
                        self.call_from_thread(self._write, "trace", self._shell_status_line(state))
                        self.call_from_thread(
                            self._refresh_status,
                            loop_status=str(state.get("loop_status", "-")),
                            active_task=str(state.get("active_task", "-")),
                            current_role=str(state.get("current_role", "-")),
                            tool_count=len(state.get("tool_results", [])),
                            audit_count=len(state.get("context_audit_records", [])),
                        )
                        last_trace_len = len(trace)
        except Exception as exc:
            self.call_from_thread(self._write, "error", f"model-backed runtime failed: {exc}")
            for line in self.application.model_setup_guidance():
                self.call_from_thread(self._write, "hint", line)
            self.call_from_thread(self._refresh_status, loop_status="error", active_task=command)
            self.call_from_thread(self._finish_turn)
            return

        if latest_state is None:
            self.call_from_thread(self._write, "error", "本轮没有产生状态更新。")
            self.call_from_thread(self._refresh_status, loop_status="idle", active_task="-")
            self.call_from_thread(self._finish_turn)
            return

        final_output = str(latest_state.get("final_output", "")).rstrip() or "(empty)"
        self.call_from_thread(self._write, "agent", final_output)
        if latest_state.get("last_result"):
            self.call_from_thread(self._write, "result", str(latest_state["last_result"]))
        self.call_from_thread(
            self._refresh_status,
            loop_status=str(latest_state.get("loop_status", "completed")),
            active_task=str(latest_state.get("active_task", "-")),
            current_role=str(latest_state.get("current_role", "-")),
            tool_count=len(latest_state.get("tool_results", [])),
            audit_count=len(latest_state.get("context_audit_records", [])),
        )
        self.call_from_thread(self._finish_turn)

    def _finish_turn(self) -> None:
        self._busy = False

    def _write_json(self, label: str, payload: object) -> None:
        for line in _json_lines(payload):
            self._write(label, line)

    def _write(self, label: str, message: str) -> None:
        self.query_one(RichLog).write(f"[{label}] {message}")

    def _refresh_status(
        self,
        *,
        loop_status: str = "idle",
        active_task: str = "-",
        current_role: str = "-",
        tool_count: int = 0,
        audit_count: int = 0,
    ) -> None:
        status = self.query_one("#status", Static)
        model_state = "ready" if self.application.model_runtime.is_configured() else "deterministic"
        status.update(
            "\n".join(
                [
                    f"session={self.session_id}  workspace={self.application.settings.workspace_dir}",
                    (
                        "mode="
                        f"{model_state}  loop={loop_status}  role={current_role}  tools={tool_count}  audits={audit_count}"
                    ),
                    (
                        "models="
                        f"{self.application.settings.model_small_name}/"
                        f"{self.application.settings.model_medium_name}/"
                        f"{self.application.settings.model_large_name}"
                    ),
                    f"active_task={active_task}",
                ]
            )
        )

    def _shell_status_line(self, state: dict[str, object]) -> str:
        active_task = str(state.get("active_task", "") or "-")
        role = str(state.get("current_role", "") or "-")
        loop_status = str(state.get("loop_status", "") or "-")
        iteration = int(state.get("iteration_count", 0))
        audits = len(state.get("context_audit_records", [])) if isinstance(state.get("context_audit_records", []), list) else 0
        return (
            f"loop={loop_status} iteration={iteration} role={role} audits={audits} active_task={active_task}"
        )

    def _looks_like_legacy_task(self, task: str) -> bool:
        prefixes = (
            "run:",
            "knowledge:",
            "search:",
            "read:",
            "write:",
            "patch:",
            "test:",
            "steps:",
            "code:",
        )
        return task.strip().startswith(prefixes)
