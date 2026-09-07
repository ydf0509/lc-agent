import uuid
from datetime import datetime, timezone
from typing import Any

from sqlmodel import SQLModel, Field
from sqlalchemy import Boolean, Column, Index, Integer, JSON, String, false, text


def utcnow():
    return datetime.now(timezone.utc)


class PromptTemplateDB(SQLModel, table=True):
    __tablename__ = "prompt_templates"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    content: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class AutomationTask(SQLModel, table=True):
    __tablename__ = "automation_tasks"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(default="", index=True)
    name: str
    agent_id: str = Field(index=True)
    prompt: str
    schedule_type: str
    schedule_config: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    notification_targets: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default=text("'[]'")),
    )
    timezone: str = ""
    enabled: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, server_default=false()))
    next_run_at: datetime | None = Field(default=None, index=True)
    last_run_at: datetime | None = Field(default=None)
    last_status: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class AutomationRun(SQLModel, table=True):
    __tablename__ = "automation_runs"
    __table_args__ = (
        Index(
            "uq_automation_runs_active_task",
            "task_id",
            unique=True,
            sqlite_where=text("status IN ('pending', 'running')"),
        ),
    )

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    task_id: str = Field(index=True)
    user_id: str = Field(default="", index=True)
    session_id: str | None = Field(default=None, index=True)
    status: str = "pending"
    scheduled_at: datetime
    started_at: datetime | None = Field(default=None)
    finished_at: datetime | None = Field(default=None)
    error: str | None = Field(default=None)
    notification_status: str = Field(
        default="not_configured",
        sa_column=Column(String, nullable=False, server_default="not_configured"),
    )
    notification_error: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)


class AgentPromptBindingDB(SQLModel, table=True):
    __tablename__ = "agent_prompt_bindings"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    agent_id: str = Field(index=True)
    prompt_id: str = Field(index=True)
    sort_order: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )


class AgentPresetDB(SQLModel, table=True):
    __tablename__ = "agent_presets"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    display_name: str | None = Field(default=None)
    system_prompt: str = ""
    default_model: str = ""
    default_delegation_description: str = Field(
        default="",
        sa_column=Column(String, nullable=False, server_default=text("''")),
    )
    can_be_subagent: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=false()),
    )
    allowed_tool_groups: list[str] | None = Field(default=None, sa_column=Column(JSON))
    allowed_mcp_servers: list[str] | None = Field(default=None, sa_column=Column(JSON))
    allowed_skills: list[str] | None = Field(default=None, sa_column=Column(JSON))
    subagents: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    enable_general_purpose_subagent: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=false()),
    )
    llm_params: dict | None = Field(default=None, sa_column=Column(JSON))
    project_mode: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=false()),
    )
    project_root: str | None = Field(default=None)
    project_extra_dirs: list[str] | None = Field(default=None, sa_column=Column(JSON))
    extra_skill_dirs: list[str] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class SessionMeta(SQLModel, table=True):
    __tablename__ = "sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    title: str = "新对话"
    agent_id: str = "chat"
    model: str = ""
    user_id: str = Field(default="", index=True)
    parent_session_id: str | None = Field(default=None, index=True)
    tool_call_id: str | None = Field(default=None)
    message_count: int = 0
    git_base_hash: str | None = Field(default=None)
    is_pinned: bool = False
    pinned_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class FileChange(SQLModel, table=True):
    __tablename__ = "file_changes"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(index=True)
    file_path: str
    change_type: str  # "edit" | "create" | "append" | "delete" | "move"
    old_string: str | None = Field(default=None)
    new_string: str | None = Field(default=None)
    tool_call_id: str | None = Field(default=None)
    move_destination: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)


class ChatUiMessage(SQLModel, table=True):
    __tablename__ = "chat_ui_messages"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(index=True)
    role: str
    content: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    tool_calls: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    usage: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    http_traces: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
