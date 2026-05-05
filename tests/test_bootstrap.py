from agentos.app import AgentOsApp
from agentos.config import Settings


def test_settings_load_defaults():
    settings = Settings.load()

    assert settings.project_root.name == "agentOs"
    assert settings.workspace_dir == settings.project_root
    assert settings.tasks_dir.name == "tasks"
    assert settings.knowledge_dir.name == "knowledge"
    assert settings.context_dir.name == "context"
    assert settings.background_jobs_dir.name == "background"
    assert settings.workspaces_dir.name == "workspaces"
    assert settings.coordination_dir.name == "coordination"
    assert settings.model_provider == "openai"
    assert settings.model_small_name == "gpt-5.4"
    assert settings.model_medium_name == "gpt-5.4"
    assert settings.model_large_name == "gpt-5.4"
    assert settings.planner_model_level == "medium"
    assert settings.executor_model_level == "medium"
    assert settings.reviewer_model_level == "medium"


def test_app_bootstrap_exposes_runtime_status():
    app = AgentOsApp.bootstrap()

    assert app.status()["runtime_status"] == "langgraph-advanced-ready"
    assert app.status()["executor"] == "LocalCommandExecutor"
