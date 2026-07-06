from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from lc_agent.db.models import SubAgentEvent, SubAgentRun


def _utcnow():
    return datetime.now(timezone.utc)


class SubAgentRunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_run(
        self,
        *,
        parent_session_id: str,
        parent_message_id: str | None,
        parent_tool_run_id: str,
        parent_agent_id: str,
        sub_agent_id: str,
        sub_agent_name: str,
        sub_thread_id: str,
        task_description: str,
        depth: int,
    ) -> SubAgentRun:
        run = SubAgentRun(
            parent_session_id=parent_session_id,
            parent_message_id=parent_message_id,
            parent_tool_run_id=parent_tool_run_id,
            parent_agent_id=parent_agent_id,
            sub_agent_id=sub_agent_id,
            sub_agent_name=sub_agent_name,
            sub_thread_id=sub_thread_id,
            task_description=task_description,
            depth=depth,
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def append_event(self, *, run_id: str, event_type: str, payload: dict[str, Any]) -> SubAgentEvent:
        result = await self.session.execute(
            select(func.max(SubAgentEvent.sequence)).where(SubAgentEvent.run_id == run_id)
        )
        max_sequence = result.scalar_one_or_none() or 0
        event = SubAgentEvent(
            run_id=run_id,
            event_type=event_type,
            payload=payload,
            sequence=max_sequence + 1,
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def finish_run(self, *, run_id: str, status: str, summary: str, final_result: str) -> SubAgentRun:
        run = await self.get_run(run_id)
        if run is None:
            raise ValueError(f"SubAgentRun not found: {run_id}")
        run.status = status
        run.summary = summary
        run.final_result = final_result
        run.ended_at = _utcnow()
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: str) -> SubAgentRun | None:
        result = await self.session.execute(select(SubAgentRun).where(SubAgentRun.id == run_id))
        return result.scalar_one_or_none()

    async def list_events(self, run_id: str) -> list[SubAgentEvent]:
        result = await self.session.execute(
            select(SubAgentEvent)
            .where(SubAgentEvent.run_id == run_id)
            .order_by(SubAgentEvent.sequence.asc())
        )
        return list(result.scalars().all())