import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from nb_langchain_agentskills import DirectorySkillLoader

from lc_agent.db.models_auth import User
from lc_agent.server.auth_middleware import get_current_user
from lc_agent.skills.filtered_loader import LcAgentSkillLoader

logger = logging.getLogger(__name__)
router = APIRouter(tags=["skills"])


def _get_loader(request: Request) -> LcAgentSkillLoader | None:
    return getattr(request.app.state, "skills_loader", None)


def _skill_path(loader: LcAgentSkillLoader, name: str) -> str | None:
    """Real skill directory for display; still resolved when the skill is disabled."""
    try:
        return str(loader.resolve_root_any(name))
    except Exception:
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
                project_skills = loader.list_overlay_skills()
                project_skill_names = {s.name for s in project_skills}
                result.extend(
                    {
                        "name": s.name,
                        "description": s.description,
                        "path": _skill_path(loader, s.name),
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
                extra_loader = DirectorySkillLoader(
                    str(resolved), exclude_dirs=["__pycache__"]
                )
                dir_skills = extra_loader.list_skills()
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
                        "path": str(extra_loader.resolve_root(s.name)),
                        "metadata": s.metadata,
                        "enabled": s.name not in loader.disabled_skills,
                        "scope": "extra",
                        "dir": str(resolved),
                    }
                )

    # Always use list_global_skills() so runtime project overlay never pollutes the global scope
    result.extend(
        {
            "name": s.name,
            "description": s.description,
            "path": _skill_path(loader, s.name),
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
        "files": skill.files,
        "root": str(skill.root),
    }


@router.get("/skills/{name}/files/{file_path:path}")
def read_skill_file(
    name: str,
    file_path: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Read a file inside a skill directory (tier 3)."""
    loader = _get_loader(request)
    if loader is None:
        raise HTTPException(status_code=404, detail="Skills not configured")
    try:
        content = loader.read_content(name, file_path)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=f"File '{file_path}' not found in skill '{name}'",
        )
    return {"skill": name, "file": file_path, "content": content}