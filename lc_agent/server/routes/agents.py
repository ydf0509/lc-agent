import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select

from lc_agent.config import get_database_url
from lc_agent.core.engine import AgentEngine
from lc_agent.core.models import AgentPreset, SubAgentLink
from lc_agent.db.engine import get_async_session as _get_db_session
from lc_agent.db.models import AgentPresetDB
from lc_agent.db.models_auth import User, UserAgentAccess
from lc_agent.db.repository import PromptRepository
from lc_agent.server.auth_middleware import get_current_user, require_admin
from lc_agent.server.dependencies import get_engine

router = APIRouter(tags=["agents"])


async def get_db(request: Request):
    db_url = get_database_url()
    session = _get_db_session(db_url)
    try:
        yield session
    finally:
        await session.close()


_AGENT_NAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]*$')
_AGENT_NAME_ERROR = (
    "Agent 名称只能使用英文字母、数字、连字符(-)和下划线(_)，"
    "且必须以字母开头，例如：code-assistant、researcher_v2"
)


def _clean_extra_skill_dirs(value: list[str] | None) -> list[str] | None:
    """Trim/dedupe extra skill dirs; reject non-absolute paths."""
    if value is None:
        return None
    cleaned: list[str] = []
    for d in value:
        d = d.strip()
        if not d:
            continue
        if not Path(d).expanduser().is_absolute():
            raise ValueError(f"自定义 Skills 目录必须使用绝对路径: {d}")
        if d not in cleaned:
            cleaned.append(d)
    return cleaned or None


class AgentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    display_name: str | None = None
    system_prompt: str
    default_model: str
    allowed_tool_groups: list[str] | None = None
    allowed_mcp_servers: list[str] | None = None
    allowed_skills: list[str] | None = None
    llm_params: dict | None = None
    subagents: list[SubAgentLink] | None = None
    enable_general_purpose_subagent: bool = False
    project_mode: bool = False
    project_root: str | None = None
    project_extra_dirs: list[str] | None = None
    extra_skill_dirs: list[str] | None = None

    @field_validator("name")
    @classmethod
    def validate_name_ascii(cls, v: str) -> str:
        if not _AGENT_NAME_PATTERN.match(v):
            raise ValueError(_AGENT_NAME_ERROR)
        return v

    @field_validator("subagents")
    @classmethod
    def validate_subagents(cls, value: list[SubAgentLink] | None) -> list[SubAgentLink] | None:
        if value is None:
            return value
        seen_ids: set[str] = set()
        for item in value:
            if not item.delegation_description.strip():
                raise ValueError("delegation_description must not be blank")
            if item.agent_id in seen_ids:
                raise ValueError(f"duplicate subagent agent_id: {item.agent_id}")
            seen_ids.add(item.agent_id)
        return value

    @field_validator("extra_skill_dirs")
    @classmethod
    def validate_extra_skill_dirs(cls, value: list[str] | None) -> list[str] | None:
        return _clean_extra_skill_dirs(value)


class AgentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    display_name: str | None = None
    system_prompt: str | None = None
    default_model: str | None = None
    allowed_tool_groups: list[str] | None = None
    allowed_mcp_servers: list[str] | None = None
    allowed_skills: list[str] | None = None
    llm_params: dict | None = None
    subagents: list[SubAgentLink] | None = None
    enable_general_purpose_subagent: bool | None = None
    project_mode: bool | None = None
    project_root: str | None = None
    project_extra_dirs: list[str] | None = None
    extra_skill_dirs: list[str] | None = None

    @field_validator("name")
    @classmethod
    def validate_name_ascii(cls, v: str | None) -> str | None:
        if v is not None and not _AGENT_NAME_PATTERN.match(v):
            raise ValueError(_AGENT_NAME_ERROR)
        return v

    @field_validator("extra_skill_dirs")
    @classmethod
    def validate_extra_skill_dirs(cls, value: list[str] | None) -> list[str] | None:
        return _clean_extra_skill_dirs(value)

    @field_validator("subagents")
    @classmethod
    def validate_subagents(cls, value: list[SubAgentLink] | None) -> list[SubAgentLink] | None:
        if value is None:
            return value
        seen_ids: set[str] = set()
        for item in value:
            if not item.delegation_description.strip():
                raise ValueError("delegation_description must not be blank")
            if item.agent_id in seen_ids:
                raise ValueError(f"duplicate subagent agent_id: {item.agent_id}")
            seen_ids.add(item.agent_id)
        return value


