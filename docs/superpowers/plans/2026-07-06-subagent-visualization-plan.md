# 子Agent完整可视化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 lc-agent 实现可配置、可持久化、可点击查看完整过程的子Agent调用能力。

**Architecture:** 使用 lc-agent 自己的轻量 SubAgentMiddleware 注入 `task` 工具，不整体迁移 deepagents。后端记录 `SubAgentRun` / `SubAgentEvent`，主聊天区只显示摘要卡片，点击后进入复用聊天渲染能力的子Agent过程视图。

**Tech Stack:** Python 3.12、FastAPI、SQLModel、LangChain `create_agent` middleware、LangGraph `astream_events`、Vue 3、Pinia、Element Plus、SSE。

---

## File Map

### Backend

- Modify: `lc_agent/core/models.py`
  - 给 `AgentPreset` 增加 `allowed_sub_agents`。

- Modify: `lc_agent/db/models.py`
  - 给 `AgentPresetDB` 增加 `allowed_sub_agents` JSON列。
  - 新增 `SubAgentRun` 和 `SubAgentEvent` 表。

- Modify: `lc_agent/app.py`
  - 从数据库加载 `allowed_sub_agents`。
  - 代码Agent注册时给 runnable 添加 `lc_agent_name` metadata。

- Modify: `lc_agent/server/routes/agents.py`
  - create/update/list agent API 读写 `allowed_sub_agents`。

- Create: `lc_agent/db/subagent_repository.py`
  - 封装子Agent run/event 的创建、更新、查询。

- Create: `lc_agent/core/subagents.py`
  - 实现 `SubAgentMiddleware`、`TaskInput`、`task` 工具构建、递归防护、子Agent执行与事件记录。

- Modify: `lc_agent/core/engine.py`
  - `create_agent(..., name=preset.id)`。
  - 网页/内置Agent按 `allowed_sub_agents` 注入 `SubAgentMiddleware`。
  - 代码Agent不自动注入。

- Modify: `lc_agent/server/stream_utils.py`
  - 让 `task` 工具事件可转换成 `sub_agent_call/update/done/error` 摘要事件。
  - 保留普通工具事件兼容。

- Create: `lc_agent/server/routes/subagents.py`
  - `GET /api/sub-agent-runs/{run_id}`。
  - `GET /api/sub-agent-runs/{run_id}/events`。

- Modify: `lc_agent/server/app.py`
  - 注册子Agent运行查询路由。

### Frontend

- Modify: `frontend/src/stores/agents.ts`
  - `AgentPreset` 增加 `allowed_sub_agents`。

- Modify: `frontend/src/components/dialogs/AgentEditorDialog.vue`
  - 增加“允许的子Agent”三值选择。
  - 代码Agent保持只读。

- Modify: `frontend/src/api/http.ts`
  - 增加子Agent run/events 查询 API。

- Modify: `frontend/src/api/sse-client.ts`
  - 增加子Agent摘要事件字段类型。

- Modify: `frontend/src/stores/chat.ts`
  - `ToolCall` 增加 `kind/subAgentId/subAgentName/subAgentRunId/currentStep/toolCallCount/tokenCount`。
  - 处理 `sub_agent_call/update/done/error` SSE事件。

- Create: `frontend/src/stores/subAgentRuns.ts`
  - 查询并缓存子Agent run/events。
  - 将 events 转换成聊天视图可渲染的数据结构。
  - 管理视图栈。

- Modify: `frontend/src/components/chat/ToolCallCard.vue`
  - 对 `kind === 'subagent'` 做摘要卡片渲染。
  - 提供“查看完整过程”事件。

- Create: `frontend/src/components/chat/SubAgentRunHeader.vue`
  - 子Agent过程视图顶部返回条/面包屑。

- Modify: `frontend/src/views/ChatView.vue`
  - 增加主视图 / 子Agent过程视图切换。
  - 子Agent视图复用现有消息段渲染。

### Tests

- Modify/Create backend tests under `tests/`:
  - agent route字段测试。
  - subagent repository测试。
  - subagent middleware调用测试。
  - SSE摘要事件测试。

- Modify/Create frontend contract tests under `frontend/scripts/`:
  - 检查 AgentEditorDialog、stores、SSE client、ToolCallCard、ChatView 的关键契约。

---

## Task 1: AgentPreset 增加 allowed_sub_agents

**Files:**
- Modify: `lc_agent/core/models.py`
- Modify: `lc_agent/db/models.py`
- Modify: `lc_agent/app.py`
- Modify: `lc_agent/server/routes/agents.py`
- Test: `tests/test_routes_agents.py`

- [ ] **Step 1: Write backend route test for allowed_sub_agents**

Add tests in `tests/test_routes_agents.py` covering create/list/update for `allowed_sub_agents`:

```python
async def test_agent_presets_persist_allowed_sub_agents(app_and_headers):
    app, headers = app_and_headers
    body = {
        "name": "Coordinator",
        "system_prompt": "Coordinate work.",
        "default_model": "",
        "allowed_tool_groups": [],
        "allowed_mcp_servers": [],
        "allowed_skills": [],
        "allowed_sub_agents": ["research_assistant"],
        "llm_params": None,
    }

    create_resp = await app.post("/api/agents", headers=headers, json=body)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["allowed_sub_agents"] == ["research_assistant"]

    agent_id = created["id"]
    update_resp = await app.put(
        f"/api/agents/{agent_id}",
        headers=headers,
        json={"allowed_sub_agents": []},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["allowed_sub_agents"] == []

    list_resp = await app.get("/api/agents", headers=headers)
    assert list_resp.status_code == 200
    listed = next(agent for agent in list_resp.json() if agent["id"] == agent_id)
    assert listed["allowed_sub_agents"] == []
```

