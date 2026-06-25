from fastapi import APIRouter, HTTPException, Request

from langchain_agentskills import SkillsToolkit

from lc_agent.skills.filtered_loader import FilteredSkillLoader

router = APIRouter(tags=["skills"])


def _get_toolkit(request: Request) -> SkillsToolkit | None:
    return getattr(request.app.state, "skills_toolkit", None)


def _get_loader(request: Request) -> FilteredSkillLoader | None:
    return getattr(request.app.state, "filtered_loader", None)


@router.get("/skills")
def list_skills(request: Request):
    """List all skills with their enabled state (tier 1 metadata)."""
    loader = _get_loader(request)
    if loader is None:
        return []
    all_skills = loader.list_all_skills()
    return [
        {
            "name": s.name,
            "description": s.description,
            "source": s.source,
            "metadata": s.metadata,
            "enabled": s.name not in loader.disabled_skills,
        }
        for s in all_skills
    ]


@router.post("/skills/{name}/toggle")
def toggle_skill(name: str, request: Request):
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
def get_skill(name: str, request: Request):
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
def read_skill_resource(name: str, resource_name: str, request: Request):
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
