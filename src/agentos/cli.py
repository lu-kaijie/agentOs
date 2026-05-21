"""CLI entrypoint for agentOs."""

from __future__ import annotations

import json
import shlex
import sys
import time

import typer
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agentos.app import AgentOsApp
from agentos.coordination.models import WorkUnitStatus
from agentos.tasks.models import TaskStatus
from agentos.tools import ToolInvocation

app = typer.Typer(
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=False,
    help="agentOs command line interface.",
)


def _echo_json(payload: object) -> None:
    """Render CLI JSON with readable UTF-8 output."""

    typer.echo(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))


def _echo_lines(lines: list[str]) -> None:
    for line in lines:
        typer.echo(line)


def _state_snapshot(state: dict[str, object]) -> list[str]:
    """Build a compact, human-readable runtime summary."""

    completed = len(state.get("completed_tasks", []))
    pending = len(state.get("pending_tasks", []))
    roles = state.get("role_records", [])
    last_role = roles[-1]["role"] if roles else "n/a"
    memory_state = state.get("memory_state", {})
    memory_layers = len(memory_state) if isinstance(memory_state, dict) else 0
    audits = state.get("context_audit_records", [])
    lines = [
        f"session_id: {state.get('session_id', '')}",
        f"loop_status: {state.get('loop_status', '')}",
        f"iteration_count: {state.get('iteration_count', 0)}",
        f"completed_tasks: {completed}",
        f"pending_tasks: {pending}",
        f"tool_results: {len(state.get('tool_results', []))}",
        f"role_records: {len(roles)} (last={last_role})",
        f"memory_layers: {memory_layers}",
        f"context_audits: {len(audits) if isinstance(audits, list) else 0}",
    ]
    if state.get("active_task"):
        lines.append(f"active_task: {state['active_task']}")
    if state.get("final_output"):
        preview = str(state["final_output"]).strip().replace("\n", " ")
        lines.append(f"final_output: {preview[:120]}")
    return lines


def _echo_state_report(title: str, state: dict[str, object]) -> None:
    """Print a staged runtime view followed by raw JSON."""

    typer.echo(title)
    typer.echo("摘要:")
    for line in _state_snapshot(state):
        typer.echo(f"- {line}")
    typer.echo("原始状态:")
    _echo_json(state)


def _shell_status_line(state: dict[str, object]) -> str:
    active_task = str(state.get("active_task", "") or "-")
    role = str(state.get("current_role", "") or "-")
    loop_status = str(state.get("loop_status", "") or "-")
    iteration = int(state.get("iteration_count", 0))
    audits = len(state.get("context_audit_records", [])) if isinstance(state.get("context_audit_records", []), list) else 0
    return (
        f"[status] loop={loop_status} iteration={iteration} role={role} audits={audits} active_task={active_task}"
    )


def _looks_like_legacy_task(task: str) -> bool:
    prefixes = ("run:", "knowledge:", "search:", "read:", "write:", "patch:", "test:", "steps:", "code:")
    return task.strip().startswith(prefixes)


def _print_model_guidance(application: AgentOsApp) -> None:
    _echo_lines(application.model_setup_guidance())


def _render_model_runtime_error(exc: Exception) -> str:
    lines = [f"model-backed runtime failed: {exc}"]
    debug_lines = getattr(exc, "debug_lines", [])
    if isinstance(debug_lines, list):
        lines.extend(str(line) for line in debug_lines)
    return "\n".join(lines)


def _textual_shell_available() -> bool:
    return bool(
        hasattr(sys.stdin, "isatty")
        and hasattr(sys.stdout, "isatty")
        and sys.stdin.isatty()
        and sys.stdout.isatty()
    )


