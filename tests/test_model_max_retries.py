# tests/test_model_max_retries.py
"""agent.model_retry.max_retries 配置 → SDK 层重试次数（_create_llm 注入 ChatOpenAI）。"""
from lc_agent.config import DEFAULT_MODEL_MAX_RETRIES
from lc_agent.core.engine import AgentEngine
from lc_agent.core.models import ModelInfo

MODEL_INFO = ModelInfo(
    model_id="test-model",
    raw_model_id="test-model",
    provider="default",
    base_url="https://api.example.com/v1",
    context_limit=64000,
)


class TestSdkMaxRetries:
    def _engine(self, sample_config: dict) -> AgentEngine:
        return AgentEngine(sample_config)

    def test_default_when_config_missing(self, sample_config):
        engine = self._engine(sample_config)
        llm = engine._create_llm(MODEL_INFO, "test-model")
        assert llm.max_retries == DEFAULT_MODEL_MAX_RETRIES

    def test_config_override(self, sample_config):
        sample_config["agent"]["model_retry"] = {"max_retries": 4}
        engine = self._engine(sample_config)
        llm = engine._create_llm(MODEL_INFO, "test-model")
        assert llm.max_retries == 4

    def test_zero_allowed(self, sample_config):
        sample_config["agent"]["model_retry"] = {"max_retries": 0}
        engine = self._engine(sample_config)
        llm = engine._create_llm(MODEL_INFO, "test-model")
        assert llm.max_retries == 0

    def test_clamp_upper(self, sample_config):
        sample_config["agent"]["model_retry"] = {"max_retries": 99}
        engine = self._engine(sample_config)
        llm = engine._create_llm(MODEL_INFO, "test-model")
        assert llm.max_retries == 10

    def test_invalid_value_falls_back_to_default(self, sample_config):
        sample_config["agent"]["model_retry"] = {"max_retries": "abc"}
        engine = self._engine(sample_config)
        llm = engine._create_llm(MODEL_INFO, "test-model")
        assert llm.max_retries == DEFAULT_MODEL_MAX_RETRIES

    def test_overrides_llm_params_passthrough(self, sample_config):
        """llm_params 里混进同名参数时，配置值优先（显式赋值在 extra_params 之后）。"""
        sample_config["agent"]["model_retry"] = {"max_retries": 5}
        engine = self._engine(sample_config)
        llm = engine._create_llm(MODEL_INFO, "test-model", llm_params={"max_retries": 1})
        assert llm.max_retries == 5
