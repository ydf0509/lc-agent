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


class SkillScanner:
    """Discovers and parses SKILL.md files from a directory."""

    def __init__(self, directory: str = "./skills"):
        self.directory = Path(directory)
        self._skills: list[SkillInfo] = []

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
            text = path.read_text(encoding="utf-8")
            frontmatter, content = self._split_frontmatter(text)

            name = frontmatter.get("name", path.parent.name)
            description = frontmatter.get("description", "")

            return SkillInfo(
                name=name,
                description=description,
                content=content.strip(),
                file_path=str(path),
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
        """Filter skills by allowed list (three-value semantics)."""
        if allowed is None:
            return self._skills
        if not allowed:
            return []
        return [s for s in self._skills if s.name in allowed]
