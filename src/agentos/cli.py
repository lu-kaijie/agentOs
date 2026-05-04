"""CLI entrypoint for agentOs."""

from __future__ import annotations

import json
import shlex

import typer
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agentos.app import AgentOsApp
from agentos.coordination.models import WorkUnitStatus
from agentos.harness.execution import ExecutionRequest
from agentos.tasks.models import TaskStatus

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="agentOs command line interface.",
)


@app.command("status")
def status() -> None:
    """Show the current bootstrap status."""

    payload = AgentOsApp.bootstrap().status()
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("run")
def run(
    task: str = typer.Argument("describe current status"),
    session_id: str = typer.Option("default", "--session-id", help="Runtime session id."),
    approve: bool = typer.Option(False, "--approve", help="Approve execution when required."),
    max_iterations: int = typer.Option(5, "--max-iterations", min=1, help="Bounded runtime loop limit."),
) -> None:
    """Run the current LangGraph runtime with a task string."""

    application = AgentOsApp.bootstrap()
    state = application.run_session_task(
        task,
        session_id=session_id,
        approve=approve,
        max_iterations=max_iterations,
    )
    typer.echo("agentOs LangGraph runtime executed.")
    typer.echo(json.dumps(state, indent=2, sort_keys=True))


@app.command("exec")
def exec_command(command: list[str] = typer.Argument(..., help="Command to execute.")) -> None:
    """Execute a command through the harness boundary."""

    application = AgentOsApp.bootstrap()
    request = ExecutionRequest(
        command=command,
        cwd=str(application.settings.workspace_dir),
    )
    result = application.runtime.executor.run(request)
    payload = {
        "command": result.command,
        "cwd": result.cwd,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "timed_out": result.timed_out,
    }
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


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
    typer.echo(json.dumps(job.to_dict(), indent=2, sort_keys=True))


@app.command("bg-status")
def bg_status(job_id: str = typer.Argument(..., help="Background job id.")) -> None:
    """Inspect one background job."""

    application = AgentOsApp.bootstrap()
    job = application.background_manager.get(job_id)
    typer.echo(json.dumps(job.to_dict(), indent=2, sort_keys=True))


@app.command("bg-list")
def bg_list() -> None:
    """List background jobs."""

    application = AgentOsApp.bootstrap()
    typer.echo(json.dumps(application.background_manager.list(), indent=2, sort_keys=True))


@app.command("workspace-create")
def workspace_create(name: str = typer.Argument(..., help="Workspace name.")) -> None:
    """Create an isolated workspace directory."""

    application = AgentOsApp.bootstrap()
    payload = application.workspace_manager.create(name)
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("workspace-list")
def workspace_list() -> None:
    """List isolated workspaces."""

    application = AgentOsApp.bootstrap()
    typer.echo(json.dumps(application.workspace_manager.list(), indent=2, sort_keys=True))


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
    typer.echo(json.dumps(unit.to_dict(), indent=2, sort_keys=True))


@app.command("unit-list")
def unit_list() -> None:
    """List delegated work units and ready work."""

    application = AgentOsApp.bootstrap()
    typer.echo(json.dumps(application.coordination_manager.summary(), indent=2, sort_keys=True))


@app.command("unit-start")
def unit_start(unit_id: int = typer.Argument(..., help="Work unit id.")) -> None:
    """Mark a delegated work unit as running."""

    application = AgentOsApp.bootstrap()
    unit = application.coordination_manager.update_status(unit_id, status=WorkUnitStatus.RUNNING)
    typer.echo(json.dumps(unit.to_dict(), indent=2, sort_keys=True))


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
    typer.echo(json.dumps(unit.to_dict(), indent=2, sort_keys=True))


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
    typer.echo(json.dumps(unit.to_dict(), indent=2, sort_keys=True))


@app.command("task-create")
def task_create(
    title: str = typer.Argument(..., help="Task title."),
    blocked_by: list[int] = typer.Option(None, "--blocked-by", help="Task ids that must complete first."),
) -> None:
    """Create a persistent task."""

    application = AgentOsApp.bootstrap()
    task = application.task_manager.create_task(title=title, blocked_by=blocked_by)
    typer.echo(json.dumps(task.to_dict(), indent=2, sort_keys=True))


@app.command("task-list")
def task_list() -> None:
    """List persisted tasks and ready work."""

    application = AgentOsApp.bootstrap()
    typer.echo(json.dumps(application.task_manager.summary(), indent=2, sort_keys=True))


@app.command("task-complete")
def task_complete(task_id: int = typer.Argument(..., help="Task id to mark completed.")) -> None:
    """Complete a task and unblock dependents."""

    application = AgentOsApp.bootstrap()
    task = application.task_manager.update_status(task_id, TaskStatus.COMPLETED)
    typer.echo(json.dumps(task.to_dict(), indent=2, sort_keys=True))


@app.command("knowledge-list")
def knowledge_list() -> None:
    """List available knowledge topics."""

    application = AgentOsApp.bootstrap()
    payload = {
        "knowledge_dir": str(application.settings.knowledge_dir),
        "topics": application.knowledge_loader.list_topics(),
    }
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("knowledge-load")
def knowledge_load(topic: str = typer.Argument(..., help="Knowledge topic to load.")) -> None:
    """Load a single knowledge topic on demand."""

    application = AgentOsApp.bootstrap()
    message = application.knowledge_loader.load_topic(topic)
    payload = {
        "topic": message.additional_kwargs.get("topic", topic),
        "source": message.additional_kwargs.get("source", ""),
        "content": message.content,
    }
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


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
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("sessions")
def sessions() -> None:
    """List persisted runtime sessions."""

    application = AgentOsApp.bootstrap()
    typer.echo(json.dumps(application.session_manager.summary(), indent=2, sort_keys=True))


def main() -> None:
    """Run the CLI app."""

    app()


if __name__ == "__main__":
    main()
