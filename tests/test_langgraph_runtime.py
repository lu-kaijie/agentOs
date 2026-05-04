from agentos.app import AgentOsApp


def test_runtime_runs_tool_enabled_task():
    app = AgentOsApp.bootstrap()

    state = app.runtime.run_task("run: pwd")

    assert state["user_task"] == "run: pwd"
    assert state["final_output"].endswith("agentOs")
    assert "exit_code=0" in state["last_result"]
    assert state["pending_command"] == []


def test_runtime_returns_guidance_without_tool_call():
    app = AgentOsApp.bootstrap()

    state = app.runtime.run_task("say hello")

    assert state["pending_command"] == []
    assert "Use the format `run: <command>`" in state["final_output"]
