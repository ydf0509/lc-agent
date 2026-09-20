from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from lc_agent.db.models_auth import User
from lc_agent.db.repository import ChatUiMessageRepository, SessionRepository
from lc_agent.server.auth_middleware import get_current_user
from lc_agent.server.dependencies import get_db_session
from lc_agent.utils.loggers import server_logger

router = APIRouter(tags=["sessions"])


class SessionCreateRequest(BaseModel):
    title: str = "新对话"
    agent_id: str = "chat"
    model: str = ""


class SessionUpdateRequest(BaseModel):
    title: str | None = None
    model: str | None = None
    is_pinned: bool | None = None


def serialize_session(s):
    return {
        "id": s.id,
        "title": s.title,
        "agent_id": s.agent_id,
        "model": s.model,
        "message_count": s.message_count,
        "is_pinned": s.is_pinned,
        "pinned_at": s.pinned_at.isoformat() if s.pinned_at else None,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }


def _check_session_access(sess, user: User) -> None:
    # 会话按账号隔离：admin 也不例外。未配 auth 的单机模式（__anonymous__）保持原样。
    if user.id == "__anonymous__":
        return
    if sess.user_id != user.id:
        raise HTTPException(status_code=403, detail="权限不足")


@router.get("/sessions")
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    days: int | None = Query(default=None, ge=1, le=3650),
    include_session_id: str | None = Query(default=None, max_length=200),
):
    repo = SessionRepository(db)
    if days is None:
        sessions = await repo.list_all(user_id=user.id)
    else:
        sessions = await repo.list_recent_for_sidebar(
            user_id=user.id,
            days=days,
            include_session_id=include_session_id,
        )
    return [serialize_session(s) for s in sessions]


@router.post("/sessions", status_code=201)
async def create_session(
    body: SessionCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    repo = SessionRepository(db)

    # Validate agent access for non-admin
    if user.role != "admin" and body.agent_id != "chat":
        from lc_agent.db.models_auth import UserAgentAccess
        from sqlalchemy import select as sa_select
        result = await db.execute(
            sa_select(UserAgentAccess).where(
                UserAgentAccess.user_id == user.id,
                UserAgentAccess.agent_id == body.agent_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="无权使用此智能体")

    session = await repo.create(
        title=body.title,
        agent_id=body.agent_id,
        model=body.model,
        user_id=user.id,
    )
    return {"id": session.id, "title": session.title}


@router.put("/sessions/{session_id}")
async def update_session(
    session_id: str,
    body: SessionUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    repo = SessionRepository(db)
    sess = await repo.get_by_id(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")
    _check_session_access(sess, user)

    update_data = body.model_dump(exclude_unset=True)
    result = await repo.update(session_id, **update_data)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return serialize_session(result)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    repo = SessionRepository(db)
    sess = await repo.get_by_id(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")
    _check_session_access(sess, user)

    deleted = await repo.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return Response(status_code=204)


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int | None = Query(default=None, ge=0),
):
    """Retrieve message history for a session (paginated, without http_traces body).

    When offset is not provided, returns the LATEST `limit` messages (most recent).
    When offset is explicitly 0 or positive, returns from that position (oldest first).
    """
    repo = SessionRepository(db)
    sess = await repo.get_by_id(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")
    _check_session_access(sess, user)

    msg_repo = ChatUiMessageRepository(db)
    total = await msg_repo.count_by_session(session_id)

    if offset is None:
        effective_offset = max(0, total - limit)
    else:
        effective_offset = offset

    ui_messages = await msg_repo.list_by_session(session_id, limit=limit, offset=effective_offset)

    if ui_messages:
        # 轮次号 = 该消息之前的 user 消息数（全局口径，与 FileChange.round_number 同源）。
        # 前端只加载窗口消息，自己数会和后端错位，这里算好直接带回去。
        round_of: dict[str, int] = {}
        round_no = 0
        for mid, mrole in await msg_repo.list_ids_roles(session_id):
            if mrole == "user":
                round_no += 1
            round_of[mid] = round_no

        return {
            "total": total,
            "offset": effective_offset,
            "limit": limit,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "tool_calls": msg.tool_calls or [],
                    "usage": msg.usage,
                    "http_traces_count": len(msg.http_traces) if msg.http_traces else 0,
                    "round_number": round_of.get(msg.id),
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in ui_messages
            ],
        }

    engine = request.app.state.engine
    checkpointer = engine._checkpointer
    if checkpointer is None:
        if sess.message_count > 0:
            raise HTTPException(status_code=503, detail="会话历史暂时无法读取，请稍后重试")
        return {"total": 0, "offset": effective_offset, "limit": limit, "messages": []}

    try:
        config = {"configurable": {"thread_id": session_id}}
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        if checkpoint_tuple is None:
            if sess.message_count > 0:
                raise HTTPException(status_code=503, detail="会话历史暂时无法读取，请稍后重试")
            return {"total": 0, "offset": effective_offset, "limit": limit, "messages": []}

        checkpoint = checkpoint_tuple.checkpoint
        channel_values = checkpoint.get("channel_values", {})
        messages = channel_values.get("messages", [])

        result = []
        for msg in messages:
            msg_type = getattr(msg, "type", "unknown")
            content = getattr(msg, "content", "")
            tool_calls = getattr(msg, "tool_calls", None)

            role = msg_type
            if msg_type == "human":
                role = "user"
            elif msg_type == "ai":
                role = "assistant"

            item = {"role": role, "content": content}

            if tool_calls:
                item["tool_calls"] = [
                    {"name": tc.get("name", ""), "args": tc.get("args", {}), "id": tc.get("id", "")}
                    for tc in tool_calls
                ]

            if msg_type == "tool":
                item["tool_call_id"] = getattr(msg, "tool_call_id", "")
                item["name"] = getattr(msg, "name", "")

            result.append(item)

        checkpoint_offset = effective_offset if effective_offset < len(result) else max(0, len(result) - limit)
        paginated = result[checkpoint_offset:checkpoint_offset + limit]
        return {"total": len(result), "offset": checkpoint_offset, "limit": limit, "messages": paginated}
    except HTTPException:
        raise
    except Exception as e:
        server_logger.exception("Failed to load messages for session %s", session_id)
        raise HTTPException(status_code=503, detail="会话历史暂时无法读取，请稍后重试") from e


@router.get("/sessions/{session_id}/messages/{message_id}/traces")
async def get_message_traces(
    session_id: str,
    message_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieve http_traces for a specific message (on-demand loading)."""
    repo = SessionRepository(db)
    sess = await repo.get_by_id(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")
    _check_session_access(sess, user)

    msg_repo = ChatUiMessageRepository(db)
    msg = await msg_repo.get_by_id(message_id)
    if msg is None or msg.session_id != session_id:
        raise HTTPException(status_code=404, detail="Message not found")

    return {"traces": msg.http_traces or []}
