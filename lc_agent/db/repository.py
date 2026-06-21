from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lc_agent.db.models import AgentPresetDB, ChatUiMessage, SessionMeta


class PresetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> list[AgentPresetDB]:
        result = await self.session.execute(select(AgentPresetDB).order_by(AgentPresetDB.created_at))
        return list(result.scalars().all())

    async def get_by_id(self, preset_id: str) -> AgentPresetDB | None:
        return await self.session.get(AgentPresetDB, preset_id)

    async def create(self, **kwargs) -> AgentPresetDB:
        preset = AgentPresetDB(**kwargs)
        self.session.add(preset)
        await self.session.commit()
        await self.session.refresh(preset)
        return preset

    async def update(self, preset_id: str, **kwargs) -> AgentPresetDB | None:
        preset = await self.get_by_id(preset_id)
        if preset is None:
            return None
        for key, value in kwargs.items():
            if hasattr(preset, key):
                setattr(preset, key, value)
        preset.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(preset)
        return preset

    async def delete(self, preset_id: str) -> bool:
        preset = await self.get_by_id(preset_id)
        if preset is None:
            return False
        await self.session.delete(preset)
        await self.session.commit()
        return True


class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self, limit: int = 50) -> list[SessionMeta]:
        result = await self.session.execute(
            select(SessionMeta).order_by(SessionMeta.updated_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, session_id: str) -> SessionMeta | None:
        return await self.session.get(SessionMeta, session_id)

    async def create(self, **kwargs) -> SessionMeta:
        sess = SessionMeta(**kwargs)
        self.session.add(sess)
        await self.session.commit()
        await self.session.refresh(sess)
        return sess

    async def update(self, session_id: str, **kwargs) -> SessionMeta | None:
        sess = await self.get_by_id(session_id)
        if sess is None:
            return None
        for key, value in kwargs.items():
            if hasattr(sess, key):
                setattr(sess, key, value)
        sess.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(sess)
        return sess

    async def delete(self, session_id: str) -> bool:
        sess = await self.get_by_id(session_id)
        if sess is None:
            return False
        await self.session.delete(sess)
        await self.session.commit()
        return True

    async def increment_messages(self, session_id: str) -> None:
        sess = await self.get_by_id(session_id)
        if sess:
            sess.message_count += 1
            sess.updated_at = datetime.now(timezone.utc)
            await self.session.commit()


class ChatUiMessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        session_id: str,
        role: str,
        content: str = "",
        tool_calls: list[dict] | None = None,
        usage: dict | None = None,
    ) -> ChatUiMessage:
        message = ChatUiMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            usage=usage,
        )
        self.session.add(message)
        await self.session.commit()
        try:
            await self.session.refresh(message)
        except Exception:
            pass
        return message

    async def list_by_session(self, session_id: str) -> list[ChatUiMessage]:
        result = await self.session.execute(
            select(ChatUiMessage)
            .where(ChatUiMessage.session_id == session_id)
            .order_by(ChatUiMessage.created_at, ChatUiMessage.id)
        )
        return list(result.scalars().all())

    async def truncate_from_message(self, session_id: str, message_id: str) -> int:
        anchor = await self.session.get(ChatUiMessage, message_id)
        if anchor is None or anchor.session_id != session_id:
            return 0

        result = await self.session.execute(
            select(ChatUiMessage)
            .where(ChatUiMessage.session_id == session_id)
            .order_by(ChatUiMessage.created_at, ChatUiMessage.id)
        )
        rows = list(result.scalars().all())
        start_idx = next((idx for idx, row in enumerate(rows) if row.id == anchor.id), -1)
        if start_idx < 0:
            return 0

        for row in rows[start_idx:]:
            await self.session.delete(row)
        await self.session.commit()
        return len(rows[start_idx:])

    async def count_by_session(self, session_id: str) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(ChatUiMessage).where(ChatUiMessage.session_id == session_id)
        )
        return int(result.scalar_one())
