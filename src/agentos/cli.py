"""CLI entrypoint for agentOs."""

from __future__ import annotations

import json

import typer

from agentos.app import AgentOsApp
from agentos.harness.execution import ExecutionRequest

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
def run(task: str = typer.Argument("describe current status")) -> None:
    """Run the current LangGraph runtime with a task string."""

    application = AgentOsApp.bootstrap()
    state = application.runtime.run_task(task)
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


def main() -> None:
    """Run the CLI app."""

    app()


if __name__ == "__main__":
    main()
