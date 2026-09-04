"""Wrapper around SkillLoader that supports runtime enable/disable toggle.

All skills default to ON.  Disabled skills are tracked in a blacklist set.
"""


from pathlib import Path

from langchain_agentskills.exceptions import SkillNotFoundError
from langchain_agentskills.loaders.base import SkillLoader
from langchain_agentskills.models import SkillContent, SkillMetadata


class _AllowedSkillsWrapper(SkillLoader):
    """Filters skill visibility by a per-preset allowed-names set.

    Thin delegation wrapper: all actual loading is delegated to ``inner``;
    only ``list_skills`` and guard methods apply the ``allowed`` filter.
    Pass this to ``SkillMiddleware`` to enforce per-preset ``allowed_skills``.

    Args:
        inner: The underlying loader (usually ``FilteredSkillLoader``).
        allowed: Set of permitted skill names, or ``None`` to allow all.
    """

    def __init__(self, inner: SkillLoader, allowed: set[str] | None = None) -> None:
        self._inner = inner
        self._allowed = allowed

    def list_skills(self) -> list[SkillMetadata]:
        skills = self._inner.list_skills()
        if self._allowed is not None:
            skills = [s for s in skills if s.name in self._allowed]
        return skills

    def has_skill(self, name: str) -> bool:
        if self._allowed is not None and name not in self._allowed:
            return False
        return self._inner.has_skill(name)

    def load_skill(self, name: str) -> SkillContent:
        if self._allowed is not None and name not in self._allowed:
            raise SkillNotFoundError(name)
        return self._inner.load_skill(name)

    def read_resource(self, skill_name: str, resource_name: str) -> str:
        if self._allowed is not None and skill_name not in self._allowed:
            raise SkillNotFoundError(skill_name)
        return self._inner.read_resource(skill_name, resource_name)

    def read_script(self, skill_name: str, script_name: str) -> Path:
        if self._allowed is not None and skill_name not in self._allowed:
            raise SkillNotFoundError(skill_name)
        return self._inner.read_script(skill_name, script_name)


class FilteredSkillLoader(SkillLoader):
    """Delegates to an inner loader but hides disabled skills.

    All skills are enabled by default.  Use :meth:`toggle` to flip a
    skill's state at runtime.

    Supports a "project overlay" — an additional SkillLoader whose skills
    take priority over global skills with the same name.
    """

    def __init__(self, inner: SkillLoader, global_skill_dirs: list[str] | None = None) -> None:
        self._inner = inner
        self._global_skill_dirs: list[str] = list(global_skill_dirs) if global_skill_dirs else []
        self._disabled: set[str] = set()
        self._project_loader: SkillLoader | None = None

    @property
    def disabled_skills(self) -> set[str]:
        return self._disabled

    @property
    def global_skill_dirs(self) -> list[str]:
        """Directories scanned for global skills."""
        return list(self._global_skill_dirs)

    def set_project_overlay(self, dirs: str | list[str] | None) -> None:
        """Set or clear the overlay skills directories.

        Accepts a single directory or a list of directories. On name conflicts
        earlier directories win (CompositeSkillLoader: first has highest priority).
        Missing directories are skipped silently.
        """
        if isinstance(dirs, str):
            dirs = [dirs]
        loaders: list[SkillLoader] = []
        if dirs:
            from langchain_agentskills.loaders import CompositeSkillLoader, DirectorySkillLoader

            for d in dirs:
                if not isinstance(d, str):
                    continue
                d = d.strip()
                if not d:
                    continue
                resolved = Path(d).expanduser()
                if resolved.is_dir():
                    loaders.append(DirectorySkillLoader(str(resolved)))
        if not loaders:
            self._project_loader = None
        elif len(loaders) == 1:
            self._project_loader = loaders[0]
        else:
            self._project_loader = CompositeSkillLoader(loaders)

    def is_enabled(self, name: str) -> bool:
        return name not in self._disabled

    def toggle(self, name: str) -> bool:
        """Toggle a skill's enabled state.  Returns the new enabled state."""
        if name in self._disabled:
            self._disabled.discard(name)
            return True
        self._disabled.add(name)
        return False

    def _project_skills(self) -> list[SkillMetadata]:
        if not self._project_loader:
            return []
        try:
            return self._project_loader.list_skills()
        except Exception:
            return []

    def list_skills(self) -> list[SkillMetadata]:
        base = [s for s in self._inner.list_skills() if s.name not in self._disabled]
        project = self._project_skills()
        if not project:
            return base
        project_names = {s.name for s in project}
        merged = [s for s in base if s.name not in project_names]
        merged.extend(project)
        return merged

    def list_all_skills(self) -> list[SkillMetadata]:
        """Return all skills including disabled ones (for UI display)."""
        base = self._inner.list_skills()
        project = self._project_skills()
        if not project:
            return base
        project_names = {s.name for s in project}
        merged = [s for s in base if s.name not in project_names]
        merged.extend(project)
        return merged

    def list_global_skills(self) -> list[SkillMetadata]:
        """Return only global skills from the base loader (no project overlay)."""
        return self._inner.list_skills()

    def load_skill(self, name: str) -> SkillContent:
        if name in self._disabled:
            raise SkillNotFoundError(name)
        if self._project_loader:
            try:
                return self._project_loader.load_skill(name)
            except SkillNotFoundError:
                pass
        return self._inner.load_skill(name)

    def read_resource(self, skill_name: str, resource_name: str) -> str:
        if skill_name in self._disabled:
            raise SkillNotFoundError(skill_name)
        if self._project_loader:
            try:
                return self._project_loader.read_resource(skill_name, resource_name)
            except (SkillNotFoundError, Exception):
                pass
        return self._inner.read_resource(skill_name, resource_name)

    def has_skill(self, name: str) -> bool:
        if name in self._disabled:
            return False
        if self._project_loader and self._project_loader.has_skill(name):
            return True
        return self._inner.has_skill(name)

    def read_script(self, skill_name: str, script_name: str) -> Path:
        if skill_name in self._disabled:
            raise SkillNotFoundError(skill_name)
        if self._project_loader:
            try:
                return self._project_loader.read_script(skill_name, script_name)
            except (SkillNotFoundError, Exception):
                pass
        return self._inner.read_script(skill_name, script_name)
