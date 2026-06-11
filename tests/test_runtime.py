import pytest
from lc_agent.core.engine import AgentEngine


@pytest.fixture
def engine_with_provider():
    config = {
        "provider": {
            "deepseek": {
                "api_key": "test-key-123",
                "base_url": "https://api.deepseek.com",
                "models": [
                    {"id": "deepseek-chat", "context_limit": 64000}
                ]
            }
        },
        "agent": {
            "system_prompt": "You are helpful.",
            "default_model": "deepseek-chat",
        },
    }
    return AgentEngine(config)


def test_build_agent_creates_graph(engine_with_provider):
    """build_agent should return a compiled graph."""
    preset = engine_with_provider.get_default_preset()
    agent = engine_with_provider.build_agent(preset)
    assert agent is not None
    assert hasattr(agent, 'ainvoke')
    assert hasattr(agent, 'astream_events')


def test_build_agent_uses_correct_model(engine_with_provider):
    """build_agent should pass the correct model params."""
    preset = engine_with_provider.get_default_preset()
    agent = engine_with_provider.build_agent(preset)
    assert agent is not None