def _run_plain_shell(
    *,
    application: AgentOsApp,
    session_id: str,
    approve: bool,
    max_iterations: int,
) -> None:
    typer.echo(f"agentOs interactive shell started for session `{session_id}`.")
    _echo_lines(application.shell_banner_lines(session_id=session_id))
    if not application.model_runtime.is_configured():
        _print_model_guidance(application)
    typer.echo("输入任务开始工作；输入 `/exit` 退出，`/status` 查看当前 session。")

    while True:
        try:
            user_task = typer.prompt("agentos")
        except (EOFError, KeyboardInterrupt):
            typer.echo("\nagentOs shell closed.")
            return

        command = user_task.strip()
        if not command:
            continue
        if command in {"/exit", "exit", "quit", ":q"}:
            typer.echo("agentOs shell closed.")
            return
        if command == "/status":
            try:
                payload = {
                    "session": application.session_manager.get_session(session_id).to_dict(),
                    "latest_turn": application.session_manager.load_latest_turn(session_id),
                }
                _echo_json(payload)
            except FileNotFoundError:
                typer.echo("当前 shell session 还没有任何 turn 记录。")
            continue

        latest_state: dict[str, object] | None = None
        if application.model_runtime.is_configured() and not _looks_like_legacy_task(command):
            typer.echo("[mode] model-backed")
            try:
                latest_state = application.run_model_session_task(
                    command,
                    session_id=session_id,
                    approve=approve,
                    max_iterations=max_iterations,
                )
            except Exception as exc:
                typer.echo(_render_model_runtime_error(exc))
                if not application.model_runtime.is_configured():
                    _print_model_guidance(application)
                continue
            typer.echo(_shell_status_line(latest_state))
            typer.echo("assistant>")
            typer.echo(str(latest_state.get("final_output", "")).rstrip())
            continue

        last_trace_len = -1
        for state in application.stream_session_task(
            command,
            session_id=session_id,
            approve=approve,
            max_iterations=max_iterations,
        ):
            latest_state = state
            trace = [str(item) for item in state.get("execution_trace", [])]
            if len(trace) != last_trace_len:
                typer.echo(_shell_status_line(state))
                last_trace_len = len(trace)
        if latest_state is None:
            typer.echo("本轮没有产生状态更新。")
            continue

        typer.echo("assistant>")
        typer.echo(str(latest_state.get("final_output", "")).rstrip())


def _launch_shell(
    *,
    session_id: str,
    approve: bool,
    max_iterations: int,
    presentation: str = "auto",
) -> None:
    application = AgentOsApp.bootstrap()
    if presentation == "tui" or (presentation == "auto" and _textual_shell_available()):
        try:
            from agentos.shell_tui import AgentShellApp
        except Exception:
            _run_plain_shell(
                application=application,
                session_id=session_id,
                approve=approve,
                max_iterations=max_iterations,
            )
            return
        AgentShellApp(
            application=application,
            session_id=session_id,
            approve=approve,
            max_iterations=max_iterations,
        ).run()
        return

    _run_plain_shell(
        application=application,
        session_id=session_id,
        approve=approve,
        max_iterations=max_iterations,
    )


@app.callback()
def default_entry(
    ctx: typer.Context,
    session_id: str = typer.Option("shell", "--session-id", help="Persistent shell session id."),
    approve: bool = typer.Option(False, "--approve", help="Approve execution when required."),
    max_iterations: int = typer.Option(8, "--max-iterations", min=1, help="Bounded runtime loop limit per turn."),
    plain: bool = typer.Option(False, "--plain", help="Force the plain shell presentation."),
    tui: bool = typer.Option(False, "--tui", help="Force the Textual shell presentation."),
) -> None:
    """Launch the default packaged shell when no subcommand is supplied."""

    if ctx.invoked_subcommand is not None:
        return
    presentation = "tui" if tui else "plain" if plain else "auto"
    _launch_shell(
        session_id=session_id,
        approve=approve,
        max_iterations=max_iterations,
        presentation=presentation,
    )
    raise typer.Exit()


def _unit_summary_lines(summary: dict[str, object], *, unit_id: int | None = None) -> list[str]:
    units = summary.get("units", [])
    if not isinstance(units, list):
        return []
    lines: list[str] = []
    for unit in units:
        if not isinstance(unit, dict):
            continue
        if unit_id is not None and int(unit.get("id", -1)) != unit_id:
            continue
        result = str(unit.get("result", "")).strip().replace("\n", " ")
        lines.append(
            f"unit {unit.get('id')} [{unit.get('status')}] role={unit.get('role')} title={unit.get('title')}"
            + (f" result={result[:80]}" if result else "")
        )
    return lines


