"""Database persistence operations for chat sessions and messages.

Business-database access goes through the global runtime config —
use ``get_business_async_session()`` (no ``db_url`` plumbing).
"""
import logging
from typing import Any

from lc_agent.utils.error_text import safe_traceback_text


logger = logging.getLogger(__name__)


async def get_session_message_count(thread_id: str) -> int:
    """Get the current message count for a session. Returns 0 if not found."""
    try:
        from lc_agent.db.engine import get_business_async_session
        from lc_agent.db.repository import SessionRepository

        session = get_business_async_session()
        try:
            repo = SessionRepository(session)
            existing = await repo.get_by_id(thread_id)
            if existing is None:
                return 0
            return existing.message_count or 0
        finally:
            await session.close()
    except Exception:
        return 0


async def get_session_user_message_count(thread_id: str) -> int:
    """Count user-role UI messages for a session.

    Used as the conversation round number: the Nth user question = round N.
    """
    try:
        from lc_agent.db.engine import get_business_async_session
        from lc_agent.db.repository import ChatUiMessageRepository

        session = get_business_async_session()
        try:
            repo = ChatUiMessageRepository(session)
            return await repo.count_by_session_role(thread_id, "user")
        finally:
            await session.close()
    except Exception:
        return 0


async def ensure_session(
    thread_id: str,
    title: str,
    agent_id: str,
    model: str,
    user_id: str = "",
) -> None:
    """Create session metadata if not exists, or update if exists."""
    try:
        from lc_agent.db.engine import get_business_async_session
        from lc_agent.db.repository import SessionRepository

        session = get_business_async_session()
        try:
            repo = SessionRepository(session)
            existing = await repo.get_by_id(thread_id)
            if existing is None:
                await repo.create(
                    id=thread_id,
                    title=title or "新对话",
                    agent_id=agent_id,
                    model=model,
                    message_count=0,
                    user_id=user_id,
                )
            else:
                await repo.update(
                    thread_id,
                    title=title or existing.title,
                    agent_id=agent_id,
                    model=model or existing.model,
                )
        finally:
            await session.close()
    except Exception:
        logger.exception("Failed to ensure session %s", thread_id)
        raise


async def increment_session_message_count(thread_id: str) -> None:
    """Increment persisted session message count after a completed round."""
    try:
        from lc_agent.db.engine import get_business_async_session
        from lc_agent.db.repository import SessionRepository

        session = get_business_async_session()
        try:
            await SessionRepository(session).increment_messages(thread_id)
        finally:
            await session.close()
    except Exception:
        logger.exception("Failed to increment message count for session %s", thread_id)
        raise


async def save_title(thread_id: str, title: str) -> None:
    """Save title to DB."""
    try:
        from lc_agent.db.engine import get_business_async_session
        from lc_agent.db.repository import SessionRepository

        session = get_business_async_session()
        try:
            await SessionRepository(session).update(thread_id, title=title)
        finally:
            await session.close()
    except Exception:
        logger.exception("Failed to save title for session %s", thread_id)
        raise


async def generate_title(
    engine: Any,
    thread_id: str,
    first_message: str,
    preset_id: str = "chat",
    selected_model_id: str = "",
    usage_sink: list[dict] | None = None,
) -> str | None:
    """Generate title from first message using the agent's model.

    usage_sink：可选出参列表，透传给 engine.generate_title 收集本次调用 usage
    （供 usage_recorder 落 source="title" 行）。
    Returns the generated title string, or None on failure.
    """
    try:
        model_id = selected_model_id
        if preset_id in engine.BUILTIN_IDS:
            for bp in engine.get_builtin_presets():
                if bp.id == preset_id:
                    model_id = model_id or bp.default_model
                    break
        else:
            preset = engine._presets.get(preset_id) or engine._custom_presets.get(preset_id)
            if preset:
                model_id = model_id or preset.default_model
        return await engine.generate_title(first_message, model_id, usage_sink=usage_sink)
    except Exception:
        logger.exception("Title generation failed for session %s", thread_id)
        return None


async def save_ui_message(
    thread_id: str,
    role: str,
    content: list[dict[str, Any]],
    *,
    tool_calls: list[dict[str, Any]] | None = None,
    usage: dict[str, Any] | None = None,
    http_traces: list[dict[str, Any]] | None = None,
) -> None:
    """Persist replay data for the web chat history."""
    try:
        from lc_agent.db.engine import get_business_async_session
        from lc_agent.db.repository import ChatUiMessageRepository

        session = get_business_async_session()
        try:
            repo = ChatUiMessageRepository(session)
            await repo.create(
                session_id=thread_id,
                role=role,
                content=content,
                tool_calls=tool_calls,
                usage=usage,
                http_traces=http_traces,
            )
        finally:
            await session.close()
    except Exception as e:
        logger.error("Failed to persist UI message for session %s\n%s", thread_id, safe_traceback_text(e))
        raise


