import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from lc_agent.core.subagents import build_subagent_task_tool
from lc_agent.db.engine import get_async_engine, reset_engine


class FakeSubAgent:
    def __init__(self, content="sub result"):
        self.content = content
        self.calls = []

    async def ainvoke(self, state, config=None):
        self.calls.append((state, config))
        return {"messages": [HumanMessage(content="task"), AIMessage(content=self.content)]}

    async def astream_events(self, state, config=None, version="v2", **kwargs):
        self.calls.append((state, config))
        yield {"event": "on_chat_model_start", "name": "FakeModel", "data": {}, "run_id": "run-1"}
        yield {
            "event": "on_chat_model_stream",
            "name": "FakeModel",
            "data": {"chunk": AIMessage(content=self.content)},
            "run_id": "run-1",
        }
        yield {
            "event": "on_chat_model_end",
            "name": "FakeModel",
            "data": {"output": AIMessage(content=self.content)},
            "run_id": "run-1",
        }


class FakeRuntime:
    tool_call_id = "tool-call-1"
    state = {"messages": []}
    config = {"configurable": {"thread_id": "parent-thread", "lc_agent_call_stack": ["parent"]}}


@pytest.fixture
async def memory_db():
    reset_engine()
    url = "sqlite+aiosqlite:///:memory:"
    engine = get_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    return url


@pytest.mark.asyncio
async def test_task_tool_invokes_allowed_subagent_and_returns_command(memory_db):
    sub_agent = FakeSubAgent("done")

    tool = build_subagent_task_tool(
        parent_agent_id="parent",
        subagents={"research": sub_agent},
        subagent_names={"research": "Research"},
        db_url=memory_db,
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