from agentos.app import AgentOsApp
from agentos.config import Settings


def test_settings_load_defaults():
    settings = Settings.load()

    assert settings.project_root.name == "agentOs"
    assert settings.workspace_dir == settings.project_root
    assert settings.model_provider == "openai"
    assert settings.model_name == "gpt-4.1-mini"


def test_app_bootstrap_exposes_runtime_status():
    app = AgentOsApp.bootstrap()

    assert app.status()["runtime_status"] == "langgraph-v1-ready"
    assert app.status()["executor"] == "LocalCommandExecutor"
