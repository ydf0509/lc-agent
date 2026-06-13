# lc_agent/server/app.py
import mimetypes
from pathlib import Path

from fastapi import FastAPI

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from lc_agent import __version__
from lc_agent.server.routes.health import router as health_router
from lc_agent.server.routes.tools import router as tools_router
from lc_agent.server.routes.models import router as models_router
from lc_agent.server.routes.agents import router as agents_router
from lc_agent.server.routes.sessions import router as sessions_router
from lc_agent.server.routes.skills import router as skills_router
from lc_agent.server.routes.mcp import router as mcp_router


def create_app(config: dict, lifespan=None) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="lc_agent",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.config = config

    app.include_router(health_router, prefix="/api")
    app.include_router(tools_router, prefix="/api")
    app.include_router(models_router, prefix="/api")
    app.include_router(agents_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")
    app.include_router(skills_router, prefix="/api")
    app.include_router(mcp_router, prefix="/api")

    return app


def mount_static_files(app: FastAPI):
    """Mount static files AFTER WebSocket routes are registered."""
    web_dist = Path(__file__).parent.parent / "web" / "dist"
    if web_dist.exists():
        app.mount("/", StaticFiles(directory=str(web_dist), html=True), name="frontend")
