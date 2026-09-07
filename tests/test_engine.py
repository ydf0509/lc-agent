# tests/test_engine.py
import pytest

from lc_agent.core.models import AgentPreset, ModelInfo, SubAgentLink


class TestAgentPreset:
    def test_creates_with_defaults(self):
        preset = AgentPreset(
            id="default",
            name="Default Agent",
            system_prompt="Hello",
            default_model="test-model",
        )
        assert preset.allowed_tool_groups is None
        assert preset.allowed_mcp_servers is None
        assert preset.allowed_skills is None

    def test_three_value_semantics_none_means_all(self):
        preset = AgentPreset(
            id="all", name="All", system_prompt="", default_model="m"
        )
        assert preset.allowed_tool_groups is None

    def test_three_value_semantics_empty_means_none(self):
        preset = AgentPreset(
            id="none", name="None", system_prompt="", default_model="m",
            allowed_tool_groups=[],
        )
        assert preset.allowed_tool_groups == []

    def test_three_value_semantics_list_means_only_those(self):
        preset = AgentPreset(
            id="some", name="Some", system_prompt="", default_model="m",
            allowed_tool_groups=["math", "text"],
        )
        assert preset.allowed_tool_groups == ["math", "text"]

    def test_accepts_subagent_links(self):
        preset = AgentPreset(
            id="p1",
            name="主智能体",
            system_prompt="x",
            default_model="m1",
            subagents=[
                SubAgentLink(
                    agent_id="child-1",
                    delegation_description="当你需要查询 funboost 知识时调用它",
                )
            ],
        )
        assert preset.subagents is not None
        assert preset.subagents[0].agent_id == "child-1"
        assert preset.subagents[0].delegation_description == "当你需要查询 funboost 知识时调用它"

    def test_subagents_defaults_to_none(self):
        preset = AgentPreset(id="p1", name="n", system_prompt="x", default_model="m1")
        assert preset.subagents is None


class TestModelInfo:
    def test_creates_model_info(self):
        info = ModelInfo(
            id="deepseek-chat",
            provider="default",
            base_url="https://api.deepseek.com/v1",
            context_limit=64000,
        )
        assert info.id == "deepseek-chat"
        assert info.context_limit == 64000


