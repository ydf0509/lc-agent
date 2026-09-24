"""lc-agent skill loader: global skill directories plus a dynamic overlay.

One loader serves the whole app:

- Visibility is delegated to the package filters. ``BlacklistSkillLoader``
  holds ``disabled_skills`` by reference, so a runtime toggle takes effect on
  ``list / load / read / resolve`` at once. ``AllowedSkillLoader`` (applied by
  the middleware, once per preset) enforces ``allowed_skills``.
- The project overlay is per-request: the engine calls
  :meth:`LcAgentSkillLoader.set_project_overlay` before building an agent. The
  overlay directories are cached as loader instances keyed by the directory
  tuple, so switching presets never re-scans a directory that was already
  scanned; the merge order is global first, overlay last (the package
  ``CompositeSkillLoader`` is last-wins, which is what makes a project skill
  override a global one of the same name).

The reporting helpers (``list_all_skills`` / ``list_global_skills`` /
``list_overlay_skills`` / ``resolve_root_any``) answer the UI's questions,
which are deliberately wider than agent visibility: they include disabled
skills, and the global report never sees the overlay.
"""

from pathlib import Path

from nb_langchain_agentskills import (
    BlacklistSkillLoader,
    CompositeSkillLoader,
    DirectorySkillLoader,
    SkillContent,
    SkillLoader,
    SkillMetadata,
    SkillNotFoundError,
)

DEFAULT_TTL_SECONDS = 60.0
DEFAULT_EXCLUDE_DIRS = ["__pycache__"]


class LcAgentSkillLoader(SkillLoader):
    """Global skills + project overlay, minus the disabled names."""

    def __init__(
        self,
        global_dirs: list[str],
        *,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
    ) -> None:
        dirs: list[str] = []
        for d in global_dirs or []:
            if isinstance(d, str) and d.strip():
                resolved = str(Path(d.strip()).expanduser().resolve())
                if resolved not in dirs:
                    dirs.append(resolved)
        if not dirs:
            raise ValueError("LcAgentSkillLoader requires at least one skills directory")

        self._ttl_seconds = float(ttl_seconds)
        self._global_dirs = dirs
        global_loaders = [
            DirectorySkillLoader(
                d,
                exclude_dirs=DEFAULT_EXCLUDE_DIRS,
                ttl_seconds=self._ttl_seconds,
            )
            for d in dirs
        ]
        self._global_loader: SkillLoader = (
            global_loaders[0]
            if len(global_loaders) == 1
            else CompositeSkillLoader(global_loaders, ttl_seconds=self._ttl_seconds)
        )
        self._overlay_cache: dict[str, SkillLoader] = {}
        self._overlay_dirs: tuple[str, ...] = ()
        self._disabled: set[str] = set()
        self._visible: SkillLoader = self._compose()

    # ------------------------------------------------------------------
    # SkillLoader contract — always the current merged, filtered view.
    # ------------------------------------------------------------------

    @property
    def last_warnings(self):
        return self._visible.last_warnings

    def list_skills(self) -> list[SkillMetadata]:
        return self._visible.list_skills()

    def load_skill(self, name: str) -> SkillContent:
        return self._visible.load_skill(name)

    def read_content(self, skill_name: str, file_path: str) -> str:
        return self._visible.read_content(skill_name, file_path)

    def resolve_root(self, skill_name: str) -> Path:
        return self._visible.resolve_root(skill_name)

    # ------------------------------------------------------------------
    # Overlay
    # ------------------------------------------------------------------

    def set_project_overlay(self, dirs: str | list[str] | None) -> None:
        """Set or clear the overlay skill directories.

        Accepts one directory or a list. Non-existent entries are skipped;
        a later directory overrides an earlier one of the same skill name.
        Calling with the current directories is a no-op.
        """
        if isinstance(dirs, str):
            dirs = [dirs]
        kept: list[str] = []
        for d in dirs or []:
            if not isinstance(d, str) or not d.strip():
                continue
            resolved = str(Path(d.strip()).expanduser().resolve())
            if not Path(resolved).is_dir() or resolved in kept:
                continue
            kept.append(resolved)

        signature = tuple(kept)
        if signature == self._overlay_dirs:
            return
        for d in signature:
            if d not in self._overlay_cache:
                self._overlay_cache[d] = DirectorySkillLoader(
                    d,
                    exclude_dirs=DEFAULT_EXCLUDE_DIRS,
                    ttl_seconds=self._ttl_seconds,
                )
        self._overlay_dirs = signature
        self._visible = self._compose()

    def _compose(self) -> SkillLoader:
        sources: list[SkillLoader] = [self._global_loader]
        sources.extend(self._overlay_cache[d] for d in self._overlay_dirs)
        inner: SkillLoader = (
            sources[0]
            if len(sources) == 1
            else CompositeSkillLoader(sources, ttl_seconds=self._ttl_seconds)
        )
        return BlacklistSkillLoader(inner, self._disabled)

    # ------------------------------------------------------------------
    # Runtime enable/disable
    # ------------------------------------------------------------------

    @property
    def disabled_skills(self) -> set[str]:
        return self._disabled

    def toggle(self, name: str) -> bool:
        """Toggle a skill's enabled state. Returns the new enabled state."""
        if name in self._disabled:
            self._disabled.discard(name)
            return True
        self._disabled.add(name)
        return False

    # ------------------------------------------------------------------
    # UI reporting (wider than agent visibility)
    # ------------------------------------------------------------------

    def list_global_skills(self) -> list[SkillMetadata]:
        """Global skills only — the runtime overlay never leaks in here."""
        return self._global_loader.list_skills()

    def list_overlay_skills(self) -> list[SkillMetadata]:
        """Skills from the current overlay directories, later ones winning."""
        merged: dict[str, SkillMetadata] = {}
        for d in self._overlay_dirs:
            for metadata in self._overlay_cache[d].list_skills():
                merged[metadata.name] = metadata
        return [merged[name] for name in sorted(merged)]

    def list_all_skills(self) -> list[SkillMetadata]:
        """Everything the UI should show, disabled skills included."""
        merged: dict[str, SkillMetadata] = {
            metadata.name: metadata for metadata in self._global_loader.list_skills()
        }
        for metadata in self.list_overlay_skills():
            merged[metadata.name] = metadata
        return [merged[name] for name in sorted(merged)]

    def resolve_root_any(self, name: str) -> Path:
        """Real directory of a skill for display, ignoring the disabled filter."""
        sources: list[SkillLoader] = [self._global_loader]
        sources.extend(self._overlay_cache[d] for d in self._overlay_dirs)
        for loader in reversed(sources):
            try:
                return loader.resolve_root(name)
            except SkillNotFoundError:
                continue
        available = sorted({metadata.name for metadata in self.list_all_skills()})
        raise SkillNotFoundError(name, available=available)