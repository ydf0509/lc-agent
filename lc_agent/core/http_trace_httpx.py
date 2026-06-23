from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx
import openai

from lc_agent.core.http_trace import HttpTraceCollector


class _TracingAsyncByteStream(httpx.AsyncByteStream):
    def __init__(
        self,
        stream: httpx.AsyncByteStream,
        on_success: Callable[[bytes, int], None],
        on_error: Callable[[Exception], None],
    ):
        self._stream = stream
        self._on_success = on_success
        self._on_error = on_error
        self._chunks: list[bytes] = []
        self._finished = False
        self._started = time.time()

    async def __aiter__(self):
        try:
            async for chunk in self._stream:
                self._chunks.append(chunk)
                yield chunk
            self._finish_success()
        except Exception as exc:
            self._finish_error(exc)
            raise

    async def aclose(self) -> None:
        try:
            await self._stream.aclose()
        except Exception as exc:
            self._finish_error(exc)
            raise
        else:
            self._finish_success()

    def _finish_success(self) -> None:
        if self._finished:
            return
        self._finished = True
        duration_ms = int((time.time() - self._started) * 1000)
        self._on_success(b"".join(self._chunks), duration_ms)

    def _finish_error(self, exc: Exception) -> None:
        if self._finished:
            return
        self._finished = True
        self._on_error(exc)


class TracingAsyncClient(openai.DefaultAsyncHttpxClient):
    def __init__(
        self,
        *,
        collector_getter: Callable[[], HttpTraceCollector | None],
        provider: str | None,
        model: str | None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._collector_getter = collector_getter
        self.provider = provider
        self.model = model

    async def send(self, request: httpx.Request, *args: Any, **kwargs: Any) -> httpx.Response:
        collector = self._collector_getter()
        started = time.time()
        trace_id: str | None = None

        if collector is not None:
            trace_id = collector.start_request(
                method=request.method,
                url=str(request.url),
                headers=dict(request.headers),
                body=request.content,
            )

        try:
            response = await super().send(request, *args, **kwargs)
        except Exception as exc:
            if collector is not None and trace_id is not None:
                collector.fail_response(trace_id, exc.__class__.__name__)
            raise

        if collector is None or trace_id is None:
            return response

        if response.is_stream_consumed:
            body = getattr(response, "content", b"")
            collector.finish_response(
                trace_id,
                status=response.status_code,
                headers=dict(response.headers),
                body=body,
                duration_ms=int((time.time() - started) * 1000),
            )
            return response

        def _finish_success(body: bytes, duration_ms: int) -> None:
            collector.finish_response(
                trace_id,
                status=response.status_code,
                headers=dict(response.headers),
                body=body,
                duration_ms=duration_ms,
            )

        def _finish_error(exc: Exception) -> None:
            collector.fail_response(trace_id, exc.__class__.__name__)

        response.stream = _TracingAsyncByteStream(response.stream, _finish_success, _finish_error)
        return response
