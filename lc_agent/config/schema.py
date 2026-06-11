from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    id: str
    context_limit: int = 8000


class ProviderConfig(BaseModel):
    api_key: str = ""
    base_url: str = ""
    models: list[ModelConfig] = Field(default_factory=list)


class DatabaseConfig(BaseModel):
    url: str = "sqlite+aiosqlite:///./lc_agent_data.db"
    checkpoint_path: str = "./lc_agent_checkpoints.db"


class SkillsConfig(BaseModel):
    directory: str = "./skills"


class McpServerConfig(BaseModel):
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)


class AppConfig(BaseModel):
    """Application configuration schema."""

    provider: dict[str, ProviderConfig | dict] = Field(default_factory=dict)
    agent: dict = Field(default_factory=lambda: {
        "system_prompt": "You are a helpful assistant.",
        "default_model": "",
        "streaming": True,
    })
    mcp: dict = Field(default_factory=dict)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    session: dict = Field(default_factory=lambda: {"db_path": ""})
    ui: dict = Field(default_factory=dict)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    mcp_servers: dict[str, McpServerConfig] = Field(default_factory=dict)
