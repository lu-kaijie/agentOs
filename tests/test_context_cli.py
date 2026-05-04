import json
from pathlib import Path

from typer.testing import CliRunner

from agentos.cli import app


runner = CliRunner()


def test_knowledge_cli_lists_topics(tmp_path: Path, monkeypatch):
    (tmp_path / "runtime.md").write_text("runtime notes", encoding="utf-8")
    monkeypatch.setenv("AGENTOS_KNOWLEDGE_DIR", str(tmp_path))

    result = runner.invoke(app, ["knowledge-list"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["topics"] == ["runtime"]


def test_context_demo_persists_compacted_session(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENTOS_CONTEXT_DIR", str(tmp_path))

    result = runner.invoke(app, ["context-demo", "demo-a"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["after_chars"] < payload["before_chars"]
    assert Path(payload["context_path"]).exists()
