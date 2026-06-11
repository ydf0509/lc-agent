from fastapi import APIRouter, Request

router = APIRouter(tags=["mcp"])


@router.get("/mcp")
def list_mcp_servers(request: Request):
    """List MCP servers with their status."""
    manager = getattr(request.app.state, "mcp_manager", None)
    if manager is None:
        return []
    return [
        {
            "name": s.name,
            "command": s.command,
            "status": s.status,
            "tools": s.tools,
            "error": s.error,
        }
        for s in manager.servers
    ]
