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
    context_dir: Path
    background_jobs_dir: Path
    workspaces_dir: Path
    coordination_dir: Path
    model_provider: str
    model_name: str

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from the environment."""

        load_dotenv()
        project_root = Path(__file__).resolve().parents[2]
        workspace_dir = Path(os.getenv("AGENTOS_WORKSPACE", str(project_root)))
        tasks_dir = Path(os.getenv("AGENTOS_TASKS_DIR", str(project_root / ".agentos" / "tasks")))
        knowledge_dir = Path(os.getenv("AGENTOS_KNOWLEDGE_DIR", str(project_root / "knowledge")))
        context_dir = Path(os.getenv("AGENTOS_CONTEXT_DIR", str(project_root / ".agentos" / "context")))
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
        model_name = os.getenv("AGENTOS_MODEL", "gpt-4.1-mini")
        return cls(
            project_root=project_root,
            workspace_dir=workspace_dir,
            tasks_dir=tasks_dir,
            knowledge_dir=knowledge_dir,
            context_dir=context_dir,
            background_jobs_dir=background_jobs_dir,
            workspaces_dir=workspaces_dir,
            coordination_dir=coordination_dir,
            model_provider=model_provider,
            model_name=model_name,
        )
