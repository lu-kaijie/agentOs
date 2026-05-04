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
    model_provider: str
    model_name: str

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from the environment."""

        load_dotenv()
        project_root = Path(__file__).resolve().parents[2]
        workspace_dir = Path(os.getenv("AGENTOS_WORKSPACE", str(project_root)))
        model_provider = os.getenv("AGENTOS_MODEL_PROVIDER", "openai")
        model_name = os.getenv("AGENTOS_MODEL", "gpt-4.1-mini")
        return cls(
            project_root=project_root,
            workspace_dir=workspace_dir,
            model_provider=model_provider,
            model_name=model_name,
        )
