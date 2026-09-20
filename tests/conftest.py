import pytest

from lc_agent.config import reset_config, set_config
from lc_agent.core.auth import AuthService
from lc_agent.db.models_auth import User


@pytest.fixture(autouse=True)
def _baseline_global_config():
    """每个测试前注册一个空基线配置，防止惰性 get_config() 触发磁盘搜索/报错。

    测试内创建 LcAgentApp/create_app 显式传 dict 时会覆盖全局。
    """
    set_config({})
    yield
    reset_config()


@pytest.fixture
def sample_config() -> dict:
    """Minimal valid configuration for testing."""
    return {
        "provider": {
            "default": {
                "api_key": "test-key",
                "base_url": "https://api.example.com/v1",
                "models": [{"model_id": "test-model", "raw_model_id": "test-model"}],
            }
        },
        "agent": {
            "system_prompt": "You are a helpful assistant.",
            "default_model": "test-model",
            "streaming": True,
        },
        "mcp": {},
        "session": {"db_path": ":memory:"},
    }


async def setup_test_auth(app, user_id: str = "test-admin", username: str = "testadmin") -> dict:
    """Configure auth on a test app and return Authorization headers."""
    import lc_agent.db.models_auth  # noqa: F401 — register User table

    from lc_agent.db.engine import get_business_async_session

    auth_service = AuthService(secret="test-secret-key-minimum16chars", token_expire_days=7)
    app.state.auth_service = auth_service

    async with get_business_async_session() as session:
        admin = User(
            id=user_id,
            username=username,
            password_hash=auth_service.hash_password("pass"),
            role="admin",
        )
        session.add(admin)
        await session.commit()

    token = auth_service.create_token(user_id=user_id, username=username, role="admin")
    return {"Authorization": f"Bearer {token}"}
