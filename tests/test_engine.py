# tests/test_engine.py
import pytest

from lc_agent.core.models import AgentPreset, ModelInfo


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
        assert preset.dangerous_tools == []

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
        assert preset.id == "__chat__"
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

        def fake_build_agent(preset, cache_key=None):
            built.append((preset.default_model, cache_key))
            agent = object()
            engine._agents[cache_key or preset.id] = agent
            return agent

        monkeypatch.setattr(engine, "build_agent", fake_build_agent)

        agent_a = engine._get_or_build_agent("__chat__", model_id="ark-deepseek-v4-flash")
        agent_b = engine._get_or_build_agent("__chat__", model_id="ark-deepseek-v4-flash")
        agent_c = engine._get_or_build_agent("__chat__")

        assert agent_a is agent_b
        assert agent_a is not agent_c
        assert built == [
            ("ark-deepseek-v4-flash", "__chat__::model::ark-deepseek-v4-flash"),
            ("test-model", "__chat__"),
        ]
        assert engine.get_default_preset().default_model == "test-model"


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
