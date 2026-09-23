from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from lc_agent.app import LcAgentApp
from lc_agent.db.engine import init_db, reset_engine
from lc_agent.tools.registry import ToolRegistry
from tests.conftest import setup_test_auth


@pytest.fixture(autouse=True)
async def setup(tmp_path):
    ToolRegistry._global_tools = {}
    ToolRegistry._group_descriptions = {}
    ToolRegistry._instance = None
    reset_engine()
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    await init_db(db_url)
    yield db_url
    ToolRegistry._global_tools = {}
    ToolRegistry._group_descriptions = {}
    ToolRegistry._instance = None
    reset_engine()


@pytest.fixture
async def app_and_headers(setup):
    db_url = setup
    config = {
        "provider": {"openai": {"base_url": "http://fake", "api_key": "sk-fake", "models": [{"model_id": "gpt-4", "raw_model_id": "gpt-4"}]}},
        "agent": {"default_model": "gpt-4", "system_prompt": "Test"},
        "database": {"url": db_url, "checkpoint_path": ":memory:"},
    }
    app = LcAgentApp(config)
    headers = await setup_test_auth(app.fastapi_app)
    return app, headers


@pytest.mark.asyncio
async def test_manual_compaction_rewrites_checkpoint(app_and_headers):
    """手动压缩：重写 checkpoint 线程（摘要+保留尾部），业务库不受影响；keep 覆盖参数生效。"""
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.checkpoint.memory import InMemorySaver

    app, headers = app_and_headers
    app.engine._checkpointer = InMemorySaver()

    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            "/api/sessions", json={"title": "C", "model": "gpt-4"}, headers=headers
        )
        session_id = create_resp.json()["id"]

        agent = app.engine._get_or_build_agent("chat", "gpt-4")
        config = {"configurable": {"thread_id": session_id}}
        msgs = []
        for i in range(6):
            msgs.append(HumanMessage(content=f"question {i}"))
            msgs.append(AIMessage(content=f"answer {i}"))
        await agent.aupdate_state(config, {"messages": msgs})

        # keep="2" → 只留最近 2 条 checkpoint 消息，其余 10 条进摘要
        resp = await client.post(
            f"/api/sessions/{session_id}/compact", json={"keep": "2"}, headers=headers
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["compacted"] is True
        assert data["summarized_count"] == 10
        assert data["kept_count"] == 2
        assert data["kept_user_count"] == 1
        # 压缩前后 checkpoint 估算（水位条“预估·待更新”用）：压缩后必须小于压缩前
        before = data["checkpoint_tokens_before"]
        after = data["checkpoint_tokens_after"]
        assert isinstance(before, int) and isinstance(after, int)
        assert 0 < after < before

        state = await agent.aget_state(config)
        new_msgs = state.values["messages"]
        assert len(new_msgs) == 3  # 摘要 + question 5 + answer 5
        assert "summary" in str(new_msgs[0].content).lower()
        assert new_msgs[1].content == "question 5"
        assert new_msgs[2].content == "answer 5"

        # 不带 keep（走配置默认 fraction）时消息量在保留范围内 → 409 无需压缩
        resp = await client.post(
            f"/api/sessions/{session_id}/compact", json={}, headers=headers
        )
        assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_and_list_sessions(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/sessions", json={"title": "Test Chat", "model": "gpt-4"}, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Chat"
        assert "id" in data

        list_resp = await client.get("/api/sessions", headers=headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1


@pytest.mark.asyncio
async def test_list_sessions_sidebar_window_does_not_hide_other_agents(app_and_headers):
    app, headers = app_and_headers
    from lc_agent.db.engine import get_async_session
    from lc_agent.db.models import SessionMeta

    db_url = app.config["database"]["url"]
    now = datetime.now(timezone.utc)
    async with get_async_session(db_url) as session:
        for index in range(55):
            session.add(SessionMeta(
                id=f"agent-a-{index}",
                title=f"Agent A {index}",
                agent_id="agent-a",
                user_id="test-admin",
                updated_at=now - timedelta(minutes=index),
            ))
        session.add(SessionMeta(
            id="agent-b-recent",
            title="Agent B recent",
            agent_id="agent-b",
            user_id="test-admin",
            updated_at=now,
        ))
        session.add(SessionMeta(
            id="agent-b-old",
            title="Agent B old",
            agent_id="agent-b",
            user_id="test-admin",
            updated_at=now - timedelta(days=31),
        ))
        await session.commit()

    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        recent_resp = await client.get("/api/sessions?days=30", headers=headers)
        included_resp = await client.get(
            "/api/sessions?days=30&include_session_id=agent-b-old",
            headers=headers,
        )

    assert recent_resp.status_code == 200
    recent_sessions = recent_resp.json()
    recent_ids = {item["id"] for item in recent_sessions}
    assert len(recent_sessions) == 56
    assert "agent-b-recent" in recent_ids
    assert "agent-b-old" not in recent_ids

    assert included_resp.status_code == 200
    included_ids = {item["id"] for item in included_resp.json()}
    assert "agent-b-old" in included_ids


@pytest.mark.asyncio
async def test_update_session_title(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/sessions", json={"title": "Original"}, headers=headers)
        session_id = create_resp.json()["id"]

        update_resp = await client.put(
            f"/api/sessions/{session_id}", json={"title": "Updated"}, headers=headers
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["title"] == "Updated"


@pytest.mark.asyncio
async def test_updating_session_with_identical_values_keeps_activity_time(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            "/api/sessions",
            json={"title": "No-op", "model": "gpt-4"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        session_id = create_resp.json()["id"]

        before = await client.get("/api/sessions", headers=headers)
        before_item = next(item for item in before.json() if item["id"] == session_id)

        update_resp = await client.put(
            f"/api/sessions/{session_id}",
            json={"model": "gpt-4"},
            headers=headers,
        )

    assert update_resp.status_code == 200
    assert update_resp.json()["updated_at"] == before_item["updated_at"]


@pytest.mark.asyncio
async def test_list_sessions_includes_default_pin_fields(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/sessions", json={"title": "Pinned Check"}, headers=headers)
        session_id = create_resp.json()["id"]

        list_resp = await client.get("/api/sessions", headers=headers)

    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data) == 1
    assert data[0]["id"] == session_id
    assert data[0]["is_pinned"] is False
    assert data[0]["pinned_at"] is None


@pytest.mark.asyncio
async def test_update_session_pin_status(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/sessions", json={"title": "Pin Me"}, headers=headers)
        session_id = create_resp.json()["id"]

        pin_resp = await client.put(
            f"/api/sessions/{session_id}",
            json={"is_pinned": True},
            headers=headers,
        )
        assert pin_resp.status_code == 200
        assert pin_resp.json()["is_pinned"] is True
        assert pin_resp.json()["pinned_at"] is not None

        list_after_pin = await client.get("/api/sessions", headers=headers)
        pinned_item = list_after_pin.json()[0]
        assert pinned_item["is_pinned"] is True
        assert pinned_item["pinned_at"] is not None

        unpin_resp = await client.put(
            f"/api/sessions/{session_id}",
            json={"is_pinned": False},
            headers=headers,
        )
        assert unpin_resp.status_code == 200
        assert unpin_resp.json()["is_pinned"] is False
        assert unpin_resp.json()["pinned_at"] is None

        list_after_unpin = await client.get("/api/sessions", headers=headers)
        unpinned_item = list_after_unpin.json()[0]
        assert unpinned_item["is_pinned"] is False
        assert unpinned_item["pinned_at"] is None


@pytest.mark.asyncio
async def test_delete_session(app_and_headers):
    app, headers = app_and_headers
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/sessions", json={"title": "To Delete"}, headers=headers)
        session_id = create_resp.json()["id"]

        del_resp = await client.delete(f"/api/sessions/{session_id}", headers=headers)
        assert del_resp.status_code == 204

        list_resp = await client.get("/api/sessions", headers=headers)
        assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_get_session_messages_returns_persisted_ui_metadata(app_and_headers):
    app, headers = app_and_headers
    from lc_agent.db.engine import get_async_session
    from lc_agent.db.models import SessionMeta
    from lc_agent.db.repository import ChatUiMessageRepository

    db_url = app.config["database"]["url"]
    async with get_async_session(db_url) as session:
        session.add(SessionMeta(
            id="thread-ui",
            title="UI test",
            user_id="test-admin",
        ))
        repo = ChatUiMessageRepository(session)
        await repo.create(session_id="thread-ui", role="user", content="funboost怎么样")
        await repo.create(
            session_id="thread-ui",
            role="assistant",
            content="不错。\n<!--TOOL:0-->\n适合任务队列。",
            tool_calls=[{"name": "nbrag", "runId": "run-1", "status": "done", "result": "资料"}],
            usage={"rounds": [{"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}]},
        )
        await session.commit()

    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/sessions/thread-ui/messages", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    msgs = data["messages"]
    assert data["total"] == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["content"] == "不错。\n<!--TOOL:0-->\n适合任务队列。"
    assert msgs[1]["tool_calls"][0]["runId"] == "run-1"
    assert msgs[1]["usage"]["rounds"][0]["total_tokens"] == 15


@pytest.mark.asyncio
async def test_get_session_messages_does_not_turn_checkpoint_failure_into_empty_history(app_and_headers):
    app, headers = app_and_headers
    from lc_agent.db.engine import get_async_session
    from lc_agent.db.models import SessionMeta

    db_url = app.config["database"]["url"]
    async with get_async_session(db_url) as session:
        session.add(SessionMeta(
            id="thread-checkpoint-failure",
            title="Checkpoint failure",
            user_id="test-admin",
            message_count=1,
        ))
        await session.commit()

    original_checkpointer = app.engine._checkpointer
    app.engine._checkpointer = None
    try:
        transport = ASGITransport(app=app.fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/sessions/thread-checkpoint-failure/messages",
                headers=headers,
            )
    finally:
        app.engine._checkpointer = original_checkpointer

    assert resp.status_code == 503
    assert resp.json()["detail"] == "会话历史暂时无法读取，请稍后重试"
