from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lc_agent.db.models import AgentPresetDB, SessionMeta


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