def _preset_to_dict(p: AgentPreset) -> dict:
    data = p.model_dump()
    if data.get("subagents") is not None:
        data["subagents"] = [item.model_dump() if hasattr(item, "model_dump") else item for item in data["subagents"]]
    if p.source == "code":
        return {
            "id": p.id,
            "name": p.name,
            "display_name": p.display_name,
            "system_prompt": p.system_prompt,
            "default_model": "custom",
            "allowed_tool_groups": [],
            "allowed_mcp_servers": [],
            "allowed_skills": [],
            "source": "code",
            "default_enabled": False,
            "subagents": data.get("subagents"),
            "enable_general_purpose_subagent": False,
        }
    data["source"] = p.source
    data["default_enabled"] = p.default_enabled
    return data


@router.get("/agents")
async def list_agents(
    engine: AgentEngine = Depends(get_engine),
    db=Depends(get_db),
    user: User = Depends(get_current_user),
):
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
            "display_name": row.display_name,
            "system_prompt": row.system_prompt,
            "default_model": row.default_model,
            "allowed_tool_groups": row.allowed_tool_groups,
            "allowed_mcp_servers": row.allowed_mcp_servers,
            "allowed_skills": row.allowed_skills,
            "llm_params": row.llm_params,
            "source": "user",
            "default_enabled": True,
            "subagents": row.subagents,
            "enable_general_purpose_subagent": row.enable_general_purpose_subagent,
            "project_mode": row.project_mode,
            "project_root": row.project_root,
            "project_extra_dirs": row.project_extra_dirs,
            "extra_skill_dirs": row.extra_skill_dirs,
        })

    if user.role != "admin":
        access_stmt = select(UserAgentAccess.agent_id).where(UserAgentAccess.user_id == user.id)
        access_rows = await db.execute(access_stmt)
        allowed_ids = set(access_rows.scalars().all())
        result = [a for a in result if a["id"] in allowed_ids]

    return result


def _validate_subagent_ids_exist(engine: AgentEngine, subagents: list[SubAgentLink] | None) -> None:
    """Validate that every subagent agent_id refers to a known preset."""
    if not subagents:
        return
    for link in subagents:
        if not engine._preset_exists(link.agent_id):
            raise HTTPException(
                status_code=422,
                detail=f"subagent agent_id not found: {link.agent_id}",
            )


def _path_exists(p: str) -> bool:
    return Path(p).expanduser().is_dir()


def _validate_project_paths_or_raise(
    project_mode: bool,
    project_root: str | None,
    project_extra_dirs: list[str] | None,
) -> None:
    """Raise HTTPException(422) if project paths are invalid when project_mode is on."""
    if not project_mode:
        return
    root = project_root.strip() if project_root else None
    if not root:
        raise HTTPException(status_code=422, detail="开启项目模式时必须填写项目根目录")
    paths_to_check: list[str] = [root]
    if project_extra_dirs:
        paths_to_check.extend(d.strip() for d in project_extra_dirs if d and d.strip())
    missing = [p for p in paths_to_check if not _path_exists(p)]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"以下路径不存在或不是目录: {' | '.join(missing)}",
        )


def _validate_extra_skill_dirs_or_raise(extra_skill_dirs: list[str] | None) -> None:
    """Raise HTTPException(422) if extra skill dirs do not exist."""
    if not extra_skill_dirs:
        return
    missing = [d for d in extra_skill_dirs if not _path_exists(d)]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"以下自定义 Skills 目录不存在或不是目录: {' | '.join(missing)}",
        )


class CheckPathsRequest(BaseModel):
    paths: list[str] = []

    @field_validator("paths")
    @classmethod
    def limit_paths(cls, v: list[str]) -> list[str]:
        if len(v) > 20:
            raise ValueError("一次最多检查 20 个路径")
        return v


@router.post("/check-paths")
async def check_paths(body: CheckPathsRequest):
    """Check whether filesystem paths exist on the server (no auth required)."""
    return [
        {"path": p, "exists": _path_exists(p)}
        for p in body.paths
    ]


