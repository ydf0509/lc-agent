"""按 tiktoken 真实编码的消息 token 计数器（供压缩中间件使用）。

langchain 的 `SummarizationMiddleware` 默认用 `count_tokens_approximately`，
那是 `字符数 / 4` 的启发式估算——对英文够用，对中文和 JSON 化的工具结果会
低估 1.75 倍左右，导致 keep 预算量不准：判定"只留了 20k"，实际留下 30k+。

这里提供一个同样签名的 `token_counter`，按 cl100k_base 真实编码。传给中间件后，
触发判断和裁剪判断（`_partial_token_counter`）都走它，两个口径保持一致。
"""

import logging
from collections.abc import Iterable
from functools import lru_cache
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.messages.utils import convert_to_messages

logger = logging.getLogger(__name__)

# 所有模型共用一个编码器：这里不是要对齐某个模型的私有分词器，
# 只是要把"字符数 / 4"换成真实的 BPE 分词，量级上准得多。
DEFAULT_ENCODING = "cl100k_base"

# 图片按固定值计，和 langchain 的近似计数器保持一致，避免把 base64 编进去。
TOKENS_PER_IMAGE = 85
EXTRA_TOKENS_PER_MESSAGE = 3


@lru_cache(maxsize=4)
def _get_encoder(encoding_name: str):
    import tiktoken

    return tiktoken.get_encoding(encoding_name)


def _collect_message_text(message, parts: list[str]) -> int:
    """把一条消息里该计入的文本追加到 parts，返回其中的图片块数量。

    抽取口径对齐 langchain_core 的 `count_tokens_approximately`：
    消息内容、AI 消息的 tool_calls、Tool 消息的 tool_call_id、role、name。
    """
    content = message.content
    images = 0

    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                block_type = block.get("type", "")
                if block_type in {"image", "image_url"}:
                    images += 1
                elif block_type == "text":
                    parts.append(block.get("text", ""))
                else:
                    parts.append(repr(block))
            else:
                parts.append(repr(block))
    else:
        parts.append(repr(content))

    # Anthropic 格式的 tool_calls 已并在 content 里，别重复计
    if isinstance(message, AIMessage) and not isinstance(content, list) and message.tool_calls:
        parts.append(repr(message.tool_calls))
    if isinstance(message, ToolMessage):
        parts.append(message.tool_call_id)

    parts.append(message.type)
    if message.name:
        parts.append(message.name)

    return images


def count_tokens_tiktoken(messages: Iterable[Any], *, encoding_name: str = DEFAULT_ENCODING) -> int:
    """统计消息列表的 token 数（tiktoken 真实编码口径）。"""
    converted = convert_to_messages(messages)
    if not converted:
        return 0

    parts: list[str] = []
    image_tokens = 0
    for message in converted:
        image_tokens += TOKENS_PER_IMAGE * _collect_message_text(message, parts)

    encoder = _get_encoder(encoding_name)
    # disallowed_special=() 关掉特殊串检查：工具结果里出现 <|endoftext|> 之类不该炸
    text_tokens = len(encoder.encode("\n".join(parts), disallowed_special=()))

    return text_tokens + image_tokens + EXTRA_TOKENS_PER_MESSAGE * len(converted)
