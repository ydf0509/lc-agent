"""Wrapper around SkillLoader that supports runtime enable/disable toggle.

All skills default to ON.  Disabled skills are tracked in a blacklist set.
"""

from __future__ import annotations

from pathlib import Path

from langchain_agentskills.exceptions import SkillNotFoundError
from langchain_agentskills.loaders.base import SkillLoader
from langchain_agentskills.models import SkillContent, SkillMetadata


class FilteredSkillLoader(SkillLoader):
    """Delegates to an inner loader but hides disabled skills.

    All skills are enabled by default.  Use :meth:`toggle` to flip a
    skill's state at runtime.
    """

    def __init__(self, inner: SkillLoader) -> None:
        self._inner = inner
        self._disabled: set[str] = set()

    @property
    def disabled_skills(self) -> set[str]:
        return self._disabled

    def is_enabled(self, name: str) -> bool:
        return name not in self._disabled

    def toggle(self, name: str) -> bool:
        """Toggle a skill's enabled state.  Returns the new enabled state."""
        if name in self._disabled:
            self._disabled.discard(name)
            return True
        self._disabled.add(name)
        return False

    def list_skills(self) -> list[SkillMetadata]:
        return [s for s in self._inner.list_skills() if s.name not in self._disabled]

    def list_all_skills(self) -> list[SkillMetadata]:
        """Return all skills including disabled ones (for UI display)."""
        return self._inner.list_skills()

    def load_skill(self, name: str) -> SkillContent:
        if name in self._disabled:
            raise SkillNotFoundError(name)
        return self._inner.load_skill(name)

    def read_resource(self, skill_name: str, resource_name: str) -> str:
        if skill_name in self._disabled:
            raise SkillNotFoundError(skill_name)
        return self._inner.read_resource(skill_name, resource_name)

    def has_skill(self, name: str) -> bool:
        if name in self._disabled:
            return False
        return self._inner.has_skill(name)

    def read_script(self, skill_name: str, script_name: str) -> Path:
        if skill_name in self._disabled:
            raise SkillNotFoundError(skill_name)
        return self._inner.read_script(skill_name, script_name)
