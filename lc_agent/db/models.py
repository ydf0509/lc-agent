import uuid
from datetime import datetime, timezone
from typing import Any

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
    allowed_sub_agents: list[str] | None = Field(default_factory=list, sa_column=Column(JSON))
    llm_params: dict | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class SessionMeta(SQLModel, table=True):
    __tablename__ = "sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    title: str = "新对话"
    agent_id: str = "__chat__"
    model: str = ""
    user_id: str = Field(default="", index=True)
    message_count: int = 0
    is_pinned: bool = False
    pinned_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ChatUiMessage(SQLModel, table=True):
    __tablename__ = "chat_ui_messages"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(index=True)
    role: str
    content: str = ""
    tool_calls: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    usage: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    http_traces: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


class SubAgentRun(SQLModel, table=True):
    __tablename__ = "sub_agent_runs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    parent_session_id: str = Field(index=True)
    parent_message_id: str | None = None
    parent_tool_run_id: str = Field(index=True)
    parent_agent_id: str
    sub_agent_id: str = Field(index=True)
    sub_agent_name: str
    sub_thread_id: str = Field(index=True)
    task_description: str = ""
    status: str = Field(default="running", index=True)
    summary: str = ""
    final_result: str = ""
    depth: int = 1
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = None


class SubAgentEvent(SQLModel, table=True):
    __tablename__ = "sub_agent_events"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    run_id: str = Field(index=True)
    event_type: str = Field(index=True)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    sequence: int = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
