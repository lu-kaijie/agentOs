"""Isolated workspace management."""

from __future__ import annotations

import json
from pathlib import Path


class WorkspaceManager:
    """Manage isolated execution directories for later parallel work."""

    def __init__(self, workspaces_dir: Path):
        self.workspaces_dir = Path(workspaces_dir)
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.workspaces_dir / "index.json"

    def create(self, name: str) -> dict[str, str]:
        path = self.workspaces_dir / name
        path.mkdir(parents=True, exist_ok=True)
        index = self._load_index()
        index[name] = str(path)
        self._save_index(index)
        return {"name": name, "path": str(path)}

    def list(self) -> dict[str, object]:
        return {
            "workspaces_dir": str(self.workspaces_dir),
            "workspaces": self._load_index(),
        }

    def resolve(self, name: str | None, default_path: str) -> str:
        if not name:
            return default_path
        index = self._load_index()
        if name not in index:
            raise FileNotFoundError(f"Workspace '{name}' does not exist")
        return str(index[name])

    def _load_index(self) -> dict[str, str]:
        if not self.index_path.exists():
            return {}
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _save_index(self, index: dict[str, str]) -> None:
        self.index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
