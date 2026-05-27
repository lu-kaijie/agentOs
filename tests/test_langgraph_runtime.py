import time
from pathlib import Path

import pytest

from agentos.app import AgentOsApp


@pytest.fixture(autouse=True)
def isolate_background_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENTOS_BACKGROUND_DIR", str(tmp_path / "background"))


def test_runtime_runs_tool_enabled_task():
    app = AgentOsApp.bootstrap()

    state = app.runtime.run_task("run: pwd")

    assert state["user_task"] == "run: pwd"
    assert state["final_output"].strip().endswith("agentOs")
    assert "exit_code=0" in state["last_result"]
    assert "tool_execute:shell_command" in state["execution_trace"]
    assert "finalize_iteration" in state["execution_trace"]
    assert state["decision"]["action"] == "run_command"
    assert state["approval_policy"]["matched_rule"] == "safe-command"
    assert state["tool_results"][0]["tool_name"] == "shell_command"
    assert state["context_bundle"]["task_hints"]["action"] == "run"
    assert "workspace" in state["context_bundle"]["sources"]
    assert "layered_memory" in state["context_bundle"]["sources"]
    assert state["memory_state"]["session_summary"]
    assert state["context_audit_records"]
    assert state["iteration_count"] == 1
    assert state["loop_status"] == "completed"


def test_runtime_returns_guidance_without_tool_call():
    app = AgentOsApp.bootstrap()

    state = app.runtime.run_task("say hello")

    assert state["decision"]["action"] == "respond"
    assert "Use `run:`, `knowledge:`, `search:`, `read:`, `write:`, `patch:`, or `test:`." in state["final_output"]


def test_runtime_loads_knowledge_topic():
    app = AgentOsApp.bootstrap()

    state = app.runtime.run_task("knowledge: langgraph-runtime")

    assert state["decision"]["action"] == "load_knowledge"
    assert "[knowledge:langgraph-runtime]" in state["loaded_knowledge"]
    assert "tool_execute:knowledge_load" in state["execution_trace"]


def test_runtime_requires_approval_for_dangerous_command():
    app = AgentOsApp.bootstrap()

    blocked = app.runtime.run_task("run: rm temp.txt")
    approved = app.runtime.run_task("run: rm temp.txt", approved=True)

    assert "Approval required" in blocked["final_output"]
    assert "Policy reason:" in blocked["final_output"]
    assert "approval_gate" in blocked["execution_trace"]
    assert blocked["approval_policy"]["matched_rule"] == "destructive-command"
    assert blocked["approval_policy"]["risk_level"] == "high"
    assert approved["decision"]["requires_approval"] is True


def test_runtime_continues_across_multiple_explicit_steps():
    app = AgentOsApp.bootstrap()

    state = app.runtime.run_task(
        "steps: run: pwd | knowledge: langgraph-runtime | say hello",
        max_iterations=5,
    )

    assert state["iteration_count"] == 3
    assert state["completed_tasks"] == [
        "run: pwd",
        "knowledge: langgraph-runtime",
        "say hello",
    ]
    assert state["pending_tasks"] == []
    assert state["loop_status"] == "completed"
    assert "[step 1]" in state["final_output"]
    assert "[knowledge:langgraph-runtime]" in state["final_output"]
    assert state["execution_trace"].count("model_decide") == 3


def test_runtime_stops_at_max_iterations_with_remaining_steps():
    app = AgentOsApp.bootstrap()

    state = app.runtime.run_task(
        "steps: say hello | say again | say once more",
        max_iterations=2,
    )

    assert state["iteration_count"] == 2
    assert state["pending_tasks"] == ["say once more"]
    assert state["loop_status"] == "stopped:max_iterations"