- [ ] **Step 2: Run targeted test and confirm failure**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_routes_agents.py::test_agent_presets_persist_allowed_sub_agents -v
```

Expected: fails because `allowed_sub_agents` is not yet accepted/returned.

- [ ] **Step 3: Add model and DB fields**

In `lc_agent/core/models.py`, extend `AgentPreset`:

```python
allowed_sub_agents: list[str] | None = None
```

In `lc_agent/db/models.py`, extend `AgentPresetDB`:

```python
allowed_sub_agents: list[str] | None = Field(default=None, sa_column=Column(JSON))
```

- [ ] **Step 4: Thread field through app loading**

In `lc_agent/app.py`, when constructing `AgentPreset` from DB row, include:

```python
allowed_sub_agents=row.allowed_sub_agents,
```

In `add_agent()`, keep codeAgent as not configurable:

```python
allowed_sub_agents=[],
```

- [ ] **Step 5: Thread field through agent routes**

In `lc_agent/server/routes/agents.py`:

- Add to `AgentCreateRequest` and `AgentUpdateRequest`:

```python
allowed_sub_agents: list[str] | None = None
```

- Add to `_preset_to_dict()` for non-code presets:

```python
"allowed_sub_agents": p.allowed_sub_agents,
```

- Add to code preset dict:

```python
"allowed_sub_agents": [],
```

- Add to list DB row response:

```python
"allowed_sub_agents": row.allowed_sub_agents,
```

- Add to `AgentPresetDB(...)` creation:

```python
allowed_sub_agents=body.allowed_sub_agents,
```

- Add to `AgentPreset(...)` creation/update:

```python
allowed_sub_agents=preset_db.allowed_sub_agents,
```

- [ ] **Step 6: Run targeted tests**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_routes_agents.py::test_agent_presets_persist_allowed_sub_agents -v
```

Expected: pass.

---

## Task 2: 子Agent运行持久化表和仓储

**Files:**
- Modify: `lc_agent/db/models.py`
- Create: `lc_agent/db/subagent_repository.py`
- Test: `tests/test_subagent_repository.py`

- [ ] **Step 1: Write repository tests**

Create `tests/test_subagent_repository.py`:

```python
import pytest

from lc_agent.db.subagent_repository import SubAgentRunRepository


@pytest.mark.asyncio
async def test_subagent_run_repository_creates_updates_and_lists_events(db_session):
    repo = SubAgentRunRepository(db_session)

    run = await repo.create_run(
        parent_session_id="parent-session",
        parent_message_id=None,
        parent_tool_run_id="tool-run-1",
        parent_agent_id="coordinator",
        sub_agent_id="research_assistant",
        sub_agent_name="research_assistant",
        sub_thread_id="parent-session:sub:tool-run-1:research_assistant",
        task_description="研究主题",
        depth=1,
    )

    assert run.status == "running"
    assert run.sub_agent_id == "research_assistant"

    event = await repo.append_event(
        run_id=run.id,
        event_type="tool_call",
        payload={"name": "nbrag_search"},
    )
    assert event.sequence == 1

    await repo.append_event(
        run_id=run.id,
        event_type="token",
        payload={"content": "hello"},
    )

    events = await repo.list_events(run.id)
    assert [item.sequence for item in events] == [1, 2]

    updated = await repo.finish_run(
        run_id=run.id,
        status="done",
        summary="完成研究",
        final_result="最终结果",
    )
    assert updated.status == "done"
    assert updated.summary == "完成研究"
    assert updated.final_result == "最终结果"
```

- [ ] **Step 2: Run targeted test and confirm failure**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_subagent_repository.py -v
```

Expected: fails because repository and models do not exist.

- [ ] **Step 3: Add database models**

In `lc_agent/db/models.py`, add:

```python
class SubAgentRun(SQLModel, table=True):
    __tablename__ = "sub_agent_runs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    parent_session_id: str = Field(index=True)
    parent_message_id: str | None = None
    parent_tool_run_id: str = Field(index=True)
    parent_agent_id: str
    sub_agent_id: str = Field(index=True)
    sub_agent_name: str
    sub_thread_id: str = Field(index=True)
    task_description: str = ""
    status: str = Field(default="running", index=True)
    summary: str = ""
    final_result: str = ""
    depth: int = 1
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = None


class SubAgentEvent(SQLModel, table=True):
    __tablename__ = "sub_agent_events"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    run_id: str = Field(index=True)
    event_type: str = Field(index=True)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    sequence: int = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
```

- [ ] **Step 4: Implement repository**

Create `lc_agent/db/subagent_repository.py`:

```python
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from lc_agent.db.models import SubAgentEvent, SubAgentRun


def _utcnow():
    return datetime.now(timezone.utc)


class SubAgentRunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_run(
        self,
        *,
        parent_session_id: str,
        parent_message_id: str | None,
        parent_tool_run_id: str,
        parent_agent_id: str,
        sub_agent_id: str,
        sub_agent_name: str,
        sub_thread_id: str,
        task_description: str,
        depth: int,
    ) -> SubAgentRun:
        run = SubAgentRun(
            parent_session_id=parent_session_id,
            parent_message_id=parent_message_id,
            parent_tool_run_id=parent_tool_run_id,
            parent_agent_id=parent_agent_id,
            sub_agent_id=sub_agent_id,
            sub_agent_name=sub_agent_name,
            sub_thread_id=sub_thread_id,
            task_description=task_description,
            depth=depth,
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def append_event(self, *, run_id: str, event_type: str, payload: dict[str, Any]) -> SubAgentEvent:
        result = await self.session.execute(
            select(func.max(SubAgentEvent.sequence)).where(SubAgentEvent.run_id == run_id)
        )
        max_sequence = result.scalar_one_or_none() or 0
        event = SubAgentEvent(
            run_id=run_id,
            event_type=event_type,
            payload=payload,
            sequence=max_sequence + 1,
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def finish_run(self, *, run_id: str, status: str, summary: str, final_result: str) -> SubAgentRun:
        run = await self.get_run(run_id)
        if run is None:
            raise ValueError(f"SubAgentRun not found: {run_id}")
        run.status = status
        run.summary = summary
        run.final_result = final_result
        run.ended_at = _utcnow()
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: str) -> SubAgentRun | None:
        result = await self.session.execute(select(SubAgentRun).where(SubAgentRun.id == run_id))
        return result.scalar_one_or_none()

    async def list_events(self, run_id: str) -> list[SubAgentEvent]:
        result = await self.session.execute(
            select(SubAgentEvent)
            .where(SubAgentEvent.run_id == run_id)
            .order_by(SubAgentEvent.sequence.asc())
        )
        return list(result.scalars().all())
```

- [ ] **Step 5: Run repository tests**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_subagent_repository.py -v
```

Expected: pass.

---

## Task 3: 实现轻量 SubAgentMiddleware 和 task 工具

**Files:**
- Create: `lc_agent/core/subagents.py`
- Modify: `lc_agent/core/engine.py`
- Test: `tests/test_subagents.py`

- [ ] **Step 1: Write middleware behavior tests**

Create `tests/test_subagents.py` with fake runnable agents:

```python
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command

from lc_agent.core.subagents import build_subagent_task_tool


class FakeSubAgent:
    def __init__(self, content="sub result"):
        self.content = content
        self.calls = []

    async def ainvoke(self, state, config=None):
        self.calls.append((state, config))
        return {"messages": [HumanMessage(content="task"), AIMessage(content=self.content)]}


class FakeRuntime:
    tool_call_id = "tool-call-1"
    state = {"messages": []}
    config = {"configurable": {"thread_id": "parent-thread", "lc_agent_call_stack": ["parent"]}}


@pytest.mark.asyncio
async def test_task_tool_invokes_allowed_subagent_and_returns_command():
    sub_agent = FakeSubAgent("done")

    tool = build_subagent_task_tool(
        parent_agent_id="parent",
        subagents={"research": sub_agent},
        subagent_names={"research": "Research"},
        db_url="sqlite+aiosqlite:///:memory:",
        max_depth=3,
    )

    result = await tool.coroutine(
        description="研究一下",
        subagent_type="research",
        runtime=FakeRuntime(),
    )

    assert isinstance(result, Command)
    messages = result.update["messages"]
    assert isinstance(messages[0], ToolMessage)
    assert messages[0].content == "done"
    assert sub_agent.calls[0][0]["messages"][0].content == "研究一下"


@pytest.mark.asyncio
async def test_task_tool_rejects_recursive_subagent_call():
    sub_agent = FakeSubAgent("done")

    tool = build_subagent_task_tool(
        parent_agent_id="parent",
        subagents={"parent": sub_agent},
        subagent_names={"parent": "Parent"},
        db_url="sqlite+aiosqlite:///:memory:",
        max_depth=3,
    )

    result = await tool.coroutine(
        description="递归",
        subagent_type="parent",
        runtime=FakeRuntime(),
    )

    assert "循环调用" in result
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_subagents.py -v
```

Expected: fails because `lc_agent.core.subagents` does not exist.

- [ ] **Step 3: Implement core subagent tool**

Create `lc_agent/core/subagents.py` with these public APIs:

```python
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, ContextT, ModelRequest, ModelResponse, ResponseT
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import StructuredTool
from langgraph.types import Command
from pydantic import BaseModel, Field


class TaskInput(BaseModel):
    description: str = Field(description="交给子Agent独立完成的完整任务描述。")
    subagent_type: str = Field(description="要调用的子Agent ID。")


TASK_SYSTEM_PROMPT = """## `task` 子Agent工具

你可以调用 `task` 工具把复杂、独立、需要多步骤完成的任务交给子Agent。
调用时必须提供：
- `subagent_type`: 可用子Agent之一
- `description`: 完整任务描述，包括背景、目标、输出格式

只在任务确实适合委托时调用子Agent；简单问题直接自己完成。
"""


def _last_ai_text(result: dict[str, Any]) -> str:
    for message in reversed(result.get("messages", [])):
        if isinstance(message, AIMessage):
            text = message.text if hasattr(message, "text") else message.content
            if isinstance(text, str) and text.strip():
                return text.strip()
            if message.content:
                return str(message.content).strip()
    return "子Agent未返回有效结果。"


def _get_runtime_configurable(runtime: Any) -> dict[str, Any]:
    config = getattr(runtime, "config", None) or {}
    configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
    return dict(configurable)


def build_subagent_task_tool(
    *,
    parent_agent_id: str,
    subagents: Mapping[str, Runnable],
    subagent_names: Mapping[str, str],
    db_url: str,
    max_depth: int = 3,
) -> StructuredTool:
    async def task(description: str, subagent_type: str, runtime: Any) -> str | Command:
        if subagent_type not in subagents:
            allowed = ", ".join(sorted(subagents))
            return f"拒绝调用子Agent：`{subagent_type}` 不在允许列表中。可用子Agent：{allowed}"

        configurable = _get_runtime_configurable(runtime)
        call_stack = list(configurable.get("lc_agent_call_stack") or [parent_agent_id])
        if subagent_type in call_stack:
            return f"拒绝调用子Agent：检测到循环调用 {' -> '.join([*call_stack, subagent_type])}"
        if len(call_stack) >= max_depth:
            return f"拒绝调用子Agent：调用深度超过限制 {max_depth}。当前调用链：{' -> '.join(call_stack)}"

        parent_thread_id = configurable.get("thread_id", "")
        tool_call_id = getattr(runtime, "tool_call_id", None) or "unknown-tool-call"
        sub_thread_id = f"{parent_thread_id}:sub:{tool_call_id}:{subagent_type}"
        sub_config: RunnableConfig = {
            "configurable": {
                **configurable,
                "thread_id": sub_thread_id,
                "lc_agent_call_stack": [*call_stack, subagent_type],
                "ls_agent_type": "subagent",
            }
        }
        result = await subagents[subagent_type].ainvoke(
            {"messages": [HumanMessage(content=description)]},
            sub_config,
        )
        content = _last_ai_text(result)
        return Command(update={"messages": [ToolMessage(content, tool_call_id=tool_call_id)]})

    return StructuredTool.from_function(
        name="task",
        description=TASK_SYSTEM_PROMPT,
        coroutine=task,
        args_schema=TaskInput,
        infer_schema=False,
    )


class SubAgentMiddleware(AgentMiddleware[Any, ContextT, ResponseT]):
    def __init__(
        self,
        *,
        parent_agent_id: str,
        subagents: Mapping[str, Runnable],
        subagent_names: Mapping[str, str],
        db_url: str,
        max_depth: int = 3,
    ) -> None:
        super().__init__()
        self.parent_agent_id = parent_agent_id
        self.subagents = dict(subagents)
        self.subagent_names = dict(subagent_names)
        available = "\n".join(f"- {agent_id}: {subagent_names.get(agent_id, agent_id)}" for agent_id in self.subagents)
        self.system_prompt = f"{TASK_SYSTEM_PROMPT}\n\n可用子Agent：\n{available}"
        self.tools = [
            build_subagent_task_tool(
                parent_agent_id=parent_agent_id,
                subagents=self.subagents,
                subagent_names=self.subagent_names,
                db_url=db_url,
                max_depth=max_depth,
            )
        ]

    def wrap_model_call(self, request: ModelRequest[ContextT], handler):
        if request.system_message is not None:
            content = [*request.system_message.content_blocks, {"type": "text", "text": f"\n\n{self.system_prompt}"}]
        else:
            content = [{"type": "text", "text": self.system_prompt}]
        return handler(request.override(system_message=SystemMessage(content=content)))

    async def awrap_model_call(self, request: ModelRequest[ContextT], handler):
        if request.system_message is not None:
            content = [*request.system_message.content_blocks, {"type": "text", "text": f"\n\n{self.system_prompt}"}]
        else:
            content = [{"type": "text", "text": self.system_prompt}]
        return await handler(request.override(system_message=SystemMessage(content=content)))
```

- [ ] **Step 4: Run subagent core tests**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_subagents.py -v
```

Expected: pass.

---

## Task 4: AgentEngine 注入子Agent middleware

**Files:**
- Modify: `lc_agent/core/engine.py`
- Modify: `lc_agent/app.py`
- Test: `tests/test_engine.py`
- Test: `tests/test_custom_agents.py`

- [ ] **Step 1: Add tests for `create_agent(name=preset.id)` and code agent metadata wrapping**

Add tests verifying:

```python
def test_build_agent_passes_preset_id_as_langchain_agent_name(monkeypatch):
    captured = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("langchain.agents.create_agent", fake_create_agent)
    engine = AgentEngine({"agent": {"default_model": "model-a"}, "provider": {}})
    preset = AgentPreset(id="planner", name="Planner", system_prompt="Plan", default_model="model-a")

    engine.build_agent(preset)

    assert captured["name"] == "planner"
```

Add a custom agent registration test that checks registered graph has `lc_agent_name` metadata if runnable supports `.with_config()`.

- [ ] **Step 2: Run targeted tests and confirm failure**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_engine.py tests/test_custom_agents.py -k "agent_name or custom" -v
```

Expected: fail until implementation.

- [ ] **Step 3: Add `name=preset.id` to create_agent**

In `AgentEngine.build_agent()`, change create_agent call:

```python
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt,
    middleware=middleware,
    name=preset.id,
    **kwargs,
)
```

- [ ] **Step 4: Wrap code agents with metadata**

In `LcAgentApp.add_agent()`, before assigning to `_agents`:

```python
if hasattr(graph, "with_config"):
    graph = graph.with_config({"metadata": {"lc_agent_name": name}, "run_name": name})
```

- [ ] **Step 5: Build allowed subagent map in AgentEngine**

Add methods to `AgentEngine`:

```python
def _allowed_subagent_ids(self, preset: AgentPreset) -> list[str]:
    if preset.allowed_sub_agents == []:
        return []
    all_ids = [p.id for p in self.get_presets() if p.id != preset.id]
    if preset.allowed_sub_agents is None:
        return all_ids
    return [agent_id for agent_id in preset.allowed_sub_agents if agent_id in all_ids and agent_id != preset.id]


def _build_subagent_middleware(self, preset: AgentPreset):
    if preset.source == "code":
        return None
    ids = self._allowed_subagent_ids(preset)
    if not ids:
        return None
    from lc_agent.core.subagents import SubAgentMiddleware
    subagents = {agent_id: self._get_or_build_agent(agent_id) for agent_id in ids}
    names = {agent_id: self._resolve_preset(agent_id).name for agent_id in ids}
    db_url = self.config.get("database", {}).get("url", "sqlite+aiosqlite:///./lc_agent_data.db")
    return SubAgentMiddleware(
        parent_agent_id=preset.id,
        subagents=subagents,
        subagent_names=names,
        db_url=db_url,
        max_depth=self.config.get("agent", {}).get("max_subagent_depth", 3),
    )
```

- [ ] **Step 6: Append middleware only for non-code agents**

In `build_agent()` after summarization middleware:

```python
subagent_middleware = self._build_subagent_middleware(preset)
if subagent_middleware is not None:
    middleware.append(subagent_middleware)
```

- [ ] **Step 7: Run targeted backend tests**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_engine.py tests/test_custom_agents.py tests/test_subagents.py -v
```

Expected: pass.

---

## Task 5: 子Agent运行事件持久化和摘要事件

**Files:**
- Modify: `lc_agent/core/subagents.py`
- Modify: `lc_agent/server/stream_utils.py`
- Test: `tests/test_subagents.py`
- Test: `tests/test_ws_events.py` or new `tests/test_stream_utils_subagents.py`

- [ ] **Step 1: Add tests for subagent summary event conversion**

Create `tests/test_stream_utils_subagents.py`:

```python
from lc_agent.server.stream_utils import convert_stream_event


def test_task_tool_start_converts_to_subagent_call_summary():
    event = {
        "event": "on_tool_start",
        "name": "task",
        "run_id": "tool-run-1",
        "data": {"input": {"subagent_type": "research", "description": "研究主题"}},
    }

    converted = convert_stream_event(event)

    assert converted[0][0] == "sub_agent_call"
    payload = converted[0][1]
    assert payload["parent_tool_run_id"] == "tool-run-1"
    assert payload["sub_agent_id"] == "research"
    assert payload["task_description"] == "研究主题"
    assert payload["status"] == "running"
```

- [ ] **Step 2: Run test and confirm failure**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_stream_utils_subagents.py -v
```

Expected: fails because `task` still converts to normal `tool_call`.

- [ ] **Step 3: Convert task tool events to subAgent summary events**

In `stream_utils.convert_stream_event()`:

For `on_tool_start` where `tool_name == "task"` and input has `subagent_type`, append:

```python
results.append(("sub_agent_call", {
    "parent_tool_run_id": event.get("run_id", ""),
    "sub_agent_id": tool_input.get("subagent_type", ""),
    "sub_agent_name": tool_input.get("subagent_type", ""),
    "task_description": tool_input.get("description", ""),
    "status": "running",
    "depth": 1,
}))
```

For `on_tool_end` where `tool_name == "task"`, append:

```python
results.append(("sub_agent_done", {
    "parent_tool_run_id": event.get("run_id", ""),
    "status": "done",
    "summary": result_str[:200],
    "final_result": result_str,
}))
```

Keep existing normal `tool_call/tool_result` behavior if the event is not `task`.

- [ ] **Step 4: Persist subagent events inside task tool**

Enhance `build_subagent_task_tool()`:

- Create a DB session via `get_async_session(db_url)`.
- Use `SubAgentRunRepository` to create run before invocation.
- Iterate `subagent.astream_events(...)` instead of only `ainvoke(...)`.
- Append converted events to `SubAgentEvent`.
- Accumulate final state or final AI text.
- Finish run as `done` or `error`.

Implementation shape:

```python
async for event in subagents[subagent_type].astream_events(
    {"messages": [HumanMessage(content=description)]},
    config=sub_config,
    version="v2",
):
    await repo.append_event(run_id=run.id, event_type=event.get("event", ""), payload=_json_safe_event(event))
```

Use a helper `_json_safe_event(event)` that stores simple JSON-safe fields: `event`, `name`, `run_id`, `data` converted to strings where needed.

- [ ] **Step 5: Run tests**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_subagents.py tests/test_stream_utils_subagents.py -v
```

Expected: pass.

---

## Task 6: 子Agent查询 API

**Files:**
- Create: `lc_agent/server/routes/subagents.py`
- Modify: `lc_agent/server/app.py`
- Test: `tests/test_routes_subagents.py`

- [ ] **Step 1: Write route tests**

Create `tests/test_routes_subagents.py`:

```python
import pytest

from lc_agent.db.subagent_repository import SubAgentRunRepository


@pytest.mark.asyncio
async def test_get_subagent_run_and_events(app_and_headers, db_session):
    app, headers = app_and_headers
    repo = SubAgentRunRepository(db_session)
    run = await repo.create_run(
        parent_session_id="session-1",
        parent_message_id=None,
        parent_tool_run_id="tool-1",
        parent_agent_id="main",
        sub_agent_id="research",
        sub_agent_name="Research",
        sub_thread_id="session-1:sub:tool-1:research",
        task_description="研究主题",
        depth=1,
    )
    await repo.append_event(run_id=run.id, event_type="token", payload={"content": "hello"})

    run_resp = await app.get(f"/api/sub-agent-runs/{run.id}", headers=headers)
    assert run_resp.status_code == 200
    assert run_resp.json()["id"] == run.id

    events_resp = await app.get(f"/api/sub-agent-runs/{run.id}/events", headers=headers)
    assert events_resp.status_code == 200
    assert events_resp.json()["events"][0]["event_type"] == "token"
```

- [ ] **Step 2: Run test and confirm failure**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_routes_subagents.py -v
```

Expected: fails because route does not exist.

- [ ] **Step 3: Implement routes**

Create `lc_agent/server/routes/subagents.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Request

from lc_agent.db.engine import get_async_session as _get_db_session
from lc_agent.db.subagent_repository import SubAgentRunRepository
from lc_agent.server.auth_middleware import get_current_user

router = APIRouter(tags=["sub-agents"])


async def get_db(request: Request):
    db_url = request.app.state.config.get("database", {}).get("url", "sqlite+aiosqlite:///./lc_agent_data.db")
    session = _get_db_session(db_url)
    try:
        yield session
    finally:
        await session.close()


@router.get("/sub-agent-runs/{run_id}")
async def get_subagent_run(run_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    repo = SubAgentRunRepository(db)
    run = await repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="SubAgentRun not found")
    return run


@router.get("/sub-agent-runs/{run_id}/events")
async def get_subagent_events(run_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    repo = SubAgentRunRepository(db)
    run = await repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="SubAgentRun not found")
    events = await repo.list_events(run_id)
    return {"run": run, "events": events}
```

- [ ] **Step 4: Register router**

In `lc_agent/server/app.py`, import and include:

```python
from lc_agent.server.routes.subagents import router as subagents_router
app.include_router(subagents_router, prefix="/api")
```

- [ ] **Step 5: Run route tests**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_routes_subagents.py -v
```

Expected: pass.

---

## Task 7: 前端 agent 配置支持 allowed_sub_agents

**Files:**
- Modify: `frontend/src/stores/agents.ts`
- Modify: `frontend/src/components/dialogs/AgentEditorDialog.vue`
- Modify: `frontend/scripts/check-chat-edit-contract.mjs`

- [ ] **Step 1: Add contract checks**

In `frontend/scripts/check-chat-edit-contract.mjs`, add checks:

```js
expectIncludes('agents.ts', files.agentsStore, 'allowed_sub_agents: string[] | null')
expectIncludes('AgentEditorDialog.vue', files.agentEditor, '允许的子Agent')
expectIncludes('AgentEditorDialog.vue', files.agentEditor, 'subAgentMode')
expectIncludes('AgentEditorDialog.vue', files.agentEditor, 'selectedSubAgents')
```

- [ ] **Step 2: Run contract and confirm failure**

Run:

```powershell
cd D:\codes\lc-agent\frontend
npm run check:chat-edit-contract
```

Expected: fails until frontend code is updated.

- [ ] **Step 3: Update AgentPreset type**

In `frontend/src/stores/agents.ts`, add:

```ts
allowed_sub_agents: string[] | null
```

- [ ] **Step 4: Add editor state**

In `AgentEditorDialog.vue`, add refs:

```ts
const subAgentMode = ref<'all' | 'none' | 'custom'>('none')
const selectedSubAgents = ref<string[]>([])
```

- [ ] **Step 5: Add UI block**

Add form item after Skills:

```vue
<el-form-item label="允许的子Agent">
  <div class="tool-group-select">
    <el-radio-group v-model="subAgentMode" size="small">
      <el-radio-button value="all">全部</el-radio-button>
      <el-radio-button value="none">无</el-radio-button>
      <el-radio-button value="custom">自定义</el-radio-button>
    </el-radio-group>
    <div v-if="subAgentMode === 'custom'" class="custom-groups">
      <el-checkbox-group v-model="selectedSubAgents">
        <el-checkbox
          v-for="agent in agentsStore.agents.filter(a => a.id !== editingId)"
          :key="agent.id"
          :value="agent.id"
        >
          {{ agent.name }}
          <el-tag size="small" style="margin-left:4px">{{ agent.source }}</el-tag>
        </el-checkbox>
      </el-checkbox-group>
    </div>
  </div>
</el-form-item>
```

- [ ] **Step 6: Read/write form values**

In `open(agent)`, initialize:

```ts
if (agent.allowed_sub_agents === null) {
  subAgentMode.value = 'all'
  selectedSubAgents.value = []
} else if (agent.allowed_sub_agents.length === 0) {
  subAgentMode.value = 'none'
  selectedSubAgents.value = []
} else {
  subAgentMode.value = 'custom'
  selectedSubAgents.value = [...agent.allowed_sub_agents]
}
```

For new agent default:

```ts
subAgentMode.value = 'none'
selectedSubAgents.value = []
```

In `handleSave()`:

```ts
const allowed_sub_agents =
  subAgentMode.value === 'all' ? null :
  subAgentMode.value === 'none' ? [] :
  selectedSubAgents.value
```

Add to `data`:

```ts
allowed_sub_agents,
```

- [ ] **Step 7: Run frontend contract**

Run:

```powershell
cd D:\codes\lc-agent\frontend
npm run check:chat-edit-contract
```

Expected: pass.

---

## Task 8: 前端子Agent摘要卡片

**Files:**
- Modify: `frontend/src/api/sse-client.ts`
- Modify: `frontend/src/stores/chat.ts`
- Modify: `frontend/src/components/chat/ToolCallCard.vue`
- Test: `frontend/scripts/check-chat-edit-contract.mjs`

- [ ] **Step 1: Add contract checks for subAgent events**

Add checks:

```js
expectIncludes('sse-client.ts', files.sseClient, 'sub_agent_call')
expectIncludes('chat.ts', files.chatStore, 'subAgentRunId?: string')
expectIncludes('ToolCallCard.vue', files.toolCallCard, '子Agent调用')
expectIncludes('ToolCallCard.vue', files.toolCallCard, '查看完整过程')
```

- [ ] **Step 2: Update SSE message type**

In `frontend/src/api/sse-client.ts`, add optional fields:

```ts
parent_tool_run_id?: string
sub_agent_id?: string
sub_agent_name?: string
task_description?: string
status?: string
current_step?: string
tool_call_count?: number
token_count?: number
summary?: string
final_result?: string
```

- [ ] **Step 3: Update ToolCall type**

In `frontend/src/stores/chat.ts`, extend `ToolCall`:

```ts
kind?: 'tool' | 'subagent'
subAgentRunId?: string
subAgentId?: string
subAgentName?: string
taskDescription?: string
currentStep?: string
toolCallCount?: number
tokenCount?: number
summary?: string
```

- [ ] **Step 4: Handle sub_agent_call/update/done/error**

In chat store SSE handler, add logic:

```ts
function upsertSubAgentToolCall(msg: SseMessage, status: ToolCall['status']) {
  const assistant = ensureAssistantMessage()
  const existing = assistant.toolCalls?.find(tc => tc.runId === msg.parent_tool_run_id)
  const toolCall: ToolCall = existing || {
    name: 'task',
    runId: msg.parent_tool_run_id,
    args: { description: msg.task_description, subagent_type: msg.sub_agent_id },
    status,
    kind: 'subagent',
    subAgentRunId: msg.run_id,
    subAgentId: msg.sub_agent_id,
    subAgentName: msg.sub_agent_name || msg.sub_agent_id,
    taskDescription: msg.task_description,
    startTime: Date.now(),
  }
  toolCall.status = status
  toolCall.currentStep = msg.current_step || toolCall.currentStep
  toolCall.toolCallCount = msg.tool_call_count ?? toolCall.toolCallCount
  toolCall.tokenCount = msg.token_count ?? toolCall.tokenCount
  toolCall.summary = msg.summary || toolCall.summary
  if (!existing) assistant.toolCalls = [...(assistant.toolCalls || []), toolCall]
}
```

Wire events:

```ts
sseClient.on('sub_agent_call', msg => upsertSubAgentToolCall(msg, 'running'))
sseClient.on('sub_agent_update', msg => upsertSubAgentToolCall(msg, 'running'))
sseClient.on('sub_agent_done', msg => upsertSubAgentToolCall(msg, 'done'))
sseClient.on('sub_agent_error', msg => upsertSubAgentToolCall(msg, 'error'))
```

- [ ] **Step 5: Render subAgent card variant**

In `ToolCallCard.vue`, conditionally render when `toolCall.kind === 'subagent'`:

```vue
<span class="tool-kind">
  <el-icon><Cpu /></el-icon>
  子Agent调用
</span>
<span class="tool-name">{{ toolCall.subAgentName || toolCall.subAgentId }}</span>
```

Add task/current step block:

```vue
<div v-if="toolCall.kind === 'subagent'" class="subagent-summary">
  <div class="subagent-task">任务：{{ toolCall.taskDescription }}</div>
  <div v-if="toolCall.currentStep" class="subagent-step">当前步骤：{{ toolCall.currentStep }}</div>
  <div class="subagent-stats">
    <span v-if="toolCall.toolCallCount != null">工具调用：{{ toolCall.toolCallCount }} 次</span>
    <span v-if="toolCall.tokenCount != null">Tokens：{{ toolCall.tokenCount }}</span>
  </div>
  <button class="view-subagent-btn" @click.stop="$emit('view-subagent', toolCall)">查看完整过程</button>
</div>
```

- [ ] **Step 6: Run frontend contract**

Run:

```powershell
cd D:\codes\lc-agent\frontend
npm run check:chat-edit-contract
```

Expected: pass.

---

## Task 9: 子Agent过程视图 Store 和 API

**Files:**
- Modify: `frontend/src/api/http.ts`
- Create: `frontend/src/stores/subAgentRuns.ts`

- [ ] **Step 1: Add API methods**

In `frontend/src/api/http.ts`:

```ts
getSubAgentRun: (id: string) => fetchApi<any>(`/sub-agent-runs/${id}`),
getSubAgentRunEvents: (id: string) => fetchApi<{ run: any; events: any[] }>(`/sub-agent-runs/${id}/events`),
```

- [ ] **Step 2: Create subAgentRuns store**

Create `frontend/src/stores/subAgentRuns.ts`:

```ts
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/api/http'
import type { ChatMessage, ToolCall } from '@/stores/chat'
import { createClientId } from '@/utils/client-id'

export interface SubAgentViewEntry {
  runId: string
  subAgentId: string
  subAgentName: string
  taskDescription: string
}

export const useSubAgentRunsStore = defineStore('subAgentRuns', () => {
  const viewStack = ref<SubAgentViewEntry[]>([])
  const runs = ref<Record<string, any>>({})
  const messagesByRun = ref<Record<string, ChatMessage[]>>({})
  const loading = ref(false)

  const currentView = computed(() => viewStack.value[viewStack.value.length - 1] || null)
  const isInSubAgentView = computed(() => !!currentView.value)
  const currentMessages = computed(() => currentView.value ? messagesByRun.value[currentView.value.runId] || [] : [])

  async function openRun(toolCall: ToolCall) {
    if (!toolCall.subAgentRunId) return
    loading.value = true
    try {
      const response = await api.getSubAgentRunEvents(toolCall.subAgentRunId)
      runs.value[toolCall.subAgentRunId] = response.run
      messagesByRun.value[toolCall.subAgentRunId] = eventsToMessages(response.events)
      viewStack.value.push({
        runId: toolCall.subAgentRunId,
        subAgentId: toolCall.subAgentId || response.run.sub_agent_id,
        subAgentName: toolCall.subAgentName || response.run.sub_agent_name,
        taskDescription: toolCall.taskDescription || response.run.task_description,
      })
    } finally {
      loading.value = false
    }
  }

  function back() {
    viewStack.value.pop()
  }

  function clear() {
    viewStack.value = []
  }

  function eventsToMessages(events: any[]): ChatMessage[] {
    const assistant: ChatMessage = {
      id: createClientId(),
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      toolCalls: [],
    }
    const contentParts: string[] = []
    for (const event of events) {
      const payload = event.payload || {}
      if (event.event_type === 'token') contentParts.push(payload.content || '')
      if (event.event_type === 'thinking') {
        contentParts.push('<!--THINK_START-->')
        contentParts.push(payload.content || '')
        contentParts.push('<!--THINK_END-->')
      }
      if (event.event_type === 'tool_call') {
        const index = assistant.toolCalls!.length
        assistant.toolCalls!.push({
          name: payload.name || '',
          runId: payload.run_id,
          args: payload.args || {},
          status: 'running',
        })
        contentParts.push(`\n<!--TOOL:${index}-->\n`)
      }
      if (event.event_type === 'tool_result') {
        const tool = [...assistant.toolCalls!].reverse().find(item => item.status === 'running')
        if (tool) {
          tool.status = 'done'
          tool.result = payload.result || ''
          tool.resultLength = tool.result.length
        }
      }
    }
    assistant.content = contentParts.join('')
    return [
      {
        id: createClientId(),
        role: 'user',
        content: currentView.value?.taskDescription || '',
        timestamp: Date.now(),
      },
      assistant,
    ]
  }

  return { viewStack, runs, loading, currentView, isInSubAgentView, currentMessages, openRun, back, clear }
})
```

- [ ] **Step 3: Run typecheck/build later with all frontend changes**

No standalone command yet; this store depends on later ChatView wiring.

---

## Task 10: ChatView 切换子Agent过程视图

**Files:**
- Create: `frontend/src/components/chat/SubAgentRunHeader.vue`
- Modify: `frontend/src/views/ChatView.vue`
- Modify: `frontend/src/components/chat/ToolCallCard.vue`

- [ ] **Step 1: Create header component**

Create `frontend/src/components/chat/SubAgentRunHeader.vue`:

```vue
<template>
  <div class="subagent-run-header">
    <button class="back-btn" type="button" @click="$emit('back')">← 返回</button>
    <div class="subagent-title">
      <div class="breadcrumb">{{ breadcrumb }}</div>
      <div class="task">{{ taskDescription }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  names: string[]
  taskDescription: string
}>()

defineEmits<{ back: [] }>()

const breadcrumb = computed(() => ['主Agent', ...props.names].join(' / '))
</script>

<style scoped>
.subagent-run-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
}
.back-btn {
  border: none;
  background: transparent;
  color: var(--el-color-primary);
  cursor: pointer;
}
.subagent-title {
  min-width: 0;
}
.breadcrumb {
  font-size: 13px;
  font-weight: 600;
}
.task {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
```

- [ ] **Step 2: Emit view-subagent from ToolCallCard**

In `ToolCallCard.vue`:

```ts
const emit = defineEmits<{ 'view-subagent': [toolCall: ToolCall] }>()
```

Use:

```vue
<button class="view-subagent-btn" @click.stop="emit('view-subagent', toolCall)">查看完整过程</button>
```

- [ ] **Step 3: Wire ChatView to subAgentRuns store**

In `ChatView.vue` import:

```ts
import { useSubAgentRunsStore } from '@/stores/subAgentRuns'
import SubAgentRunHeader from '@/components/chat/SubAgentRunHeader.vue'
```

Setup:

```ts
const subAgentRunsStore = useSubAgentRunsStore()
const displayedMessages = computed(() => subAgentRunsStore.isInSubAgentView ? subAgentRunsStore.currentMessages : messages.value)
```

Update `bubbleList` to use `displayedMessages.value` instead of `messages.value`.

Render header above BubbleList:

```vue
<SubAgentRunHeader
  v-if="subAgentRunsStore.currentView"
  :names="subAgentRunsStore.viewStack.map(item => item.subAgentName)"
  :task-description="subAgentRunsStore.currentView.taskDescription"
  @back="subAgentRunsStore.back"
/>
```

In `ToolCallCard` usage:

```vue
<ToolCallCard
  :tool-call="item.toolCalls[seg.toolIndex!]"
  :collapsed="item.toolCalls[seg.toolIndex!]?.status === 'done'"
  @view-subagent="subAgentRunsStore.openRun"
/>
```

Hide ChatInput while in subAgent view:

```vue
<ChatInput
  v-if="!subAgentRunsStore.isInSubAgentView"
  ...
/>
```

- [ ] **Step 4: Build frontend**

Run:

```powershell
cd D:\codes\lc-agent\frontend
npm run build
```

Expected: build succeeds.

---

## Task 11: Full backend verification

**Files:**
- No new files unless tests reveal targeted fixes.

- [ ] **Step 1: Run Python compile**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m py_compile lc_agent\core\models.py lc_agent\db\models.py lc_agent\db\subagent_repository.py lc_agent\core\subagents.py lc_agent\core\engine.py lc_agent\app.py lc_agent\server\routes\agents.py lc_agent\server\routes\subagents.py lc_agent\server\stream_utils.py lc_agent\server\app.py
```

Expected: exit code 0.

- [ ] **Step 2: Run targeted backend tests**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_routes_agents.py tests/test_subagent_repository.py tests/test_subagents.py tests/test_stream_utils_subagents.py tests/test_routes_subagents.py -v
```

Expected: pass.

- [ ] **Step 3: Run broader backend tests likely affected by agent/session paths**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_engine.py tests/test_custom_agents.py tests/test_routes_sessions.py tests/test_ws_events.py -v
```

Expected: pass or only unrelated pre-existing failures.

---

## Task 12: Frontend verification and bfzs restart

**Files:**
- No new files unless verification reveals targeted fixes.

- [ ] **Step 1: Run frontend contract**

Run:

```powershell
cd D:\codes\lc-agent\frontend
npm run check:chat-edit-contract
```

Expected: pass.

- [ ] **Step 2: Run frontend build**

Run:

```powershell
cd D:\codes\lc-agent\frontend
npm run build
```

Expected: build succeeds and outputs to `lc_agent/web/dist`.

- [ ] **Step 3: Restart bfzs with project skill script**

Run:

```powershell
D:\codes\lc-agent\.agents\skills\restart-bfzs\scripts\restart.ps1
```

Expected: frontend build succeeds, bfzs backend restarts on port `8001`.

- [ ] **Step 4: Manual smoke test**

Use browser:

1. Login `admin / 123456`.
2. Create a webpage Agent named `Research Caller`.
3. Configure allowed subAgents to include code agent `research_assistant` if registered by bfzs.
4. Start a new session with `Research Caller`.
5. Ask it to delegate a task to `research_assistant`.
6. Verify main chat shows only a subAgent summary card.
7. Click “查看完整过程”。
8. Verify subAgent process view opens and displays events.
9. Refresh page and verify the same card still opens historical process.

---

## Self-Review Checklist

- Spec coverage:
  - `allowed_sub_agents`: Task 1, Task 7.
  - CodeAgent boundary: Task 4.
  - `task` tool and middleware: Task 3, Task 4.
  - Persistence: Task 2, Task 5, Task 6.
  - SSE summary events: Task 5, Task 8.
  - Frontend card: Task 8.
  - Full process view: Task 9, Task 10.
  - Verification/restart: Task 11, Task 12.

- Placeholder scan:
  - No `TBD` or vague “handle later” items remain.

- Type consistency:
  - Backend uses `allowed_sub_agents` snake_case consistently.
  - Frontend API payload keeps server snake_case and maps into TS camelCase for runtime fields.
  - `subAgentRunId` maps to SSE/API `run_id`.

---

## Execution Notes

- Do not delete bfzs DB files without explicit user approval.
- Do not auto-inject subAgent tools into code-registered agents.
- Keep first implementation focused on confirmed spec; do not add voice/multimodal/cost features.
- After backend or frontend changes, restart bfzs using `D:\codes\lc-agent\.agents\skills\restart-bfzs\scripts\restart.ps1`.
