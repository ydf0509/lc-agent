import pytest

from lc_agent.db.models import AgentPresetDB, SessionMeta
from lc_agent.db.engine import get_async_session, init_db, reset_engine


@pytest.fixture(autouse=True)
async def setup_db():
    reset_engine()
    await init_db("sqlite+aiosqlite:///:memory:")
    yield
    reset_engine()


@pytest.mark.asyncio
async def test_create_agent_preset():
    async with get_async_session("sqlite+aiosqlite:///:memory:") as session:
        preset = AgentPresetDB(name="Test Agent", system_prompt="Hello", default_model="gpt-4")
        session.add(preset)
        await session.commit()
        await session.refresh(preset)
        assert preset.id is not None
        assert preset.name == "Test Agent"
        assert preset.created_at is not None


@pytest.mark.asyncio
async def test_create_session():
    async with get_async_session("sqlite+aiosqlite:///:memory:") as session:
        sess = SessionMeta(title="Test Chat", agent_id="__default__", model="gpt-4")
        session.add(sess)
        await session.commit()
        await session.refresh(sess)
        assert sess.id is not None
        assert sess.title == "Test Chat"
        assert sess.message_count == 0


@pytest.mark.asyncio
async def test_session_default_values():
    async with get_async_session("sqlite+aiosqlite:///:memory:") as session:
        sess = SessionMeta()
        session.add(sess)
        await session.commit()
        await session.refresh(sess)
        assert sess.title == "新对话"
        assert sess.agent_id == "__default__"