async def save_partial_assistant_message(
    thread_id: str,
    *,
    content_parts: list[str],
    tool_calls: list[dict[str, Any]],
    usage_rounds: list[dict[str, Any]],
    elapsed_ms: int,
) -> bool:
    """把「已产生的部分」落成一条 assistant UI 消息，返回是否真的写了。

    正常结束路径本来就会写；取消 / 前端断开 / 异常这些早退路径过去直接 return，
    导致这一轮的 usage 与工具调用在 chat_ui_messages 里永久缺失（只有用量账单表
    record_usage 有记录），右侧概览与刷新后的历史都看不到。
    """
    if not (content_parts or tool_calls or usage_rounds):
        return False
    from lc_agent.server.stream_utils import split_chat_usage_rounds

    # 还没跑完的工具在快照里仍是 running，落库前统一标成 interrupted，
    # 否则历史里那张卡片会永远显示"执行中"。
    persisted_tool_calls = [
        {**tc, "status": "interrupted"} if tc.get("status") in (None, "running") else tc
        for tc in tool_calls
    ]

    await save_ui_message(
        thread_id,
        "assistant",
        [{"type": "text", "text": "".join(content_parts)}],
        tool_calls=persisted_tool_calls or None,
        usage={
            "rounds": split_chat_usage_rounds(usage_rounds),
            "tool_call_count": len(tool_calls),
            "total_duration_ms": elapsed_ms,
        },
    )
    return True


async def persist_interrupted_round(
    thread_id: str,
    *,
    content_parts: list[str],
    tool_calls: list[dict[str, Any]],
    usage_rounds: list[dict[str, Any]],
    elapsed_ms: int,
) -> None:
    """早退路径（取消 / 前端断开 / 异常）补写这一轮已产生的 UI 记录。

    失败只记日志、不向上抛：调用方随后还要给前端发终止事件，
    不能让落库问题打断收尾流程。
    """
    try:
        wrote = await save_partial_assistant_message(
            thread_id,
            content_parts=content_parts,
            tool_calls=tool_calls,
            usage_rounds=usage_rounds,
            elapsed_ms=elapsed_ms,
        )
        if wrote:
            await increment_session_message_count(thread_id)
    except Exception as e:
        logger.error("Failed to persist interrupted round for session %s\n%s", thread_id, safe_traceback_text(e))


async def persist_interrupted_resume_round(
    thread_id: str,
    *,
    content_parts: list[str],
    tool_calls: list[dict[str, Any]],
    usage_rounds: list[dict[str, Any]],
    elapsed_ms: int,
) -> None:
    """中断续跑（resume）早退时，把已产生的部分**追加**到上一条 assistant 消息。

    resume 与首次发送不同：整轮共用同一条 assistant 消息（正常结束走
    append_to_last_assistant_message），所以这里也必须追加而不是新建，
    否则续跑被取消/出错会多出一条重复的 assistant 气泡；消息数也不递增。
    失败只记日志、不向上抛。
    """
    new_content = "".join(content_parts)
    if not (new_content or tool_calls or usage_rounds):
        return
    try:
        from lc_agent.server.stream_utils import split_chat_usage_rounds

        persisted_tool_calls = [
            {**tc, "status": "interrupted"} if tc.get("status") in (None, "running") else tc
            for tc in tool_calls
        ]
        await append_to_last_assistant_message(
            thread_id,
            new_content,
            all_tool_calls=persisted_tool_calls or None,
            usage_rounds=split_chat_usage_rounds(usage_rounds) or None,
            resume_duration_ms=elapsed_ms,
        )
    except Exception as e:
        logger.error("Failed to persist interrupted resume round for session %s\n%s", thread_id, safe_traceback_text(e))


async def truncate_from_message(thread_id: str, message_id: str) -> None:
    """Delete persisted UI messages from the edited anchor onward."""
    try:
        from lc_agent.db.engine import get_business_async_session
        from lc_agent.db.repository import ChatUiMessageRepository

        session = get_business_async_session()
        try:
            repo = ChatUiMessageRepository(session)
            await repo.truncate_from_message(thread_id, message_id)
        finally:
            await session.close()
    except Exception:
        logger.exception("Failed to truncate UI messages for session %s", thread_id)
        raise


async def load_resume_context(thread_id: str) -> tuple[list[dict[str, Any]], int]:
    """Load tool_calls and http_traces count from the last assistant message for interrupt continuation."""
    try:
        from lc_agent.db.engine import get_business_async_session
        from lc_agent.db.repository import ChatUiMessageRepository

        session = get_business_async_session()
        try:
            repo = ChatUiMessageRepository(session)
            last_msg = await repo.get_last_assistant(thread_id)
            if last_msg is None:
                return [], 0
            return list(last_msg.tool_calls or []), last_msg.http_traces_count or 0
        finally:
            await session.close()
    except Exception:
        return [], 0