def _all_units_terminal(summary: dict[str, object], *, unit_id: int | None = None) -> bool:
    units = summary.get("units", [])
    if not isinstance(units, list):
        return False
    filtered = [
        unit
        for unit in units
        if isinstance(unit, dict) and (unit_id is None or int(unit.get("id", -1)) == unit_id)
    ]
    if not filtered:
        return False
    return all(str(unit.get("status")) in {"completed", "failed"} for unit in filtered)


@app.command("status")
def status() -> None:
    """Show the current bootstrap status."""

    payload = AgentOsApp.bootstrap().status()
    _echo_json(payload)


@app.command("run")
def run(
    task: str = typer.Argument("describe current status"),
    session_id: str = typer.Option("default", "--session-id", help="Runtime session id."),
    approve: bool = typer.Option(False, "--approve", help="Approve execution when required."),
    max_iterations: int = typer.Option(5, "--max-iterations", min=1, help="Bounded runtime loop limit."),
    model: bool = typer.Option(False, "--model", help="Use the real model-backed runtime path."),
) -> None:
    """Run the current LangGraph runtime with a task string."""

    application = AgentOsApp.bootstrap()
    try:
        if model:
            if not application.model_runtime.is_configured():
                _print_model_guidance(application)
                raise typer.Exit(code=1)
            state = application.run_model_session_task(
                task,
                session_id=session_id,
                approve=approve,
                max_iterations=max_iterations,
            )
        else:
            state = application.run_session_task(
                task,
                session_id=session_id,
                approve=approve,
                max_iterations=max_iterations,
            )
    except Exception as exc:
        typer.echo(_render_model_runtime_error(exc))
        if not application.model_runtime.is_configured():
            _print_model_guidance(application)
        raise typer.Exit(code=1) from exc
    _echo_state_report("agentOs LangGraph runtime executed.", state)


@app.command("exec")
def exec_command(command: list[str] = typer.Argument(..., help="Command to execute.")) -> None:
    """Execute a command through the harness boundary."""

    application = AgentOsApp.bootstrap()
    result = application.tool_registry.invoke(
        ToolInvocation(
            tool_name="shell_command",
            arguments={"command": command, "cwd": str(application.settings.workspace_dir)},
        )
    )
    _echo_json(result.to_dict())


@app.command("bg-run")
def bg_run(
    command: str = typer.Argument(..., help="Command string to execute in background."),
    workspace: str = typer.Option("", "--workspace", help="Optional isolated workspace name."),
    session_id: str = typer.Option("", "--session-id", help="Optional owning session id."),
) -> None:
    """Launch a background command."""

    application = AgentOsApp.bootstrap()
    cwd = application.workspace_manager.resolve(workspace or None, str(application.settings.workspace_dir))
    job = application.background_manager.run(command=shlex.split(command), cwd=cwd, session_id=session_id)
    _echo_json(job.to_dict())


@app.command("bg-status")
def bg_status(job_id: str = typer.Argument(..., help="Background job id.")) -> None:
    """Inspect one background job."""

    application = AgentOsApp.bootstrap()
    job = application.background_manager.get(job_id)
    _echo_json(job.to_dict())


@app.command("bg-list")
def bg_list() -> None:
    """List background jobs."""

    application = AgentOsApp.bootstrap()
    _echo_json(application.background_manager.list())


@app.command("workspace-create")
def workspace_create(name: str = typer.Argument(..., help="Workspace name.")) -> None:
    """Create an isolated workspace directory."""

    application = AgentOsApp.bootstrap()
    payload = application.workspace_manager.create(name)
    _echo_json(payload)


@app.command("workspace-list")
def workspace_list() -> None:
    """List isolated workspaces."""

    application = AgentOsApp.bootstrap()
    _echo_json(application.workspace_manager.list())


