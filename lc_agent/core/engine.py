# lc_agent/core/engine.py
from __future__ import annotations

from typing import Any, AsyncIterator

from lc_agent.core.models import AgentPreset, ModelInfo
from lc_agent.tools.registry import ToolRegistry


class AgentEngine:
    """Core agent engine wrapping LangChain create_agent with middleware support."""

    def __init__(self, config: dict, checkpointer=None):
        self.config = config
        self.tool_registry = ToolRegistry()
        self._checkpointer = checkpointer
        self._agents: dict[str, Any] = {}
        self._current_preset: AgentPreset | None = None
        self._models: list[ModelInfo] = self._parse_models(config)
        self._presets: dict[str, AgentPreset] = {}
        self._custom_presets: dict[str, AgentPreset] = {}
        self._agent_mcp_gen: dict[str, int] = {}
        self._mcp_generation: int = 0

    def _parse_models(self, config: dict) -> list[ModelInfo]:
        """Extract ModelInfo list from config."""
        models = []
        for provider_name, provider_conf in config.get("provider", {}).items():
            if isinstance(provider_conf, dict):
                for model_conf in provider_conf.get("models", []):
                    models.append(ModelInfo(
                        id=model_conf["id"],
                        provider=provider_name,
                        base_url=provider_conf.get("base_url", ""),
                        context_limit=model_conf.get("context_limit", 8000),
                        api_key=provider_conf.get("api_key", ""),
                    ))
        return models

    def get_models(self) -> list[ModelInfo]:
        """Return available models."""
        return self._models

    BUILTIN_IDS = {"__chat__", "__empty__", "__power__"}

    def get_builtin_presets(self) -> list[AgentPreset]:
        """Return the three built-in agent presets."""
        agent_conf = self.config.get("agent", {})
        default_model = agent_conf.get("default_model", "")
        return [
            AgentPreset(
                id="__chat__",
                name="Chat",
                system_prompt="You are a helpful assistant. Respond in the user's language.",
                default_model=default_model,
                allowed_tool_groups=[],
                allowed_mcp_servers=[],
                allowed_skills=[],
                source="builtin",
                default_enabled=False,
            ),
            AgentPreset(
                id="__empty__",
                name="Empty",
                system_prompt=agent_conf.get("system_prompt", "You are a helpful assistant."),
                default_model=default_model,
                allowed_tool_groups=None,
                allowed_mcp_servers=None,
                allowed_skills=None,
                source="builtin",
                default_enabled=False,
            ),
            AgentPreset(
                id="__power__",
                name="Power",
                system_prompt=agent_conf.get("system_prompt", "You are a helpful assistant."),
                default_model=default_model,
                allowed_tool_groups=None,
                allowed_mcp_servers=None,
                allowed_skills=None,
                source="builtin",
                default_enabled=True,
            ),
        ]

    def get_default_preset(self) -> AgentPreset:
        """Return the default agent (Chat - safest)."""
        return self.get_builtin_presets()[0]

    def build_agent(self, preset: AgentPreset | None = None):
        """Build a LangGraph ReAct agent from preset."""
        if preset is None:
            preset = self.get_default_preset()
        self._current_preset = preset

        system_prompt = preset.system_prompt
        if hasattr(self, '_skill_scanner') and self._skill_scanner:
            enabled_skills = self._skill_scanner.get_filtered(preset.allowed_skills)
            if enabled_skills:
                skills_text = "\n\n---\n\n".join(
                    f"## Skill: {s.name}\n\n{s.content}" for s in enabled_skills
                )
                system_prompt = f"{system_prompt}\n\n# Available Skills\n\n{skills_text}"

        tools = self.tool_registry.get_filtered_tools(preset.allowed_tool_groups)

        if hasattr(self, '_mcp_manager') and self._mcp_manager:
            mcp_tools = self._mcp_manager.get_filtered_langchain_tools(preset.allowed_mcp_servers)
            tools = tools + mcp_tools

        model_info = self._find_model(preset.default_model)
        llm = self._create_llm(model_info, preset.default_model)

        from langgraph.prebuilt import create_react_agent

        kwargs: dict[str, Any] = {}
        if self._checkpointer:
            kwargs["checkpointer"] = self._checkpointer

        if preset.dangerous_tools:
            kwargs["interrupt_before"] = ["tools"]

        agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt=system_prompt,
            **kwargs,
        )

        self._agents[preset.id] = agent
        return agent

    def _create_llm(self, model_info: ModelInfo | None, model_id: str):
        """Create a ChatOpenAI instance from model info."""
        from langchain_openai import ChatOpenAI

        if model_info:
            return ChatOpenAI(
                model=model_info.id,
                base_url=model_info.base_url or None,
                api_key=model_info.api_key or "not-set",
                temperature=0.7,
                stream_usage=True,
            )
        return ChatOpenAI(model=model_id, api_key="not-set", stream_usage=True)

    def _find_model(self, model_id: str) -> ModelInfo | None:
        """Find model info by ID."""
        for m in self._models:
            if m.id == model_id:
                return m
        return None

    def _resolve_preset(self, preset_id: str) -> AgentPreset:
        """Resolve a preset ID to an AgentPreset object."""
        if preset_id in self.BUILTIN_IDS:
            for bp in self.get_builtin_presets():
                if bp.id == preset_id:
                    return bp
        if preset_id in self._custom_presets:
            return self._custom_presets[preset_id]
        if preset_id in self._presets:
            return self._presets[preset_id]
        return self.get_default_preset()

    def _get_or_build_agent(self, preset_id: str):
        """Get cached agent or build a new one. Rebuilds if MCP state changed."""
        preset = self._resolve_preset(preset_id)
        mcp_gen = getattr(self, '_mcp_generation', 0)
        cached = self._agents.get(preset_id)
        cached_gen = self._agent_mcp_gen.get(preset_id, -1)
        if cached is None or cached_gen != mcp_gen:
            agent = self.build_agent(preset)
            self._agent_mcp_gen[preset_id] = mcp_gen
            return agent
        return cached

    async def chat(self, message: str, thread_id: str, preset_id: str = "__chat__") -> str:
        """Send a message and get a response (non-streaming)."""
        agent = self._get_or_build_agent(preset_id)

        config = {"configurable": {"thread_id": thread_id}}
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
        )
        messages = result.get("messages", [])
        if messages:
            return messages[-1].content
        return ""

    async def chat_stream(self, message: str, thread_id: str, preset_id: str = "__chat__") -> AsyncIterator[dict]:
        """Stream chat responses as events."""
        agent = self._get_or_build_agent(preset_id)

        config = {"configurable": {"thread_id": thread_id}}
        async for event in agent.astream_events(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            version="v2",
        ):
            yield event

    async def generate_title(self, user_message: str, model_id: str = "") -> str:
        """Generate a short conversation title from the user's first message."""
        model_info = self._find_model(model_id) if model_id else None
        if model_info is None and self._models:
            model_info = self._models[0]
        if model_info is None:
            return user_message[:20]

        llm = self._create_llm(model_info, model_info.id)
        try:
            resp = await llm.ainvoke([
                {"role": "system", "content": "用10个字以内为这段对话生成一个简洁标题。只输出标题，不要标点符号和引号。"},
                {"role": "user", "content": user_message[:200]},
            ])
            title = resp.content.strip().strip('"\'""').strip()
            return title[:30] if title else user_message[:20]
        except Exception:
            return user_message[:20]

    def get_presets(self) -> list[AgentPreset]:
        """Return all agent presets (including default and custom)."""
        default = self.get_default_preset()
        return [default] + list(self._presets.values()) + list(self._custom_presets.values())

    def add_preset(self, preset: AgentPreset) -> AgentPreset:
        """Add a new agent preset."""
        self._presets[preset.id] = preset
        return preset

    def update_preset(self, preset_id: str, data: dict) -> AgentPreset | None:
        """Update an existing preset."""
        if preset_id not in self._presets:
            return None
        existing = self._presets[preset_id]
        updated = existing.model_copy(update=data)
        self._presets[preset_id] = updated
        return updated

    def delete_preset(self, preset_id: str) -> bool:
        """Delete a preset. Cannot delete builtin."""
        if preset_id in self.BUILTIN_IDS:
            return False
        return self._presets.pop(preset_id, None) is not None
