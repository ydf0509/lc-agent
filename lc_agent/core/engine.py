# lc_agent/core/engine.py
from __future__ import annotations

from typing import Any, AsyncIterator

from langgraph.checkpoint.memory import InMemorySaver

from lc_agent.core.models import AgentPreset, ModelInfo
from lc_agent.tools.registry import ToolRegistry


class AgentEngine:
    """Core agent engine wrapping LangChain create_agent with middleware support."""

    def __init__(self, config: dict):
        self.config = config
        self.tool_registry = ToolRegistry()
        self._checkpointer = InMemorySaver()
        self._agents: dict[str, Any] = {}
        self._current_preset: AgentPreset | None = None
        self._models: list[ModelInfo] = self._parse_models(config)

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

    def get_default_preset(self) -> AgentPreset:
        """Create default preset from config."""
        agent_conf = self.config.get("agent", {})
        return AgentPreset(
            id="__default__",
            name="Default Agent",
            system_prompt=agent_conf.get("system_prompt", "You are a helpful assistant."),
            default_model=agent_conf.get("default_model", ""),
        )

    def build_agent(self, preset: AgentPreset | None = None):
        """Build a LangGraph agent from preset.

        Uses langchain.agents.create_agent if available (v1+),
        falls back to langgraph.prebuilt.create_react_agent.
        """
        if preset is None:
            preset = self.get_default_preset()
        self._current_preset = preset

        tools = self.tool_registry.get_filtered_tools(preset.allowed_tool_groups)

        model_info = self._find_model(preset.default_model)

        try:
            from langchain.agents import create_agent
            agent = create_agent(
                model=f"openai:{preset.default_model}",
                tools=tools,
                system_prompt=preset.system_prompt,
                interrupt_on=preset.dangerous_tools or None,
                checkpointer=self._checkpointer,
            )
        except (ImportError, AttributeError):
            from langgraph.prebuilt import create_react_agent
            from langchain_openai import ChatOpenAI

            if model_info:
                llm = ChatOpenAI(
                    model=preset.default_model,
                    base_url=model_info.base_url,
                    api_key=model_info.api_key,
                )
            else:
                llm = ChatOpenAI(model=preset.default_model)

            agent = create_react_agent(
                model=llm,
                tools=tools,
                prompt=preset.system_prompt,
                checkpointer=self._checkpointer,
            )

        self._agents[preset.id] = agent
        return agent

    def _find_model(self, model_id: str) -> ModelInfo | None:
        """Find model info by ID."""
        for m in self._models:
            if m.id == model_id:
                return m
        return None

    async def chat(self, message: str, thread_id: str, preset_id: str = "__default__") -> str:
        """Send a message and get a response (non-streaming)."""
        agent = self._agents.get(preset_id)
        if agent is None:
            agent = self.build_agent(self._current_preset or self.get_default_preset())

        config = {"configurable": {"thread_id": thread_id}}
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
        )
        messages = result.get("messages", [])
        if messages:
            return messages[-1].content
        return ""

    async def chat_stream(self, message: str, thread_id: str) -> AsyncIterator[dict]:
        """Stream chat responses as events."""
        agent = self._agents.get("__default__")
        if agent is None:
            agent = self.build_agent()

        config = {"configurable": {"thread_id": thread_id}}
        async for event in agent.astream_events(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            version="v2",
        ):
            yield event

    def get_presets(self) -> list[AgentPreset]:
        """Return all agent presets (including default)."""
        if not hasattr(self, '_presets'):
            self._presets: dict[str, AgentPreset] = {}
        default = self.get_default_preset()
        return [default] + list(self._presets.values())

    def add_preset(self, preset: AgentPreset) -> AgentPreset:
        """Add a new agent preset."""
        if not hasattr(self, '_presets'):
            self._presets = {}
        self._presets[preset.id] = preset
        return preset

    def update_preset(self, preset_id: str, data: dict) -> AgentPreset | None:
        """Update an existing preset."""
        if not hasattr(self, '_presets'):
            self._presets = {}
        if preset_id not in self._presets:
            return None
        existing = self._presets[preset_id]
        updated = existing.model_copy(update=data)
        self._presets[preset_id] = updated
        return updated

    def delete_preset(self, preset_id: str) -> bool:
        """Delete a preset. Cannot delete default."""
        if not hasattr(self, '_presets'):
            self._presets = {}
        if preset_id == "__default__":
            return False
        return self._presets.pop(preset_id, None) is not None
