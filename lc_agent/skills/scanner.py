from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class SkillInfo:
    name: str
    description: str
    content: str
    file_path: str
    group: str = ""
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SkillScanner:
    """Discovers and parses SKILL.md files from a directory."""

    def __init__(self, directory: str = "./skills"):
        self.directory = Path(directory)
        self._skills: list[SkillInfo] = []
        self._disabled_skills: set[str] = set()

    @property
    def skills(self) -> list[SkillInfo]:
        return self._skills

    def scan(self) -> list[SkillInfo]:
        """Scan directory recursively for SKILL.md files."""
        self._skills = []
        if not self.directory.exists():
            return self._skills

        for skill_file in self.directory.rglob("SKILL.md"):
            skill = self._parse_skill(skill_file)
            if skill:
                self._skills.append(skill)

        return self._skills

    def _parse_skill(self, path: Path) -> SkillInfo | None:
        """Parse a SKILL.md file with YAML frontmatter."""
        try:
            text = path.read_text(encoding="utf-8-sig")
            frontmatter, content = self._split_frontmatter(text)

            name = frontmatter.get("name", path.parent.name)
            description = frontmatter.get("description", "")
            metadata = frontmatter.get("metadata", {}) or {}
            group = metadata.get("group", "")

            return SkillInfo(
                name=name,
                description=description,
                content=content.strip(),
                file_path=str(path),
                group=group,
                metadata=metadata,
            )
        except Exception:
            return None

    def _split_frontmatter(self, text: str) -> tuple[dict, str]:
        """Split YAML frontmatter from markdown content."""
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
        if match:
            fm = yaml.safe_load(match.group(1)) or {}
            return fm, match.group(2)
        return {}, text

    def get_by_name(self, name: str) -> SkillInfo | None:
        """Get a skill by name."""
        for skill in self._skills:
            if skill.name == name:
                return skill
        return None

    def get_filtered(self, allowed: list[str] | None) -> list[SkillInfo]:
        """Filter skills by allowed list (three-value semantics).
        Also excludes runtime-disabled skills.
        """
        if allowed is None:
            skills = self._skills
        elif not allowed:
            return []
        else:
            skills = [s for s in self._skills if s.name in allowed]

        if self._disabled_skills:
            skills = [s for s in skills if s.name not in self._disabled_skills]
        return skills

    def get_groups(self) -> list[str]:
        """Return unique skill group names."""
        groups = set()
        for s in self._skills:
            if s.group:
                groups.add(s.group)
        return sorted(groups)

    def get_by_group(self, group: str) -> list[SkillInfo]:
        """Get all skills in a specific group."""
        return [s for s in self._skills if s.group == group]
