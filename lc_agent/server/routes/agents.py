import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select

from lc_agent.core.engine import AgentEngine
from lc_agent.core.models import AgentPreset
from lc_agent.db.engine import get_async_session as _get_db_session
from lc_agent.db.models import AgentPresetDB
from lc_agent.server.dependencies import get_engine

router = APIRouter(tags=["agents"])


async def get_db(request: Request):
    db_url = request.app.state.config.get("database", {}).get("url", "sqlite+aiosqlite:///./lc_agent_data.db")
    session = _get_db_session(db_url)
    try:
        yield session
    finally:
        await session.close()


class AgentCreateRequest(BaseModel):
    name: str
    system_prompt: str
    default_model: str
    allowed_tool_groups: list[str] | None = None
    allowed_mcp_servers: list[str] | None = None
    allowed_skills: list[str] | None = None
    dangerous_tools: list[str] = []


class AgentUpdateRequest(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    default_model: str | None = None
    allowed_tool_groups: list[str] | None = None
    allowed_mcp_servers: list[str] | None = None
    allowed_skills: list[str] | None = None
    dangerous_tools: list[str] | None = None


def _preset_to_dict(p: AgentPreset) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "system_prompt": p.system_prompt,
        "default_model": p.default_model,
        "allowed_tool_groups": p.allowed_tool_groups,
        "allowed_mcp_servers": p.allowed_mcp_servers,
        "allowed_skills": p.allowed_skills,
        "dangerous_tools": p.dangerous_tools,
        "source": p.source,
        "default_enabled": p.default_enabled,
    }


@router.get("/agents")
async def list_agents(engine: AgentEngine = Depends(get_engine), db=Depends(get_db)):
    """List all agent presets (builtin + code + DB-persisted)."""
    result = []

    for bp in engine.get_builtin_presets():
        result.append(_preset_to_dict(bp))

    for p in engine._custom_presets.values():
        result.append(_preset_to_dict(p))

    stmt = select(AgentPresetDB)
    rows = await db.execute(stmt)
    for row in rows.scalars().all():
        result.append({
            "id": row.id,
            "name": row.name,
            "system_prompt": row.system_prompt,
            "default_model": row.default_model,
            "allowed_tool_groups": row.allowed_tool_groups,
            "allowed_mcp_servers": row.allowed_mcp_servers,
            "allowed_skills": row.allowed_skills,
            "dangerous_tools": row.dangerous_tools,
            "source": "user",
            "default_enabled": True,
        })

    return result


