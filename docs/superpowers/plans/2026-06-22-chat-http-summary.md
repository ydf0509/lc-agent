# Chat HTTP Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为聊天气泡增加“请求 HTTP / 响应 HTTP”按钮，展示同一轮 AI 调用的上游模型 HTTP 摘要。

**Architecture:** 后端新增一个轮次级 `HttpTraceCollector`，通过 `http_async_client` 注入到 `ChatOpenAIReasoning` 的 OpenAI-compatible 调用链里，采集真实 request/response 摘要并脱敏；这些 traces 持久化到 assistant 消息上。前端在 `ChatView` 中把 assistant 的 traces 映射给同轮 user / assistant 气泡，并在 `MessageToolbar` 中通过 popover 展示请求视图和响应视图。

**Tech Stack:** Python 3.12, FastAPI, SQLModel + Alembic, LangChain / langchain-openai, httpx, Vue 3 + TypeScript + Pinia + Element Plus

**Spec:** `docs/superpowers/specs/2026-06-22-chat-http-summary-design.md`

---

## 文件清单

| 操作 | 文件路径 | 职责 |
|---|---|---|
| 新建 | `lc_agent/core/http_trace.py` | HTTP trace 数据结构、脱敏、collector、contextvar 绑定 |
| 新建 | `lc_agent/core/http_trace_httpx.py` | 记录 request/response 的 `httpx.AsyncClient` / stream 包装 |
| 修改 | `lc_agent/core/chat_model.py` | 继续保留 reasoning 提取，并允许复用 tracing client |
| 修改 | `lc_agent/core/engine.py` | 为 OpenAI-compatible 模型注入 tracing async client，并暴露 trace meta helper |
| 修改 | `lc_agent/server/websocket.py` | 每轮创建 collector，done 时回传并持久化 `http_traces` |
| 修改 | `lc_agent/db/models.py` | 给 `ChatUiMessage` 增加 `http_traces` JSON 字段 |
| 修改 | `lc_agent/db/repository.py` | repository create/list 支持 `http_traces` |
| 修改 | `lc_agent/server/routes/sessions.py` | session history 返回 `http_traces` |
| 新建 | `lc_agent/db/migrations/versions/20260622_add_http_traces_to_chat_ui_messages.py` | Alembic schema revision |
| 新建 | `tests_my/ai_tests/test_http_trace.py` | collector / redaction 单测 |
| 新建 | `tests_my/ai_tests/test_http_trace_httpx.py` | tracing async client 单测 |
| 新建 | `tests_my/ai_tests/test_chat_http_storage.py` | repository + session history 单测 |
| 修改 | `frontend/src/api/websocket.ts` | websocket done payload 增加 `http_traces` 字段 |
| 修改 | `frontend/src/stores/chat.ts` | `HttpTrace` 类型、history/done 归一化 |
| 新建 | `frontend/src/components/chat/HttpTracePopover.vue` | 请求/响应 popover 内容组件 |
| 修改 | `frontend/src/components/chat/MessageToolbar.vue` | 新增 `请求 HTTP` / `响应 HTTP` 按钮 |
| 修改 | `frontend/src/views/ChatView.vue` | 同轮 traces 映射并传给 toolbar |
| 新建 | `frontend/scripts/check-chat-http-data-contract.mjs` | 前端数据契约测试 |
| 新建 | `frontend/scripts/check-chat-http-ui-contract.mjs` | 前端 UI 契约测试 |
| 修改 | `frontend/package.json` | 注册前端契约测试脚本 |

---

### Task 1: 实现 HTTP trace 数据结构、脱敏与 collector

**Files:**
- Create: `lc_agent/core/http_trace.py`
- Create: `tests_my/ai_tests/test_http_trace.py`

- [ ] **Step 1: 编写失败测试，固定 collector 输出与脱敏规则**

在 `tests_my/ai_tests/test_http_trace.py` 中创建：

```python
import pytest

from lc_agent.core.http_trace import HttpTraceCollector


def test_redacts_sensitive_headers_and_body_fields():
    collector = HttpTraceCollector(provider="litellm", model="ds-deepseek-v4-flash")

    trace_id = collector.start_request(
        method="POST",
        url="https://proxy.test/v1/chat/completions",
        headers={
            "Authorization": "Bearer secret-token",
            "Content-Type": "application/json",
        },
        body='{"messages":[{"role":"user","content":"hi"}],"api_key":"abc123"}',
    )
    collector.finish_response(
        trace_id,
        status=200,
        headers={
            "content-type": "application/json",
            "set-cookie": "session=secret-cookie",
        },
        body='{"id":"resp-1","token":"resp-secret","choices":[{"message":{"content":"hello"}}]}',
        duration_ms=125,
    )

    traces = collector.snapshot()
    assert len(traces) == 1
    trace = traces[0]
    assert trace["sequence"] == 1
    assert trace["provider"] == "litellm"
    assert trace["model"] == "ds-deepseek-v4-flash"
    assert trace["request"]["headers"]["Authorization"] == "Bearer ***"
    assert '"api_key": "***"' in trace["request"]["body"]
    assert trace["response"]["headers"]["set-cookie"] == "***"
    assert '"token": "***"' in trace["response"]["body"]
    assert trace["response"]["status"] == 200
    assert trace["durationMs"] == 125


def test_keeps_failed_trace_with_error_text():
    collector = HttpTraceCollector(provider="litellm", model="ark-glm-5.1")

    trace_id = collector.start_request(
        method="POST",
        url="https://proxy.test/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        body='{"messages":[]}',
    )
    collector.fail_response(trace_id, "ReadTimeout")

    [trace] = collector.snapshot()
    assert trace["request"]["url"] == "https://proxy.test/v1/chat/completions"
    assert trace["error"] == "ReadTimeout"
    assert trace["response"]["status"] is None
```