class TestAgentEngine:
    def test_creates_with_config(self, sample_config):
        from lc_agent.core.engine import AgentEngine
        engine = AgentEngine(sample_config)
        assert engine.config == sample_config

    def test_build_agent_configures_todo_middleware_final_answer_guard(self, sample_config, monkeypatch):
        from lc_agent.core.engine import AgentEngine

        from langchain.agents.middleware import TodoListMiddleware

        captured = {}
        engine = AgentEngine(sample_config)

        monkeypatch.setattr(engine, "_create_llm", lambda model_info, model_id, llm_params=None: object())
        monkeypatch.setattr(engine, "_build_summarization_middleware", lambda preset: [])

        def fake_create_agent(**kwargs):
            captured.update(kwargs)
            return object()

        monkeypatch.setattr("lc_agent.core.engine.create_agent", fake_create_agent)

        engine.build_agent()

        # Look it up by type: PatchToolCallsMiddleware is registered first, so
        # indexing by position breaks every time the middleware order changes.
        todo_middleware = next(
            (mw for mw in captured["middleware"] if isinstance(mw, TodoListMiddleware)),
            None,
        )
        assert todo_middleware is not None, "TodoListMiddleware was not registered"
        assert "After you start writing the substantive final answer" in todo_middleware.system_prompt
        assert "do not call `write_todos` again" in todo_middleware.system_prompt
        assert "Do not create todo items whose only purpose" in todo_middleware.tool_description
        assert "If the only remaining todo is about producing the final answer" in todo_middleware.tool_description

    def test_build_agent_passes_memory_store_and_context_schema(self, sample_config, monkeypatch):
        from lc_agent.core.engine import AgentEngine
        from lc_agent.core.memory import AgentRuntimeContext

        captured = {}
        store = object()
        engine = AgentEngine(sample_config, store=store)

        class FakeAgent:
            pass

        def fake_create_agent(**kwargs):
            captured.update(kwargs)
            return FakeAgent()

        monkeypatch.setattr("lc_agent.core.engine.create_agent", fake_create_agent)

        engine.build_agent(cache_key="memory-test")

        assert captured["store"] is store
        assert captured["context_schema"] is AgentRuntimeContext

    def test_build_agent_adds_memory_tools_when_store_enabled(self, sample_config, monkeypatch):
        from lc_agent.core.engine import AgentEngine
        from lc_agent.middlewares import SystemPromptMiddleware
        from lc_agent.core.memory import MEMORY_SYSTEM_PROMPT

        captured = {}
        config = {
            **sample_config,
            "memory": {
                "enabled": True,
                "type": "sqlite",
                "path": "./lc_agent_memory.db",
                "save_policy": "explicit",
                "retrieval_policy": "manual",
                "semantic_search": {"enabled": False},
            },
        }
        engine = AgentEngine(config, store=object())

        monkeypatch.setattr(engine, "_create_llm", lambda model_info, model_id, llm_params=None: object())
        monkeypatch.setattr(engine, "_build_summarization_middleware", lambda preset: [])

        def fake_create_agent(**kwargs):
            captured.update(kwargs)
            return object()

        monkeypatch.setattr("lc_agent.core.engine.create_agent", fake_create_agent)

        engine.build_agent()

        expected_tools = {
            "memory__insert_memory",
            "memory__update_memory",
            "memory__get_memory",
            "memory__search_memories",
            "memory__list_memories",
            "memory__delete_memory",
        }
        assert expected_tools.issubset({tool.name for tool in captured["tools"]})

        # Memory prompt is now injected as a separate middleware content block,
        # not concatenated into system_prompt.
        assert MEMORY_SYSTEM_PROMPT not in captured["system_prompt"]
        middleware_list = captured.get("middleware", [])
        memory_mw = next(
            (m for m in middleware_list if getattr(m, "name", None) == "MemoryPromptMiddleware"),
            None,
        )
        assert memory_mw is not None, "MemoryPromptMiddleware not found in middleware list"
        assert isinstance(memory_mw, SystemPromptMiddleware)
        assert memory_mw._text == MEMORY_SYSTEM_PROMPT

        # Middleware order: memory before TodoListMiddleware
        names = [getattr(m, "name", type(m).__name__) for m in middleware_list]
        assert names.index("MemoryPromptMiddleware") < names.index("TodoListMiddleware")

    def test_parses_models_from_config(self, sample_config):
        from lc_agent.core.engine import AgentEngine
        engine = AgentEngine(sample_config)
        models = engine.get_models()
        assert len(models) == 1
        assert models[0].id == "test-model"
        assert models[0].context_limit == 8000

    def test_get_default_preset(self, sample_config):
        from lc_agent.core.engine import AgentEngine
        engine = AgentEngine(sample_config)
        preset = engine.get_default_preset()
        assert preset.id == "chat"
        assert preset.system_prompt == "You are a helpful assistant. Respond in the user's language."
        assert preset.default_model == "test-model"

    def test_model_override_uses_separate_agent_cache_key(self, sample_config, monkeypatch):
        from lc_agent.core.engine import AgentEngine

        config = {
            **sample_config,
            "provider": {
                "default": {
                    "api_key": "test-key",
                    "base_url": "https://api.example.com/v1",
                    "models": [
                        {"id": "test-model", "context_limit": 8000},
                        {"id": "ark-deepseek-v4-flash", "context_limit": 200000},
                    ],
                }
            },
        }
        engine = AgentEngine(config)
        built: list[tuple[str, str | None]] = []

        def fake_build_agent(preset, cache_key=None, llm_params=None, **_kwargs):
            built.append((preset.default_model, cache_key))
            agent = object()
            engine._agents[cache_key or preset.id] = agent
            return agent

        monkeypatch.setattr(engine, "build_agent", fake_build_agent)

        agent_a = engine._get_or_build_agent("chat", model_id="ark-deepseek-v4-flash")
        agent_b = engine._get_or_build_agent("chat", model_id="ark-deepseek-v4-flash")
        agent_c = engine._get_or_build_agent("chat")

        assert agent_a is agent_b
        assert agent_a is not agent_c
        assert built == [
            ("ark-deepseek-v4-flash", "chat::model::ark-deepseek-v4-flash"),
            ("test-model", "chat"),
        ]
        assert engine.get_default_preset().default_model == "test-model"

    def test_invalidate_agent_cache_removes_model_variants(self, sample_config):
        from lc_agent.core.engine import AgentEngine

        engine = AgentEngine(sample_config)
        engine._agents["agent-a"] = object()
        engine._agents["agent-a::model::m1"] = object()
        engine._agents["agent-a::model::m2"] = object()
        engine._agents["agent-b"] = object()
        engine._agent_mcp_gen["agent-a"] = 0
        engine._agent_mcp_gen["agent-a::model::m1"] = 0
        engine._agent_mcp_gen["agent-b"] = 0

        engine.invalidate_agent_cache("agent-a")

        assert "agent-a" not in engine._agents
        assert "agent-a::model::m1" not in engine._agents
        assert "agent-a::model::m2" not in engine._agents
        assert "agent-b" in engine._agents
        assert "agent-a" not in engine._agent_mcp_gen
        assert "agent-a::model::m1" not in engine._agent_mcp_gen
        assert "agent-b" in engine._agent_mcp_gen

    @pytest.mark.asyncio
    async def test_chat_stream_accepts_replay_history(self, sample_config, monkeypatch):
        from lc_agent.core.engine import AgentEngine

        engine = AgentEngine(sample_config, store=object())
        captured = {}

        class FakeAgent:
            async def astream_events(self, inputs, *, config, context, version):
                captured["inputs"] = inputs
                captured["config"] = config
                captured["context"] = context
                captured["version"] = version
                if False:
                    yield {}

        monkeypatch.setattr(
            engine,
            "_get_or_build_agent",
            lambda preset_id, model_id="", llm_params=None: FakeAgent(),
        )

        events = []
        async for event in engine.chat_stream(
            [{"type": "text", "text": "新问题"}],
            "thread-1",
            history=[{"role": "user", "content": "第一问"}],
        ):
            events.append(event)

        assert captured["inputs"] == {
            "messages": [
                {"role": "user", "content": "第一问"},
                {"role": "user", "content": [{"type": "text", "text": "新问题"}]},
            ]
        }
        assert captured["config"] == {
            "configurable": {"thread_id": "thread-1"},
            "recursion_limit": 100,
        }
        assert captured["context"].user_id == "anonymous"
        assert captured["version"] == "v2"
        assert events == []

    @pytest.mark.asyncio
    async def test_chat_stream_passes_user_context(self, sample_config, monkeypatch):
        from lc_agent.core.engine import AgentEngine
        from lc_agent.core.memory import AgentRuntimeContext

        captured = {}
        engine = AgentEngine(sample_config, store=object())

        class FakeAgent:
            async def astream_events(self, payload, *, config, context, version):
                captured["payload"] = payload
                captured["config"] = config
                captured["context"] = context
                captured["version"] = version
                if False:
                    yield {}

        monkeypatch.setattr(engine, "_get_or_build_agent", lambda *args, **kwargs: FakeAgent())

        events = [
            event async for event in engine.chat_stream(
                [{"type": "text", "text": "hello"}],
                "thread-1",
                user_id="user-123",
            )
        ]

        assert events == []
        assert captured["context"] == AgentRuntimeContext(user_id="user-123")
        assert captured["config"]["configurable"]["thread_id"] == "thread-1"
        assert captured["version"] == "v2"

    @pytest.mark.asyncio
    async def test_chat_stream_omits_memory_context_without_store(self, sample_config, monkeypatch):
        from lc_agent.core.engine import AgentEngine

        captured = {}
        engine = AgentEngine(sample_config)

        class FakeAgent:
            async def astream_events(self, payload, **kwargs):
                captured["payload"] = payload
                captured["kwargs"] = kwargs
                if False:
                    yield {}

        monkeypatch.setattr(engine, "_get_or_build_agent", lambda *args, **kwargs: FakeAgent())

        events = [
            event async for event in engine.chat_stream(
                [{"type": "text", "text": "hello"}],
                "thread-1",
                user_id="user-123",
            )
        ]

        assert events == []
        assert "context" not in captured["kwargs"]
        assert captured["kwargs"]["config"]["configurable"]["thread_id"] == "thread-1"
        assert captured["kwargs"]["version"] == "v2"

    @pytest.mark.asyncio
    async def test_reset_thread_uses_checkpointer_delete(self, sample_config):
        from lc_agent.core.engine import AgentEngine

        class FakeCheckpointer:
            def __init__(self):
                self.calls = []

            async def adelete_thread(self, thread_id):
                self.calls.append(thread_id)

        checkpointer = FakeCheckpointer()
        engine = AgentEngine(sample_config, checkpointer=checkpointer)

        await engine.reset_thread("thread-reset")

        assert checkpointer.calls == ["thread-reset"]


