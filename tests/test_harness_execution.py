from agentos.harness.execution import ExecutionRequest, LocalCommandExecutor


def test_local_executor_runs_command():
    executor = LocalCommandExecutor()
    request = ExecutionRequest(command=["pwd"], cwd=".")

    result = executor.run(request)

    assert result.exit_code == 0
    assert result.timed_out is False
    assert result.cwd.endswith("agentOs")
    assert "agentOs" in result.stdout


def test_local_executor_reports_failure_exit_code():
    executor = LocalCommandExecutor()
    request = ExecutionRequest(command=["bash", "-lc", "exit 7"], cwd=".")

    result = executor.run(request)

    assert result.exit_code == 7
    assert result.timed_out is False
