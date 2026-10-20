"""ChatOpenAIReasoning 固定走 chat completions（use_responses_api 钉死为 False）。

背景：langchain-openai 在 use_responses_api=None 时会按启发式自动路由到
/v1/responses——模型名含 "codex"、gpt-5-*-pro 前缀、payload 带内置工具、
include/truncation/reasoning 参数任一命中即触发。而 ChatOpenAIReasoning 的流
解析完全基于 chat completions 格式（choices[0].delta.reasoning_content），
Responses 流没有 choices[N].delta 结构，一旦被路由过去，reasoning 提取与
usage 去重会静默失效。因此该类必须把 use_responses_api 强制钉死为 False。
"""

from lc_agent.core.chat_model import ChatOpenAIReasoning


def _make(**kwargs) -> ChatOpenAIReasoning:
    params = dict(
        model="gpt-4o", api_key="not-set", base_url="http://localhost:1234/v1",
    )
    params.update(kwargs)
    return ChatOpenAIReasoning(**params)


def test_default_pinned_to_false():
    assert _make().use_responses_api is False


def test_explicit_true_is_forced_back_to_false():
    """config llm_params 透传 use_responses_api=True 也必须被压回。"""
    assert _make(use_responses_api=True).use_responses_api is False


def test_routing_never_flips_to_responses():
    """模型名含 codex + payload 带内置工具，也不允许路由到 Responses。"""
    model = _make(model="gpt-5.3-codex")
    payload = {"tools": [{"type": "web_search"}]}
    assert model._use_responses_api(payload) is False


def test_reasoning_effort_does_not_flip_routing():
    """engine 会传 reasoning_effort（o 系列参数），不应触发 Responses 路由。"""
    model = _make(reasoning_effort="medium")
    assert model._use_responses_api({}) is False
