import pytest
from httpx import ASGITransport, AsyncClient

from lc_agent.app import LcAgentApp
from lc_agent.db.engine import get_async_session, init_db, reset_engine
from lc_agent.db.subagent_repository import SubAgentRunRepository
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
        "provider": {"openai": {"base_url": "http://fake", "api_key": "sk-fake", "models": [{"id": "gpt-4"}]}},
        "agent": {"default_model": "gpt-4", "system_prompt": "You are helpful."},
        "database": {"url": db_url, "checkpoint_path": ":memory:"},
    }
    app = LcAgentApp(config)
    headers = await setup_test_auth(app.fastapi_app, db_url)
    return app, headers


@pytest.fixture
async def db_session(setup):
    url = setup
    async with get_async_session(url) as session:
        yield session


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

    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        run_resp = await client.get(f"/api/sub-agent-runs/{run.id}", headers=headers)
        assert run_resp.status_code == 200
        assert run_resp.json()["id"] == run.id

        events_resp = await client.get(f"/api/sub-agent-runs/{run.id}/events", headers=headers)
        assert events_resp.status_code == 200
        assert events_resp.json()["events"][0]["event_type"] == "token"