- [ ] **Step 2: 运行测试，确认当前失败**

```bash
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests_my/ai_tests/test_http_trace.py -q
```

预期：失败，报 `ModuleNotFoundError: No module named 'lc_agent.core.http_trace'`。

- [ ] **Step 3: 实现 `lc_agent/core/http_trace.py`**

创建 `lc_agent/core/http_trace.py`：

```python
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
_SENSITIVE_BODY_KEYS = {"api_key", "token", "password", "secret", "access_token", "refresh_token"}
_CURRENT_COLLECTOR: ContextVar[HttpTraceCollector | None] = ContextVar("http_trace_collector", default=None)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _mask_header(name: str, value: Any) -> str:
    value_str = "" if value is None else str(value)
    if name.lower() in _SENSITIVE_HEADERS:
        if value_str.lower().startswith("bearer "):
            return "Bearer ***"
        return "***"
    return value_str


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
    text = body.decode("utf-8", errors="replace") if isinstance(body, (bytes, bytearray)) else str(body)
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
    def __init__(self, *, provider: str | None, model: str | None):
        self.provider = provider
        self.model = model
        self._seq = 0
        self._traces: list[_PendingTrace] = []

    def start_request(self, *, method: str | None, url: str | None, headers: dict[str, Any] | None, body: Any) -> str:
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
```

- [ ] **Step 4: 重新运行测试，确认 collector 通过**

```bash
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests_my/ai_tests/test_http_trace.py -q
```

预期：`2 passed`。

- [ ] **Step 5: 提交 Task 1**

```bash
git add tests_my/ai_tests/test_http_trace.py lc_agent/core/http_trace.py
git commit -m "feat: add http trace collector and redaction"
```

---

### Task 2: 实现 tracing httpx client，并接入 ChatOpenAIReasoning / engine

**Files:**
- Create: `lc_agent/core/http_trace_httpx.py`
- Modify: `lc_agent/core/chat_model.py`
- Modify: `lc_agent/core/engine.py`
- Create: `tests_my/ai_tests/test_http_trace_httpx.py`

- [ ] **Step 1: 编写失败测试，固定 tracing client 与 engine 注入行为**

在 `tests_my/ai_tests/test_http_trace_httpx.py` 中创建：

```python
import httpx
import pytest

from lc_agent.core.http_trace import HttpTraceCollector
from lc_agent.core.http_trace_httpx import TracingAsyncClient


@pytest.mark.asyncio
async def test_tracing_async_client_records_request_and_response():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"id": "cmpl-1", "choices": [{"message": {"content": "hi"}}]},
        )

    collector = HttpTraceCollector(provider="litellm", model="ds-deepseek-v4-flash")
    client = TracingAsyncClient(
        collector_getter=lambda: collector,
        provider="litellm",
        model="ds-deepseek-v4-flash",
        transport=httpx.MockTransport(handler),
    )

    response = await client.post(
        "https://proxy.test/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 200
    traces = collector.snapshot()
    assert len(traces) == 1
    assert traces[0]["request"]["method"] == "POST"
    assert traces[0]["request"]["url"] == "https://proxy.test/v1/chat/completions"
    assert '"content": "hello"' in traces[0]["request"]["body"]
    assert '"content": "hi"' in traces[0]["response"]["body"]


@pytest.mark.asyncio
async def test_engine_uses_chatopenai_reasoning_with_tracing_client():
    from lc_agent.core.chat_model import ChatOpenAIReasoning
    from lc_agent.core.engine import AgentEngine
    from lc_agent.core.models import ModelInfo

    engine = AgentEngine({"provider": {}, "agent": {"default_model": "", "system_prompt": ""}})
    model_info = ModelInfo(
        id="ds-deepseek-v4-flash",
        provider="litellm",
        base_url="http://localhost:4000/v1",
        api_key="sk-no-key-needed",
    )

    llm = engine._create_llm(model_info, model_info.id)
    assert isinstance(llm, ChatOpenAIReasoning)
    assert llm.http_async_client is not None
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests_my/ai_tests/test_http_trace_httpx.py -q
```

预期：失败，报 `ModuleNotFoundError: No module named 'lc_agent.core.http_trace_httpx'` 或 engine 断言失败。

- [ ] **Step 3: 实现 tracing async client**

创建 `lc_agent/core/http_trace_httpx.py`：

```python
from __future__ import annotations

import time
from typing import Callable

import httpx

from lc_agent.core.http_trace import HttpTraceCollector


class TracingAsyncClient(httpx.AsyncClient):
    def __init__(
        self,
        *,
        collector_getter: Callable[[], HttpTraceCollector | None],
        provider: str | None,
        model: str | None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._collector_getter = collector_getter
        self._provider = provider
        self._model = model

    async def send(self, request: httpx.Request, *args, **kwargs) -> httpx.Response:
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
            body = await response.aread()
            rebuilt = httpx.Response(
                status_code=response.status_code,
                headers=response.headers,
                content=body,
                request=request,
                extensions=response.extensions,
            )
            if collector is not None and trace_id is not None:
                collector.finish_response(
                    trace_id,
                    status=rebuilt.status_code,
                    headers=dict(rebuilt.headers),
                    body=body,
                    duration_ms=int((time.time() - started) * 1000),
                )
            return rebuilt
        except Exception as exc:
            if collector is not None and trace_id is not None:
                collector.fail_response(trace_id, exc.__class__.__name__)
            raise
```

