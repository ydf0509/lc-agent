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
        assert preset.id == "__default__"
        assert preset.system_prompt == "You are a helpful assistant."
        assert preset.default_model == "test-model"
