# lc_agent/core/engine.py
import logging
from collections.abc import Callable
from typing import Annotated, Any, AsyncIterator, Literal

from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain.agents.middleware.summarization import SummarizationMiddleware

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolCallId
from langchain_core.tools import tool as lc_tool
from pydantic import Field as _PydanticField

from lc_agent.config import get_config_value
from lc_agent.core.engine_helpers.content_helpers import _convert_history_item, _convert_text_file_blocks
from lc_agent.core.engine_helpers.project_context import _build_project_context_text
from lc_agent.skills.skill_middleware import _LcAgentSkillMiddleware
from lc_agent.middlewares.patch_tool_calls import PatchToolCallsMiddleware
from lc_agent.core.engine_helpers.subagent_helpers import SubAgentDescriptor, _extract_subagent_result
from lc_agent.core.http_trace import (
    HttpTraceCollector,
    bind_http_trace_collector,
    get_http_trace_collector,
    register_subagent_collector,
    reset_http_trace_collector,
)
from lc_agent.core.http_trace_httpx import TracingAsyncClient
from lc_agent.core.models import AgentPreset, ModelInfo
from lc_agent.middlewares.inject_current_time_prompt_middleware import inject_current_time_prompt_middleware
from lc_agent.middlewares.system_prompt import SystemPromptMiddleware
from lc_agent.prompts.subagent_prompts import GENERAL_PURPOSE_DESCRIPTION, SUBAGENT_DELEGATION_PROMPT, TASK_SYSTEM_PROMPT, TASK_TOOL_DESCRIPTION
from lc_agent.prompts.todo_prompts import TODO_SYSTEM_PROMPT, TODO_TOOL_DESCRIPTION
from lc_agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class AgentEngine:
    """Core agent engine wrapping langchain.agents.create_agent with middleware support."""

    def __init__(self, config: dict, checkpointer=None, store=None):
        self.config = config
        self.tool_registry = ToolRegistry()
        self._checkpointer = checkpointer
        self._store = store
        self._agents: dict[str, Any] = {}
        self._agent_subagent_tools: dict[str, set[str]] = {}
        self._agent_subagent_display_map: dict[str, dict[str, str]] = {}
        self._current_preset: AgentPreset | None = None
        self._models: list[ModelInfo] = self._parse_models(config)
        self._presets: dict[str, AgentPreset] = {}
        self._custom_presets: dict[str, AgentPreset] = {}
        self._code_agent_factories: dict[
            str, Callable[[str, dict[str, Any] | None], Any]
        ] = {}
        self._agent_mcp_gen: dict[str, int] = {}
        self._mcp_generation: int = 0
        self.recursion_limit: int = get_config_value(config, "agent.recursion_limit", 100)
        # Cache for project git/OS context text, keyed by resolved project_root.
        # Populated asynchronously in chat_stream; cleared on agent cache invalidation.
        self._project_ctx_text_cache: dict[str, str] = {}

    def _memory_enabled(self) -> bool:
        memory_conf = self.config.get("memory", {})
        if isinstance(memory_conf, dict):
            return memory_conf.get("enabled", True)
        return getattr(memory_conf, "enabled", True)

    def _is_code_agent(self, preset_id: str) -> bool:
        preset = self._resolve_preset(preset_id)
        return preset.source == "code" or preset_id in self._custom_presets

    def _should_use_memory_context(self, preset_id: str) -> bool:
        return self._store is not None and self._memory_enabled() and not self._is_code_agent(preset_id)

    def register_code_agent_factory(
        self,
        name: str,
        factory: Callable[[str, dict[str, Any] | None], Any],
    ) -> None:
        """Register a lazy factory for a code-defined graph.

        Factories are used when a graph must be built from runtime resources such as
        connected MCP tool schemas or the application's checkpointer.
        """
        self._code_agent_factories[name] = factory

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

    BUILTIN_IDS = {"chat", "empty", "power"}

    def get_builtin_presets(self) -> list[AgentPreset]:
        """Return the three built-in agent presets."""
        agent_conf = self.config.get("agent", {})
        default_model = agent_conf.get("default_model", "")
        return [
            AgentPreset(
                id="chat",
                name="chat",
                display_name="Chat",
                system_prompt="You are a helpful assistant. Respond in the user's language.",
                default_model=default_model,
                allowed_tool_groups=[],
                allowed_mcp_servers=[],
                allowed_skills=[],
                source="builtin",
                default_enabled=False,
            ),
            AgentPreset(
                id="empty",
                name="empty",
                display_name="Empty",
                system_prompt=agent_conf.get("system_prompt", "You are a helpful assistant."),
                default_model=default_model,
                allowed_tool_groups=None,
                allowed_mcp_servers=None,
                allowed_skills=[],
                source="builtin",
                default_enabled=False,
            ),
            AgentPreset(
                id="power",
                name="power",
                display_name="Power",
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

    def _preset_exists(self, preset_id: str) -> bool:
        """Return True if preset_id refers to a known preset."""
        return (
            preset_id in self.BUILTIN_IDS
            or preset_id in self._custom_presets
            or preset_id in self._presets
        )

    def _build_subagent_registry(
        self,
        preset: AgentPreset,
        depth: int,
        building_set: frozenset[str],
    ) -> dict[str, SubAgentDescriptor]:
        max_depth = get_config_value(self.config, "agent.max_subagent_depth", 2)
        if depth >= max_depth:
            return {}

        registry: dict[str, SubAgentDescriptor] = {}
        subagent_candidates: list[tuple[str, str]] = []
        if getattr(preset, "subagents", None):
            for subagent_link in preset.subagents:
                subagent_candidates.append((
                    subagent_link.agent_id,
                    (subagent_link.delegation_description or "").strip(),
                ))

        for subagent_id, relationship_description in subagent_candidates:
            if subagent_id in building_set:
                logger.warning("Subagent circular reference detected: %s — skipping", subagent_id)
                continue
            if not self._preset_exists(subagent_id):
                logger.warning("Subagent preset not found: %s — skipping", subagent_id)
                continue
            subagent_preset = self._resolve_preset(subagent_id)
            if not getattr(subagent_preset, "can_be_subagent", False):
                logger.warning("Subagent not eligible (can_be_subagent off): %s — skipping", subagent_id)
                continue
            display_name = subagent_preset.display_name or subagent_preset.name
            subagent_type = subagent_preset.name
            suffix = 1
            while subagent_type in registry:
                suffix += 1
                subagent_type = f"{subagent_preset.name}-{suffix}"
            registry[subagent_type] = SubAgentDescriptor(
                subagent_type=subagent_type,
                preset_id=subagent_id,
                display_name=display_name,
                description=(
                    relationship_description
                    or (getattr(subagent_preset, "default_delegation_description", "") or "").strip()
                    or display_name
                ),
            )

        if getattr(preset, "enable_general_purpose_subagent", False):
            gp_id = f"__gp__:{preset.id}"
            gp_preset = preset.model_copy(update={
                "id": gp_id,
                "subagents": None,
                "enable_general_purpose_subagent": False,
            })
            self._presets[gp_id] = gp_preset
            registry["general-purpose"] = SubAgentDescriptor(
                subagent_type="general-purpose",
                preset_id=gp_id,
                display_name="通用助手",
                description=GENERAL_PURPOSE_DESCRIPTION,
            )

        return registry

    def _make_task_tool(
        self,
        registry: dict[str, SubAgentDescriptor],
        depth: int,
        building_set: frozenset[str],
    ):
        async def _run_subagent(subagent_type: str, description: str, config: RunnableConfig, tool_call_id: str) -> str:
            descriptor = registry.get(subagent_type)
            if descriptor is None:
                available = ", ".join(sorted(registry))
                return f"[Sub-agent error: Unknown subagent_type '{subagent_type}'. Available: {available}]"

            try:
                sub_agent = self._get_or_build_agent(descriptor.preset_id, _depth=depth)
            except Exception as exc:
                logger.exception("Subagent %s failed to build: %s", descriptor.preset_id, exc)
                return f"[Sub-agent error: {exc}]"

            configurable = (config or {}).get("configurable", {})
            parent_tid = configurable.get("thread_id") or ""
            lg_ns = configurable.get("checkpoint_ns", "")
            tc_id = next(
                (seg.split(":", 1)[1] for seg in lg_ns.split("|") if seg.startswith("tools:")),
                tool_call_id,
            )
            sub_thread_id = f"{parent_tid}--sa--{tc_id}"
            sub_config = {
                **(config or {}),
                "configurable": {
                    **((config or {}).get("configurable") or {}),
                    "thread_id": sub_thread_id,
                    "sub_session_id": sub_thread_id,
                },
            }

            from lc_agent.tools.system_tools._file_change_tracker import (
                bind_session_for_file_tracking,
                reset_session_for_file_tracking,
            )

            _sa_collector = HttpTraceCollector(provider=None, model=None)
            _trace_token = bind_http_trace_collector(_sa_collector)
            _file_token = bind_session_for_file_tracking(sub_thread_id)
            try:
                result = await sub_agent.ainvoke(
                    {"messages": [{"role": "user", "content": description}]},
                    config=sub_config,
                )
                msgs = result.get("messages", [])
                return _extract_subagent_result(msgs)
            except Exception as exc:
                logger.exception("Subagent %s failed: %s", descriptor.preset_id, exc)
                return f"[Sub-agent error: {exc}]"
            finally:
                reset_session_for_file_tracking(_file_token)
                reset_http_trace_collector(_trace_token)
                register_subagent_collector(sub_thread_id, _sa_collector)

        available_agents_str = "\n\n".join(
            f"<subagent>\n"
            f"  <subagent_type>{d.subagent_type}</subagent_type>\n"
            f"  <when_to_use>{d.description}</when_to_use>\n"
            f"</subagent>"
            for d in registry.values()
        )
        task_description = TASK_TOOL_DESCRIPTION.format(available_agents=available_agents_str)

        available_types = sorted(descriptor.subagent_type for descriptor in registry.values())
        subagent_type_field_desc = (
            f"The type of subagent to use. Must be exactly one of: "
            f"{', '.join(repr(t) for t in available_types)}. "
            "Do not translate or modify it."
        )
        description_field_desc = (
            "A detailed description of the task for the subagent to perform autonomously. "
            "Must include ALL necessary background and context — the subagent cannot access your "
            "conversation history and you cannot send follow-up messages. "
            "Specify exactly what the subagent must return in its final and only reply "
            "(sections, format, language, length)."
        )

        @lc_tool("task", description=task_description)
        async def task(
            subagent_type: Annotated[Literal[*available_types], _PydanticField(  # type: ignore[valid-type]
                description=subagent_type_field_desc,
            )],
            description: Annotated[str, _PydanticField(description=description_field_desc)],
            tool_call_id: Annotated[str, InjectedToolCallId],
            config: RunnableConfig,
        ) -> str:
            return await _run_subagent(subagent_type, description, config, tool_call_id)

        return task

    def build_agent(
        self,
        preset: AgentPreset | None = None,
        cache_key: str | None = None,
        llm_params: dict | None = None,
        building_set: frozenset[str] | None = None,
        _depth: int = 0,
    ):
        """Build a LangGraph ReAct agent from preset."""
        if preset is None:
            preset = self.get_default_preset()
        self._current_preset = preset

        system_prompt = f"<instructions>\n{preset.system_prompt}\n</instructions>"
        # Subagents need an explicit reminder that only the final message is returned to the caller
        tools = self.tool_registry.get_filtered_tools(preset.allowed_tool_groups)

        # Set project skills overlay (only top-level; subagents inherit parent's overlay)
        # project_mode is the master switch: without it, project_root is ignored entirely.
        # Normalize to resolved path so it matches the cache key from chat_stream/chat.
        _effective_project_root: str | None = None
        if preset.project_mode and preset.project_root:
            from pathlib import Path as _PRoot
            _effective_project_root = str(_PRoot(preset.project_root).expanduser().resolve())
        if _depth == 0 and hasattr(self, '_skills_toolkit') and self._skills_toolkit:
            loader = getattr(self._skills_toolkit, '_resolved_loader', None)
            if loader and hasattr(loader, 'set_project_overlay'):
                # Overlay = project skills dir (project_mode) + per-preset extra skill dirs.
                # extra_skill_dirs works independently of project_mode.
                _overlay_dirs: list[str] = []
                if _effective_project_root:
                    from pathlib import Path as _Path
                    _overlay_dirs.append(str(_Path(_effective_project_root) / ".agents" / "skills"))
                for _d in (preset.extra_skill_dirs or []):
                    if isinstance(_d, str) and _d.strip():
                        _overlay_dirs.append(_d.strip())
                loader.set_project_overlay(_overlay_dirs or None)

        _memory_middleware: SystemPromptMiddleware | None = None
        _skills_middleware: _LcAgentSkillMiddleware | None = None
        if hasattr(self, '_skills_toolkit') and self._skills_toolkit:
            allowed = preset.allowed_skills
            if allowed is None or allowed:
                loader = self._skills_toolkit._resolved_loader
                if loader:
                    _candidate = _LcAgentSkillMiddleware(
                        loader,
                        allowed_skills=allowed,
                        executor=self._skills_toolkit._executor,
                    )
                    if _candidate.has_visible_skills:
                        _skills_middleware = _candidate

        if hasattr(self, '_mcp_manager') and self._mcp_manager:
            mcp_tools = self._mcp_manager.get_filtered_langchain_tools(preset.allowed_mcp_servers)
            tools = tools + mcp_tools

        kwargs: dict[str, Any] = {}
        if self._checkpointer:
            kwargs["checkpointer"] = self._checkpointer

        if self._store is not None and self._memory_enabled():
            from lc_agent.core.memory import (
                AgentRuntimeContext,
                MEMORY_SYSTEM_PROMPT,
                build_memory_tools,
            )

            tools = tools + build_memory_tools()
            _memory_middleware = SystemPromptMiddleware(MEMORY_SYSTEM_PROMPT, "MemoryPromptMiddleware")
            kwargs["store"] = self._store
            kwargs["context_schema"] = AgentRuntimeContext

        new_building = (building_set or frozenset()) | {preset.id}
        subagent_registry = self._build_subagent_registry(preset, depth=_depth, building_set=new_building)
        subagent_tool_names: set[str] = set()
        subagent_display_map: dict[str, str] = {}
        if subagent_registry:
            tools.append(self._make_task_tool(subagent_registry, _depth + 1, new_building))
            subagent_tool_names = {"task"}
            subagent_display_map = {
                descriptor.subagent_type: descriptor.display_name
                for descriptor in subagent_registry.values()
            }

        model_info = self._find_model(preset.default_model)
        effective_params = {**(preset.llm_params or {}), **(llm_params or {})}
        llm = self._create_llm(model_info, preset.default_model, llm_params=effective_params or None)

        middleware = []
        # Patch dangling tool calls (e.g. after a manual stop leaves an AIMessage
        # with tool_calls but no following ToolMessage) so the next model call
        # doesn't 400 on "tool_calls must be followed by tool messages".
        middleware.append(PatchToolCallsMiddleware())
        if _depth > 0:
            middleware.append(SystemPromptMiddleware(
                SUBAGENT_DELEGATION_PROMPT, "SubagentDelegationMiddleware", prepend=True
            ))

        # Prompt library entries: each becomes a separate content block with XML wrapping.
        # Content body is not XML-escaped so prompt text is readable as-is.
        import html as _html
        for _ep_idx, (_ep_name, _ep_content) in enumerate(preset.extra_system_prompts):
            _safe_name = _html.escape(_ep_name, quote=True) if _ep_name else ""
            _mw_id = _ep_name if _ep_name else str(_ep_idx)
            middleware.append(SystemPromptMiddleware(
                f'<extra_instruction name="{_safe_name}">\n{_ep_content}\n</extra_instruction>',
                f"ExtraPrompt:{_mw_id}",
            ))

        # Project folder mode (all controlled by project_mode master switch)
        if _depth == 0 and _effective_project_root:
            # 1. AGENTS.md rules injection
            _agents_md = self._read_project_agents_md(_effective_project_root)
            if _agents_md:
                middleware.append(SystemPromptMiddleware(
                    f"<project_rules>\n## Project Rules (AGENTS.md)\n\n{_agents_md}\n</project_rules>",
                    "ProjectAgentsMdMiddleware",
                ))
            # 2. Git status + OS context snapshot injection
            # Use cached text pre-computed async in chat_stream; fall back to sync if missing.
            _ctx_text = self._project_ctx_text_cache.get(_effective_project_root) or _build_project_context_text(_effective_project_root)
            middleware.append(SystemPromptMiddleware(_ctx_text, "ProjectContextMiddleware"))
            # 3. Per-tool-group usage guidelines (injected only for enabled groups)
            from lc_agent.prompts.builtin_agent_prompts import TOOL_GROUP_GUIDELINES
            _tg = preset.allowed_tool_groups  # None=all, []=none, [...]=specific
            for _group_id, _group_prompt in TOOL_GROUP_GUIDELINES.items():
                if _tg is None or _group_id in _tg:
                    middleware.append(SystemPromptMiddleware(_group_prompt, f"{_group_id}GuidelinesMiddleware"))

        if _memory_middleware is not None:
            middleware.append(_memory_middleware)
        if _skills_middleware is not None:
            middleware.append(_skills_middleware)
        if _depth == 0 and subagent_registry:
            middleware.append(SystemPromptMiddleware(TASK_SYSTEM_PROMPT, "TaskSystemPromptMiddleware"))
        if _depth == 0:
            middleware.append(TodoListMiddleware(
                system_prompt=TODO_SYSTEM_PROMPT,
                tool_description=TODO_TOOL_DESCRIPTION,
            ))
        middleware.extend(self._build_summarization_middleware(preset))
        if _depth == 0:
            from lc_agent.middlewares import AskUserMiddleware
            middleware.append(AskUserMiddleware())
        middleware.append(inject_current_time_prompt_middleware)

        # Only top-level agents need human-in-the-loop approval; sub-agents run autonomously
        if hasattr(self, '_permissions_service') and self._permissions_service and _depth == 0:
            from langchain.agents.middleware import HumanInTheLoopMiddleware
            # Include skill middleware tools so they're subject to permission checks
            hitl_tools = list(tools)
            if _skills_middleware is not None:
                hitl_tools.extend(_skills_middleware.tools)
            interrupt_on = {
                tool.name: {
                    "allowed_decisions": ["approve", "reject"],
                    "when": self._permissions_service.should_interrupt,
                }
                for tool in hitl_tools
                if tool.name != "ask_user"
            }
            if interrupt_on:
                middleware.append(HumanInTheLoopMiddleware(interrupt_on=interrupt_on))

        agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=system_prompt,
            middleware=middleware,
            **kwargs,
        )

        resolved_cache_key = cache_key or preset.id
        self._agents[resolved_cache_key] = agent
        self._agent_subagent_tools[resolved_cache_key] = subagent_tool_names
        self._agent_subagent_display_map[resolved_cache_key] = subagent_display_map
        return agent

    @staticmethod
    def _read_project_agents_md(project_root: str) -> str | None:
        """Read AGENTS.md from project root. Returns content or None."""
        from pathlib import Path
        p = Path(project_root) / "AGENTS.md"
        if not p.is_file():
            return None
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            return None

    async def _ensure_project_mcp(self, project_root: str | None) -> None:
        """Load project-level MCP servers from .agents/mcp.json.

        Clears previous project servers first to handle preset switching.
        """
        await self._mcp_manager.clear_project_servers()

        if not project_root:
            return

        from pathlib import Path
        import json
        mcp_file = Path(project_root) / ".agents" / "mcp.json"
        if not mcp_file.is_file():
            return
        try:
            config = json.loads(mcp_file.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(config, dict) or not config:
            return
        # Support both flat {name: conf} and the industry-standard {mcpServers: {name: conf}} wrapper
        if "mcpServers" in config and isinstance(config["mcpServers"], dict):
            config = config["mcpServers"]
        await self._mcp_manager.merge_project_servers(config)

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

    def _create_llm(
        self,
        model_info: ModelInfo | None,
        model_id: str,
        llm_params: dict | None = None,
    ):
        """Create a chat model instance.

        Uses ChatOpenAIReasoning when base_url is set — extracts reasoning_content
        from any provider that returns it (DeepSeek, GLM, etc).
        Uses init_chat_model for standard providers (handles provider routing).
        """
        params = llm_params or {}
        temperature = params.get("temperature", 0.7)
        reasoning_effort = params.get("reasoning_effort")
        # passthrough: top_p, top_k, presence_penalty, frequency_penalty, max_tokens, etc.
        HANDLED_KEYS = {"temperature", "reasoning_effort"}
        extra_params = {k: v for k, v in params.items() if k not in HANDLED_KEYS and v is not None}

        if model_info and model_info.base_url:
            from lc_agent.core.chat_model import ChatOpenAIReasoning
            kwargs: dict[str, Any] = dict(
                model=model_info.id,
                base_url=model_info.base_url,
                api_key=model_info.api_key or "not-set",
                temperature=temperature,
                stream_usage=True,
                http_async_client=self._build_tracing_async_client(model_info, model_id),
                **extra_params,
            )
            if model_info.max_output_tokens > 0:
                kwargs["max_tokens"] = model_info.max_output_tokens
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort
            return ChatOpenAIReasoning(**kwargs)

        from langchain.chat_models import init_chat_model

        if model_info:
            model_str = f"{model_info.provider}:{model_info.id}" if model_info.provider else model_info.id
            kwargs: dict[str, Any] = dict(
                api_key=model_info.api_key or "not-set",
                temperature=temperature,
                stream_usage=True,
                **extra_params,
            )
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort
            return init_chat_model(model_str, **kwargs)

        kwargs: dict[str, Any] = dict(api_key="not-set", temperature=temperature, stream_usage=True, **extra_params)
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort
        return init_chat_model(model_id, **kwargs)

    def _find_model(self, model_id: str) -> ModelInfo | None:
        """Find model info by ID."""
        for m in self._models:
            if m.id == model_id:
                return m
        return None

    def _build_summarization_middleware(self, preset: AgentPreset) -> list:
        """Build SummarizationMiddleware based on config, returns empty list if disabled."""
        summ_conf = get_config_value(self.config, "agent.summarization", {})
        if not summ_conf.get("enabled", True):
            return []

        summ_model_id = summ_conf.get("default_model", "") or preset.default_model
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

    def _get_agent_cache_key(
        self,
        preset_id: str,
        model_id: str = "",
        llm_params: dict | None = None,
        _depth: int = 0,
    ) -> str:
        key = f"{preset_id}::model::{model_id}" if model_id else preset_id
        if llm_params:
            import json
            key = f"{key}::llm::{json.dumps(llm_params, sort_keys=True)}"
        if _depth:
            key = f"{key}::depth::{_depth}"
        return key

    def get_subagent_tool_names(
        self,
        preset_id: str,
        model_id: str = "",
        llm_params: dict | None = None,
        _depth: int = 0,
    ) -> set[str]:
        """Return the set of tool names (not IDs) that are sub-agents for the given preset."""
        cache_key = self._get_agent_cache_key(
            preset_id,
            model_id if self._find_model(model_id) else "",
            llm_params=llm_params,
            _depth=_depth,
        )
        return self._agent_subagent_tools.get(cache_key, set())

    def get_subagent_display_name_map(
        self,
        preset_id: str,
        model_id: str = "",
        llm_params: dict | None = None,
        _depth: int = 0,
    ) -> dict[str, str]:
        """Return {tool_name: display_name} for sub-agents of the given preset."""
        cache_key = self._get_agent_cache_key(
            preset_id,
            model_id if self._find_model(model_id) else "",
            llm_params=llm_params,
            _depth=_depth,
        )
        return self._agent_subagent_display_map.get(cache_key, {})

    def invalidate_agent_cache(self, preset_id: str, keep_exact: bool = False) -> None:
        """Remove cached agents for a preset, including model/llm_params override variants."""
        prefix = f"{preset_id}::"
        keys = [
            key
            for key in self._agents
            if key.startswith(prefix) or (key == preset_id and not keep_exact)
        ]
        for key in keys:
            self._agents.pop(key, None)
            self._agent_mcp_gen.pop(key, None)
            self._agent_subagent_tools.pop(key, None)
            self._agent_subagent_display_map.pop(key, None)
        # Clear project context cache so a re-edited preset gets a fresh git snapshot.
        self._project_ctx_text_cache.clear()

    def invalidate_all_agents(self) -> None:
        """Remove all cached agents, forcing rebuild on next use."""
        self._agents.clear()
        self._agent_mcp_gen.clear()
        self._agent_subagent_tools.clear()
        self._agent_subagent_display_map.clear()
        self._project_ctx_text_cache.clear()

    def _resolve_preset_for_model(self, preset_id: str, model_id: str = "") -> AgentPreset:
        preset = self._resolve_preset(preset_id)
        if model_id and self._find_model(model_id):
            return preset.model_copy(update={"default_model": model_id})
        return preset

    def _get_or_build_agent(
        self,
        preset_id: str,
        model_id: str = "",
        llm_params: dict | None = None,
        _depth: int = 0,
    ):
        """Get cached agent or build a new one. Rebuilds preset agents if MCP state changed."""
        preset = self._resolve_preset(preset_id)
        if preset.source == "code" or preset_id in self._custom_presets:
            factory = self._code_agent_factories.get(preset_id)
            if factory is not None:
                selected_model_id = (
                    model_id
                    if model_id and self._find_model(model_id)
                    else get_config_value(self.config, "agent.default_model", "")
                )
                cache_key = self._get_agent_cache_key(
                    preset_id,
                    selected_model_id,
                    llm_params=llm_params,
                    _depth=_depth,
                )
                mcp_gen = getattr(self, "_mcp_generation", 0)
                cached = self._agents.get(cache_key)
                cached_gen = self._agent_mcp_gen.get(cache_key, -1)
                if cached is None or cached_gen != mcp_gen:
                    cached = factory(selected_model_id, llm_params)
                    self._agents[cache_key] = cached
                    self._agent_mcp_gen[cache_key] = mcp_gen
                return cached

            agent = self._agents.get(preset_id)
            if agent is None:
                raise ValueError(f"Code agent '{preset_id}' is registered without a graph")
            return agent

        if model_id and self._find_model(model_id):
            preset = preset.model_copy(update={"default_model": model_id})
        cache_key = self._get_agent_cache_key(
            preset_id,
            model_id if preset.default_model == model_id else "",
            llm_params=llm_params,
            _depth=_depth,
        )
        mcp_gen = getattr(self, '_mcp_generation', 0)
        cached = self._agents.get(cache_key)
        cached_gen = self._agent_mcp_gen.get(cache_key, -1)
        if cached is None or cached_gen != mcp_gen:
            agent = self.build_agent(preset, cache_key=cache_key, llm_params=llm_params, _depth=_depth)
            self._agent_mcp_gen[cache_key] = mcp_gen
            return agent
        return cached

    async def chat(
        self,
        message: str,
        thread_id: str,
        preset_id: str = "chat",
        model_id: str = "",
        user_id: str = "anonymous",
    ) -> str:
        """Send a message and get a response (non-streaming)."""
        preset = self._resolve_preset(preset_id)
        _eff_root = preset.project_root if preset.project_mode else None
        if _eff_root:
            from pathlib import Path as _PPath
            if not _PPath(_eff_root).is_dir():
                raise ValueError(f"项目根目录不存在或不可访问: {_eff_root}")
            _eff_root = str(_PPath(_eff_root).expanduser().resolve())
        from lc_agent.tools.system_tools._config import set_active_project
        set_active_project(_eff_root, preset.project_extra_dirs if preset.project_mode else None)
        if hasattr(self, '_mcp_manager') and self._mcp_manager:
            await self._ensure_project_mcp(_eff_root)
        if _eff_root and _eff_root not in self._project_ctx_text_cache:
            import asyncio as _asyncio
            self._project_ctx_text_cache[_eff_root] = await _asyncio.to_thread(
                _build_project_context_text, _eff_root
            )
        agent = self._get_or_build_agent(preset_id, model_id)

        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": self.recursion_limit}
        invoke_kwargs: dict[str, Any] = {"config": config}
        if self._should_use_memory_context(preset_id):
            from lc_agent.core.memory import AgentRuntimeContext, normalize_memory_user_id

            invoke_kwargs["context"] = AgentRuntimeContext(user_id=normalize_memory_user_id(user_id))
        result = await agent.ainvoke({"messages": [{"role": "user", "content": message}]}, **invoke_kwargs)
        messages = result.get("messages", [])
        if messages:
            return messages[-1].content
        return ""

    async def chat_stream(
        self,
        message: list[dict[str, Any]],
        thread_id: str,
        preset_id: str = "chat",
        model_id: str = "",
        history: list[dict[str, str]] | None = None,
        llm_params: dict | None = None,
        user_id: str = "anonymous",
    ) -> AsyncIterator[dict]:
        """Stream chat responses as events.

        message: LangChain content blocks list, e.g. [{"type":"text","text":"..."}, {"type":"image_url","image_url":{"url":"data:..."}}]
        """
        # Validate and activate project context (project_mode is the master switch)
        preset = self._resolve_preset(preset_id)
        _eff_project_root = preset.project_root if preset.project_mode else None
        if preset.project_mode and not _eff_project_root:
            raise ValueError("项目模式已开启，但 project_root 未设置，请编辑 Agent 并填写项目根目录。")
        if _eff_project_root:
            from pathlib import Path as _PPath
            if not _PPath(_eff_project_root).is_dir():
                raise ValueError(
                    f"项目根目录不存在或不可访问: {_eff_project_root}\n"
                    f"请检查 Preset 的 project_root 配置是否正确。"
                )
            # Normalize to resolved path for consistent cache key (matches ContextVar in _config.py)
            _eff_project_root = str(_PPath(_eff_project_root).expanduser().resolve())

        from lc_agent.tools.system_tools._config import set_active_project
        _eff_extra_dirs = preset.project_extra_dirs if preset.project_mode else None
        set_active_project(_eff_project_root, _eff_extra_dirs)

        # Load project MCP servers (or clear previous project's servers on switch)
        if hasattr(self, '_mcp_manager') and self._mcp_manager:
            await self._ensure_project_mcp(_eff_project_root)

        # Pre-compute git/OS context text asynchronously (avoids blocking event loop).
        # Cached per resolved project_root; cleared when agent cache is invalidated.
        if _eff_project_root and _eff_project_root not in self._project_ctx_text_cache:
            import asyncio as _asyncio
            self._project_ctx_text_cache[_eff_project_root] = await _asyncio.to_thread(
                _build_project_context_text, _eff_project_root
            )

        agent = self._get_or_build_agent(preset_id, model_id, llm_params=llm_params)

        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": self.recursion_limit}
        message = _convert_text_file_blocks(message)
        history = [_convert_history_item(item) for item in (history or [])]
        input_messages = list(history)
        input_messages.append({"role": "user", "content": message})
        stream_kwargs: dict[str, Any] = {"config": config, "version": "v2"}
        if self._should_use_memory_context(preset_id):
            from lc_agent.core.memory import AgentRuntimeContext, normalize_memory_user_id

            stream_kwargs["context"] = AgentRuntimeContext(user_id=normalize_memory_user_id(user_id))
        async for event in agent.astream_events(
            {"messages": input_messages},
            **stream_kwargs,
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