- [ ] **Step 4: 在 `ChatOpenAIReasoning` 与 engine 中接入 tracing client**

在 `lc_agent/core/chat_model.py` 顶部保持现有 reasoning 提取逻辑不动，只补一个小 helper，确保 tracing client 类型可直接传入：

```python
from typing import Any

# ...保留现有 imports...

class ChatOpenAIReasoning(ChatOpenAI):
    # 保留现有 _convert_chunk_to_generation_chunk 实现

    def with_tracing_client(self, http_async_client: Any) -> "ChatOpenAIReasoning":
        self.http_async_client = http_async_client
        self.async_client = None
        self.root_async_client = None
        self.validate_environment()
        return self
```

在 `lc_agent/core/engine.py` 中添加 import，并替换 `_create_llm`：

```python
from lc_agent.core.http_trace import get_http_trace_collector
from lc_agent.core.http_trace_httpx import TracingAsyncClient

# ...

    def get_model_trace_meta(self, model_info: ModelInfo | None, model_id: str) -> tuple[str | None, str | None]:
        provider = model_info.provider if model_info else None
        model_name = model_info.id if model_info else model_id
        return provider, model_name

    def _build_tracing_async_client(self, model_info: ModelInfo | None, model_id: str):
        provider, resolved_model = self.get_model_trace_meta(model_info, model_id)
        return TracingAsyncClient(
            collector_getter=get_http_trace_collector,
            provider=provider,
            model=resolved_model,
            timeout=self.config.get("agent", {}).get("request_timeout", 120),
        )

    def _create_llm(self, model_info: ModelInfo | None, model_id: str):
        tracing_async_client = self._build_tracing_async_client(model_info, model_id)
        if model_info and model_info.base_url:
            from lc_agent.core.chat_model import ChatOpenAIReasoning
            return ChatOpenAIReasoning(
                model=model_info.id,
                base_url=model_info.base_url,
                api_key=model_info.api_key or "not-set",
                temperature=0.7,
                stream_usage=True,
                http_async_client=tracing_async_client,
            )

        from langchain.chat_models import init_chat_model

        if model_info:
            model_str = f"{model_info.provider}:{model_info.id}" if model_info.provider else model_info.id
            return init_chat_model(
                model_str,
                api_key=model_info.api_key or "not-set",
                temperature=0.7,
                stream_usage=True,
            )

        return init_chat_model(model_id, api_key="not-set", temperature=0.7, stream_usage=True)
```

- [ ] **Step 5: 重新运行 tracing 测试**

```bash
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests_my/ai_tests/test_http_trace_httpx.py -q
```

预期：`2 passed`。

- [ ] **Step 6: 再跑现有 reasoning 回归测试**

```bash
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests_my/ai_tests/test_chat_openai_reasoning.py -q
```

预期：现有 `ChatOpenAIReasoning` 测试继续通过。

- [ ] **Step 7: 提交 Task 2**

```bash
git add tests_my/ai_tests/test_http_trace_httpx.py lc_agent/core/http_trace_httpx.py lc_agent/core/chat_model.py lc_agent/core/engine.py
git commit -m "feat: trace openai-compatible http requests"
```

---

### Task 3: 绑定聊天轮次，持久化 `http_traces`，并暴露给 session history

**Files:**
- Modify: `lc_agent/server/websocket.py`
- Modify: `lc_agent/db/models.py`
- Modify: `lc_agent/db/repository.py`
- Modify: `lc_agent/server/routes/sessions.py`
- Create: `lc_agent/db/migrations/versions/20260622_add_http_traces_to_chat_ui_messages.py`
- Create: `tests_my/ai_tests/test_chat_http_storage.py`

- [ ] **Step 1: 编写失败测试，固定 repository 和 session history 行为**

在 `tests_my/ai_tests/test_chat_http_storage.py` 中创建：

```python
from types import SimpleNamespace

import pytest

from lc_agent.db.engine import init_db, get_async_session, reset_engine
from lc_agent.db.repository import ChatUiMessageRepository
from lc_agent.server.routes.sessions import get_session_messages


@pytest.mark.asyncio
async def test_session_history_returns_http_traces(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'chat-http.db'}"
    reset_engine()
    await init_db(db_url)
    session = get_async_session(db_url)
    try:
        repo = ChatUiMessageRepository(session)
        await repo.create(
            session_id="sess-1",
            role="assistant",
            content="hello",
            http_traces=[
                {
                    "id": "trace-1",
                    "sequence": 1,
                    "kind": "llm_http",
                    "provider": "litellm",
                    "model": "ds-deepseek-v4-flash",
                    "startedAt": 1,
                    "durationMs": 99,
                    "request": {"method": "POST", "url": "https://proxy.test/v1/chat/completions", "headers": {}, "body": "{}", "bodyFormat": "json"},
                    "response": {"status": 200, "headers": {}, "body": "{}", "bodyFormat": "json", "ok": True},
                    "error": None,
                }
            ],
        )

        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(engine=None)))
        messages = await get_session_messages("sess-1", request=request, db=session)
        assert messages[0]["http_traces"][0]["sequence"] == 1
        assert messages[0]["http_traces"][0]["response"]["status"] == 200
    finally:
        await session.close()
        reset_engine()
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests_my/ai_tests/test_chat_http_storage.py -q
```

预期：失败，报 `ChatUiMessageRepository.create()` 不接受 `http_traces`，或 history 返回缺字段。