async def append_to_last_assistant_message(
    thread_id: str,
    content: str,
    *,
    all_tool_calls: list[dict[str, Any]] | None = None,
    usage_rounds: list[dict] | None = None,
    http_traces: list[dict[str, Any]] | None = None,
    resume_duration_ms: int = 0,
) -> None:
    """Update the last assistant message after interrupt resume.

    ``all_tool_calls`` replaces the entire tool_calls array (it already
    contains both pre-interrupt tools with updated statuses and new tools).
    """
    try:
        from lc_agent.db.engine import get_business_async_session
        from lc_agent.db.repository import ChatUiMessageRepository

        session = get_business_async_session()
        try:
            repo = ChatUiMessageRepository(session)
            last_msg = await repo.get_last_assistant(thread_id)
            if last_msg is None:
                return

            if content:
                existing = list(last_msg.content) if isinstance(last_msg.content, list) else []
                if existing and isinstance(existing[-1], dict) and existing[-1].get("type") == "text":
                    existing[-1] = {**existing[-1], "text": (existing[-1].get("text") or "") + content}
                else:
                    existing.append({"type": "text", "text": content})
                last_msg.content = existing
            if all_tool_calls is not None:
                last_msg.tool_calls = all_tool_calls
            if usage_rounds:
                old = last_msg.usage or {}
                last_msg.usage = {
                    **old,
                    "rounds": (old.get("rounds") or []) + usage_rounds,
                    "tool_call_count": len(all_tool_calls or []),
                    "total_duration_ms": (old.get("total_duration_ms") or 0) + resume_duration_ms,
                }
            if http_traces:
                last_msg.http_traces = (last_msg.http_traces or []) + list(http_traces)
                last_msg.http_traces_count = len(last_msg.http_traces)
            session.add(last_msg)
            await session.commit()
        finally:
            await session.close()
    except Exception:
        logger.exception("Failed to update last assistant message for session %s", thread_id)
        raise


async def create_subsession(
    sub_session_id: str,
    parent_session_id: str,
    tool_call_id: str,
    agent_id: str,
    title: str,
    user_id: str = "",
) -> None:
    """Create a sub-session record linked to its parent session."""
    try:
        from lc_agent.db.engine import get_business_async_session
        from lc_agent.db.models import SessionMeta

        session = get_business_async_session()
        try:
            new_session = SessionMeta(
                id=sub_session_id,
                title=title,
                agent_id=agent_id,
                model="",
                user_id=user_id,
                message_count=0,
                parent_session_id=parent_session_id,
                tool_call_id=tool_call_id,
            )
            session.add(new_session)
            await session.commit()
        finally:
            await session.close()
    except Exception:
        logger.exception("Failed to create sub-session %s", sub_session_id)
        raise


async def save_subsession_delegation_message(
    sub_session_id: str,
    query: str,
) -> None:
    """Insert the synthetic delegation message as the first message in a sub-session."""
    await save_ui_message(
        sub_session_id, "system", [{"type": "text", "text": f"委托任务: {query}"}],
    )


async def save_file_change(
    session_id: str,
    file_path: str,
    change_type: str,
    *,
    old_string: str | None = None,
    new_string: str | None = None,
    tool_call_id: str | None = None,
    move_destination: str | None = None,
    round_number: int | None = None,
    line_start: int | None = None,
    context_before: str | None = None,
    context_after: str | None = None,
) -> None:
    """Persist a file change record."""
    try:
        from lc_agent.db.engine import get_business_async_session
        from lc_agent.db.repository import FileChangeRepository

        session = get_business_async_session()
        try:
            repo = FileChangeRepository(session)
            await repo.create(
                session_id=session_id,
                file_path=file_path,
                change_type=change_type,
                old_string=old_string,
                new_string=new_string,
                tool_call_id=tool_call_id,
                move_destination=move_destination,
                round_number=round_number,
                line_start=line_start,
                context_before=context_before,
                context_after=context_after,
            )
        finally:
            await session.close()
    except Exception:
        logger.exception("Failed to save file change for session %s", session_id)


async def save_git_base_hash(session_id: str, git_base_hash: str) -> None:
    """Save git base hash to session metadata."""
    try:
        from lc_agent.db.engine import get_business_async_session
        from lc_agent.db.repository import SessionRepository

        session = get_business_async_session()
        try:
            repo = SessionRepository(session)
            sess = await repo.get_by_id(session_id)
            if sess and not sess.git_base_hash:
                await repo.update(session_id, git_base_hash=git_base_hash)
        finally:
            await session.close()
    except Exception:
        logger.exception("Failed to save git base hash for session %s", session_id)


async def finalize_subsession_message(
    sub_session_id: str,
    content: str,
    tool_calls: list[dict] | None = None,
    usage: dict | None = None,
    http_traces: list[dict] | None = None,
) -> None:
    """Save the sub-agent's assistant message and increment message count."""
    await save_ui_message(
        sub_session_id, "assistant", [{"type": "text", "text": content}],
        tool_calls=tool_calls,
        usage=usage,
        http_traces=http_traces,
    )
    await increment_session_message_count(sub_session_id)
