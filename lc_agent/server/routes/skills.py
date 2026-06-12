from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["skills"])


@router.get("/skills")
def list_skills(request: Request):
    """List discovered skills."""
    scanner = getattr(request.app.state, "skill_scanner", None)
    if scanner is None:
        return []
    return [
        {
            "name": s.name,
            "description": s.description,
            "group": s.group,
            "file_path": s.file_path,
            "enabled": s.name not in scanner._disabled_skills,
        }
        for s in scanner.skills
    ]


@router.post("/skills/{name}/toggle")
def toggle_skill(name: str, request: Request):
    """Toggle a skill's enabled state at runtime."""
    scanner = getattr(request.app.state, "skill_scanner", None)
    if scanner is None:
        raise HTTPException(status_code=404, detail="Skill scanner not found")
    skill = next((s for s in scanner.skills if s.name == name), None)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    if name in scanner._disabled_skills:
        scanner._disabled_skills.discard(name)
        enabled = True
    else:
        scanner._disabled_skills.add(name)
        enabled = False
    return {"name": name, "enabled": enabled}


@router.get("/skills/groups")
def list_skill_groups(request: Request):
    """List skills grouped by their metadata.group field."""
    scanner = getattr(request.app.state, "skill_scanner", None)
    if scanner is None:
        return []

    groups: dict[str, list] = {}
    for s in scanner.skills:
        group_name = s.group or "__ungrouped__"
        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append({"name": s.name, "description": s.description})

    return [
        {"group": g, "skills": skills}
        for g, skills in sorted(groups.items())
    ]