@router.post("/agents", status_code=201)
async def create_agent(
    body: AgentCreateRequest,
    engine: AgentEngine = Depends(get_engine),
    db=Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Create a new agent preset (persisted to DB)."""
    _validate_subagent_ids_exist(engine, body.subagents)
    _validate_project_paths_or_raise(body.project_mode, body.project_root, body.project_extra_dirs)
    _validate_extra_skill_dirs_or_raise(body.extra_skill_dirs)
    preset_db = AgentPresetDB(
        id=str(uuid.uuid4()),
        name=body.name,
        display_name=body.display_name,
        system_prompt=body.system_prompt,
        default_model=body.default_model,
        allowed_tool_groups=body.allowed_tool_groups,
        allowed_mcp_servers=body.allowed_mcp_servers,
        allowed_skills=body.allowed_skills,
        llm_params=body.llm_params,
        subagents=[item.model_dump() for item in body.subagents] if body.subagents else None,
        enable_general_purpose_subagent=body.enable_general_purpose_subagent,
        project_mode=body.project_mode,
        project_root=body.project_root,
        project_extra_dirs=body.project_extra_dirs,
        extra_skill_dirs=body.extra_skill_dirs,
    )
    db.add(preset_db)
    await db.commit()
    await db.refresh(preset_db)

    preset = AgentPreset(
        id=preset_db.id,
        name=preset_db.name,
        display_name=preset_db.display_name,
        system_prompt=preset_db.system_prompt,
        default_model=preset_db.default_model,
        allowed_tool_groups=preset_db.allowed_tool_groups,
        allowed_mcp_servers=preset_db.allowed_mcp_servers,
        allowed_skills=preset_db.allowed_skills,
        llm_params=preset_db.llm_params,
        subagents=[SubAgentLink.model_validate(item) for item in preset_db.subagents] if preset_db.subagents else None,
        enable_general_purpose_subagent=preset_db.enable_general_purpose_subagent,
        project_mode=preset_db.project_mode,
        project_root=preset_db.project_root,
        project_extra_dirs=preset_db.project_extra_dirs,
        extra_skill_dirs=preset_db.extra_skill_dirs,
    )
    engine._presets[preset.id] = preset

    return _preset_to_dict(preset)


@router.get("/agents/available-subagents")
async def list_available_subagents(
    engine: AgentEngine = Depends(get_engine),
    db=Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return presets visible to the current user for sub-agent selection.

    Excludes the ``chat`` builtin. Admins see all presets; regular users only
    see presets explicitly granted through ``UserAgentAccess``.
    """
    result = []

    for p in engine._custom_presets.values():
        result.append({
            "id": p.id,
            "name": p.name,
            "display_name": p.display_name,
            "source": "code",
            "description": p.default_delegation_description or "",
        })

    for bp in engine.get_builtin_presets():
        if bp.id == "chat":
            continue
        result.append({
            "id": bp.id,
            "name": bp.name,
            "display_name": bp.display_name,
            "source": "builtin",
            "description": bp.default_delegation_description or "",
        })

    stmt = select(AgentPresetDB)
    rows = await db.execute(stmt)
    for row in rows.scalars().all():
        result.append({
            "id": row.id,
            "name": row.name,
            "display_name": row.display_name,
            "source": "user",
            "description": "",
        })

    if user.role != "admin":
        access_stmt = select(UserAgentAccess.agent_id).where(UserAgentAccess.user_id == user.id)
        access_rows = await db.execute(access_stmt)
        allowed_ids = set(access_rows.scalars().all())
        result = [agent for agent in result if agent["id"] in allowed_ids]

    return result


@router.put("/agents/{agent_id}")
async def update_agent(
    agent_id: str,
    body: AgentUpdateRequest,
    engine: AgentEngine = Depends(get_engine),
    db=Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Update an agent preset."""
    if agent_id in engine.BUILTIN_IDS:
        raise HTTPException(status_code=400, detail="Cannot edit builtin agent")

    _validate_subagent_ids_exist(engine, body.subagents)
    update_data = body.model_dump(exclude_unset=True)

    if agent_id in engine._custom_presets:
        raise HTTPException(
            status_code=403,
            detail="Code agents are defined by their registered graph and cannot be edited from the UI",
        )

    stmt = select(AgentPresetDB).where(AgentPresetDB.id == agent_id)
    result = await db.execute(stmt)
    preset_db = result.scalar_one_or_none()
    if preset_db is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    merged_mode = update_data.get("project_mode", preset_db.project_mode)
    merged_root = update_data.get("project_root", preset_db.project_root)
    merged_extra = update_data.get("project_extra_dirs", preset_db.project_extra_dirs)
    _validate_project_paths_or_raise(merged_mode, merged_root, merged_extra)
    _validate_extra_skill_dirs_or_raise(update_data.get("extra_skill_dirs", preset_db.extra_skill_dirs))

    for key, value in update_data.items():
        setattr(preset_db, key, value)
    preset_db.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(preset_db)

    extra = await PromptRepository(db).resolve_extra_prompts(preset_db.id)
    preset = AgentPreset(
        id=preset_db.id,
        name=preset_db.name,
        display_name=preset_db.display_name,
        system_prompt=preset_db.system_prompt,
        default_model=preset_db.default_model,
        allowed_tool_groups=preset_db.allowed_tool_groups,
        allowed_mcp_servers=preset_db.allowed_mcp_servers,
        allowed_skills=preset_db.allowed_skills,
        llm_params=preset_db.llm_params,
        subagents=[SubAgentLink.model_validate(item) for item in preset_db.subagents] if preset_db.subagents else None,
        enable_general_purpose_subagent=preset_db.enable_general_purpose_subagent,
        project_mode=preset_db.project_mode,
        project_root=preset_db.project_root,
        project_extra_dirs=preset_db.project_extra_dirs,
        extra_skill_dirs=preset_db.extra_skill_dirs,
        extra_system_prompts=extra,
    )
    engine._presets[preset.id] = preset
    engine.invalidate_agent_cache(agent_id)

    return _preset_to_dict(preset)


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    engine: AgentEngine = Depends(get_engine),
    db=Depends(get_db),
    admin: User = Depends(require_admin),
):
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

    # Clean up prompt bindings before deleting the agent
    await PromptRepository(db).set_bindings_for_agent(agent_id, [])
    await db.delete(preset_db)
    await db.commit()

    engine._presets.pop(agent_id, None)
    engine.invalidate_agent_cache(agent_id)

    return Response(status_code=204)


@router.post("/agents/{agent_id}/activate")
def activate_agent(
    agent_id: str,
    request: Request,
    engine: AgentEngine = Depends(get_engine),
    admin: User = Depends(require_admin),
):
    """Apply an agent's default toggle state to MCP servers and tool groups.

    - Agents with default_enabled=False (Empty): disable all MCP + tool groups
    - Agents with default_enabled=True (Power): enable all MCP + tool groups
    - Chat agent (allowed=[]): no change needed (preset blocks everything)
    """
    from lc_agent.tools.registry import ToolRegistry

    preset = engine._resolve_preset(agent_id)
    if preset.source == "code" or agent_id in engine._custom_presets:
        return {
            "agent_id": agent_id,
            "action": "none",
            "reason": "code agent is controlled by its registered graph",
        }
    manager = getattr(request.app.state, "mcp_manager", None)
    loader = getattr(request.app.state, "filtered_loader", None)
    registry = ToolRegistry()

    if preset.allowed_tool_groups == [] and preset.allowed_mcp_servers == [] and preset.allowed_skills == []:
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

    changed_skills = []
    if loader:
        all_skill_names = {skill.name for skill in loader.list_all_skills()}
        if preset.allowed_skills is None:
            target_skill_names = sorted(all_skill_names)
        else:
            target_skill_names = [name for name in preset.allowed_skills if name in all_skill_names]
        for skill_name in target_skill_names:
            is_disabled = skill_name in loader.disabled_skills
            if target_enabled and is_disabled:
                loader.disabled_skills.discard(skill_name)
                changed_skills.append(skill_name)
            elif not target_enabled and not is_disabled:
                loader.disabled_skills.add(skill_name)
                changed_skills.append(skill_name)

    if changed_mcp or changed_groups or changed_skills:
        engine._mcp_generation += 1

    return {
        "agent_id": agent_id,
        "default_enabled": target_enabled,
        "changed_mcp": changed_mcp,
        "changed_groups": changed_groups,
        "changed_skills": changed_skills,
    }
