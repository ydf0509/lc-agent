from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from lc_agent.db.repository import SessionRepository
from lc_agent.server.dependencies import get_db_session

router = APIRouter(tags=["sessions"])


class SessionCreateRequest(BaseModel):
    title: str = "新对话"
    agent_id: str = "__default__"
    model: str = ""


class SessionUpdateRequest(BaseModel):
    title: str | None = None


@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db_session)):
    repo = SessionRepository(db)
    sessions = await repo.list_all()
    return [
        {
            "id": s.id,
            "title": s.title,
            "agent_id": s.agent_id,
            "model": s.model,
            "message_count": s.message_count,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions
    ]


@router.post("/sessions", status_code=201)
async def create_session(body: SessionCreateRequest, db: AsyncSession = Depends(get_db_session)):
    repo = SessionRepository(db)
    session = await repo.create(title=body.title, agent_id=body.agent_id, model=body.model)
    return {"id": session.id, "title": session.title}


@router.put("/sessions/{session_id}")
async def update_session(session_id: str, body: SessionUpdateRequest, db: AsyncSession = Depends(get_db_session)):
    repo = SessionRepository(db)
    update_data = body.model_dump(exclude_unset=True)
    result = await repo.update(session_id, **update_data)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"id": result.id, "title": result.title}


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db_session)):
    repo = SessionRepository(db)
    deleted = await repo.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return Response(status_code=204)