- [ ] **Step 3: 扩展 SQLModel 与 repository**

在 `lc_agent/db/models.py` 的 `ChatUiMessage` 上增加字段：

```python
class ChatUiMessage(SQLModel, table=True):
    __tablename__ = "chat_ui_messages"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(index=True)
    role: str
    content: str = ""
    tool_calls: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    usage: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    http_traces: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
```

在 `lc_agent/db/repository.py` 的 `create()` 上增加参数并透传：

```python
    async def create(
        self,
        *,
        session_id: str,
        role: str,
        content: str = "",
        tool_calls: list[dict] | None = None,
        usage: dict | None = None,
        http_traces: list[dict] | None = None,
    ) -> ChatUiMessage:
        message = ChatUiMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            http_traces=http_traces,
        )
```

- [ ] **Step 4: 编写 Alembic revision**

创建 `lc_agent/db/migrations/versions/20260622_add_http_traces_to_chat_ui_messages.py`：

```python
"""add http_traces to chat_ui_messages

Revision ID: 20260622_http_traces
Revises: a342dc61a740
Create Date: 2026-06-22 20:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260622_http_traces"
down_revision: Union[str, Sequence[str], None] = "a342dc61a740"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("chat_ui_messages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("http_traces", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("chat_ui_messages", schema=None) as batch_op:
        batch_op.drop_column("http_traces")
```

- [ ] **Step 5: 在 websocket 每轮绑定 collector，并在 done/history 中回传 traces**

在 `lc_agent/server/websocket.py` 中加入 import：

```python
from lc_agent.core.http_trace import HttpTraceCollector, bind_http_trace_collector, reset_http_trace_collector
```

在 `handle_message()` 的 `msg_type == "message"` 分支里，围绕 `engine.chat_stream(...)` 包一层 collector：

```python
                model_info = self.engine._find_model(model_id) if model_id else None
                provider, resolved_model = self.engine.get_model_trace_meta(model_info, model_id)
                http_trace_collector = HttpTraceCollector(provider=provider, model=resolved_model)
                trace_token = bind_http_trace_collector(http_trace_collector)
                try:
                    stream = self.engine.chat_stream(content, thread_id, preset_id, **stream_kwargs)
                    async for event in stream:
                        if self._cancel_flags.get(thread_id):
                            await websocket.send_json({"type": "cancelled"})
                            return
                        assistant_in_thinking = self._accumulate_assistant_display_state(
                            event,
                            assistant_content_parts,
                            assistant_tool_calls,
                            assistant_in_thinking,
                        )
                        await self._send_event(websocket, event)
                        prev_len = len(usage_rounds)
                        self._accumulate_usage(event, usage_rounds)
                        if len(usage_rounds) > prev_len:
                            usage_rounds[-1]["duration_ms"] = int((time.time() - round_start_time) * 1000)
                            round_start_time = time.time()
                            await websocket.send_json({"type": "llm_usage", **usage_rounds[-1]})
                finally:
                    reset_http_trace_collector(trace_token)

                http_traces = http_trace_collector.snapshot()
                done_payload: dict[str, Any] = {"type": "done"}
                if usage_rounds:
                    done_payload["usage"] = usage_rounds
                if http_traces:
                    done_payload["http_traces"] = http_traces
                if assistant_content_parts or assistant_tool_calls or usage_rounds or http_traces:
                    await self._save_ui_message(
                        thread_id,
                        "assistant",
                        "".join(assistant_content_parts),
                        tool_calls=assistant_tool_calls or None,
                        usage={
                            "rounds": usage_rounds,
                            "tool_call_count": len(assistant_tool_calls),
                            "total_duration_ms": int((time.time() - stream_start_time) * 1000),
                        },
                        http_traces=http_traces or None,
                    )
```

同时把 `_save_ui_message()` 签名扩成：

```python
    async def _save_ui_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        *,
        tool_calls: list[dict[str, Any]] | None = None,
        usage: dict[str, Any] | None = None,
        http_traces: list[dict[str, Any]] | None = None,
    ):
        # ...
                await repo.create(
                    session_id=thread_id,
                    role=role,
                    content=content,
                    tool_calls=tool_calls,
                    usage=usage,
                    http_traces=http_traces,
                )
```

在 `lc_agent/server/routes/sessions.py` 的 UI history 返回中追加：

```python
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "tool_calls": msg.tool_calls or [],
                "usage": msg.usage,
                "http_traces": msg.http_traces or [],
                "created_at": msg.created_at.isoformat(),
            }
```

- [ ] **Step 6: 重新运行存储/history 测试**

```bash
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests_my/ai_tests/test_chat_http_storage.py -q
```

预期：`1 passed`。

- [ ] **Step 7: 提交 Task 3**

```bash
git add tests_my/ai_tests/test_chat_http_storage.py lc_agent/db/models.py lc_agent/db/repository.py lc_agent/server/routes/sessions.py lc_agent/server/websocket.py lc_agent/db/migrations/versions/20260622_add_http_traces_to_chat_ui_messages.py
git commit -m "feat: persist chat http traces"
```

---

### Task 4: 扩展前端 websocket/store 数据契约，接收 `http_traces`

**Files:**
- Modify: `frontend/src/api/websocket.ts`
- Modify: `frontend/src/stores/chat.ts`
- Create: `frontend/scripts/check-chat-http-data-contract.mjs`
- Modify: `frontend/package.json`

- [ ] **Step 1: 编写失败的前端数据契约测试**

创建 `frontend/scripts/check-chat-http-data-contract.mjs`：

