from fastapi import APIRouter, Depends, Request

from lc_agent.server.dependencies import get_registry
from lc_agent.tools.registry import ToolRegistry

router = APIRouter(tags=["tools"])


@router.get("/tools")
def list_tools(registry: ToolRegistry = Depends(get_registry)):
    """List all registered tools."""
    tools = []
    for name, entry in registry._global_tools.items():
        group = entry["group"]
        tools.append({
            "name": name,
            "group": group,
            "group_description": registry._group_descriptions.get(group, group),
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
    disabled = registry._disabled_groups
    return [
        {
            "id": group,
            "description": registry._group_descriptions.get(group, group),
            "tools": tools,
            "enabled": group not in disabled,
        }
        for group, tools in sorted(groups.items())
    ]


@router.post("/tools/groups/{group_id}/toggle")
def toggle_tool_group(group_id: str, registry: ToolRegistry = Depends(get_registry)):
    """Toggle a tool group's enabled state."""
    if group_id in registry._disabled_groups:
        registry._disabled_groups.discard(group_id)
        enabled = True
    else:
        registry._disabled_groups.add(group_id)
        enabled = False
    return {"id": group_id, "enabled": enabled}
