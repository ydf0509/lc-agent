import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from lc_agent.core.engine import AgentEngine
from lc_agent.core.models import AgentPreset
from lc_agent.server.dependencies import get_engine

router = APIRouter(tags=["agents"])


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


@router.get("/agents")
def list_agents(engine: AgentEngine = Depends(get_engine)):
    """List all agent presets."""
    return [preset.model_dump() for preset in engine.get_presets()]


@router.post("/agents", status_code=201)
def create_agent(body: AgentCreateRequest, engine: AgentEngine = Depends(get_engine)):
    """Create a new agent preset."""
    preset = AgentPreset(
        id=str(uuid.uuid4()),
        name=body.name,
        system_prompt=body.system_prompt,
        default_model=body.default_model,
        allowed_tool_groups=body.allowed_tool_groups,
        allowed_mcp_servers=body.allowed_mcp_servers,
        allowed_skills=body.allowed_skills,
        dangerous_tools=body.dangerous_tools,
    )
    engine.add_preset(preset)
    return preset.model_dump()


@router.put("/agents/{agent_id}")
def update_agent(agent_id: str, body: AgentUpdateRequest, engine: AgentEngine = Depends(get_engine)):
    """Update an agent preset."""
    update_data = body.model_dump(exclude_unset=True)
    result = engine.update_preset(agent_id, update_data)
    if result is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return result.model_dump()


@router.delete("/agents/{agent_id}", status_code=204)
def delete_agent(agent_id: str, engine: AgentEngine = Depends(get_engine)):
    """Delete an agent preset."""
    if agent_id == "__default__":
        raise HTTPException(status_code=400, detail="Cannot delete default agent")
    deleted = engine.delete_preset(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")
    return Response(status_code=204)
