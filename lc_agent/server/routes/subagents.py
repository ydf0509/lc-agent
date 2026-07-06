from fastapi import APIRouter, Depends, HTTPException, Request

from lc_agent.db.engine import get_async_session as _get_db_session
from lc_agent.db.subagent_repository import SubAgentRunRepository
from lc_agent.server.auth_middleware import get_current_user

router = APIRouter(tags=["sub-agents"])


async def get_db(request: Request):
    db_url = request.app.state.config.get("database", {}).get("url", "sqlite+aiosqlite:///./lc_agent_data.db")
    async with _get_db_session(db_url) as session:
        yield session


@router.get("/sub-agent-runs/{run_id}")
async def get_subagent_run(run_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    repo = SubAgentRunRepository(db)
    run = await repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="SubAgentRun not found")
    return run


@router.get("/sub-agent-runs/{run_id}/events")
async def get_subagent_events(run_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    repo = SubAgentRunRepository(db)
    run = await repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="SubAgentRun not found")
    events = await repo.list_events(run_id)
    return {"run": run, "events": events}