@app.command("unit-create")
def unit_create(
    title: str = typer.Argument(..., help="Delegated work title."),
    role: str = typer.Option(..., "--role", help="Role assigned to this unit."),
    task_id: int = typer.Option(None, "--task-id", help="Optional linked task id."),
    workspace: str = typer.Option("", "--workspace", help="Optional workspace name."),
    depends_on: list[int] = typer.Option(None, "--depends-on", help="Other unit ids that must complete first."),
    instructions: str = typer.Option("", "--instructions", help="Optional role-specific instructions."),
    command: list[str] = typer.Option(None, "--command", help="Optional delegated command."),
) -> None:
    """Create a delegated work unit."""

    application = AgentOsApp.bootstrap()
    unit = application.coordination_manager.create_unit(
        title=title,
        role=role,
        task_id=task_id,
        workspace=workspace,
        depends_on=depends_on,
        instructions=instructions,
        command=command,
    )
    _echo_json(unit.to_dict())


@app.command("unit-list")
def unit_list() -> None:
    """List delegated work units and ready work."""

    application = AgentOsApp.bootstrap()
    _echo_json(application.coordination_manager.summary())


@app.command("unit-watch")
def unit_watch(
    unit_id: int = typer.Option(None, "--unit-id", help="Optional specific work unit id."),
    poll_count: int = typer.Option(10, "--poll-count", min=1, help="Maximum watch cycles."),
    poll_interval: float = typer.Option(0.5, "--poll-interval", min=0.1, help="Seconds between watch cycles."),
) -> None:
    """Watch delegated work units for status changes."""

    application = AgentOsApp.bootstrap()
    last_snapshot: list[str] = []
    typer.echo("agentOs watching delegated work units.")
    for poll_index in range(1, poll_count + 1):
        summary = application.coordination_manager.summary()
        lines = _unit_summary_lines(summary, unit_id=unit_id)
        if poll_index == 1 or lines != last_snapshot:
            typer.echo(f"unit watch cycle {poll_index}/{poll_count}")
            for line in lines or ["- no matching work units"]:
                typer.echo(f"- {line}")
        last_snapshot = lines
        if _all_units_terminal(summary, unit_id=unit_id):
            typer.echo("所有关注的 work unit 已进入终态。")
            typer.echo("原始状态:")
            _echo_json(summary)
            return
        if poll_index < poll_count:
            time.sleep(poll_interval)
    typer.echo("达到 watch 上限，返回当前状态。")
    typer.echo("原始状态:")
    _echo_json(application.coordination_manager.summary())


@app.command("unit-start")
def unit_start(unit_id: int = typer.Argument(..., help="Work unit id.")) -> None:
    """Mark a delegated work unit as running."""

    application = AgentOsApp.bootstrap()
    unit = application.coordination_manager.update_status(unit_id, status=WorkUnitStatus.RUNNING)
    _echo_json(unit.to_dict())


@app.command("unit-complete")
def unit_complete(
    unit_id: int = typer.Argument(..., help="Work unit id."),
    result: str = typer.Option("", "--result", help="Completion result summary."),
) -> None:
    """Mark a delegated work unit as completed."""

    application = AgentOsApp.bootstrap()
    unit = application.coordination_manager.update_status(
        unit_id,
        status=WorkUnitStatus.COMPLETED,
        result=result,
    )
    _echo_json(unit.to_dict())


@app.command("unit-exec")
def unit_exec(unit_id: int = typer.Argument(..., help="Work unit id.")) -> None:
    """Execute a delegated work unit through the local harness."""

    application = AgentOsApp.bootstrap()
    unit = application.coordination_manager.execute_unit(
        unit_id,
        executor=application.runtime.executor,
        default_cwd=str(application.settings.workspace_dir),
        workspace_resolver=application.workspace_manager.resolve,
        task_manager=application.task_manager,
    )
    _echo_json(unit.to_dict())


@app.command("task-create")
def task_create(
    title: str = typer.Argument(..., help="Task title."),
    blocked_by: list[int] = typer.Option(None, "--blocked-by", help="Task ids that must complete first."),
) -> None:
    """Create a persistent task."""

    application = AgentOsApp.bootstrap()
    task = application.task_manager.create_task(title=title, blocked_by=blocked_by)
    _echo_json(task.to_dict())


