"""Demand-loaded knowledge and skill resources for tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from langchain_core.messages import SystemMessage


@dataclass(slots=True)
class SkillReference:
    path: str


@dataclass(slots=True)
class SkillScript:
    path: str


@dataclass(slots=True)
class SkillSpec:
    name: str
    description: str = ""
    when_to_use: str = ""
    triggers: list[str] = field(default_factory=list)
    role_hints: dict[str, str] = field(default_factory=dict)
    references: list[SkillReference] = field(default_factory=list)
    scripts: list[SkillScript] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    source_path: str = ""
    body: str = ""

    def catalog_entry(self, role: str = "") -> dict[str, str]:
        entry = {
            "name": self.name,
            "description": self.description.strip(),
            "when_to_use": self.when_to_use.strip() or self.description.strip(),
        }
        role_hint = self.role_hints.get(role, "").strip() if role else ""
        if role_hint:
            entry["when_to_use"] = role_hint
        return entry

    def summary_text(self) -> str:
        lines = [f"[skill:{self.name}]"]
        if self.description:
            lines.append(self.description)
        if self.when_to_use:
            lines.append(f"when_to_use: {self.when_to_use}")
        if self.role_hints:
            lines.append("role_hints:")
            for role, hint in sorted(self.role_hints.items()):
                lines.append(f"- {role}: {hint}")
        if self.references:
            lines.append("references:")
            for reference in self.references:
                lines.append(f"- {reference.path}")
        if self.scripts:
            lines.append("scripts:")
            for script in self.scripts:
                lines.append(f"- {script.path}")
        if self.allowed_tools:
            lines.append("allowed_tools: " + ", ".join(self.allowed_tools))
        return "\n".join(lines).strip()

    def full_text(self) -> str:
        lines = [self.summary_text()]
        if self.body.strip():
            lines.append("")
            lines.append(self.body.strip())
        return "\n".join(lines).strip()


class KnowledgeLoader:
    """Load task-relevant knowledge and user-defined skills on demand."""

    def __init__(self, knowledge_dir: Path, skills_dir: Path | None = None):
        self.knowledge_dir = Path(knowledge_dir)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir = Path(skills_dir) if skills_dir is not None else self.knowledge_dir.parent / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def list_topics(self) -> list[str]:
        topics = []
        for path in sorted(self.knowledge_dir.glob("*")):
            if path.is_file() and path.suffix in {".md", ".txt"}:
                topics.append(path.stem)
        return topics

    def list_skills(self) -> list[str]:
        skills = []
        for path in sorted(self.skills_dir.iterdir()):
            if path.is_dir() and (path / "SKILL.md").exists():
                skills.append(path.name)
        return skills

    def skill_catalog(self, role: str = "") -> list[dict[str, str]]:
        return [self.load_skill_spec(name).catalog_entry(role=role) for name in self.list_skills()]

    def skill_index(self) -> str:
        lines = ["[skills:index]"]
        for name in self.list_skills():
            spec = self.load_skill_spec(name)
            description = spec.description or "No description provided."
            lines.append(f"- {name}: {description}")
        return "\n".join(lines)

    def load_topic(self, topic: str) -> SystemMessage:
        if topic.startswith("skill:"):
            return self.load_skill(topic[len("skill:") :])
        for suffix in (".md", ".txt"):
            candidate = self.knowledge_dir / f"{topic}{suffix}"
            if candidate.exists():
                content = candidate.read_text(encoding="utf-8")
                return SystemMessage(
                    content=f"[knowledge:{topic}]\n{content}",
                    additional_kwargs={"topic": topic, "source": str(candidate), "resource_type": "knowledge"},
                )
        raise FileNotFoundError(f"Knowledge topic '{topic}' does not exist")

    def load_skill(self, reference: str) -> SystemMessage:
        name, level, target = self._parse_skill_reference(reference)
        spec = self.load_skill_spec(name)
        content = self.render_skill(spec, level=level, target=target)
        return SystemMessage(
            content=content,
            additional_kwargs={
                "topic": f"skill:{name}",
                "source": spec.source_path,
                "resource_type": "skill",
                "skill_name": name,
                "skill_level": level,
                "skill_target": target,
            },
        )

    def load_skill_spec(self, name: str) -> SkillSpec:
        path = self.skills_dir / name / "SKILL.md"
        if not path.exists():
            raise FileNotFoundError(f"Skill '{name}' does not exist")
        raw = path.read_text(encoding="utf-8")
        metadata, body = self._parse_skill_markdown(raw)
        references = [SkillReference(path=item) for item in metadata.get("references", [])]
        scripts = [SkillScript(path=item) for item in metadata.get("scripts", [])]
        role_hints = dict(metadata.get("role_hints", metadata.get("roles", {})))
        return SkillSpec(
            name=str(metadata.get("name", name)),
            description=str(metadata.get("description", "")),
            when_to_use=str(metadata.get("when_to_use", metadata.get("usage", ""))),
            triggers=[str(item).strip() for item in metadata.get("triggers", []) if str(item).strip()],
            role_hints={str(key): str(value) for key, value in role_hints.items()},
            references=references,
            scripts=scripts,
            allowed_tools=[str(item) for item in metadata.get("allowed_tools", [])],
            source_path=str(path),
            body=body.strip(),
        )

    def match_skills(self, task: str, role: str = "") -> list[SkillSpec]:
        task_text = task.strip().lower()
        if not task_text:
            return []
        matches: list[SkillSpec] = []
        for name in self.list_skills():
            spec = self.load_skill_spec(name)
            candidates = [spec.name, spec.description, *spec.triggers]
            if any(candidate and candidate.lower() in task_text for candidate in candidates):
                matches.append(spec)
                continue
            if role and role in spec.role_hints and spec.role_hints[role].lower() in task_text:
                matches.append(spec)
        return matches

    def render_skill(self, spec: SkillSpec, *, level: str = "summary", target: str = "") -> str:
        normalized = level.strip().lower()
        if normalized in {"index", "summary", ""}:
            return spec.summary_text()
        if normalized == "reference":
            return self._render_skill_reference(spec, target)
        if normalized == "full":
            return spec.full_text()
        if normalized == "script":
            return self._render_skill_script(spec, target)
        raise ValueError(f"Unsupported skill level '{level}'")

    def _render_skill_reference(self, spec: SkillSpec, target: str) -> str:
        if not target:
            raise ValueError("skill reference loading requires a target path")
        return self._render_reference_block(spec, target)

    def _render_reference_block(self, spec: SkillSpec, target: str) -> str:
        reference_path = (Path(spec.source_path).parent / target).resolve()
        skill_root = Path(spec.source_path).parent.resolve()
        if not str(reference_path).startswith(str(skill_root)):
            raise ValueError("skill reference must stay within the skill directory")
        if not reference_path.exists():
            raise FileNotFoundError(f"Skill reference '{target}' does not exist for skill '{spec.name}'")
        content = reference_path.read_text(encoding="utf-8")
        return f"[skill:{spec.name}:reference:{target}]\n{content}"

    def _render_skill_script(self, spec: SkillSpec, target: str) -> str:
        if not target:
            raise ValueError("skill script loading requires a target path")
        script_path = (Path(spec.source_path).parent / target).resolve()
        skill_root = Path(spec.source_path).parent.resolve()
        if not str(script_path).startswith(str(skill_root)):
            raise ValueError("skill script must stay within the skill directory")
        if not script_path.exists():
            raise FileNotFoundError(f"Skill script '{target}' does not exist for skill '{spec.name}'")
        return f"[skill:{spec.name}:script:{target}]\n{script_path}"

    def _parse_skill_reference(self, reference: str) -> tuple[str, str, str]:
        raw = reference.strip()
        if not raw:
            raise ValueError("skill reference must not be empty")
        name, sep, remainder = raw.partition("#")
        if not sep:
            return name, "summary", ""
        if remainder == "full":
            return name, "full", ""
        if remainder == "summary":
            return name, "summary", ""
        if remainder == "index":
            return name, "index", ""
        if remainder.startswith("ref:"):
            return name, "reference", remainder.split(":", 1)[1]
        if remainder.startswith("script:"):
            return name, "script", remainder.split(":", 1)[1]
        return name, "summary", ""

    def _parse_skill_markdown(self, raw: str) -> tuple[dict[str, object], str]:
        lines = raw.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}, raw
        try:
            end_index = lines[1:].index("---") + 1
        except ValueError:
            return {}, raw
        metadata_lines = lines[1:end_index]
        body = "\n".join(lines[end_index + 1 :])
        metadata = self._parse_simple_frontmatter(metadata_lines)
        return metadata, body

    def _parse_simple_frontmatter(self, lines: list[str]) -> dict[str, object]:
        metadata: dict[str, object] = {}
        index = 0
        while index < len(lines):
            raw_line = lines[index]
            if not raw_line.strip():
                index += 1
                continue
            if raw_line.startswith("  "):
                index += 1
                continue
            key, sep, value = raw_line.partition(":")
            if not sep:
                index += 1
                continue
            key = key.strip().replace("-", "_")
            value = value.strip()
            if value:
                metadata[key] = self._strip_scalar(value)
                index += 1
                continue
            child_lines: list[str] = []
            index += 1
            while index < len(lines):
                candidate = lines[index]
                if not candidate.strip():
                    child_lines.append(candidate)
                    index += 1
                    continue
                if not candidate.startswith("  "):
                    break
                child_lines.append(candidate)
                index += 1
            metadata[key] = self._parse_indented_block(child_lines)
        return metadata

    def _parse_indented_block(self, lines: list[str]) -> object:
        cleaned = [line for line in lines if line.strip()]
        if not cleaned:
            return []
        if all(line.lstrip().startswith("- ") for line in cleaned):
            return [self._strip_scalar(line.lstrip()[2:].strip()) for line in cleaned]
        result: dict[str, object] = {}
        index = 0
        while index < len(cleaned):
            line = cleaned[index].strip()
            key, sep, value = line.partition(":")
            if not sep:
                index += 1
                continue
            normalized = key.strip().replace("-", "_")
            if value.strip():
                result[normalized] = self._strip_scalar(value.strip())
                index += 1
                continue
            nested_lines: list[str] = []
            index += 1
            while index < len(cleaned):
                candidate = cleaned[index]
                indent = len(candidate) - len(candidate.lstrip())
                if indent <= 2:
                    break
                nested_lines.append(candidate[2:])
                index += 1
            nested_parsed = self._parse_indented_block([line[2:] if line.startswith("  ") else line for line in nested_lines])
            if isinstance(nested_parsed, dict) and "hint" in nested_parsed and len(nested_parsed) == 1:
                result[normalized] = str(nested_parsed["hint"])
            else:
                result[normalized] = nested_parsed
        return result

    def _strip_scalar(self, value: str) -> str:
        stripped = value.strip()
        if (stripped.startswith('"') and stripped.endswith('"')) or (
            stripped.startswith("'") and stripped.endswith("'")
        ):
            return stripped[1:-1]
        return stripped
