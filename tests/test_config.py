# tests/test_config.py
import os
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from lc_agent.config.loader import load_config_from_file, substitute_env_vars
from lc_agent.config.schema import AppConfig


class TestSubstituteEnvVars:
    def test_replaces_env_var(self, monkeypatch):
        monkeypatch.setenv("TEST_API_KEY", "sk-12345")
        result = substitute_env_vars({"key": "{env:TEST_API_KEY}"})
        assert result == {"key": "sk-12345"}

    def test_leaves_non_env_strings_unchanged(self):
        result = substitute_env_vars({"key": "plain-value"})
        assert result == {"key": "plain-value"}

    def test_handles_nested_dicts(self, monkeypatch):
        monkeypatch.setenv("NESTED_VAL", "secret")
        data = {"outer": {"inner": "{env:NESTED_VAL}"}}
        result = substitute_env_vars(data)
        assert result == {"outer": {"inner": "secret"}}

    def test_handles_lists(self, monkeypatch):
        monkeypatch.setenv("LIST_VAL", "item")
        data = {"items": ["{env:LIST_VAL}", "static"]}
        result = substitute_env_vars(data)
        assert result == {"items": ["item", "static"]}

    def test_missing_env_var_raises(self):
        with pytest.raises(ValueError, match="Environment variable 'NONEXISTENT' not found"):
            substitute_env_vars({"key": "{env:NONEXISTENT}"})


class TestLoadConfigFromFile:
    def test_loads_jsonc_file(self, tmp_path):
        config_file = tmp_path / "config.jsonc"
        config_file.write_text(
            """{
            // This is a comment
            "agent": {
                "system_prompt": "Hello",
                "default_model": "test-model",
                "streaming": true
            },
            "provider": {
                "default": {
                    "api_key": "sk-test",
                    "base_url": "https://api.example.com/v1",
                    "models": [{"id": "test-model", "context_limit": 8000}]
                }
            },
            "mcp": {},
            "session": {"db_path": ":memory:"}
        }"""
        )
        config = load_config_from_file(str(config_file))
        assert config["agent"]["system_prompt"] == "Hello"

    def test_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config_from_file("/nonexistent/path/config.jsonc")


class TestAppConfig:
    def test_validates_minimal_config(self):
        config = AppConfig(
            provider={"default": {"api_key": "sk-test", "base_url": "https://api.example.com/v1", "models": [{"id": "m1", "context_limit": 4000}]}},
            agent={"system_prompt": "Hi", "default_model": "m1", "streaming": True},
        )
        assert config.agent["default_model"] == "m1"

    def test_rejects_missing_agent_section(self):
        with pytest.raises(ValidationError):
            AppConfig(agent="not a dict")
