# lc_agent/server/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lc_agent import __version__
from lc_agent.server.routes.health import router as health_router


def create_app(config: dict) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="lc_agent",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
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

    return app
