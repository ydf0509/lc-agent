# tests/test_app.py
import pytest

from lc_agent.app import LcAgentApp


class TestLcAgentApp:
    def test_creates_with_config(self, sample_config):
        app = LcAgentApp(sample_config)
        assert app.config == sample_config

    def test_has_fastapi_app(self, sample_config):
        app = LcAgentApp(sample_config)
        assert app.fastapi_app is not None

    def test_has_engine(self, sample_config):
        app = LcAgentApp(sample_config)
        assert app.engine is not None

    def test_default_host_and_port(self, sample_config):
        app = LcAgentApp(sample_config)
        assert app.host == "127.0.0.1"
        assert app.port == 8000

    def test_custom_host_and_port(self, sample_config):
        app = LcAgentApp(sample_config, host="0.0.0.0", port=9000)
        assert app.host == "0.0.0.0"
        assert app.port == 9000

    def test_resolves_desktop_title_from_ui_app_name(self, sample_config):
        config = {
            **sample_config,
            "ui": {"app_name": "心有灵犀"},
        }
        app = LcAgentApp(config)
        assert app._resolve_desktop_title(None) == "心有灵犀"

    def test_explicit_desktop_title_overrides_ui_app_name(self, sample_config):
        config = {
            **sample_config,
            "ui": {"app_name": "心有灵犀"},
        }
        app = LcAgentApp(config)
        assert app._resolve_desktop_title("自定义标题") == "自定义标题"