```javascript
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const read = (relativePath) => readFileSync(join(root, relativePath), 'utf8')

const chatStore = read('src/stores/chat.ts')
const websocket = read('src/api/websocket.ts')
const failures = []

function expectIncludes(name, content, expected) {
  if (!content.includes(expected)) failures.push(`${name} 缺少: ${expected}`)
}

expectIncludes('chat.ts', chatStore, 'export interface HttpTrace')
expectIncludes('chat.ts', chatStore, 'httpTraces?: HttpTrace[]')
expectIncludes('chat.ts', chatStore, 'function normalizeHttpTrace')
expectIncludes('chat.ts', chatStore, 'function normalizeHttpTraces')
expectIncludes('chat.ts', chatStore, 'httpTraces: normalizeHttpTraces(msg.http_traces || msg.httpTraces)')
expectIncludes('chat.ts', chatStore, 'last.httpTraces = normalizeHttpTraces((msg as any).http_traces || (msg as any).httpTraces)')
expectIncludes('websocket.ts', websocket, 'http_traces?: any[]')

if (failures.length > 0) {
  console.error('聊天 HTTP 数据契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('聊天 HTTP 数据契约测试通过')
```

在 `frontend/package.json` 里先加 script：

```json
"test:chat-http-data": "node scripts/check-chat-http-data-contract.mjs"
```

- [ ] **Step 2: 运行契约测试，确认失败**

```bash
cd frontend && npm run test:chat-http-data
```

预期：失败，提示缺少 `HttpTrace`、`normalizeHttpTrace` 等定义。

- [ ] **Step 3: 扩展 websocket 与 chat store 类型**

在 `frontend/src/api/websocket.ts` 的 `WsMessage` 上追加：

```ts
export interface WsMessage {
  type: string
  content?: string
  thread_id?: string
  title?: string
  name?: string
  result?: string
  message?: string
  run_id?: string
  args?: Record<string, any>
  action_requests?: any[]
  review_configs?: any[]
  input_tokens?: number
  output_tokens?: number
  total_tokens?: number
  cache_read_tokens?: number
  reasoning_tokens?: number
  usage?: any[]
  http_traces?: any[]
}
```

在 `frontend/src/stores/chat.ts` 顶部新增类型和归一化函数：

```ts
export interface HttpTraceMessagePart {
  method?: string
  url?: string
  headers: Record<string, string>
  body: string
  bodyFormat?: 'json' | 'text' | 'empty' | 'unknown'
}

export interface HttpTraceResponsePart {
  status?: number
  headers: Record<string, string>
  body: string
  bodyFormat?: 'json' | 'text' | 'empty' | 'unknown'
  ok?: boolean
}

export interface HttpTrace {
  id: string
  sequence: number
  kind: 'llm_http'
  provider?: string
  model?: string
  startedAt: number
  durationMs?: number
  request: HttpTraceMessagePart
  response: HttpTraceResponsePart
  error?: string | null
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'tool'
  content: string
  timestamp: number
  toolCalls?: ToolCall[]
  segments?: ContentSegment[]
  isStreaming?: boolean
  usage?: MessageUsage
  httpTraces?: HttpTrace[]
}

function normalizeHttpTrace(raw: any): HttpTrace {
  return {
    id: raw.id || createClientId(),
    sequence: raw.sequence ?? 0,
    kind: 'llm_http',
    provider: raw.provider || undefined,
    model: raw.model || undefined,
    startedAt: raw.startedAt ?? raw.started_at ?? Date.now(),
    durationMs: raw.durationMs ?? raw.duration_ms,
    request: {
      method: raw.request?.method || undefined,
      url: raw.request?.url || undefined,
      headers: raw.request?.headers || {},
      body: raw.request?.body || '空',
      bodyFormat: raw.request?.bodyFormat ?? raw.request?.body_format ?? 'unknown',
    },
    response: {
      status: raw.response?.status,
      headers: raw.response?.headers || {},
      body: raw.response?.body || '未返回',
      bodyFormat: raw.response?.bodyFormat ?? raw.response?.body_format ?? 'unknown',
      ok: raw.response?.ok,
    },
    error: raw.error ?? null,
  }
}

function normalizeHttpTraces(raw: any): HttpTrace[] | undefined {
  if (!Array.isArray(raw) || raw.length === 0) return undefined
  return raw.map(normalizeHttpTrace)
}
```

把 `normalizeHistoryMessage()` 的返回值补上：

```ts
    httpTraces: normalizeHttpTraces(msg.http_traces || msg.httpTraces),
```

把 websocket done handler 补上：

```ts
      if (last) {
        last.isStreaming = false
        if (last.usage && streamStartTime) {
          last.usage.totalDuration = Date.now() - streamStartTime
        }
        const usageData = (msg as any).usage as any[] | undefined
        if (usageData && usageData.length > 0 && last.usage) {
          mergeFinalUsageRounds(last.usage.rounds, usageData)
        }
        last.httpTraces = normalizeHttpTraces((msg as any).http_traces || (msg as any).httpTraces)
      }
```

- [ ] **Step 4: 运行前端数据契约测试**

```bash
cd frontend && npm run test:chat-http-data
```

预期：`聊天 HTTP 数据契约测试通过`。

- [ ] **Step 5: 提交 Task 4**

```bash
git add frontend/src/api/websocket.ts frontend/src/stores/chat.ts frontend/scripts/check-chat-http-data-contract.mjs frontend/package.json
git commit -m "feat: receive chat http traces in frontend store"
```

---

### Task 5: 新增 HTTP popover 组件，并在 MessageToolbar 中加入请求/响应按钮

