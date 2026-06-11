from fastapi import APIRouter, Request

router = APIRouter(tags=["skills"])


@router.get("/skills")
def list_skills(request: Request):
    """List discovered skills."""
    scanner = getattr(request.app.state, "skill_scanner", None)
    if scanner is None:
        return []
    return [
        {"name": s.name, "description": s.description, "file_path": s.file_path}
        for s in scanner.skills
    ]