@app.command("task-list")
def task_list() -> None:
    """List persisted tasks and ready work."""

    application = AgentOsApp.bootstrap()
    _echo_json(application.task_manager.summary())


@app.command("task-complete")
def task_complete(task_id: int = typer.Argument(..., help="Task id to mark completed.")) -> None:
    """Complete a task and unblock dependents."""

    application = AgentOsApp.bootstrap()
    task = application.task_manager.update_status(task_id, TaskStatus.COMPLETED)
    _echo_json(task.to_dict())


@app.command("knowledge-list")
def knowledge_list() -> None:
    """List available knowledge topics."""

    application = AgentOsApp.bootstrap()
    payload = {
        "knowledge_dir": str(application.settings.knowledge_dir),
        "topics": application.knowledge_loader.list_topics(),
        "skills_dir": str(application.settings.skills_dir),
        "skills": application.knowledge_loader.list_skills(),
    }
    _echo_json(payload)


@app.command("knowledge-load")
def knowledge_load(topic: str = typer.Argument(..., help="Knowledge topic to load.")) -> None:
    """Load a single knowledge topic on demand."""

    application = AgentOsApp.bootstrap()
    result = application.tool_registry.invoke(
        ToolInvocation(tool_name="knowledge_load", arguments={"topic": topic})
    )
    _echo_json(result.to_dict())


@app.command("skill-list")
def skill_list() -> None:
    """List available user-defined skills."""

    application = AgentOsApp.bootstrap()
    payload = {
        "skills_dir": str(application.settings.skills_dir),
        "skills": application.knowledge_loader.list_skills(),
    }
    _echo_json(payload)


@app.command("skill-show")
def skill_show(
    name: str = typer.Argument(..., help="Skill name."),
    level: str = typer.Option("summary", "--level", help="summary/full/reference/script"),
    target: str = typer.Option("", "--target", help="Optional reference/script target."),
) -> None:
    """Load one skill through the structured tool registry."""

    application = AgentOsApp.bootstrap()
    result = application.tool_registry.invoke(
        ToolInvocation(tool_name="skill_load", arguments={"name": name, "level": level, "target": target})
    )
    _echo_json(result.to_dict())


@app.command("context-demo")
def context_demo(session_id: str = typer.Argument("demo", help="Context session id.")) -> None:
    """Demonstrate compaction of long session context."""

    application = AgentOsApp.bootstrap()
    messages = [
        HumanMessage(content="Inspect the repository layout."),
        ToolMessage(
            content=("very long tool output " * 40).strip(),
            tool_call_id="demo-tool-1",
        ),
        AIMessage(content="I found the repository structure."),
        HumanMessage(content="Keep only the important information."),
    ]
    compacted, path = application.context_manager.compact_messages(
        session_id=session_id,
        messages=messages,
        max_chars=180,
    )
    payload = {
        "session_id": session_id,
        "before_chars": application.context_manager.total_chars(messages),
        "after_chars": application.context_manager.total_chars(compacted),
        "message_types": [message.type for message in compacted],
        "context_path": str(path),
    }
    _echo_json(payload)


@app.command("sessions")
def sessions() -> None:
    """List persisted runtime sessions."""

    application = AgentOsApp.bootstrap()
    _echo_json(application.session_manager.summary())


@app.command("tool-list")
def tool_list() -> None:
    """List registered coding-agent tools."""

    application = AgentOsApp.bootstrap()
    payload = {"tools": application.tool_registry.list_tools()}
    _echo_json(payload)


@app.command("tool-run")
def tool_run(
    tool_name: str = typer.Argument(..., help="Registered tool name."),
    argument: list[str] = typer.Option(None, "--arg", help="Tool argument in key=value form."),
) -> None:
    """Run one registered tool through the structured tool registry."""

    application = AgentOsApp.bootstrap()
    arguments: dict[str, object] = {}
    for item in argument or []:
        key, _, value = item.partition("=")
        arguments[key] = value
    result = application.tool_registry.invoke(ToolInvocation(tool_name=tool_name, arguments=arguments))
    _echo_json(result.to_dict())