@router.post("/agents", status_code=201)
async def create_agent(body: AgentCreateRequest, engine: AgentEngine = Depends(get_engine), db=Depends(get_db)):
    """Create a new agent preset (persisted to DB)."""
    preset_db = AgentPresetDB(
        id=str(uuid.uuid4()),
        name=body.name,
        system_prompt=body.system_prompt,
        default_model=body.default_model,
        allowed_tool_groups=body.allowed_tool_groups,
        allowed_mcp_servers=body.allowed_mcp_servers,
        allowed_skills=body.allowed_skills,
        dangerous_tools=body.dangerous_tools,
    )
    db.add(preset_db)
    await db.commit()
    await db.refresh(preset_db)

    preset = AgentPreset(
        id=preset_db.id,
        name=preset_db.name,
        system_prompt=preset_db.system_prompt,
        default_model=preset_db.default_model,
        allowed_tool_groups=preset_db.allowed_tool_groups,
        allowed_mcp_servers=preset_db.allowed_mcp_servers,
        allowed_skills=preset_db.allowed_skills,
        dangerous_tools=preset_db.dangerous_tools,
    )
    engine._presets[preset.id] = preset

    return {
        **preset.model_dump(),
        "source": "user",
    }


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: str, body: AgentUpdateRequest, engine: AgentEngine = Depends(get_engine), db=Depends(get_db)):
    """Update an agent preset."""
    if agent_id in engine.BUILTIN_IDS:
        raise HTTPException(status_code=400, detail="Cannot edit builtin agent")

    update_data = body.model_dump(exclude_unset=True)

    if agent_id in engine._custom_presets:
        allowed_fields = {"allowed_tool_groups", "allowed_mcp_servers", "allowed_skills", "dangerous_tools"}
        invalid_fields = set(update_data.keys()) - allowed_fields
        if invalid_fields:
            raise HTTPException(
                status_code=403,
                detail=f"Code agent only allows modifying: {', '.join(allowed_fields)}. Got: {', '.join(invalid_fields)}"
            )
        existing = engine._custom_presets[agent_id]
        updated = existing.model_copy(update=update_data)
        engine._custom_presets[agent_id] = updated
        engine.invalidate_agent_cache(agent_id, keep_exact=True)
        return {**updated.model_dump(), "source": "code"}

    stmt = select(AgentPresetDB).where(AgentPresetDB.id == agent_id)
    result = await db.execute(stmt)
    preset_db = result.scalar_one_or_none()
    if preset_db is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    for key, value in update_data.items():
        setattr(preset_db, key, value)
    preset_db.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(preset_db)

    preset = AgentPreset(
        id=preset_db.id,
        name=preset_db.name,
        system_prompt=preset_db.system_prompt,
        default_model=preset_db.default_model,
        allowed_tool_groups=preset_db.allowed_tool_groups,
        allowed_mcp_servers=preset_db.allowed_mcp_servers,
        allowed_skills=preset_db.allowed_skills,
        dangerous_tools=preset_db.dangerous_tools,
    )
    engine._presets[preset.id] = preset
    engine.invalidate_agent_cache(agent_id)

    return {**preset.model_dump(), "source": "user"}


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, engine: AgentEngine = Depends(get_engine), db=Depends(get_db)):
    """Delete an agent preset."""
    if agent_id in engine.BUILTIN_IDS:
        raise HTTPException(status_code=400, detail="Cannot delete builtin agent")
    if agent_id in engine._custom_presets:
        raise HTTPException(status_code=403, detail="Cannot delete code-registered agent")

    stmt = select(AgentPresetDB).where(AgentPresetDB.id == agent_id)
    result = await db.execute(stmt)
    preset_db = result.scalar_one_or_none()
    if preset_db is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    await db.delete(preset_db)
    await db.commit()

    engine._presets.pop(agent_id, None)
    engine.invalidate_agent_cache(agent_id)

    return Response(status_code=204)


@router.post("/agents/{agent_id}/activate")
def activate_agent(agent_id: str, request: Request, engine: AgentEngine = Depends(get_engine)):
    """Apply an agent's default toggle state to MCP servers and tool groups.

    - Agents with default_enabled=False (Empty): disable all MCP + tool groups
    - Agents with default_enabled=True (Power): enable all MCP + tool groups
    - Chat agent (allowed=[]): no change needed (preset blocks everything)
    """
    from lc_agent.tools.registry import ToolRegistry

    preset = engine._resolve_preset(agent_id)
    manager = getattr(request.app.state, "mcp_manager", None)
    registry = ToolRegistry()

    if preset.allowed_tool_groups == [] and preset.allowed_mcp_servers == []:
        return {"agent_id": agent_id, "action": "none", "reason": "preset blocks all"}

    target_enabled = preset.default_enabled

    changed_mcp = []
    if manager:
        for server in manager.servers:
            if server.enabled != target_enabled:
                server.enabled = target_enabled
                if not target_enabled:
                    server.status = "disabled"
                elif server.name in manager._sessions:
                    server.status = "connected"
                else:
                    server.status = "disconnected"
                changed_mcp.append(server.name)

    changed_groups = []
    for group in registry.get_group_names():
        is_disabled = group in registry._disabled_groups
        if target_enabled and is_disabled:
            registry._disabled_groups.discard(group)
            changed_groups.append(group)
        elif not target_enabled and not is_disabled:
            registry._disabled_groups.add(group)
            changed_groups.append(group)

    if changed_mcp or changed_groups:
        engine._mcp_generation += 1

    return {
        "agent_id": agent_id,
        "default_enabled": target_enabled,
        "changed_mcp": changed_mcp,
        "changed_groups": changed_groups,
    }
