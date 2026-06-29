# lc_agent/core/engine.py
from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from langchain.agents.middleware import TodoListMiddleware
from langchain.agents.middleware.summarization import SummarizationMiddleware

from lc_agent.core.http_trace import get_http_trace_collector
from lc_agent.core.http_trace_httpx import TracingAsyncClient
from lc_agent.core.models import AgentPreset, ModelInfo
from lc_agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class AgentEngine:
    """Core agent engine wrapping langchain.agents.create_agent with middleware support."""

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
        self.recursion_limit: int = config.get("agent", {}).get("recursion_limit", 100)

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
                        max_output_tokens=model_conf.get("max_output_tokens", 0),
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

    def build_agent(self, preset: AgentPreset | None = None, cache_key: str | None = None):
        """Build a LangGraph ReAct agent from preset."""
        if preset is None:
            preset = self.get_default_preset()
        self._current_preset = preset

        system_prompt = preset.system_prompt
        tools = self.tool_registry.get_filtered_tools(preset.allowed_tool_groups)

        if hasattr(self, '_skills_toolkit') and self._skills_toolkit:
            allowed = preset.allowed_skills
            if allowed is None or allowed:
                skill_tools = [
                    t for t in self._skills_toolkit.get_tools()
                    if t.name != "list_skills"
                ]
                tools = tools + skill_tools
                loader = self._skills_toolkit._resolved_loader
                if loader:
                    all_skills = loader.list_skills()
                    if allowed is not None:
                        all_skills = [s for s in all_skills if s.name in allowed]
                    if all_skills:
                        lines = ["# Available Skills", ""]
                        for s in all_skills:
                            lines.append(f"- **{s.name}**: {s.description}")
                        lines.append("")
                        lines.append(
                            "Use `load_skill` to get full instructions for a skill, "
                            "`read_skill_resource` to read its resources, "
                            "and `run_skill_script` to execute its scripts."
                        )
                        system_prompt = f"{system_prompt}\n\n" + "\n".join(lines)

        if hasattr(self, '_mcp_manager') and self._mcp_manager:
            mcp_tools = self._mcp_manager.get_filtered_langchain_tools(preset.allowed_mcp_servers)
            tools = tools + mcp_tools

        model_info = self._find_model(preset.default_model)
        llm = self._create_llm(model_info, preset.default_model)

        from langchain.agents import create_agent

        kwargs: dict[str, Any] = {}
        if self._checkpointer:
            kwargs["checkpointer"] = self._checkpointer

        if preset.dangerous_tools:
            kwargs["interrupt_before"] = ["tools"]

        middleware = [TodoListMiddleware()]
        middleware.extend(self._build_summarization_middleware(preset))

        agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=system_prompt,
            middleware=middleware,
            **kwargs,
        )

        self._agents[cache_key or preset.id] = agent
        return agent

    def _build_tracing_async_client(self, model_info: ModelInfo | None, model_id: str):
        provider = model_info.provider if model_info else None
        resolved_model = model_info.id if model_info else model_id
        base_url = model_info.base_url if model_info and model_info.base_url else None
        return TracingAsyncClient(
            collector_getter=get_http_trace_collector,
            provider=provider,
            model=resolved_model,
            base_url=base_url or "https://api.openai.com/v1",
            timeout=120,
        )

    def _create_llm(self, model_info: ModelInfo | None, model_id: str):
        """Create a chat model instance.

        Uses ChatOpenAIReasoning when base_url is set — extracts reasoning_content
        from any provider that returns it (DeepSeek, GLM, etc).
        Uses init_chat_model for standard providers (handles provider routing).
        """
        if model_info and model_info.base_url:
            from lc_agent.core.chat_model import ChatOpenAIReasoning
            kwargs: dict[str, Any] = dict(
                model=model_info.id,
                base_url=model_info.base_url,
                api_key=model_info.api_key or "not-set",
                temperature=0.7,
                stream_usage=True,
                http_async_client=self._build_tracing_async_client(model_info, model_id),
            )
            if model_info.max_output_tokens > 0:
                kwargs["max_tokens"] = model_info.max_output_tokens
            return ChatOpenAIReasoning(**kwargs)

        from langchain.chat_models import init_chat_model

        if model_info:
            model_str = f"{model_info.provider}:{model_info.id}" if model_info.provider else model_info.id
            return init_chat_model(
                model_str,
                api_key=model_info.api_key or "not-set",
                temperature=0.7,
                stream_usage=True,
            )

        return init_chat_model(model_id, api_key="not-set", temperature=0.7, stream_usage=True)

    def _find_model(self, model_id: str) -> ModelInfo | None:
        """Find model info by ID."""
        for m in self._models:
            if m.id == model_id:
                return m
        return None

    def _build_summarization_middleware(self, preset: AgentPreset) -> list:
        """Build SummarizationMiddleware based on config, returns empty list if disabled."""
        summ_conf = self.config.get("agent", {}).get("summarization", {})
        if not summ_conf.get("enabled", True):
            return []

        summ_model_id = summ_conf.get("model", "") or preset.default_model
        model_info = self._find_model(summ_model_id)
        llm = self._create_llm(model_info, summ_model_id)

        trigger = self._parse_context_size(summ_conf.get("trigger")) or ("fraction", 0.85)
        keep = self._parse_context_size(summ_conf.get("keep")) or ("fraction", 0.20)

        needs_profile = trigger[0] == "fraction" or keep[0] == "fraction"
        if needs_profile and model_info:
            llm.profile = {"max_input_tokens": model_info.context_limit}

        kwargs: dict[str, Any] = {"model": llm, "keep": keep, "trigger": trigger}

        try:
            mw = SummarizationMiddleware(**kwargs)
            logger.info("SummarizationMiddleware enabled: trigger=%s, keep=%s", trigger, keep)
            return [mw]
        except Exception:
            logger.exception("Failed to create SummarizationMiddleware")
            return []

    @staticmethod
    def _parse_context_size(value) -> tuple | None:
        """Parse a context size value from config (e.g. ["fraction", 0.85]) into a tuple."""
        if value is None:
            return None
        if isinstance(value, (list, tuple)) and len(value) == 2:
            kind, amount = value
            if kind in ("fraction", "tokens", "messages"):
                return (kind, amount)
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

    def _get_agent_cache_key(self, preset_id: str, model_id: str = "") -> str:
        if model_id:
            return f"{preset_id}::model::{model_id}"
        return preset_id

    def invalidate_agent_cache(self, preset_id: str, keep_exact: bool = False) -> None:
        """Remove cached agents for a preset, including model override variants."""
        prefix = f"{preset_id}::model::"
        keys = [
            key
            for key in self._agents
            if key.startswith(prefix) or (key == preset_id and not keep_exact)
        ]
        for key in keys:
            self._agents.pop(key, None)
            self._agent_mcp_gen.pop(key, None)

    def _resolve_preset_for_model(self, preset_id: str, model_id: str = "") -> AgentPreset:
        preset = self._resolve_preset(preset_id)
        if model_id and self._find_model(model_id):
            return preset.model_copy(update={"default_model": model_id})
        return preset

    def _get_or_build_agent(self, preset_id: str, model_id: str = ""):
        """Get cached agent or build a new one. Rebuilds if MCP state changed."""
        preset = self._resolve_preset_for_model(preset_id, model_id)
        cache_key = self._get_agent_cache_key(preset_id, model_id if preset.default_model == model_id else "")
        mcp_gen = getattr(self, '_mcp_generation', 0)
        cached = self._agents.get(cache_key)
        cached_gen = self._agent_mcp_gen.get(cache_key, -1)
        if cached is None or cached_gen != mcp_gen:
            agent = self.build_agent(preset, cache_key=cache_key)
            self._agent_mcp_gen[cache_key] = mcp_gen
            return agent
        return cached

    async def chat(self, message: str, thread_id: str, preset_id: str = "__chat__", model_id: str = "") -> str:
        """Send a message and get a response (non-streaming)."""
        agent = self._get_or_build_agent(preset_id, model_id)

        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": self.recursion_limit}
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
        )
        messages = result.get("messages", [])
        if messages:
            return messages[-1].content
        return ""

    async def chat_stream(
        self,
        message: str,
        thread_id: str,
        preset_id: str = "__chat__",
        model_id: str = "",
        history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[dict]:
        """Stream chat responses as events."""
        agent = self._get_or_build_agent(preset_id, model_id)

        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": self.recursion_limit}
        input_messages = list(history or [])
        input_messages.append({"role": "user", "content": message})
        async for event in agent.astream_events(
            {"messages": input_messages},
            config=config,
            version="v2",
        ):
            yield event

    async def reset_thread(self, thread_id: str) -> None:
        """Delete all checkpoints for a thread if the checkpointer supports it."""
        if not self._checkpointer:
            return

        deleter = getattr(self._checkpointer, "adelete_thread", None)
        if callable(deleter):
            await deleter(thread_id)
            return

        sync_deleter = getattr(self._checkpointer, "delete_thread", None)
        if callable(sync_deleter):
            sync_deleter(thread_id)

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
