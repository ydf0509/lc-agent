# lc_agent/core/models.py
from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    """LLM model metadata."""

    id: str
    provider: str
    base_url: str
    context_limit: int = 8000
    api_key: str = ""


class AgentPreset(BaseModel):
    """Agent preset configuration (three-value semantics from nb_agent).

    For allowed_* fields:
      None  = all allowed (default)
      []    = all disabled
      ["a"] = only specified items allowed
    """

    id: str
    name: str
    system_prompt: str
    default_model: str

    allowed_tool_groups: list[str] | None = None
    allowed_mcp_servers: list[str] | None = None
    allowed_skills: list[str] | None = None

    dangerous_tools: list[str] = Field(default_factory=list)