def test_runtime_reenters_completed_background_results(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENTOS_BACKGROUND_DIR", str(tmp_path / "background"))
    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("AGENTOS_KNOWLEDGE_DIR", str(tmp_path / "knowledge"))
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    (knowledge_dir / "langgraph-runtime.md").write_text("# Runtime from background", encoding="utf-8")

    app = AgentOsApp.bootstrap()
    job = app.background_manager.run(
        ["bash", "-lc", "printf 'knowledge: langgraph-runtime'"],
        cwd=str(tmp_path),
    )

    deadline = time.time() + 5
    while time.time() < deadline:
        refreshed = app.background_manager.get(job.id)
        if refreshed.status == "completed":
            break
        time.sleep(0.1)

    state = app.runtime.run_task("say hello", max_iterations=5)

    assert state["consumed_background_jobs"] == [job.id]
    assert "background_reentry" in state["execution_trace"]
    assert "background_results_detected=1" in state["execution_trace"]
    assert "tool_execute:knowledge_load" in state["execution_trace"]
    assert "[knowledge:langgraph-runtime]" in state["final_output"]
    assert state["completed_tasks"][0] == f"background_result:{job.id}"


def test_runtime_context_selection_changes_with_task_and_history_size(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    (tmp_path / "README.md").write_text("alpha beta gamma\n", encoding="utf-8")

    app = AgentOsApp.bootstrap()
    state = app.runtime.run_task(
        "steps: read: README.md | search: alpha | say hello | say again | say once more",
        max_iterations=5,
    )

    bundle = state["context_bundle"]

    assert bundle["task"] == "say once more"
    assert bundle["task_hints"]["action"] == "respond"
    assert bundle["role_view"]["focus"] == "execution"
    assert "history" in bundle["sources"]
    assert "tool_results" in bundle["sources"]
    assert "layered_memory" in bundle["sources"]
    assert "..." in bundle["history_summary"] or "..." in bundle["tool_summary"] or "..." in bundle["trace_summary"]


def test_runtime_persists_context_policy_records(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    (tmp_path / "README.md").write_text("context policy runtime\n", encoding="utf-8")

    app = AgentOsApp.bootstrap()
    state = app.runtime.run_task(
        "code: steps: read: README.md | test: python -c print(2)",
        max_iterations=5,
    )

    assert state["context_policy_records"]
    assert state["context_audit_records"]
    record = state["context_policy_records"][0]
    assert "task_hints" in record["selectors"]
    assert "workspace_signals" in record["retrievers"]


def test_runtime_runs_bounded_role_based_coding_workflow(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    (tmp_path / "README.md").write_text("role based workflow\n", encoding="utf-8")

    app = AgentOsApp.bootstrap()
    state = app.runtime.run_task(
        "code: steps: read: README.md | write: notes.txt => role workflow | test: python -c print(789)",
        max_iterations=5,
    )

    roles = [record["role"] for record in state["role_records"]]

    assert roles[0] == "planner"
    assert "executor" in roles
    assert roles[-1] == "reviewer"
    assert "planner_role" in state["execution_trace"]
    assert "reviewer_role" in state["execution_trace"]
    assert state["completed_tasks"][0].startswith("role:planner:")
    assert state["completed_tasks"][-1].startswith("role:reviewer:")
    assert state["role_records"][-1]["metadata"]["reviewed_tool_count"] >= 1
    assert "Reviewer accepted" in state["final_output"]


def test_runtime_persists_structured_role_handoffs(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    (tmp_path / "README.md").write_text("handoff workflow\n", encoding="utf-8")

    app = AgentOsApp.bootstrap()
    state = app.runtime.run_task(
        "code: steps: read: README.md | test: python -c print(1)",
        max_iterations=5,
    )

    assert state["role_handoffs"]
    handoff = state["role_handoffs"][0]
    assert handoff["source_role"] == "planner"
    assert handoff["target_role"] == "executor"
    assert "summary" in handoff


def test_graph_model_mode_uses_model_decision_strategy(monkeypatch):
    from agentos.runtime.app import GraphModelDecisionStrategy, RuntimeDecision

    calls = {"count": 0}

    def fake_decide(self, **kwargs):
        calls["count"] += 1
        assert kwargs["state"]["context_bundle"]
        return RuntimeDecision(action="respond", response="model graph response")

    monkeypatch.setattr(GraphModelDecisionStrategy, "decide", fake_decide)

    app = AgentOsApp.bootstrap()
    state = app.runtime.run_task("summarize the repo", execution_mode="model")

    assert calls["count"] == 1
    assert state["execution_mode"] == "model"
    assert state["decision"]["action"] == "respond"
    assert "decision_strategy=model" in state["execution_trace"]
    assert "prepare_context" in state["execution_trace"]
    assert "respond_directly" in state["execution_trace"]
    assert "finalize_iteration" in state["execution_trace"]
    assert state["final_output"] == "model graph response"


def test_graph_model_decision_strategy_uses_required_tool_call(monkeypatch):
    from agentos.config import Settings
    from agentos.runtime.app import GraphModelDecisionStrategy, RuntimeDecision

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured = {}

    class BoundModel:
        def invoke(self, messages):
            captured["messages"] = messages
            return type(
                "Message",
                (),
                {
                    "content": "",
                    "tool_calls": [
                        {
                            "name": "RuntimeDecision",
                            "args": {
                                "action": "use_tool",
                                "tool_name": "file_read",
                                "tool_input": {"path": "README.md"},
                            },
                        }
                    ],
                },
            )()

    class FakeModel:
        def bind_tools(self, tools, *, tool_choice=None, **kwargs):
            captured["tools"] = tools
            captured["tool_choice"] = tool_choice
            return BoundModel()

    monkeypatch.setattr(
        GraphModelDecisionStrategy,
        "_build_chat_model",
        lambda self, model_name: FakeModel(),
    )

    class FakeToolRegistry:
        def list_tools(self):
            return [
                {"name": "file_read", "description": "Read one workspace file."},
                {"name": "repo_search", "description": "Search the repository."},
                {"name": "shell_command", "description": "Run a shell-like command."},
                {"name": "knowledge_load", "description": "Load a knowledge topic."},
            ]

    strategy = GraphModelDecisionStrategy(
        settings=Settings.load(),
        tool_registry=FakeToolRegistry(),
    )

    decision = strategy.decide(
        active_task="read README",
        state={"context_bundle": {"bundle_preview": ""}, "tool_results": []},
    )

    assert captured["tools"] == [RuntimeDecision]
    assert captured["tool_choice"] == "required"
    assert "Return JSON only" not in captured["messages"][0].content
    assert "tool_name=file_read" in captured["messages"][0].content
    assert "bash -lc" in captured["messages"][0].content
    assert "Available use_tool tool_name values" in captured["messages"][0].content
    assert "Registered ToolRegistry tools" in captured["messages"][0].content
    assert "file_read: Read one workspace file." in captured["messages"][0].content
    assert "Use action=run_command for shell_command semantics." in captured["messages"][0].content
    assert 'command=["mv", "source", "dest"]' in captured["messages"][0].content
    assert decision.action == "use_tool"
    assert decision.tool_name == "file_read"
    assert decision.tool_input == {"path": "README.md"}


def test_graph_model_decision_strategy_rejects_plain_text(monkeypatch):
    from agentos.config import Settings
    from agentos.runtime.app import (
        GraphModelDecisionError,
        GraphModelDecisionStrategy,
        RuntimeDecision,
    )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class BoundModel:
        def invoke(self, messages):
            return type("Message", (), {"content": '{"action":"respond","response":"nope"}'})()

    class FakeModel:
        def bind_tools(self, tools, *, tool_choice=None, **kwargs):
            return BoundModel()

    monkeypatch.setattr(
        GraphModelDecisionStrategy,
        "_build_chat_model",
        lambda self, model_name: FakeModel(),
    )

    strategy = GraphModelDecisionStrategy(settings=Settings.load())

    with pytest.raises(GraphModelDecisionError) as exc_info:
        strategy.decide(
            active_task="answer directly",
            state={"context_bundle": {"bundle_preview": ""}, "tool_results": []},
        )

    assert "did not return a RuntimeDecision tool call" in str(exc_info.value)
    assert any(line.startswith("[debug] raw_repr=") for line in exc_info.value.debug_lines)


def test_graph_model_decision_prompt_includes_remembered_facts(monkeypatch):
    from agentos.config import Settings
    from agentos.runtime.app import GraphModelDecisionStrategy, RuntimeDecision

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured = {}

    class BoundModel:
        def invoke(self, messages):
            captured["messages"] = messages
            return type(
                "Message",
                (),
                {
                    "content": "",
                    "tool_calls": [
                        {
                            "name": "RuntimeDecision",
                            "args": {"action": "respond", "response": "ok"},
                        }
                    ],
                },
            )()

    class FakeModel:
        def bind_tools(self, tools, *, tool_choice=None, **kwargs):
            return BoundModel()

    monkeypatch.setattr(
        GraphModelDecisionStrategy,
        "_build_chat_model",
        lambda self, model_name: FakeModel(),
    )

    strategy = GraphModelDecisionStrategy(settings=Settings.load())
    strategy.decide(
        active_task="请告诉我目前三个测试代号分别是什么。",
        state={
            "context_bundle": {
                "bundle_preview": "memory summary without test codes",
                "layered_memory": {
                    "working_memory": {
                        "accepted_constraints": [
                            "请记住第一个测试代号：蓝色风筝。",
                            "请记住第二个测试代号：银色钥匙。",
                            "请记住第三个测试代号：绿色罗盘。",
                        ]
                    },
                    "recent_messages": [
                        {"type": "human", "content": "请记住第三个测试代号：绿色罗盘。"},
                    ],
                },
            },
            "tool_results": [],
        },
    )

    prompt = captured["messages"][1].content
    assert "Structured memory" in prompt
    assert "蓝色风筝" in prompt
    assert "银色钥匙" in prompt
    assert "绿色罗盘" in prompt


def test_graph_model_decision_prompt_includes_structured_memory(monkeypatch):
    from agentos.config import Settings
    from agentos.runtime.app import GraphModelDecisionStrategy

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured = {}

    class BoundModel:
        def invoke(self, messages):
            captured["messages"] = messages
            return type(
                "Message",
                (),
                {
                    "content": "",
                    "tool_calls": [
                        {
                            "name": "RuntimeDecision",
                            "args": {"action": "respond", "response": "ok"},
                        }
                    ],
                },
            )()

    class FakeModel:
        def bind_tools(self, tools, *, tool_choice=None, **kwargs):
            return BoundModel()

    monkeypatch.setattr(
        GraphModelDecisionStrategy,
        "_build_chat_model",
        lambda self, model_name: FakeModel(),
    )

    strategy = GraphModelDecisionStrategy(settings=Settings.load())
    strategy.decide(
        active_task="请告诉我目前三个测试代号分别是什么。",
        state={
            "context_bundle": {
                "bundle_preview": "compressed preview",
                "user_profile": {
                    "preferred_language": "zh-CN",
                    "response_style": ["brief"],
                    "stable_preferences": ["回答要短一点"],
                },
                "remembered_facts": [
                    {"key": "test_code_1", "value": "蓝色风筝", "source_text": "请记住第一个测试代号：蓝色风筝。"},
                    {"key": "test_code_2", "value": "银色钥匙", "source_text": "请记住第二个测试代号：银色钥匙。"},
                ],
                "task_state": {"current_goal": "验证记忆", "completed_actions": ["已创建 source.txt"]},
                "layered_memory": {"recent_messages": []},
            },
            "tool_results": [],
        },
    )

    prompt = captured["messages"][1].content
    assert "preferred_language=zh-CN" in prompt
    assert "response_style=brief" in prompt
    assert "test_code_1=蓝色风筝" in prompt
    assert "test_code_2=银色钥匙" in prompt
    assert "current_goal=验证记忆" in prompt


def test_graph_model_mode_runs_multiple_tool_iterations_with_context(monkeypatch):
    from agentos.runtime.app import GraphModelDecisionStrategy, RuntimeDecision

    calls = {"count": 0}

    def fake_decide(self, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return RuntimeDecision(action="use_tool", tool_name="file_read", tool_input={"path": "README.md"})
        assert kwargs["state"]["tool_results"]
        return RuntimeDecision(action="respond", response="done after reading")

    monkeypatch.setattr(GraphModelDecisionStrategy, "decide", fake_decide)

    app = AgentOsApp.bootstrap()
    state = app.runtime.run_task("read then summarize", execution_mode="model", max_iterations=3)

    assert calls["count"] == 2
    assert state["execution_trace"].count("prepare_context") == 2
    assert state["execution_trace"].count("model_decide") == 2
    assert "tool_execute:file_read" in state["execution_trace"]
    assert state["tool_results"][0]["tool_name"] == "file_read"
    assert state["loop_status"] == "completed"


def test_graph_model_mode_carries_session_messages_between_turns(tmp_path: Path, monkeypatch):
    from agentos.runtime.app import GraphModelDecisionStrategy, RuntimeDecision

    monkeypatch.setenv("AGENTOS_CONTEXT_DIR", str(tmp_path / "context"))
    monkeypatch.setenv("AGENTOS_SESSIONS_DIR", str(tmp_path / "sessions"))
    calls = {"count": 0}

    def fake_decide(self, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return RuntimeDecision(action="respond", response="记住了：蓝色风筝。")
        recent_messages = kwargs["state"]["context_bundle"]["layered_memory"]["recent_messages"]
        contents = "\n".join(str(item.get("content", "")) for item in recent_messages)
        assert "蓝色风筝" in contents
        return RuntimeDecision(action="respond", response="第一个测试代号是蓝色风筝。")

    monkeypatch.setattr(GraphModelDecisionStrategy, "decide", fake_decide)

    app = AgentOsApp.bootstrap()
    app.run_graph_model_session_task("请记住第一个测试代号：蓝色风筝。", session_id="memory-carry")
    state = app.run_graph_model_session_task("刚才第一个测试代号是什么？", session_id="memory-carry")

    assert calls["count"] == 2
    assert state["final_output"] == "第一个测试代号是蓝色风筝。"


def test_graph_model_session_keeps_structured_memory_across_long_tool_conversation(tmp_path: Path, monkeypatch):
    from agentos.runtime.app import GraphModelDecisionStrategy, RuntimeDecision

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("AGENTOS_CONTEXT_DIR", str(tmp_path / "context"))
    monkeypatch.setenv("AGENTOS_SESSIONS_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("AGENTOS_WORKSPACE", str(workspace))
    calls = {"count": 0}

    def fake_decide(self, **kwargs):
        calls["count"] += 1
        task = kwargs["active_task"]
        state = kwargs["state"]
        if "阅读 source.txt" in task and not state["tool_results"]:
            return RuntimeDecision(action="use_tool", tool_name="file_read", tool_input={"path": "source.txt"})
        if "阅读 source.txt" in task:
            assert state["tool_results"][0]["status"] == "error"
            return RuntimeDecision(action="respond", response="没有 source.txt。")
        if "创建 source.txt" in task and not state["tool_results"]:
            return RuntimeDecision(
                action="use_tool",
                tool_name="file_write",
                tool_input={"path": "source.txt", "content": "hello agentos memory test"},
            )
        if "创建 source.txt" in task:
            return RuntimeDecision(action="respond", response="已创建 source.txt。")
        if "目前三个测试代号" in task:
            memory = state["context_bundle"]["remembered_facts"]
            facts = {item["key"]: item["value"] for item in memory}
            assert facts["test_code_1"] == "蓝色风筝"
            assert facts["test_code_2"] == "银色钥匙"
            assert facts["test_code_3"] == "绿色罗盘"
            assert state["context_bundle"]["user_profile"]["preferred_language"] == "zh-CN"
            assert "brief" in state["context_bundle"]["user_profile"]["response_style"]
            return RuntimeDecision(action="respond", response="蓝色风筝、银色钥匙、绿色罗盘。偏好：中文、简短。")
        return RuntimeDecision(action="respond", response="记住了。")

    monkeypatch.setattr(GraphModelDecisionStrategy, "decide", fake_decide)

    app = AgentOsApp.bootstrap()
    turns = [
        "从现在开始，请记住：我偏好中文回答，回答要短一点。",
        "请记住第一个测试代号：蓝色风筝。",
        "请记住第二个测试代号：银色钥匙。",
        "请阅读 source.txt，并用一句话告诉我里面是什么。",
        "请创建 source.txt，内容是 hello agentos memory test。",
        "普通对话 1",
        "普通对话 2",
        "普通对话 3",
        "请记住第三个测试代号：绿色罗盘。",
        "普通对话 4",
        "普通对话 5",
        "普通对话 6",
    ]
    for turn in turns:
        app.run_graph_model_session_task(turn, session_id="long-memory", max_iterations=3)

    state = app.run_graph_model_session_task(
        "请告诉我目前三个测试代号分别是什么，也说出我的回答偏好。",
        session_id="long-memory",
        max_iterations=3,
    )

    assert state["final_output"] == "蓝色风筝、银色钥匙、绿色罗盘。偏好：中文、简短。"
    assert calls["count"] >= len(turns)


def test_graph_model_mode_persists_final_answer_not_raw_tool_output(tmp_path: Path, monkeypatch):
    from agentos.runtime.app import GraphModelDecisionStrategy, RuntimeDecision

    monkeypatch.setenv("AGENTOS_CONTEXT_DIR", str(tmp_path / "context"))
    monkeypatch.setenv("AGENTOS_SESSIONS_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path / "workspace"))
    (tmp_path / "workspace").mkdir()
    calls = {"count": 0}

    def fake_decide(self, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return RuntimeDecision(
                action="use_tool",
                tool_name="file_write",
                tool_input={"path": "notes.txt", "content": "hello"},
            )
        return RuntimeDecision(action="respond", response="已创建 notes.txt。")

    monkeypatch.setattr(GraphModelDecisionStrategy, "decide", fake_decide)

    app = AgentOsApp.bootstrap()
    app.run_graph_model_session_task("请创建 notes.txt", session_id="compact-output")

    messages = app.context_manager.load_session("compact-output")
    assert messages[-1].content == "已创建 notes.txt。"
    assert "bytes_written" not in messages[-1].content


def test_graph_model_mode_uses_harness_for_test_run(monkeypatch):
    from agentos.runtime.app import GraphModelDecisionStrategy, RuntimeDecision

    monkeypatch.setattr(
        GraphModelDecisionStrategy,
        "decide",
        lambda self, **kwargs: RuntimeDecision(
            action="use_tool",
            tool_name="test_run",
            tool_input={"command": "python -c print(999)"},
        ),
    )

    app = AgentOsApp.bootstrap()
    state = app.runtime.run_task("run tests", execution_mode="model", max_iterations=1)

    assert state["tool_results"][0]["tool_name"] == "test_run"
    payload = state["tool_results"][0]["payload"]
    assert payload["exit_code"] == 0
    assert payload["stdout"] == "999\n"
    assert "tool_execute:test_run" in state["execution_trace"]


def test_graph_model_mode_turns_tool_errors_into_model_context(tmp_path: Path, monkeypatch):
    from agentos.runtime.app import GraphModelDecisionStrategy, RuntimeDecision

    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    calls = {"count": 0}

    def fake_decide(self, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return RuntimeDecision(
                action="use_tool",
                tool_name="file_patch",
                tool_input={"path": "missing.txt", "target": "x", "replacement": "y"},
            )
        assert kwargs["state"]["tool_results"][0]["status"] == "error"
        return RuntimeDecision(action="respond", response="missing.txt does not exist")

    monkeypatch.setattr(GraphModelDecisionStrategy, "decide", fake_decide)

    app = AgentOsApp.bootstrap()
    state = app.runtime.run_task("patch missing file", execution_mode="model", max_iterations=3)

    assert calls["count"] == 2
    assert state["tool_results"][0]["status"] == "error"
    assert state["tool_results"][0]["tool_name"] == "file_patch"
    assert state["loop_status"] == "completed"
    assert state["final_output"].endswith("missing.txt does not exist")


def test_graph_model_mode_pauses_for_pending_approval(tmp_path: Path, monkeypatch):
    from agentos.runtime.app import GraphModelDecisionStrategy, RuntimeDecision

    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    (tmp_path / "source.txt").write_text("move me", encoding="utf-8")
    monkeypatch.setattr(
        GraphModelDecisionStrategy,
        "decide",
        lambda self, **kwargs: RuntimeDecision(action="run_command", command=["mv", "source.txt", "dest.txt"]),
    )

    app = AgentOsApp.bootstrap()
    state = app.runtime.run_task("move the file", execution_mode="model")

    assert state["loop_status"] == "waiting_approval"
    assert state["pending_approval"]["command"] == ["mv", "source.txt", "dest.txt"]
    assert state["tool_results"] == []
    assert (tmp_path / "source.txt").exists()
    assert not (tmp_path / "dest.txt").exists()


def test_graph_model_mode_approval_resume_executes_exact_pending_command(tmp_path: Path, monkeypatch):
    from agentos.runtime.app import GraphModelDecisionStrategy, RuntimeDecision

    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("AGENTOS_SESSIONS_DIR", str(tmp_path / "sessions"))
    (tmp_path / "source.txt").write_text("move me", encoding="utf-8")
    calls = {"count": 0}

    def fake_decide(self, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return RuntimeDecision(action="run_command", command=["mv", "source.txt", "dest.txt"])
        return RuntimeDecision(action="respond", response="move complete")

    monkeypatch.setattr(GraphModelDecisionStrategy, "decide", fake_decide)

    app = AgentOsApp.bootstrap()
    blocked = app.run_graph_model_session_task("move the file", session_id="approval-demo")
    approved = app.approve_pending_approval("approval-demo")

    assert blocked["loop_status"] == "waiting_approval"
    assert approved["approval_outcome"]["status"] == "approved"
    assert approved["tool_results"][-1]["payload"]["command"] == ["mv", "source.txt", "dest.txt"]
    assert (tmp_path / "dest.txt").read_text(encoding="utf-8") == "move me"


def test_graph_model_mode_approval_reject_does_not_execute_command(tmp_path: Path, monkeypatch):
    from agentos.runtime.app import GraphModelDecisionStrategy, RuntimeDecision

    monkeypatch.setenv("AGENTOS_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("AGENTOS_SESSIONS_DIR", str(tmp_path / "sessions"))
    (tmp_path / "source.txt").write_text("move me", encoding="utf-8")
    calls = {"count": 0}

    def fake_decide(self, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return RuntimeDecision(action="run_command", command=["mv", "source.txt", "dest.txt"])
        return RuntimeDecision(action="respond", response="move skipped")

    monkeypatch.setattr(GraphModelDecisionStrategy, "decide", fake_decide)

    app = AgentOsApp.bootstrap()
    blocked = app.run_graph_model_session_task("move the file", session_id="approval-reject-demo")
    rejected = app.reject_pending_approval("approval-reject-demo")

    assert blocked["loop_status"] == "waiting_approval"
    assert rejected["approval_outcome"]["status"] == "rejected"
    assert rejected["tool_results"] == []
    assert (tmp_path / "source.txt").exists()
    assert not (tmp_path / "dest.txt").exists()
