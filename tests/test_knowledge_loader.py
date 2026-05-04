from pathlib import Path

from agentos.knowledge import KnowledgeLoader


def test_knowledge_loader_lists_and_loads_topics(tmp_path: Path):
    (tmp_path / "langgraph.md").write_text("graph notes", encoding="utf-8")
    (tmp_path / "ignore.json").write_text("{}", encoding="utf-8")

    loader = KnowledgeLoader(tmp_path)

    assert loader.list_topics() == ["langgraph"]
    message = loader.load_topic("langgraph")
    assert "[knowledge:langgraph]" in message.content
    assert message.additional_kwargs["topic"] == "langgraph"
