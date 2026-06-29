# lc_agent/server/routes/health.py
from fastapi import APIRouter, Request

from lc_agent import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request):
    """Health check endpoint."""
    config = request.app.state.config
    return {
        "status": "ok",
        "version": __version__,
        "config_loaded": config.get("_config_path") is not None,
        "app_name": config.get("ui", {}).get("app_name"),
    }
