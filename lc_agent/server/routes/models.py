from fastapi import APIRouter, Depends

from lc_agent.core.engine import AgentEngine
from lc_agent.server.dependencies import get_engine

router = APIRouter(tags=["models"])


@router.get("/models")
def list_models(engine: AgentEngine = Depends(get_engine)):
    """List all configured models."""
    return [
        {
            "id": m.id,
            "provider": m.provider,
            "base_url": m.base_url,
            "context_limit": m.context_limit,
        }
        for m in engine.get_models()
    ]
