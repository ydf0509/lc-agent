import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from langchain_agentskills import SkillsToolkit

from lc_agent.db.models_auth import User
from lc_agent.server.auth_middleware import get_current_user
from lc_agent.skills.filtered_loader import FilteredSkillLoader

logger = logging.getLogger(__name__)
router = APIRouter(tags=["skills"])


def _get_toolkit(request: Request) -> SkillsToolkit | None:
    return getattr(request.app.state, "skills_toolkit", None)


def _get_loader(request: Request) -> FilteredSkillLoader | None:
    return getattr(request.app.state, "filtered_loader", None)


def _resolve_skill_path(skill_name: str, search_dirs: list[str]) -> str | None:
    """Find SKILL.md absolute path for a skill by scanning directories."""
    for d in search_dirs:
        candidate = Path(d).expanduser().resolve() / skill_name / "SKILL.md"
        if candidate.is_file():
            return str(candidate)
    return None


@router.get("/skills")
def list_skills(
    request: Request,
    project_root: str | None = None,
    extra_dirs: list[str] = Query(default=[]),
    user: User = Depends(get_current_user),
):
    """List all skills with their enabled state (tier 1 metadata).

    Scopes in the response:
    - ``scope="project"`` — skills found in ``{project_root}/.agents/skills/`` (when ``project_root`` is given)
    - ``scope="extra"``   — skills from explicitly supplied ``extra_dirs`` (repeatable query param)
    - ``scope="global"``  — all other skills from the global loader

    On name conflicts the runtime priority is: project > extra > global;
    the listing mirrors that (later scopes skip names already claimed).
    """
    loader = _get_loader(request)
    if loader is None:
        return []

    result: list[dict] = []
    project_skill_names: set[str] = set()
    extra_skill_names: set[str] = set()

    if project_root:
        # Normalize the path to handle ~, relative paths, and cross-platform separators
        resolved_root = Path(project_root).expanduser().resolve()
        project_skills_dir = resolved_root / ".agents" / "skills"
        if project_skills_dir.is_dir():
            # Keep loader state in sync so subsequent toggle_skill() recognizes project skills
            loader.set_project_overlay(str(project_skills_dir))
            try:
                project_skills = loader._project_skills()
                project_skill_names = {s.name for s in project_skills}
                result.extend(
                    {
                        "name": s.name,
                        "description": s.description,
                        "path": _resolve_skill_path(s.name, [str(project_skills_dir)]),
                        "source": str(s.source) if s.source else None,
                        "metadata": s.metadata,
                        "enabled": s.name not in loader.disabled_skills,
                        "scope": "project",
                    }
                    for s in project_skills
                )
            except Exception:
                logger.warning(
                    "Failed to scan project skills at %s", project_skills_dir, exc_info=True
                )

    # Explicit extra skill directories (per-preset config, scanned read-only)
    if extra_dirs:
        from langchain_agentskills.loaders import DirectorySkillLoader

        for d in extra_dirs:
            if not isinstance(d, str):
                continue
            d = d.strip()
            if not d:
                continue
            resolved = Path(d).expanduser()
            if not resolved.is_dir():
                continue
            try:
                dir_skills = DirectorySkillLoader(str(resolved)).list_skills()
            except Exception:
                logger.warning("Failed to scan extra skills dir at %s", d, exc_info=True)
                continue
            for s in dir_skills:
                if s.name in project_skill_names or s.name in extra_skill_names:
                    continue
                extra_skill_names.add(s.name)
                result.append(
                    {
                        "name": s.name,
                        "description": s.description,
                        "path": _resolve_skill_path(s.name, [str(resolved)]),
                        "source": str(s.source) if s.source else None,
                        "metadata": s.metadata,
                        "enabled": s.name not in loader.disabled_skills,
                        "scope": "extra",
                        "dir": str(resolved),
                    }
                )

    # Always use list_global_skills() so runtime project overlay never pollutes the global scope
    global_dirs = loader.global_skill_dirs
    result.extend(
        {
            "name": s.name,
            "description": s.description,
            "path": _resolve_skill_path(s.name, global_dirs),
            "source": str(s.source) if s.source else None,
            "metadata": s.metadata,
            "enabled": s.name not in loader.disabled_skills,
            "scope": "global",
        }
        for s in loader.list_global_skills()
        if s.name not in project_skill_names and s.name not in extra_skill_names
    )
    return result


@router.post("/skills/{name}/toggle")
def toggle_skill(
    name: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Toggle a skill's enabled state at runtime."""
    loader = _get_loader(request)
    if loader is None:
        raise HTTPException(status_code=404, detail="Skills not configured")
    all_names = {s.name for s in loader.list_all_skills()}
    if name not in all_names:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    enabled = loader.toggle(name)
    engine = getattr(request.app.state, "engine", None)
    if engine:
        engine._mcp_generation += 1
    return {"name": name, "enabled": enabled}


@router.get("/skills/{name}")
def get_skill(
    name: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Load a skill's full content (tier 2)."""
    loader = _get_loader(request)
    if loader is None:
        raise HTTPException(status_code=404, detail="Skills not configured")
    try:
        skill = loader.load_skill(name)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return {
        "name": skill.metadata.name,
        "description": skill.metadata.description,
        "body": skill.body,
        "resources": skill.resources,
        "scripts": skill.scripts,
    }


@router.get("/skills/{name}/resources/{resource_name:path}")
def read_skill_resource(
    name: str,
    resource_name: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Read a skill resource file (tier 3)."""
    loader = _get_loader(request)
    if loader is None:
        raise HTTPException(status_code=404, detail="Skills not configured")
    try:
        content = loader.read_resource(name, resource_name)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=f"Resource '{resource_name}' not found in skill '{name}'",
        )
    return {"skill": name, "resource": resource_name, "content": content}