@app.command("session-show")
def session_show(session_id: str = typer.Argument(..., help="Persisted session id.")) -> None:
    """Show one persisted session and its latest recorded turn."""

    application = AgentOsApp.bootstrap()
    try:
        memory = application.context_manager.load_memory(session_id).to_dict()
    except FileNotFoundError:
        memory = {}
    payload = {
        "session": application.session_manager.get_session(session_id).to_dict(),
        "latest_turn": application.session_manager.load_latest_turn(session_id),
        "memory_state": memory,
    }
    _echo_json(payload)


@app.command("resume")
def resume(
    session_id: str = typer.Argument(..., help="Persisted session id."),
    task: str = typer.Argument("", help="Optional next task for the resumed session."),
    approve: bool = typer.Option(False, "--approve", help="Approve execution when required."),
    max_iterations: int = typer.Option(5, "--max-iterations", min=1, help="Bounded runtime loop limit."),
    poll_iterations: int = typer.Option(1, "--poll-iterations", min=1, help="Maximum bounded poll cycles before resuming."),
    poll_interval: float = typer.Option(0.2, "--poll-interval", min=0.1, help="Seconds to sleep between poll cycles."),
) -> None:
    """Resume a persisted runtime session."""

    application = AgentOsApp.bootstrap()
    state = application.resume_session(
        session_id,
        task=task,
        approve=approve,
        max_iterations=max_iterations,
        poll_iterations=poll_iterations,
        poll_interval=poll_interval,
    )
    _echo_state_report("agentOs resumed session.", state)


@app.command("watch")
def watch(
    session_id: str = typer.Argument(..., help="Persisted session id."),
    task: str = typer.Argument("", help="Optional next task for the watched session."),
    approve: bool = typer.Option(False, "--approve", help="Approve execution when required."),
    max_iterations: int = typer.Option(5, "--max-iterations", min=1, help="Bounded runtime loop limit."),
    poll_count: int = typer.Option(5, "--poll-count", min=1, help="Maximum watch cycles."),
    poll_interval: float = typer.Option(0.5, "--poll-interval", min=0.1, help="Seconds between watch cycles."),
) -> None:
    """Watch a session with bounded poll-and-resume cycles."""

    application = AgentOsApp.bootstrap()
    latest_state: dict[str, object] | None = None
    typer.echo(f"agentOs watching session `{session_id}`.")
    for poll_index in range(1, poll_count + 1):
        latest_state = application.resume_session(
            session_id,
            task=task,
            approve=approve,
            max_iterations=max_iterations,
            poll_iterations=1,
            poll_interval=poll_interval,
        )
        typer.echo(f"watch cycle {poll_index}/{poll_count}")
        for line in _state_snapshot(latest_state):
            typer.echo(f"- {line}")
        if str(latest_state.get("loop_status", "")) == "completed":
            break
        if poll_index < poll_count:
            time.sleep(poll_interval)
    if latest_state is None:
        raise typer.Exit(code=1)
    typer.echo("原始状态:")
    _echo_json(latest_state)


@app.command("shell")
def shell(
    session_id: str = typer.Option("shell", "--session-id", help="Persistent shell session id."),
    approve: bool = typer.Option(False, "--approve", help="Approve execution when required."),
    max_iterations: int = typer.Option(8, "--max-iterations", min=1, help="Bounded runtime loop limit per turn."),
    plain: bool = typer.Option(False, "--plain", help="Force the plain shell presentation."),
    tui: bool = typer.Option(False, "--tui", help="Force the Textual shell presentation."),
) -> None:
    """Run a persistent interactive agent shell."""

    presentation = "tui" if tui else "plain" if plain else "auto"
    _launch_shell(
        session_id=session_id,
        approve=approve,
        max_iterations=max_iterations,
        presentation=presentation,
    )


def main() -> None:
    """Run the CLI app."""

    app()


if __name__ == "__main__":
    main()
