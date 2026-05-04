from agentos.app import AgentOsApp


def test_runtime_runs_tool_enabled_task():
    app = AgentOsApp.bootstrap()

    state = app.runtime.run_task("run: pwd")

    assert state["user_task"] == "run: pwd"
    assert state["final_output"].endswith("agentOs")
    assert "exit_code=0" in state["last_result"]
    assert "tool_execute" in state["execution_trace"]
    assert state["decision"]["action"] == "run_command"


def test_runtime_returns_guidance_without_tool_call():
    app = AgentOsApp.bootstrap()

    state = app.runtime.run_task("say hello")

    assert state["decision"]["action"] == "respond"
    assert "Use `run: <command>` or `knowledge: <topic>`." in state["final_output"]


def test_runtime_loads_knowledge_topic():
    app = AgentOsApp.bootstrap()

    state = app.runtime.run_task("knowledge: langgraph-runtime")

    assert state["decision"]["action"] == "load_knowledge"
    assert "[knowledge:langgraph-runtime]" in state["loaded_knowledge"]
    assert "knowledge_execute" in state["execution_trace"]


def test_runtime_requires_approval_for_dangerous_command():
    app = AgentOsApp.bootstrap()

    blocked = app.runtime.run_task("run: rm temp.txt")
    approved = app.runtime.run_task("run: rm temp.txt", approved=True)

    assert "Approval required" in blocked["final_output"]
    assert "approval_gate" in blocked["execution_trace"]
    assert approved["decision"]["requires_approval"] is True
