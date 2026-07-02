from __future__ import annotations

import json
import time
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any, TypedDict


class HttpMessagePart(TypedDict):
    method: str | None
    url: str | None
    headers: dict[str, str]
    body: str
    bodyFormat: str


class HttpResponsePart(TypedDict):
    status: int | None
    headers: dict[str, str]
    body: str
    bodyFormat: str
    ok: bool | None


class HttpTrace(TypedDict):
    id: str
    sequence: int
    kind: str
    provider: str | None
    model: str | None
    startedAt: int
    durationMs: int | None
    request: HttpMessagePart
    response: HttpResponsePart
    error: str | None


_SENSITIVE_HEADERS = {
    "authorization",
    "api-key",
    "x-api-key",
    "cookie",
    "set-cookie",
}
_SENSITIVE_BODY_KEYS = {
    "api_key",
    "token",
    "password",
    "secret",
    "access_token",
    "refresh_token",
}
_CURRENT_COLLECTOR: ContextVar[HttpTraceCollector | None] = ContextVar(
    "http_trace_collector",
    default=None,
)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _mask_header(name: str, value: Any) -> str:
    text = "" if value is None else str(value)
    if name.lower() in _SENSITIVE_HEADERS:
        if text.lower().startswith("bearer "):
            return "Bearer ***"
        return "***"
    return text


def _mask_json_obj(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            key: ("***" if key.lower() in _SENSITIVE_BODY_KEYS else _mask_json_obj(value))
            for key, value in obj.items()
        }
    if isinstance(obj, list):
        return [_mask_json_obj(item) for item in obj]
    return obj


def _normalize_headers(headers: dict[str, Any] | None) -> dict[str, str]:
    if not headers:
        return {}
    return {str(key): _mask_header(str(key), value) for key, value in headers.items()}


def _normalize_body(body: Any) -> tuple[str, str]:
    if body is None:
        return "空", "empty"
    if isinstance(body, (dict, list)):
        return json.dumps(_mask_json_obj(body), ensure_ascii=False, indent=2), "json"

    if isinstance(body, (bytes, bytearray)):
        text = body.decode("utf-8", errors="replace")
    else:
        text = str(body)

    text = text.strip()
    if not text:
        return "空", "empty"

    try:
        parsed = json.loads(text)
    except Exception:
        return text, "text"

    return json.dumps(_mask_json_obj(parsed), ensure_ascii=False, indent=2), "json"


@dataclass(slots=True)
class _PendingTrace:
    id: str
    sequence: int
    provider: str | None
    model: str | None
    started_at: int
    request_method: str | None
    request_url: str | None
    request_headers: dict[str, str]
    request_body: str
    request_body_format: str
    response_status: int | None = None
    response_headers: dict[str, str] = field(default_factory=dict)
    response_body: str = "未返回"
    response_body_format: str = "unknown"
    response_ok: bool | None = None
    duration_ms: int | None = None
    error: str | None = None


class HttpTraceCollector:
    def __init__(self, *, provider: str | None, model: str | None, seq_offset: int = 0):
        self.provider = provider
        self.model = model
        self._seq = seq_offset
        self._traces: list[_PendingTrace] = []

    def start_request(
        self,
        *,
        method: str | None,
        url: str | None,
        headers: dict[str, Any] | None,
        body: Any,
    ) -> str:
        self._seq += 1
        request_body, request_body_format = _normalize_body(body)
        trace = _PendingTrace(
            id=f"trace-{self._seq}",
            sequence=self._seq,
            provider=self.provider,
            model=self.model,
            started_at=_now_ms(),
            request_method=method,
            request_url=url,
            request_headers=_normalize_headers(headers),
            request_body=request_body,
            request_body_format=request_body_format,
        )
        self._traces.append(trace)
        return trace.id

    def finish_response(
        self,
        trace_id: str,
        *,
        status: int | None,
        headers: dict[str, Any] | None,
        body: Any,
        duration_ms: int | None,
    ) -> None:
        trace = next(item for item in self._traces if item.id == trace_id)
        response_body, response_body_format = _normalize_body(body)
        trace.response_status = status
        trace.response_headers = _normalize_headers(headers)
        trace.response_body = response_body
        trace.response_body_format = response_body_format
        trace.response_ok = bool(status is not None and 200 <= status < 400)
        trace.duration_ms = duration_ms

    def fail_response(self, trace_id: str, error: str) -> None:
        trace = next(item for item in self._traces if item.id == trace_id)
        trace.error = error
        trace.response_ok = False

    def snapshot(self) -> list[HttpTrace]:
        return [
            {
                "id": trace.id,
                "sequence": trace.sequence,
                "kind": "llm_http",
                "provider": trace.provider,
                "model": trace.model,
                "startedAt": trace.started_at,
                "durationMs": trace.duration_ms,
                "request": {
                    "method": trace.request_method,
                    "url": trace.request_url,
                    "headers": trace.request_headers,
                    "body": trace.request_body,
                    "bodyFormat": trace.request_body_format,
                },
                "response": {
                    "status": trace.response_status,
                    "headers": trace.response_headers,
                    "body": trace.response_body,
                    "bodyFormat": trace.response_body_format,
                    "ok": trace.response_ok,
                },
                "error": trace.error,
            }
            for trace in self._traces
        ]


def bind_http_trace_collector(collector: HttpTraceCollector) -> Token:
    return _CURRENT_COLLECTOR.set(collector)


def reset_http_trace_collector(token: Token) -> None:
    _CURRENT_COLLECTOR.reset(token)


def get_http_trace_collector() -> HttpTraceCollector | None:
    return _CURRENT_COLLECTOR.get()
