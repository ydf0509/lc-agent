import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from lc_agent.db.engine import get_async_engine, get_async_session, reset_engine
from lc_agent.db.subagent_repository import SubAgentRunRepository


@pytest.fixture
async def db_session():
    reset_engine()
    url = "sqlite+aiosqlite:///:memory:"
    engine = get_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with get_async_session(url) as session:
        yield session
    reset_engine()


@pytest.mark.asyncio
async def test_subagent_run_repository_creates_updates_and_lists_events(db_session: AsyncSession):
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