**Files:**
- Create: `frontend/src/components/chat/HttpTracePopover.vue`
- Modify: `frontend/src/components/chat/MessageToolbar.vue`
- Create: `frontend/scripts/check-chat-http-ui-contract.mjs`
- Modify: `frontend/package.json`

- [ ] **Step 1: 编写失败的 UI 契约测试**

创建 `frontend/scripts/check-chat-http-ui-contract.mjs`：

```javascript
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const read = (relativePath) => readFileSync(join(root, relativePath), 'utf8')

const toolbar = read('src/components/chat/MessageToolbar.vue')
const popover = read('src/components/chat/HttpTracePopover.vue')
const failures = []

function expectIncludes(name, content, expected) {
  if (!content.includes(expected)) failures.push(`${name} 缺少: ${expected}`)
}

expectIncludes('MessageToolbar.vue', toolbar, '请求 HTTP')
expectIncludes('MessageToolbar.vue', toolbar, '响应 HTTP')
expectIncludes('MessageToolbar.vue', toolbar, 'HttpTracePopover')
expectIncludes('MessageToolbar.vue', toolbar, 'showHttpRequest')
expectIncludes('MessageToolbar.vue', toolbar, 'showHttpResponse')
expectIncludes('HttpTracePopover.vue', popover, "mode: 'request' | 'response'")
expectIncludes('HttpTracePopover.vue', popover, 'Request Headers')
expectIncludes('HttpTracePopover.vue', popover, 'Response Headers')
expectIncludes('HttpTracePopover.vue', popover, 'Request Body')
expectIncludes('HttpTracePopover.vue', popover, 'Response Body')

if (failures.length > 0) {
  console.error('聊天 HTTP UI 契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('聊天 HTTP UI 契约测试通过')
```

在 `frontend/package.json` 中追加：

```json
"test:chat-http-ui": "node scripts/check-chat-http-ui-contract.mjs"
```

- [ ] **Step 2: 运行 UI 契约测试，确认失败**

```bash
cd frontend && npm run test:chat-http-ui
```

预期：失败，提示缺少 `HttpTracePopover.vue`、请求/响应按钮文案等。

- [ ] **Step 3: 创建 `HttpTracePopover.vue`**

创建 `frontend/src/components/chat/HttpTracePopover.vue`：

```vue
<script setup lang="ts">
import { computed } from 'vue'
import type { HttpTrace } from '@/stores/chat'

const props = defineProps<{
  traces: HttpTrace[]
  mode: 'request' | 'response'
}>()

const title = computed(() => props.mode === 'request' ? '请求 HTTP' : '响应 HTTP')

function formatBody(body: string) {
  if (!body) return '空'
  try {
    return JSON.stringify(JSON.parse(body), null, 2)
  } catch {
    return body
  }
}

function formatTime(ts?: number) {
  if (!ts) return '-'
  return new Date(ts).toLocaleTimeString()
}
</script>

<template>
  <div class="http-trace-popover">
    <div class="panel-header">
      <strong>{{ title }}</strong>
      <span class="panel-subtitle">本轮共 {{ traces.length }} 次上游调用</span>
    </div>

    <div v-for="trace in traces" :key="trace.id" class="trace-card">
      <div class="trace-row trace-meta">
        <span class="trace-seq">第 {{ trace.sequence }} 次{{ mode === 'request' ? '调用' : '响应' }}</span>
        <el-tag size="small" :type="mode === 'request' ? 'success' : (trace.response.ok ? 'primary' : 'danger')">
          {{ mode === 'request' ? (trace.request.method || 'HTTP') : (trace.response.status ?? '失败') }}
        </el-tag>
      </div>
      <div class="trace-url">{{ trace.request.url || '未采集' }}</div>
      <div class="trace-row">
        <span v-if="mode === 'request'">发起时间：{{ formatTime(trace.startedAt) }}</span>
        <span v-else>耗时：{{ trace.durationMs ?? '-' }} ms</span>
      </div>

      <template v-if="mode === 'request'">
        <div class="trace-block-title">Request Headers</div>
        <pre class="trace-code">{{ formatBody(JSON.stringify(trace.request.headers || {}, null, 2)) }}</pre>
        <div class="trace-block-title">Request Body</div>
        <pre class="trace-code">{{ formatBody(trace.request.body) }}</pre>
      </template>
      <template v-else>
        <div class="trace-block-title">Response Headers</div>
        <pre class="trace-code">{{ formatBody(JSON.stringify(trace.response.headers || {}, null, 2)) }}</pre>
        <div class="trace-block-title">Response Body</div>
        <pre class="trace-code">{{ formatBody(trace.response.body) }}</pre>
        <div v-if="trace.error" class="trace-error">请求失败：{{ trace.error }}</div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.http-trace-popover {
  width: min(460px, 80vw);
  max-height: 70vh;
  overflow: auto;
}
.panel-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 10px;
}
.panel-subtitle {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.trace-card {
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 10px;
  margin-top: 10px;
}
.trace-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.trace-meta {
  align-items: center;
}
.trace-url {
  margin: 6px 0;
  font-size: 12px;
  word-break: break-all;
}
.trace-block-title {
  margin-top: 8px;
  margin-bottom: 4px;
  font-size: 12px;
  font-weight: 600;
}
.trace-code {
  margin: 0;
  padding: 8px;
  border-radius: 8px;
  background: var(--el-fill-color-light);
  max-height: 220px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}
.trace-error {
  margin-top: 8px;
  color: var(--el-color-danger);
  font-size: 12px;
}
</style>
```

