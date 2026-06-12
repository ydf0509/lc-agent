from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from lc_agent.db.repository import SessionRepository
from lc_agent.server.dependencies import get_db_session, get_engine

router = APIRouter(tags=["sessions"])


class SessionCreateRequest(BaseModel):
    title: str = "新对话"
    agent_id: str = "__chat__"
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


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, request: Request):
    """Retrieve message history for a session from the LangGraph checkpoint."""
    engine = request.app.state.engine
    checkpointer = engine._checkpointer
    if checkpointer is None:
        return []

    try:
        config = {"configurable": {"thread_id": session_id}}
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        if checkpoint_tuple is None:
            return []

        checkpoint = checkpoint_tuple.checkpoint
        channel_values = checkpoint.get("channel_values", {})
        messages = channel_values.get("messages", [])

        result = []
        for msg in messages:
            msg_type = getattr(msg, "type", "unknown")
            content = getattr(msg, "content", "")
            tool_calls = getattr(msg, "tool_calls", None)

            item = {"role": msg_type, "content": content}

            if tool_calls:
                item["tool_calls"] = [
                    {"name": tc.get("name", ""), "args": tc.get("args", {}), "id": tc.get("id", "")}
                    for tc in tool_calls
                ]

            if msg_type == "tool":
                item["tool_call_id"] = getattr(msg, "tool_call_id", "")
                item["name"] = getattr(msg, "name", "")

            result.append(item)

        return result
    except Exception as e:
        print(f"[Sessions] Failed to load messages for {session_id}: {e}")
        return []
