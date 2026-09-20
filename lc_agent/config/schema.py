from typing import Any

from pydantic import BaseModel, Field, model_validator

from lc_agent.config.utils import DEFAULT_MAX_SUBAGENT_DEPTH, DEFAULT_RECURSION_LIMIT


class ModelConfig(BaseModel):
    model_id: str       # 前端用的全局唯一别名（标识/统计/显示用，从不进请求体）
    raw_model_id: str   # 渠道期望的真实模型名（请求一律发这个）兼定价兜底 + 统计归并用
    context_limit: int = 200000  # maps to LangChain profile["max_input_tokens"]
    max_output_tokens: int = 65536


class ProviderConfig(BaseModel):
    api_key: str = ""
    base_url: str = ""
    models: list[ModelConfig] = Field(default_factory=list)


class DatabaseConfig(BaseModel):
    url: str = "sqlite+aiosqlite:///./lc_agent_data.db"
    checkpoint_path: str = "./lc_agent_checkpoints.db"
    # LangGraph has no generic SQLAlchemy checkpointer: only SQLite and
    # PostgreSQL exist as official savers. Set this to a PostgreSQL URL to use
    # AsyncPostgresSaver; leave empty to fall back to checkpoint_path (SQLite).
    checkpoint_url: str = ""


class MemorySemanticSearchConfig(BaseModel):
    enabled: bool = True
    api_key: str = "{env:NBRAG_API_KEY}"
    base_url: str = "https://api.siliconflow.cn/v1"
    model: str = "BAAI/bge-m3"
    dims: int = 1024


class MemoryConfig(BaseModel):
    enabled: bool = True
    type: str = "sqlite"
    path: str = "./lc_agent_memory.db"
    save_policy: str = "explicit"
    retrieval_policy: str = "manual"
    semantic_search: MemorySemanticSearchConfig = Field(default_factory=MemorySemanticSearchConfig)


class McpServerConfig(BaseModel):
    type: str = "local"  # "local", "sse", "http"
    command: str | list[str] = ""
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str = ""
    enabled: bool = True

    @model_validator(mode="before")
    @classmethod
    def infer_http_type_from_url(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("url") and not data.get("type"):
            return {**data, "type": "http"}
        return data


class AuthConfig(BaseModel):
    secret: str = ""
    token_expire_days: int = 7
    # 系统账号名：框架自动创建，用于归属非真人发起的调用（见 docs/tasks/lcagent_as_mcp.md）。
    # 管理界面把它标记为"系统"，角色锁定为 user、不可删除（见 docs/tasks/user_role_management.md §2.2）。
    service_username: str = "lcagent_as_mcp_user"


class UsageStatsConfig(BaseModel):
    """Token 用量统计开关（docs/tasks/token_stats.md §3.4）。

    enabled=False 只关采集（recorder no-op）；表照建、已落库数据照常可查。
    """

    enabled: bool = True


class AppConfig(BaseModel):
    """Application configuration schema."""

    provider: dict[str, ProviderConfig | dict] = Field(default_factory=dict)
    agent: dict = Field(default_factory=lambda: {
        "system_prompt": "You are a helpful assistant.",
        "default_model": "",
        "streaming": True,
        "recursion_limit": DEFAULT_RECURSION_LIMIT,
        "max_subagent_depth": DEFAULT_MAX_SUBAGENT_DEPTH,
    })
    mcp: dict = Field(default_factory=dict)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    usage_stats: UsageStatsConfig = Field(default_factory=UsageStatsConfig)
    session: dict = Field(default_factory=lambda: {"db_path": ""})
    ui: dict = Field(default_factory=dict)
    skills: list[str] = Field(default_factory=lambda: ["./skills"])
    mcpServers: dict[str, McpServerConfig] = Field(default_factory=dict)