- [ ] **Step 4: 修改 `MessageToolbar.vue`，新增请求/响应按钮**

在 `frontend/src/components/chat/MessageToolbar.vue` 中：

```vue
<script setup lang="ts">
import { ref } from 'vue'
import {
  singleMessageToMarkdown,
  extractThinking,
  extractToolCalls,
  extractAnswer,
  copyToClipboard,
} from '@/utils/copy-markdown'
import HttpTracePopover from '@/components/chat/HttpTracePopover.vue'
import type { ChatMessage, HttpTrace } from '@/stores/chat'

const props = defineProps<{
  message: ChatMessage
  modelName?: string
  hasThinking?: boolean
  hasToolCalls?: boolean
  hasAnswer?: boolean
  httpTraces?: HttpTrace[]
  showHttpRequest?: boolean
  showHttpResponse?: boolean
}>()

// 保留现有 copiedKey / doCopy / copyXxx 函数
</script>

<template>
  <div class="message-toolbar">
    <template v-if="message.role === 'user'">
      <button class="tb-btn" @click="copyUser">
        {{ copiedKey === 'all' ? '已复制 ✓' : '📋 复制' }}
      </button>
      <el-popover
        v-if="showHttpRequest && httpTraces?.length"
        placement="bottom-end"
        :width="460"
        trigger="click"
      >
        <template #reference>
          <button class="tb-btn">🌐 请求 HTTP</button>
        </template>
        <HttpTracePopover :traces="httpTraces" mode="request" />
      </el-popover>
    </template>
    <template v-else>
      <button class="tb-btn" @click="copyAll">
        {{ copiedKey === 'all' ? '已复制 ✓' : '📋 复制全部' }}
      </button>
      <button v-if="hasThinking" class="tb-btn" @click="copyThinking">
        {{ copiedKey === 'thinking' ? '已复制 ✓' : '💭 复制思考' }}
      </button>
      <button v-if="hasToolCalls" class="tb-btn" @click="copyTools">
        {{ copiedKey === 'tools' ? '已复制 ✓' : '🔧 复制工具' }}
      </button>
      <button v-if="hasAnswer" class="tb-btn" @click="copyAnswer">
        {{ copiedKey === 'answer' ? '已复制 ✓' : '📝 复制回答' }}
      </button>
      <el-popover
        v-if="showHttpResponse && httpTraces?.length"
        placement="bottom-start"
        :width="460"
        trigger="click"
      >
        <template #reference>
          <button class="tb-btn">🌐 响应 HTTP</button>
        </template>
        <HttpTracePopover :traces="httpTraces" mode="response" />
      </el-popover>
    </template>
  </div>
</template>
```

- [ ] **Step 5: 运行 UI 契约测试**

```bash
cd frontend && npm run test:chat-http-ui
```

预期：`聊天 HTTP UI 契约测试通过`。

- [ ] **Step 6: 提交 Task 5**

```bash
git add frontend/src/components/chat/HttpTracePopover.vue frontend/src/components/chat/MessageToolbar.vue frontend/scripts/check-chat-http-ui-contract.mjs frontend/package.json
git commit -m "feat: add chat http summary popovers"
```

---

### Task 6: 在 ChatView 做同轮 traces 映射，并完成端到端验证

**Files:**
- Modify: `frontend/src/views/ChatView.vue`
- Modify: `frontend/src/components/chat/MessageToolbar.vue`
- Modify: `frontend/scripts/check-chat-http-ui-contract.mjs`

- [ ] **Step 1: 先扩展 UI 契约测试，固定 ChatView round mapping 行为**

在 `frontend/scripts/check-chat-http-ui-contract.mjs` 末尾增加：

```javascript
const chatView = read('src/views/ChatView.vue')
expectIncludes('ChatView.vue', chatView, 'function buildRoundHttpTraceMap')
expectIncludes('ChatView.vue', chatView, 'httpTraces: roundHttpTraceMap.get(msg.id)')
expectIncludes('ChatView.vue', chatView, ':http-traces="item.httpTraces"')
expectIncludes('ChatView.vue', chatView, ':show-http-request="item.hasHttpRequest"')
expectIncludes('ChatView.vue', chatView, ':show-http-response="item.hasHttpResponse"')
```

- [ ] **Step 2: 运行 UI 契约测试，确认 ChatView 相关断言失败**

```bash
cd frontend && npm run test:chat-http-ui
```

预期：失败，提示缺少 `buildRoundHttpTraceMap` 等内容。

- [ ] **Step 3: 在 `ChatView.vue` 中建立同轮 traces 映射**

在 `frontend/src/views/ChatView.vue` 的 `<script setup>` 中：

