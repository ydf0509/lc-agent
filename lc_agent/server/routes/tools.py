from fastapi import APIRouter, Depends

from lc_agent.server.dependencies import get_registry
from lc_agent.tools.registry import ToolRegistry

router = APIRouter(tags=["tools"])


@router.get("/tools")
def list_tools(registry: ToolRegistry = Depends(get_registry)):
    """List all registered tools."""
    tools = []
    for name, entry in registry._global_tools.items():
        tools.append({
            "name": name,
            "group": entry["group"],
            "description": entry["tool"].description,
        })
    return tools


@router.get("/tools/groups")
def list_tool_groups(registry: ToolRegistry = Depends(get_registry)):
    """List tool groups with their tools."""
    groups: dict[str, list] = {}
    for name, entry in registry._global_tools.items():
        group_name = entry["group"] or "__ungrouped__"
        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append({
            "name": name,
            "description": entry["tool"].description,
        })
    return [
        {"name": group, "tools": tools}
        for group, tools in sorted(groups.items())
    ]
