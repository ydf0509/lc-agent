from fastapi import APIRouter, HTTPException, Request

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
            "type": s.type,
            "command": s.command,
            "url": s.url,
            "enabled": s.enabled,
            "status": s.status,
            "tools": s.tools,
            "error": s.error,
        }
        for s in manager.servers
    ]


@router.post("/mcp/{name}/toggle")
def toggle_mcp_server(name: str, request: Request):
    """Toggle a MCP server's enabled state at runtime."""
    manager = getattr(request.app.state, "mcp_manager", None)
    if manager is None:
        raise HTTPException(status_code=404, detail="MCP manager not found")
    server = manager.get_server(name)
    if server is None:
        raise HTTPException(status_code=404, detail=f"MCP server '{name}' not found")
    server.enabled = not server.enabled
    if not server.enabled:
        server.status = "disabled"
    elif server.status == "disabled":
        server.status = "disconnected"
    return {"name": name, "enabled": server.enabled, "status": server.status}