```ts
import type { ToolCall, MessageUsage, ReplayMessage, HttpTrace, ChatMessage } from '@/stores/chat'

// ...

type ChatBubbleItem = BubbleListItemProps & {
  role: 'user' | 'ai'
  messageId: string
  isMarkdown?: boolean
  toolCalls?: ToolCall[]
  segments?: ContentSegment[]
  usage?: MessageUsage
  hasThinking?: boolean
  hasToolCalls?: boolean
  hasAnswer?: boolean
  httpTraces?: HttpTrace[]
  hasHttpRequest?: boolean
  hasHttpResponse?: boolean
}

function buildRoundHttpTraceMap(source: ChatMessage[]): Map<string, HttpTrace[] | undefined> {
  const map = new Map<string, HttpTrace[] | undefined>()
  let lastUserId: string | null = null

  for (const msg of source) {
    if (msg.role === 'user') {
      lastUserId = msg.id
      if (!map.has(msg.id)) map.set(msg.id, undefined)
      continue
    }
    if (msg.role !== 'assistant') continue

    if (msg.httpTraces?.length) {
      map.set(msg.id, msg.httpTraces)
      if (lastUserId) {
        map.set(lastUserId, msg.httpTraces)
      }
    }
  }

  return map
}

const bubbleList = computed((): ChatBubbleItem[] => {
  const roundHttpTraceMap = buildRoundHttpTraceMap(messages.value)
  return messages.value
    .filter(msg => msg.role === 'user' || msg.role === 'assistant')
    .map((msg, idx, arr) => {
      const segs = msg.role === 'assistant' && hasStructuredSegments(msg.content || '', msg.toolCalls)
        ? parseSegments(msg.content || '', msg.toolCalls)
        : undefined
      const httpTraces = roundHttpTraceMap.get(msg.id)
      return {
        key: msg.id,
        messageId: msg.id,
        role: msg.role === 'assistant' ? 'ai' : 'user',
        placement: msg.role === 'user' ? 'end' : 'start',
        content: msg.content || '',
        shape: 'corner' as const,
        variant: (msg.role === 'user' ? 'outlined' : 'filled') as 'outlined' | 'filled',
        isMarkdown: msg.role !== 'user',
        toolCalls: msg.toolCalls,
        usage: msg.usage,
        segments: segs,
        httpTraces,
        hasThinking: segs?.some(s => s.type === 'thinking' && s.text?.trim()) ?? false,
        hasToolCalls: segs?.some(s => s.type === 'tool') ?? false,
        hasAnswer: segs?.some(s => s.type === 'text' && s.text?.trim()) ?? false,
        hasHttpRequest: msg.role === 'user' && Boolean(httpTraces?.length),
        hasHttpResponse: msg.role === 'assistant' && Boolean(httpTraces?.length),
        loading:
          msg.role === 'assistant'
          && idx === arr.length - 1
          && isStreaming.value
          && !msg.content,
        avatarSize: '28px',
        avatarGap: '8px',
      }
    })
})
```

把 `MessageToolbar` 传参改成：

```vue
            <MessageToolbar
              v-if="getOriginalMessage(item.messageId) && !item.loading"
              :message="getOriginalMessage(item.messageId)!"
              :model-name="sessionModel"
              :has-thinking="item.hasThinking"
              :has-tool-calls="item.hasToolCalls"
              :has-answer="item.hasAnswer"
              :http-traces="item.httpTraces"
              :show-http-request="item.hasHttpRequest"
              :show-http-response="item.hasHttpResponse"
            />
```

- [ ] **Step 4: 重新运行两个前端契约测试**

```bash
cd frontend && npm run test:chat-http-data && npm run test:chat-http-ui
```

预期：两个契约测试都通过。

- [ ] **Step 5: 运行现有前端契约回归与构建**

```bash
cd frontend && npm run test:chat-identity && npm run build
```

预期：
- `聊天身份与思考展示契约测试通过`
- `vue-tsc --noEmit && vite build` 通过

- [ ] **Step 6: 运行后端新增测试全集**

```bash
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests_my/ai_tests/test_http_trace.py tests_my/ai_tests/test_http_trace_httpx.py tests_my/ai_tests/test_chat_http_storage.py -q
```

预期：全部通过。

- [ ] **Step 7: 提交 Task 6**

```bash
git add frontend/src/views/ChatView.vue frontend/src/components/chat/MessageToolbar.vue frontend/scripts/check-chat-http-ui-contract.mjs
git commit -m "feat: show http summaries on chat bubbles"
```

---

### Task 7: 最终整体验证

**Files:**
- Modify: none
- Test: backend + frontend commands only

- [ ] **Step 1: 运行后端回归组合**

```bash
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests_my/ai_tests/test_chat_openai_reasoning.py tests_my/ai_tests/test_http_trace.py tests_my/ai_tests/test_http_trace_httpx.py tests_my/ai_tests/test_chat_http_storage.py -q
```

预期：全部通过。

- [ ] **Step 2: 运行前端回归组合**

```bash
cd frontend && npm run test:chat-http-data && npm run test:chat-http-ui && npm run test:chat-identity && npm run build
```

预期：全部通过。

- [ ] **Step 3: 手动验收清单**

手动打开聊天页面，确认：

```text
1. 发送一条会触发上游模型调用的消息。
2. user 气泡出现“🌐 请求 HTTP”。
3. assistant 气泡出现“🌐 响应 HTTP”。
4. 点击 user 按钮，只看到 Request Headers / Request Body。
5. 点击 assistant 按钮，只看到 Response Headers / Response Body。
6. JSON body 被格式化显示。
7. Authorization / token / cookie 等被脱敏。
8. 刷新页面后，历史消息仍能看到 HTTP 按钮和摘要。
```

- [ ] **Step 4: 提交最终验证说明**

```bash
git status --short
```

预期：工作区干净；若不干净，先处理剩余文件后再进入 code review 或执行阶段。

---

## 自检结果

- **Spec coverage:** 已覆盖按钮分流、popover 展示、同轮共享 traces、全部调用顺序展示、脱敏、OpenAI-compatible 首版范围、持久化与历史回放。
- **Placeholder scan:** 无 `TODO` / `TBD` / “自行实现”类占位表述。
- **Type consistency:** 后端统一使用 `http_traces`（持久化/接口），前端统一归一化为 `httpTraces`（运行时）；请求/响应按钮字段统一为 `showHttpRequest` / `showHttpResponse`。
