import pytest


@pytest.fixture
def sample_config() -> dict:
    """Minimal valid configuration for testing."""
    return {
        "provider": {
            "default": {
                "api_key": "test-key",
                "base_url": "https://api.example.com/v1",
                "models": [{"id": "test-model", "context_limit": 8000}],
            }
        },
        "agent": {
            "system_prompt": "You are a helpful assistant.",
            "default_model": "test-model",
            "streaming": True,
        },
        "mcp": {},
        "session": {"db_path": ":memory:"},
    }
