# Chat Event Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist new chat UI messages so refreshed/history conversations restore assistant tool cards, tool results, and token usage.

**Architecture:** Add a `chat_ui_messages` SQLModel table and repository for Web UI replay data. The WebSocket handler records user messages and accumulates assistant display content, tool calls, and usage during streaming, then saves the completed assistant message. The session history route reads this UI table first, and the frontend normalizes history payloads into the same `ChatMessage` structure used by live streaming.

**Tech Stack:** Python 3.12, FastAPI, SQLModel, async SQLAlchemy, pytest, Vue 3, Pinia, TypeScript, Vite.

---

## File Structure

- Modify `lc_agent/db/models.py`: add `ChatUiMessage` table with JSON fields for `tool_calls` and `usage`.
- Modify `lc_agent/db/repository.py`: add `ChatUiMessageRepository` with `create()` and `list_by_session()`.
- Modify `lc_agent/server/routes/sessions.py`: inject DB session into history route and return UI messages when present.
- Modify `lc_agent/server/websocket.py`: accumulate assistant UI state and persist user/assistant UI messages.
- Modify `frontend/src/stores/chat.ts`: normalize persisted history payloads into `ChatMessage`.
- Modify `tests/test_db.py`: cover UI message persistence.
- Modify `tests/test_routes_sessions.py`: cover history route returning persisted UI metadata.
- Modify `tests/test_ws_events.py`: cover WebSocket handler saving user and assistant UI records.
- Create `frontend/scripts/check-chat-history-contract.mjs`: static contract test for frontend history normalization helper behavior.
- Modify `frontend/package.json`: add `test:chat-history` script.

## Task 1: DB Model And Repository

**Files:**
- Modify: `lc_agent/db/models.py`
- Modify: `lc_agent/db/repository.py`
- Modify: `tests/test_db.py`

- [ ] **Step 1: Write the failing repository test**

Add this test to `tests/test_db.py`:

```python
@pytest.mark.asyncio
async def test_chat_ui_message_repository_preserves_tool_calls_and_usage():
    async with get_async_session("sqlite+aiosqlite:///:memory:") as session:
        repo = ChatUiMessageRepository(session)

        await repo.create(session_id="thread-1", role="user", content="查一下 langgraph")
        await repo.create(
            session_id="thread-1",
            role="assistant",
            content="我查到了。\n<!--TOOL:0-->\n结论如下。",
            tool_calls=[
                {
                    "name": "nbrag_search",
                    "runId": "run-1",
                    "args": {"query": "langgraph"},
                    "status": "done",
                    "result": "LangGraph docs",
                    "duration": 12,
                    "resultLength": 14,
                }
            ],
            usage={
                "rounds": [
                    {
                        "input_tokens": 12,
                        "output_tokens": 8,
                        "total_tokens": 20,
                        "cache_read_tokens": 3,
                        "reasoning_tokens": 0,
                        "duration_ms": 1200,
                    }
                ],
                "tool_call_count": 1,
                "total_duration_ms": 1400,
            },
        )

        messages = await repo.list_by_session("thread-1")

        assert [m.role for m in messages] == ["user", "assistant"]
        assert messages[1].content == "我查到了。\n<!--TOOL:0-->\n结论如下。"
        assert messages[1].tool_calls[0]["runId"] == "run-1"
        assert messages[1].usage["rounds"][0]["total_tokens"] == 20
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_db.py::test_chat_ui_message_repository_preserves_tool_calls_and_usage -q
```

Expected: FAIL because `ChatUiMessageRepository` is not defined.

- [ ] **Step 3: Implement model and repository**

In `lc_agent/db/models.py`, add:

```python
class ChatUiMessage(SQLModel, table=True):
    __tablename__ = "chat_ui_messages"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(index=True)
    role: str
    content: str = ""
    tool_calls: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    usage: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
```

In `lc_agent/db/repository.py`, add:

```python
class ChatUiMessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        session_id: str,
        role: str,
        content: str = "",
        tool_calls: list[dict] | None = None,
        usage: dict | None = None,
    ) -> ChatUiMessage:
        message = ChatUiMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            usage=usage,
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def list_by_session(self, session_id: str) -> list[ChatUiMessage]:
        result = await self.session.execute(
            select(ChatUiMessage)
            .where(ChatUiMessage.session_id == session_id)
            .order_by(ChatUiMessage.created_at, ChatUiMessage.id)
        )
        return list(result.scalars().all())
```

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command. Expected: PASS.

## Task 2: Session History Route

**Files:**
- Modify: `lc_agent/server/routes/sessions.py`
- Modify: `tests/test_routes_sessions.py`

- [ ] **Step 1: Write the failing route test**

Add this test to `tests/test_routes_sessions.py`:

```python
@pytest.mark.asyncio
async def test_get_session_messages_returns_persisted_ui_metadata(app):
    from lc_agent.db.engine import get_async_session
    from lc_agent.db.repository import ChatUiMessageRepository

    async with get_async_session("sqlite+aiosqlite:///:memory:") as session:
        repo = ChatUiMessageRepository(session)
        await repo.create(session_id="thread-ui", role="user", content="funboost怎么样")
        await repo.create(
            session_id="thread-ui",
            role="assistant",
            content="不错。\n<!--TOOL:0-->\n适合任务队列。",
            tool_calls=[{"name": "nbrag", "runId": "run-1", "status": "done", "result": "资料"}],
            usage={"rounds": [{"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}]},
        )

    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/sessions/thread-ui/messages")

    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["role"] == "user"
    assert data[1]["role"] == "assistant"
    assert data[1]["content"] == "不错。\n<!--TOOL:0-->\n适合任务队列。"
    assert data[1]["tool_calls"][0]["runId"] == "run-1"
    assert data[1]["usage"]["rounds"][0]["total_tokens"] == 15
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_routes_sessions.py::test_get_session_messages_returns_persisted_ui_metadata -q
```

Expected: FAIL because the route still reads only LangGraph checkpoint messages.

- [ ] **Step 3: Implement route UI-message branch**

Change `get_session_messages()` to accept `db: AsyncSession = Depends(get_db_session)`, read `ChatUiMessageRepository(db).list_by_session(session_id)`, and return records when present:

```python
ui_messages = await ChatUiMessageRepository(db).list_by_session(session_id)
if ui_messages:
    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "tool_calls": msg.tool_calls or [],
            "usage": msg.usage,
            "created_at": msg.created_at.isoformat(),
        }
        for msg in ui_messages
    ]
```

Keep the existing checkpoint fallback after this branch.

- [ ] **Step 4: Run route test**

Run the same pytest command. Expected: PASS.

## Task 3: WebSocket Persistence

**Files:**
- Modify: `lc_agent/server/websocket.py`
- Modify: `tests/test_ws_events.py`

- [ ] **Step 1: Write the failing WebSocket persistence test**

Add this test to `tests/test_ws_events.py`:

```python
@pytest.mark.asyncio
async def test_handle_message_persists_user_and_assistant_ui_messages(handler):
    from lc_agent.db.engine import get_async_session, init_db, reset_engine
    from lc_agent.db.repository import ChatUiMessageRepository

    reset_engine()
    await init_db("sqlite+aiosqlite:///:memory:")
    ws = AsyncMock()

    async def fake_stream(msg, tid, pid):
        chunk = MagicMock()
        chunk.content = "先查资料。"
        chunk.additional_kwargs = {}
        yield {"event": "on_chat_model_stream", "data": {"chunk": chunk}}
        yield {
            "event": "on_tool_start",
            "name": "nbrag_search",
            "run_id": "run-1",
            "data": {"input": {"query": "funboost"}},
        }
        yield {
            "event": "on_tool_end",
            "name": "nbrag_search",
            "run_id": "run-1",
            "data": {"output": "funboost 是任务队列框架"},
        }
        output = MagicMock()
        output.usage_metadata = {
            "input_tokens": 10,
            "output_tokens": 6,
            "total_tokens": 16,
            "input_token_details": {"cache_read": 2},
        }
        yield {"event": "on_chat_model_end", "data": {"output": output}}
        chunk2 = MagicMock()
        chunk2.content = "适合异步任务。"
        chunk2.additional_kwargs = {}
        yield {"event": "on_chat_model_stream", "data": {"chunk": chunk2}}

    handler.engine.chat_stream = fake_stream

    await handler.handle_message(ws, "thread-persist", {"type": "message", "content": "funboost怎么样"})

    async with get_async_session("sqlite+aiosqlite:///:memory:") as session:
        records = await ChatUiMessageRepository(session).list_by_session("thread-persist")

    assert [r.role for r in records] == ["user", "assistant"]
    assert records[0].content == "funboost怎么样"
    assert "<!--TOOL:0-->" in records[1].content
    assert records[1].tool_calls[0]["name"] == "nbrag_search"
    assert records[1].tool_calls[0]["runId"] == "run-1"
    assert records[1].tool_calls[0]["result"] == "funboost 是任务队列框架"
    assert records[1].usage["rounds"][0]["total_tokens"] == 16
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_ws_events.py::test_handle_message_persists_user_and_assistant_ui_messages -q
```

Expected: FAIL because the WebSocket handler does not persist UI messages.

- [ ] **Step 3: Implement minimal WebSocket accumulation**

In `handle_message()`, create assistant state:

```python
assistant_content_parts: list[str] = []
assistant_tool_calls: list[dict[str, Any]] = []
assistant_in_thinking = False
stream_start_time = time.time()
```

Before streaming, save the user UI message with `ChatUiMessageRepository`.

During each event, update assistant state:

```python
assistant_in_thinking = self._accumulate_assistant_display_state(
    event,
    assistant_content_parts,
    assistant_tool_calls,
    assistant_in_thinking,
)
```

After the stream completes, save assistant UI message with:

```python
await self._save_ui_message(
    thread_id,
    "assistant",
    "".join(assistant_content_parts),
    tool_calls=assistant_tool_calls or None,
    usage={
        "rounds": usage_rounds,
        "tool_call_count": len(assistant_tool_calls),
        "total_duration_ms": int((time.time() - stream_start_time) * 1000),
    } if usage_rounds or assistant_tool_calls else None,
)
```

Add helper methods `_save_ui_message()` and `_accumulate_assistant_display_state()` to keep `handle_message()` readable.

- [ ] **Step 4: Run WebSocket persistence test**

Run the same pytest command. Expected: PASS.

## Task 4: Frontend History Normalization

**Files:**
- Modify: `frontend/src/stores/chat.ts`
- Create: `frontend/scripts/check-chat-history-contract.mjs`
- Modify: `frontend/package.json`

- [ ] **Step 1: Write the failing frontend contract test**

Create `frontend/scripts/check-chat-history-contract.mjs`:

```javascript
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const chatStore = readFileSync(join(root, 'src/stores/chat.ts'), 'utf8')
const failures = []

function expectIncludes(expected) {
  if (!chatStore.includes(expected)) failures.push(`chat.ts 缺少: ${expected}`)
}

expectIncludes('function normalizeHistoryMessage')
expectIncludes('function ensureToolMarkers')
expectIncludes('tool_calls')
expectIncludes('runId: tc.runId || tc.run_id || tc.id')
expectIncludes('usage: normalizeHistoryUsage')
expectIncludes('<!--TOOL:${idx}-->')

if (failures.length > 0) {
  console.error('聊天历史恢复契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('聊天历史恢复契约测试通过')
```

Add script:

```json
"test:chat-history": "node scripts/check-chat-history-contract.mjs"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
npm run test:chat-history
```

Expected: FAIL because the helper functions do not exist.

- [ ] **Step 3: Implement frontend normalization**

In `frontend/src/stores/chat.ts`, add pure helpers before `useChatStore`:

```typescript
function ensureToolMarkers(content: string, toolCalls?: ToolCall[]): string {
  if (!toolCalls?.length) return content
  const missingIndexes = toolCalls
    .map((_, idx) => idx)
    .filter(idx => !content.includes(`<!--TOOL:${idx}-->`))
  if (missingIndexes.length === 0) return content
  return `${content}\n${missingIndexes.map(idx => `<!--TOOL:${idx}-->`).join('\n')}\n`
}

function normalizeHistoryUsage(rawUsage: any): MessageUsage | undefined {
  if (!rawUsage) return undefined
  const rounds = (rawUsage.rounds || []).map((round: any) => ({
    inputTokens: round.inputTokens ?? round.input_tokens ?? 0,
    outputTokens: round.outputTokens ?? round.output_tokens ?? 0,
    totalTokens: round.totalTokens ?? round.total_tokens ?? 0,
    cacheReadTokens: round.cacheReadTokens ?? round.cache_read_tokens ?? 0,
    reasoningTokens: round.reasoningTokens ?? round.reasoning_tokens ?? 0,
    duration: round.duration ?? round.duration_ms,
  }))
  return {
    rounds,
    toolCallCount: rawUsage.toolCallCount ?? rawUsage.tool_call_count ?? 0,
    totalDuration: rawUsage.totalDuration ?? rawUsage.total_duration_ms,
  }
}

function normalizeHistoryMessage(msg: any): ChatMessage | null {
  const role = msg.role === 'human' ? 'user' : msg.role === 'ai' ? 'assistant' : msg.role
  if (!['user', 'assistant', 'tool'].includes(role)) return null
  const toolCalls = (msg.tool_calls || msg.toolCalls || []).map((tc: any) => ({
    name: tc.name || '',
    args: tc.args || {},
    result: tc.result,
    status: tc.status || 'done',
    duration: tc.duration,
    resultLength: tc.resultLength ?? tc.result_length ?? tc.result?.length,
  }))
  const content = ensureToolMarkers(msg.content || '', toolCalls)
  return {
    id: msg.id || crypto.randomUUID(),
    role,
    content,
    timestamp: msg.created_at ? new Date(msg.created_at).getTime() : Date.now(),
    toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
    usage: normalizeHistoryUsage(msg.usage),
  }
}
```

Change `loadMessages()` to map with `normalizeHistoryMessage()` and drop `tool` records when persisted assistant records already include tool results.

- [ ] **Step 4: Run frontend contract test**

Run the same npm command. Expected: PASS.

## Task 5: Full Verification

**Files:**
- All modified files from previous tasks.

- [ ] **Step 1: Run focused backend tests**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_db.py tests/test_routes_sessions.py tests/test_ws_events.py -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend history contract**

Run:

```powershell
npm run test:chat-history
```

Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run:

```powershell
npm run build
```

Expected: PASS.

- [ ] **Step 4: Inspect git diff**

Run:

```powershell
git diff --stat
git diff --check
```

Expected: only intended files changed; no whitespace errors.

