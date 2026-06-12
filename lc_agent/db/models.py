import uuid
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON


def utcnow():
    return datetime.now(timezone.utc)


class AgentPresetDB(SQLModel, table=True):
    __tablename__ = "agent_presets"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    system_prompt: str = ""
    default_model: str = ""
    allowed_tool_groups: list[str] | None = Field(default=None, sa_column=Column(JSON))
    allowed_mcp_servers: list[str] | None = Field(default=None, sa_column=Column(JSON))
    allowed_skills: list[str] | None = Field(default=None, sa_column=Column(JSON))
    dangerous_tools: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class SessionMeta(SQLModel, table=True):
    __tablename__ = "sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    title: str = "新对话"
    agent_id: str = "__chat__"
    model: str = ""
    message_count: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
