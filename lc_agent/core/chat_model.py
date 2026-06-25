"""ChatOpenAI subclass that extracts reasoning_content from streaming deltas.

ChatOpenAI only supports official OpenAI API fields. Many providers (DeepSeek,
GLM, etc.) return a non-standard `reasoning_content` field in the streaming
delta for chain-of-thought / thinking content. This subclass captures it into
`additional_kwargs["reasoning_content"]` so downstream handlers can display it.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk
from langchain_openai import ChatOpenAI


class ChatOpenAIReasoning(ChatOpenAI):
    """ChatOpenAI with reasoning_content extraction from streaming deltas.

    Drop-in replacement for ChatOpenAI. Works with any provider that returns
    `reasoning_content` or `reasoning` in the streaming delta dict (e.g.
    DeepSeek, GLM with thinking mode, OpenRouter).

    Also fixes the max_tokens → max_completion_tokens rename that ChatOpenAI
    applies for the OpenAI API — non-OpenAI providers (DeepSeek, GLM, etc.)
    still expect `max_tokens`.
    """

    @property
    def _default_params(self) -> dict[str, Any]:
        params = super()._default_params
        if "max_completion_tokens" in params:
            params["max_tokens"] = params["max_completion_tokens"]
        return params

    def _get_request_payload(
        self,
        input_: Any,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict:
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        if "max_completion_tokens" in payload:
            payload["max_tokens"] = payload["max_completion_tokens"]
        return payload

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ) -> ChatGenerationChunk | None:
        generation_chunk = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info,
        )
        if generation_chunk is None:
            return None

        choices = chunk.get("choices") or chunk.get("chunk", {}).get("choices") or []
        if not choices:
            return generation_chunk

        delta = choices[0].get("delta") or {}
        if isinstance(generation_chunk.message, AIMessageChunk):
            reasoning = delta.get("reasoning_content")
            if reasoning is None:
                reasoning = delta.get("reasoning")
            if reasoning is not None:
                generation_chunk.message.additional_kwargs["reasoning_content"] = reasoning

        return generation_chunk
