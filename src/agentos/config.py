"""Project configuration loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    """Minimal runtime settings for the current milestone."""

    project_root: Path
    workspace_dir: Path
    tasks_dir: Path
    knowledge_dir: Path
    skills_dir: Path
    context_dir: Path
    sessions_dir: Path
    background_jobs_dir: Path
    workspaces_dir: Path
    coordination_dir: Path
    model_provider: str
    model_small_name: str
    model_medium_name: str
    model_large_name: str
    planner_model_level: str
    executor_model_level: str
    reviewer_model_level: str
    openai_api_key: str
    openai_base_url: str
    model_enabled: bool

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from the environment."""

        load_dotenv()
        project_root = Path(os.getenv("AGENTOS_PROJECT_ROOT", str(Path.cwd()))).resolve()
        workspace_dir = Path(os.getenv("AGENTOS_WORKSPACE", str(project_root)))
        tasks_dir = Path(os.getenv("AGENTOS_TASKS_DIR", str(project_root / ".agentos" / "tasks")))
        knowledge_dir = Path(os.getenv("AGENTOS_KNOWLEDGE_DIR", str(project_root / "knowledge")))
        skills_dir = Path(os.getenv("AGENTOS_SKILLS_DIR", str(project_root / "skills")))
        context_dir = Path(os.getenv("AGENTOS_CONTEXT_DIR", str(project_root / ".agentos" / "context")))
        sessions_dir = Path(os.getenv("AGENTOS_SESSIONS_DIR", str(project_root / ".agentos" / "sessions")))
        background_jobs_dir = Path(
            os.getenv("AGENTOS_BACKGROUND_DIR", str(project_root / ".agentos" / "background"))
        )
        workspaces_dir = Path(
            os.getenv("AGENTOS_WORKSPACES_DIR", str(project_root / ".agentos" / "workspaces"))
        )
        coordination_dir = Path(
            os.getenv("AGENTOS_COORDINATION_DIR", str(project_root / ".agentos" / "coordination"))
        )
        model_provider = os.getenv("AGENTOS_MODEL_PROVIDER", "openai")
        model_small_name = os.getenv("AGENTOS_MODEL_SMALL", "gpt-5.4")
        model_medium_name = os.getenv("AGENTOS_MODEL_MEDIUM", "gpt-5.4")
        model_large_name = os.getenv("AGENTOS_MODEL_LARGE", "gpt-5.4")
        planner_model_level = os.getenv("AGENTOS_PLANNER_MODEL_LEVEL", "medium")
        executor_model_level = os.getenv("AGENTOS_EXECUTOR_MODEL_LEVEL", "medium")
        reviewer_model_level = os.getenv("AGENTOS_REVIEWER_MODEL_LEVEL", "medium")
        openai_api_key = os.getenv("OPENAI_API_KEY", "")
        openai_base_url = os.getenv("OPENAI_BASE_URL", "")
        model_enabled = os.getenv("AGENTOS_MODEL_ENABLED", "1").lower() not in {"0", "false", "no"}
        return cls(
            project_root=project_root,
            workspace_dir=workspace_dir,
            tasks_dir=tasks_dir,
            knowledge_dir=knowledge_dir,
            skills_dir=skills_dir,
            context_dir=context_dir,
            sessions_dir=sessions_dir,
            background_jobs_dir=background_jobs_dir,
            workspaces_dir=workspaces_dir,
            coordination_dir=coordination_dir,
            model_provider=model_provider,
            model_small_name=model_small_name,
            model_medium_name=model_medium_name,
            model_large_name=model_large_name,
            planner_model_level=planner_model_level,
            executor_model_level=executor_model_level,
            reviewer_model_level=reviewer_model_level,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
            model_enabled=model_enabled,
        )
