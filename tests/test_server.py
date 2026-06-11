# tests/test_server.py
import pytest
from httpx import ASGITransport, AsyncClient

from lc_agent.server.app import create_app


@pytest.fixture
def app(sample_config):
    return create_app(sample_config)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    async def test_health_returns_ok(self, client):
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    async def test_health_includes_config_status(self, client):
        response = await client.get("/api/health")
        data = response.json()
        assert "config_loaded" in data


class TestCORS:
    async def test_cors_allows_all_origins(self, client):
        response = await client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
