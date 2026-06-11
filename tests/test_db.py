import pytest

from lc_agent.db.models import AgentPresetDB, SessionMeta
from lc_agent.db.engine import get_async_session, init_db, reset_engine
from lc_agent.db.repository import PresetRepository, SessionRepository


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


@pytest.mark.asyncio
async def test_preset_repository_crud():
    async with get_async_session("sqlite+aiosqlite:///:memory:") as session:
        repo = PresetRepository(session)

        created = await repo.create(name="Coder", system_prompt="Code", default_model="gpt-4")
        assert created.id is not None

        fetched = await repo.get_by_id(created.id)
        assert fetched.name == "Coder"

        updated = await repo.update(created.id, name="Super Coder")
        assert updated.name == "Super Coder"

        all_presets = await repo.list_all()
        assert len(all_presets) == 1

        deleted = await repo.delete(created.id)
        assert deleted is True

        all_presets = await repo.list_all()
        assert len(all_presets) == 0


@pytest.mark.asyncio
async def test_session_repository_crud():
    async with get_async_session("sqlite+aiosqlite:///:memory:") as session:
        repo = SessionRepository(session)

        created = await repo.create(title="Hello chat", agent_id="__default__", model="gpt-4")
        assert created.id is not None

        await repo.increment_messages(created.id)
        fetched = await repo.get_by_id(created.id)
        assert fetched.message_count == 1

        sessions = await repo.list_all()
        assert len(sessions) == 1

        await repo.delete(created.id)
        sessions = await repo.list_all()
        assert len(sessions) == 0
