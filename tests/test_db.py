import pytest

from lc_agent.db.models import AgentPresetDB, SessionMeta
from lc_agent.db.engine import get_async_session, init_db, reset_engine
from lc_agent.db.repository import ChatUiMessageRepository, PresetRepository, SessionRepository


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
        assert sess.agent_id == "__chat__"


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


@pytest.mark.asyncio
async def test_chat_ui_message_repository_truncates_from_message_id():
    async with get_async_session("sqlite+aiosqlite:///:memory:") as session:
        repo = ChatUiMessageRepository(session)

        kept = await repo.create(session_id="thread-edit", role="user", content="第一问")
        edited = await repo.create(session_id="thread-edit", role="user", content="第二问旧内容")
        await repo.create(session_id="thread-edit", role="assistant", content="旧回答")
        await repo.create(session_id="other-thread", role="user", content="别的会话")

        deleted = await repo.truncate_from_message("thread-edit", edited.id)
        messages = await repo.list_by_session("thread-edit")
        other_messages = await repo.list_by_session("other-thread")

        assert deleted == 2
        assert [m.id for m in messages] == [kept.id]
        assert [m.content for m in other_messages] == ["别的会话"]