class TestCreateLlm:
    """Test _create_llm method with ChatOpenAIReasoning and init_chat_model."""

    def test_base_url_uses_chat_openai_reasoning(self, sample_config):
        """All models with base_url should use ChatOpenAIReasoning for reasoning extraction."""
        from lc_agent.core.engine import AgentEngine
        from lc_agent.core.models import ModelInfo
        from lc_agent.core.chat_model import ChatOpenAIReasoning

        engine = AgentEngine(sample_config)
        for model_id in ["ds-deepseek-v4-flash", "ark-deepseek-v4-flash", "ark-glm-5.1", "gpt-4o"]:
            model_info = ModelInfo(
                id=model_id,
                provider="litellm",
                base_url="http://localhost:4000/v1",
                api_key="sk-no-key",
            )
            llm = engine._create_llm(model_info, model_id)
            assert isinstance(llm, ChatOpenAIReasoning), f"{model_id} should use ChatOpenAIReasoning"
            assert llm.model_name == model_id

    def test_chat_openai_reasoning_is_subclass_of_chatopenai(self, sample_config):
        """ChatOpenAIReasoning should be a drop-in replacement for ChatOpenAI."""
        from lc_agent.core.chat_model import ChatOpenAIReasoning
        from langchain_openai import ChatOpenAI
        assert issubclass(ChatOpenAIReasoning, ChatOpenAI)

    def test_creates_llm_without_base_url_uses_init_chat_model(self, sample_config):
        """When no base_url, should use init_chat_model for provider routing."""
        from lc_agent.core.engine import AgentEngine
        from lc_agent.core.models import ModelInfo
        from langchain_openai import ChatOpenAI

        engine = AgentEngine(sample_config)
        model_info = ModelInfo(
            id="deepseek-chat",
            provider="deepseek",
            base_url="",
            api_key="test-key",
        )
        llm = engine._create_llm(model_info, "deepseek-chat")
        assert llm is not None
        assert hasattr(llm, 'ainvoke')
        # Should NOT be ChatOpenAI when using standard provider routing
        from langchain_deepseek import ChatDeepSeek
        assert isinstance(llm, ChatDeepSeek)

    def test_creates_llm_fallback_when_no_model_info(self, sample_config):
        """When model_info is None, should use init_chat_model with bare model_id."""
        from lc_agent.core.engine import AgentEngine

        engine = AgentEngine(sample_config)
        llm = engine._create_llm(None, "gpt-4o")
        assert llm is not None
        assert hasattr(llm, 'ainvoke')

    def test_creates_llm_passes_temperature(self, sample_config):
        """LLM should be configured with temperature=0.7."""
        from lc_agent.core.engine import AgentEngine
        from lc_agent.core.models import ModelInfo

        engine = AgentEngine(sample_config)
        model_info = ModelInfo(
            id="gpt-4o",
            provider="openai",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
        )
        llm = engine._create_llm(model_info, "gpt-4o")
        assert llm.temperature == 0.7

    def test_creates_llm_enables_stream_usage(self, sample_config):
        """LLM should have stream_usage=True for token tracking."""
        from lc_agent.core.engine import AgentEngine
        from lc_agent.core.models import ModelInfo

        engine = AgentEngine(sample_config)
        model_info = ModelInfo(
            id="gpt-4o",
            provider="openai",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
        )
        llm = engine._create_llm(model_info, "gpt-4o")
        assert llm.stream_usage is True
