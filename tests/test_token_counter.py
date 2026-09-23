# tests/test_token_counter.py
"""tiktoken 计数器：口径、边界、中间件接线。"""

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.messages.utils import count_tokens_approximately

from lc_agent.middlewares.summarization_events import NotifyingSummarizationMiddleware
from lc_agent.utils.token_counter import count_tokens_tiktoken

CHINESE_TEXT = "这是一段中文测试文本，用来对比两种计数口径的差异。" * 20


def _sample_messages():
    return [
        HumanMessage(content=CHINESE_TEXT),
        AIMessage(
            content="",
            tool_calls=[{"name": "nbrag_retrieve", "args": {"q": "中文查询"}, "id": "c1"}],
        ),
        ToolMessage(content='{"result": "' + "中文结果" * 200 + '"}', tool_call_id="c1"),
    ]


def test_empty_messages_is_zero():
    assert count_tokens_tiktoken([]) == 0


def test_chinese_counted_higher_than_approximate():
    """近似计数器按 字符数/4 估，中文会被严重低估，tiktoken 应明显更大。"""
    messages = _sample_messages()
    approx = count_tokens_approximately(messages)
    counted = count_tokens_tiktoken(messages)
    assert counted > approx * 1.5


def test_prefix_counts_are_monotonic():
    """二分查找依赖前缀计数单调不减。"""
    messages = _sample_messages()
    counts = [count_tokens_tiktoken(messages[:i]) for i in range(len(messages) + 1)]
    assert counts == sorted(counts)


def test_special_token_strings_do_not_raise():
    """工具结果里出现 <|endoftext|> 这类串不应抛异常。"""
    messages = [HumanMessage(content="含特殊串 <|endoftext|> 和 <|im_start|> 的文本")]
    assert count_tokens_tiktoken(messages) > 0


def test_image_block_counted_as_fixed_cost():
    """图片块按固定值计，不能把 base64 编码算进去。"""
    messages = [
        HumanMessage(
            content=[
                {"type": "text", "text": "看这张图"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + "A" * 50000}},
            ]
        )
    ]
    assert count_tokens_tiktoken(messages) < 100


def test_passing_token_counter_unifies_both_paths():
    """传了自定义计数器后，触发判断与裁剪判断（_partial_token_counter）同源。"""
    model = GenericFakeChatModel(messages=iter(["ok"]))
    model.profile = {"max_input_tokens": 100000}

    mw = NotifyingSummarizationMiddleware(
        model=model,
        trigger=("fraction", 0.85),
        keep=("fraction", 0.20),
        token_counter=count_tokens_tiktoken,
    )
    assert mw.token_counter is count_tokens_tiktoken
    assert mw._partial_token_counter is count_tokens_tiktoken

    # 不传时是默认近似计数器，两个口径不同源（对照组）
    default_mw = NotifyingSummarizationMiddleware(
        model=model,
        trigger=("fraction", 0.85),
        keep=("fraction", 0.20),
    )
    assert default_mw.token_counter is not default_mw._partial_token_counter
