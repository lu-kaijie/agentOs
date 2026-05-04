"""Demand-loaded knowledge for tasks."""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import SystemMessage


class KnowledgeLoader:
    """Load task-relevant knowledge on demand from the filesystem."""

    def __init__(self, knowledge_dir: Path):
        self.knowledge_dir = Path(knowledge_dir)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)

    def list_topics(self) -> list[str]:
        topics = []
        for path in sorted(self.knowledge_dir.glob("*")):
            if path.is_file() and path.suffix in {".md", ".txt"}:
                topics.append(path.stem)
        return topics

    def load_topic(self, topic: str) -> SystemMessage:
        for suffix in (".md", ".txt"):
            candidate = self.knowledge_dir / f"{topic}{suffix}"
            if candidate.exists():
                content = candidate.read_text(encoding="utf-8")
                return SystemMessage(
                    content=f"[knowledge:{topic}]\n{content}",
                    additional_kwargs={"topic": topic, "source": str(candidate)},
                )
        raise FileNotFoundError(f"Knowledge topic '{topic}' does not exist")
