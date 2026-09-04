# lc_agent/core/models.py
from pydantic import BaseModel


class SubAgentLink(BaseModel):
    agent_id: str
    delegation_description: str


class ModelInfo(BaseModel):
    """LLM model metadata."""

    id: str
    provider: str
    base_url: str
    context_limit: int = 8000
    max_output_tokens: int = 0
    api_key: str = ""


class AgentPreset(BaseModel):
    """Agent preset configuration (three-value semantics from nb_agent).

    For allowed_* fields:
      None  = all allowed (default)
      []    = all disabled
      ["a"] = only specified items allowed

    source: "builtin" | "code" | "user"
    default_enabled: controls whether tools/MCP/skills default to ON or OFF in the UI
    """

    id: str
    name: str
    display_name: str | None = None
    system_prompt: str
    default_model: str
    default_delegation_description: str = ""

    allowed_tool_groups: list[str] | None = None
    allowed_mcp_servers: list[str] | None = None
    allowed_skills: list[str] | None = None

    llm_params: dict | None = None

    source: str = "user"
    default_enabled: bool = True

    subagents: list[SubAgentLink] | None = None
    enable_general_purpose_subagent: bool = False

    project_mode: bool = False
    project_root: str | None = None
    project_extra_dirs: list[str] | None = None

    # Explicit per-preset skill directories (absolute paths). Independent of
    # project_mode; loaded in addition to global and project skills.
    extra_skill_dirs: list[str] | None = None

    # Ordered (name, content) pairs from the prompt library, injected after system_prompt.
    # Populated at runtime; not stored in DB.
    extra_system_prompts: list[tuple[str, str]] = []
