from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lc_agent.db.models import (
    AgentPresetDB,
    AgentPromptBindingDB,
    AutomationRun,
    AutomationTask,
    ChatUiMessage,
    FileChange,
    PromptTemplateDB,
    SessionMeta,
)
from lc_agent.db.models_auth import User
from lc_agent.db.models_usage import LlmUsage, ModelPrice
from lc_agent.db.usage_pricing import bucket_end, compute_cost, resolve_prices_for


AUTOMATION_ACTIVE_STATUSES = ("pending", "running")


class PromptRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> list[PromptTemplateDB]:
        result = await self.session.execute(select(PromptTemplateDB).order_by(PromptTemplateDB.created_at))
        return list(result.scalars().all())

    async def get_by_id(self, prompt_id: str) -> PromptTemplateDB | None:
        return await self.session.get(PromptTemplateDB, prompt_id)

    async def create(self, name: str, content: str) -> PromptTemplateDB:
        pt = PromptTemplateDB(name=name, content=content)
        self.session.add(pt)
        await self.session.commit()
        await self.session.refresh(pt)
        return pt

    async def update(self, prompt_id: str, **kwargs) -> PromptTemplateDB | None:
        pt = await self.get_by_id(prompt_id)
        if pt is None:
            return None
        for key, value in kwargs.items():
            if hasattr(pt, key):
                setattr(pt, key, value)
        pt.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(pt)
        return pt

    async def delete(self, prompt_id: str) -> bool:
        pt = await self.get_by_id(prompt_id)
        if pt is None:
            return False
        await self.session.delete(pt)
        await self.session.commit()
        return True

    async def get_agent_ids_using_prompt(self, prompt_id: str) -> list[str]:
        result = await self.session.execute(
            select(AgentPromptBindingDB.agent_id).where(AgentPromptBindingDB.prompt_id == prompt_id)
        )
        return list(result.scalars().all())

    async def get_bindings_for_agent(self, agent_id: str) -> list[AgentPromptBindingDB]:
        result = await self.session.execute(
            select(AgentPromptBindingDB)
            .where(AgentPromptBindingDB.agent_id == agent_id)
            .order_by(AgentPromptBindingDB.sort_order)
        )
        return list(result.scalars().all())

    async def set_bindings_for_agent(self, agent_id: str, prompt_ids: list[str]) -> None:
        await self.session.execute(
            delete(AgentPromptBindingDB).where(AgentPromptBindingDB.agent_id == agent_id)
        )
        for order, pid in enumerate(prompt_ids):
            self.session.add(AgentPromptBindingDB(agent_id=agent_id, prompt_id=pid, sort_order=order))
        await self.session.commit()

    async def resolve_extra_prompts(self, agent_id: str) -> list[tuple[str, str]]:
        """Return ordered (name, content) pairs for prompts bound to this agent."""
        stmt = (
            select(PromptTemplateDB.name, PromptTemplateDB.content)
            .join(AgentPromptBindingDB, AgentPromptBindingDB.prompt_id == PromptTemplateDB.id)
            .where(AgentPromptBindingDB.agent_id == agent_id)
            .order_by(AgentPromptBindingDB.sort_order)
        )
        result = await self.session.execute(stmt)
        return [(name, content) for name, content in result.all() if content and content.strip()]


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

    async def list_all(self, limit: int = 50, user_id: str | None = None) -> list[SessionMeta]:
        stmt = select(SessionMeta).where(~SessionMeta.id.contains("--sa--"))
        if user_id:
            stmt = stmt.where(SessionMeta.user_id == user_id)
        stmt = stmt.order_by(SessionMeta.updated_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_recent_for_sidebar(
        self,
        user_id: str | None = None,
        days: int = 30,
        include_session_id: str | None = None,
    ) -> list[SessionMeta]:
        """List sidebar sessions from a rolling window without a global row cap."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        conditions = [
            ~SessionMeta.id.contains("--sa--"),
            SessionMeta.updated_at >= cutoff,
        ]
        if include_session_id:
            conditions[-1] = or_(
                SessionMeta.updated_at >= cutoff,
                SessionMeta.id == include_session_id,
            )
        stmt = select(SessionMeta).where(*conditions)
        if user_id:
            stmt = stmt.where(SessionMeta.user_id == user_id)
        stmt = stmt.order_by(SessionMeta.updated_at.desc())
        result = await self.session.execute(stmt)
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

        changed = False
        if "is_pinned" in kwargs:
            is_pinned = bool(kwargs.pop("is_pinned"))
            if sess.is_pinned != is_pinned:
                sess.is_pinned = is_pinned
                sess.pinned_at = datetime.now(timezone.utc) if is_pinned else None
                changed = True

        for key, value in kwargs.items():
            if hasattr(sess, key) and getattr(sess, key) != value:
                setattr(sess, key, value)
                changed = True

        if not changed:
            return sess

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

    async def list_children(self, parent_session_id: str) -> list[SessionMeta]:
        result = await self.session.execute(
            select(SessionMeta)
            .where(SessionMeta.parent_session_id == parent_session_id)
            .order_by(SessionMeta.created_at)
        )
        return list(result.scalars().all())

    async def increment_messages(self, session_id: str) -> None:
        sess = await self.get_by_id(session_id)
        if sess:
            sess.message_count += 1
            sess.updated_at = datetime.now(timezone.utc)
            await self.session.commit()


class AutomationTaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self, user_id: str | None = None) -> list[AutomationTask]:
        stmt = select(AutomationTask).order_by(AutomationTask.updated_at.desc())
        if user_id:
            stmt = stmt.where(AutomationTask.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, task_id: str) -> AutomationTask | None:
        return await self.session.get(AutomationTask, task_id)

    async def create(self, **kwargs) -> AutomationTask:
        task = AutomationTask(**kwargs)
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def update(self, task_id: str, **kwargs) -> AutomationTask | None:
        task = await self.get_by_id(task_id)
        if task is None:
            return None
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        task.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def delete(self, task_id: str) -> bool:
        task = await self.get_by_id(task_id)
        if task is None:
            return False
        await self.session.delete(task)
        await self.session.commit()
        return True


class AutomationRunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_task(self, task_id: str, limit: int = 50) -> list[AutomationRun]:
        result = await self.session.execute(
            select(AutomationRun)
            .where(AutomationRun.task_id == task_id)
            .order_by(AutomationRun.scheduled_at.desc(), AutomationRun.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_task(self, task_id: str) -> int:
        result = await self.session.execute(
            select(func.count(AutomationRun.id)).where(AutomationRun.task_id == task_id)
        )
        return int(result.scalar_one())

    async def list_active(self) -> list[AutomationRun]:
        result = await self.session.execute(
            select(AutomationRun).where(AutomationRun.status.in_(AUTOMATION_ACTIVE_STATUSES))
        )
        return list(result.scalars().all())

    async def list_active_by_task(self, task_id: str) -> list[AutomationRun]:
        result = await self.session.execute(
            select(AutomationRun).where(
                AutomationRun.task_id == task_id,
                AutomationRun.status.in_(AUTOMATION_ACTIVE_STATUSES),
            )
        )
        return list(result.scalars().all())

    async def list_all(self, user_id: str | None = None, limit: int = 100) -> list[AutomationRun]:
        stmt = (
            select(AutomationRun)
            .order_by(AutomationRun.scheduled_at.desc(), AutomationRun.created_at.desc())
            .limit(limit)
        )
        if user_id:
            stmt = stmt.where(AutomationRun.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_all(self, user_id: str | None = None) -> int:
        stmt = select(func.count(AutomationRun.id))
        if user_id:
            stmt = stmt.where(AutomationRun.user_id == user_id)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_by_id(self, run_id: str) -> AutomationRun | None:
        return await self.session.get(AutomationRun, run_id)

    async def create(self, **kwargs) -> AutomationRun | None:
        run = AutomationRun(**kwargs)
        self.session.add(run)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            return None
        await self.session.refresh(run)
        return run

    async def update(self, run_id: str, **kwargs) -> AutomationRun | None:
        run = await self.get_by_id(run_id)
        if run is None:
            return None
        for key, value in kwargs.items():
            if hasattr(run, key):
                setattr(run, key, value)
        await self.session.commit()
        await self.session.refresh(run)
        return run


class ChatUiMessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        session_id: str,
        role: str,
        content: list[dict] | None = None,
        tool_calls: list[dict] | None = None,
        usage: dict | None = None,
        http_traces: list[dict] | None = None,
    ) -> ChatUiMessage:
        message = ChatUiMessage(
            session_id=session_id,
            role=role,
            content=content or [],
            tool_calls=tool_calls,
            usage=usage,
            http_traces=http_traces,
        )
        self.session.add(message)
        await self.session.commit()
        try:
            await self.session.refresh(message)
        except Exception:
            pass
        return message

    async def list_by_session(
        self,
        session_id: str,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ChatUiMessage]:
        stmt = (
            select(ChatUiMessage)
            .where(ChatUiMessage.session_id == session_id)
            .order_by(ChatUiMessage.created_at, ChatUiMessage.id)
        )
        if offset > 0:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, message_id: str) -> ChatUiMessage | None:
        return await self.session.get(ChatUiMessage, message_id)

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

    async def get_last_assistant(self, session_id: str) -> ChatUiMessage | None:
        result = await self.session.execute(
            select(ChatUiMessage)
            .where(ChatUiMessage.session_id == session_id, ChatUiMessage.role == "assistant")
            .order_by(ChatUiMessage.created_at.desc(), ChatUiMessage.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_by_session(self, session_id: str) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(ChatUiMessage).where(ChatUiMessage.session_id == session_id)
        )
        return int(result.scalar_one())

    async def count_by_session_role(self, session_id: str, role: str) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(ChatUiMessage).where(
                ChatUiMessage.session_id == session_id,
                ChatUiMessage.role == role,
            )
        )
        return int(result.scalar_one())


class FileChangeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs) -> FileChange:
        fc = FileChange(**kwargs)
        self.session.add(fc)
        await self.session.commit()
        try:
            await self.session.refresh(fc)
        except Exception:
            pass
        return fc

    async def list_by_session(self, session_id: str) -> list[FileChange]:
        result = await self.session.execute(
            select(FileChange)
            .where(FileChange.session_id == session_id)
            .order_by(FileChange.created_at)
        )
        return list(result.scalars().all())

    async def delete_by_session(self, session_id: str) -> int:
        rows = await self.list_by_session(session_id)
        for row in rows:
            await self.session.delete(row)
        await self.session.commit()
        return len(rows)


GROUP_COLUMNS = {
    "user": "user_id",
    "agent": "agent_id",
    "model_id": "model_id",
    "raw_model_id": "raw_model_id",
    "provider": "provider",
    "role": "role",
}

_TOKEN_SUMS = (
    "sum(input_tokens)",
    "sum(output_tokens)",
    "sum(cache_read_tokens)",
    "sum(cache_write_tokens)",
    "sum(reasoning_tokens)",
)


def _bucket_expr(granularity: str) -> str:
    """按服务器本地时区切桶（token_stats.md §3.1，2026-09-07 定）。"""
    if granularity == "month":
        return "strftime('%Y-%m', datetime(ts, 'localtime'))"
    return "date(datetime(ts, 'localtime'))"


class UsageRepository:
    """llm_usage 聚合查询（docs/tasks/token_stats.md §5）。

    聚合 SQL 只做求和，不碰价格；金额在 Python 侧按 (bucket, model_id) 换算。
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _load_prices(self) -> list[ModelPrice]:
        """价格表全量载入（几十行），供会话金额归并使用。"""
        result = await self.session.execute(select(ModelPrice))
        return list(result.scalars().all())

    async def _usernames(self) -> dict[str, str]:
        """user_id -> username 映射，看板显示用户名而非 UUID。"""
        result = await self.session.execute(select(User.id, User.username))
        return {uid: uname for uid, uname in result.all()}

    async def _agent_names(self) -> dict[str, str]:
        """agent_id -> 展示名映射（预设 agent 用 display_name，内置/未知 id 回退原值）。"""
        result = await self.session.execute(
            select(AgentPresetDB.id, AgentPresetDB.display_name, AgentPresetDB.name)
        )
        return {aid: (disp or name) for aid, disp, name in result.all()}

    def _validate_group_by(self, group_by: list[str]) -> list[str]:
        for g in group_by:
            if g not in GROUP_COLUMNS and g != "bucket":
                raise ValueError(f"非法 group_by 值: {g}")
        return group_by

    async def summary(
        self,
        *,
        date_from: str,
        date_to: str,
        group_by: list[str],
        granularity: str = "day",
        include_sub: bool = True,
        user_id: str | None = None,
    ) -> list[dict]:
        """通用聚合：按 group_by 维度 + 时间桶求和。

        日期过滤在 localtime 表达式上进行，与切桶口径一致（否则边界 8 小时错位）。
        """
        self._validate_group_by(group_by)
        bucket = _bucket_expr(granularity)
        # 日期过滤恒按天切（"2026-09" 与 "2026-09-01" 字符串比较会错位漏行）
        where_bucket = _bucket_expr("day")
        select_parts = [f"{bucket} AS bucket", "model_id", "raw_model_id", "provider"]
        group_parts = ["bucket", "model_id", "raw_model_id", "provider"]
        for g in group_by:
            if g == "bucket":
                continue  # bucket 已在 select_parts 首位，重复别名会自引用报错
            col = GROUP_COLUMNS[g]
            select_parts.append(f"{col} AS \"{g}\"")
            if col not in group_parts:
                group_parts.append(col)
        select_parts.extend(_TOKEN_SUMS)
        select_parts.append("count(*) AS calls")

        sql = f"""
            SELECT {", ".join(select_parts)}
            FROM llm_usage
            WHERE {where_bucket} >= :date_from AND {where_bucket} <= :date_to
        """
        params: dict = {"date_from": date_from, "date_to": date_to}
        if not include_sub:
            sql += " AND role = 'main'"
        if user_id is not None:
            sql += " AND user_id = :user_id"
            params["user_id"] = user_id
        sql += f" GROUP BY {', '.join(group_parts)} ORDER BY bucket"

        result = await self.session.execute(text(sql), params)
        rows = []
        for r in result.mappings():
            rows.append({
                "bucket": r["bucket"],
                "model_id": r["model_id"],
                "raw_model_id": r["raw_model_id"],
                "provider": r["provider"],
                **({g: r[g] for g in group_by}),
                "input_tokens": r["sum(input_tokens)"] or 0,
                "output_tokens": r["sum(output_tokens)"] or 0,
                "cache_read_tokens": r["sum(cache_read_tokens)"] or 0,
                "cache_write_tokens": r["sum(cache_write_tokens)"] or 0,
                "reasoning_tokens": r["sum(reasoning_tokens)"] or 0,
                "calls": r["calls"] or 0,
            })
        if "user" in group_by:
            # user_id → username，看板与 CSV 显示用户名（查不到时回退原始 id）
            umap = await self._usernames()
            for row in rows:
                row["user"] = umap.get(row.get("user"), row.get("user"))
        if "agent" in group_by:
            # agent_id → 展示名，同上
            amap = await self._agent_names()
            for row in rows:
                row["agent"] = amap.get(row.get("agent"), row.get("agent"))
        return rows

    async def totals(
        self,
        *,
        date_from: str,
        date_to: str,
        include_sub: bool = True,
        user_id: str | None = None,
    ) -> dict:
        """全量合计（看板顶部卡片用）。"""
        bucket = _bucket_expr("day")
        sql = f"""
            SELECT
                sum(input_tokens) AS input_tokens,
                sum(output_tokens) AS output_tokens,
                sum(cache_read_tokens) AS cache_read_tokens,
                sum(cache_write_tokens) AS cache_write_tokens,
                count(*) AS calls,
                count(DISTINCT CASE WHEN user_id != '' THEN user_id END) AS active_users,
                count(DISTINCT session_id) AS session_count
            FROM llm_usage
            WHERE {bucket} >= :date_from AND {bucket} <= :date_to
        """
        params: dict = {"date_from": date_from, "date_to": date_to}
        if not include_sub:
            sql += " AND role = 'main'"
        if user_id is not None:
            sql += " AND user_id = :user_id"
            params["user_id"] = user_id
        result = await self.session.execute(text(sql), params)
        r = result.mappings().one()
        return {
            "input_tokens": r["input_tokens"] or 0,
            "output_tokens": r["output_tokens"] or 0,
            "cache_read_tokens": r["cache_read_tokens"] or 0,
            "cache_write_tokens": r["cache_write_tokens"] or 0,
            "calls": r["calls"] or 0,
            "active_users": r["active_users"] or 0,
            "session_count": r["session_count"] or 0,
        }

    async def top_sessions(
        self,
        *,
        date_from: str,
        date_to: str,
        limit: int = 50,
        include_sub: bool = True,
        user_id: str | None = None,
    ) -> list[dict]:
        """消费最高的会话，join sessions 取标题/用户/agent。

        金额在（会话 × 天 × 模型）粒度算好后归并到会话——跨模型会话的钱不会算错；
        排序按金额降序（没配价的排后面，按 token 量兜底排序）。
        """
        bucket = _bucket_expr("day")
        sql = f"""
            SELECT u.session_id,
                   {bucket.replace('ts', 'u.ts')} AS bucket,
                   u.model_id,
                   u.raw_model_id,
                   max(u.agent_id) AS agent_id,
                   max(u.user_id) AS user_id,
                   max(s.title) AS title,
                   sum(u.input_tokens) AS input_tokens,
                   sum(u.output_tokens) AS output_tokens,
                   sum(u.cache_read_tokens) AS cache_read_tokens,
                   sum(u.cache_write_tokens) AS cache_write_tokens,
                   count(*) AS calls
            FROM llm_usage u
            LEFT JOIN sessions s ON s.id = u.session_id
            WHERE {bucket.replace('ts', 'u.ts')} >= :date_from
              AND {bucket.replace('ts', 'u.ts')} <= :date_to
        """
        params: dict = {"date_from": date_from, "date_to": date_to}
        if not include_sub:
            sql += " AND u.role = 'main'"
        if user_id is not None:
            sql += " AND u.user_id = :user_id"
            params["user_id"] = user_id
        sql += """
            GROUP BY u.session_id, bucket, u.model_id, u.raw_model_id
        """
        result = await self.session.execute(text(sql), params)
        umap = await self._usernames()
        amap = await self._agent_names()

        # （会话 × 天 × 模型）粒度算钱（桶末时刻匹配当时生效价）
        prices = await self._load_prices()
        sessions: dict[str, dict] = {}
        for r in result.mappings():
            at = bucket_end(r["bucket"], "day")
            cost = compute_cost(
                {
                    "input": r["input_tokens"] or 0,
                    "output": r["output_tokens"] or 0,
                    "cache_read": r["cache_read_tokens"] or 0,
                    "cache_write": r["cache_write_tokens"] or 0,
                },
                resolve_prices_for(prices, r["model_id"] or "", r["raw_model_id"] or "", at),
            )
            sid = r["session_id"]
            agg = sessions.get(sid)
            if agg is None:
                agg = sessions[sid] = {
                    "session_id": sid,
                    "title": r["title"] or "(无标题)",
                    "user_id": r["user_id"] or "",
                    "username": umap.get(r["user_id"] or "", r["user_id"] or ""),
                    "agent_id": r["agent_id"] or "",
                    "agent_name": amap.get(r["agent_id"] or "", r["agent_id"] or ""),
                    "model_id": r["model_id"] or "",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read_tokens": 0,
                    "cache_write_tokens": 0,
                    "calls": 0,
                    "cost": 0.0,
                    "_cost_missing": False,
                    "_unpriced": set(),
                }
            if r["model_id"] and not agg["model_id"]:
                agg["model_id"] = r["model_id"]
            agg["input_tokens"] += r["input_tokens"] or 0
            agg["output_tokens"] += r["output_tokens"] or 0
            agg["cache_read_tokens"] += r["cache_read_tokens"] or 0
            agg["cache_write_tokens"] += r["cache_write_tokens"] or 0
            agg["calls"] += r["calls"] or 0
            if cost is None:
                agg["_cost_missing"] = True
                agg["_unpriced"].add(r["model_id"] or r["raw_model_id"] or "")
            else:
                agg["cost"] += cost

        rows = list(sessions.values())
        for row in rows:
            if row["_cost_missing"]:
                row["cost"] = None  # 有没配价的部分，整体显示「—」
            else:
                row["cost"] = round(row["cost"], 4)
            row.pop("_cost_missing")
            row["unpriced_models"] = sorted(row.pop("_unpriced"))
        rows.sort(
            key=lambda x: (
                x["cost"] is None,  # 配了价的排前面
                x["cost"] or 0,
                x["input_tokens"] + x["output_tokens"],  # 没配价的按 token 量兜底
            ),
            reverse=True,
        )
        return rows[:limit]

    async def session_detail(self, session_id: str) -> list[dict]:
        """下钻：某会话每次 LLM 调用的明细（含按当天生效价算的单次金额）。"""
        prices = await self._load_prices()
        result = await self.session.execute(
            select(LlmUsage)
            .where(LlmUsage.session_id == session_id)
            .order_by(LlmUsage.ts)
        )
        rows = []
        for u in result.scalars().all():
            cost = None
            if u.ts is not None:
                # ts 存 naive UTC（utcnow），与 SQL 的 datetime(ts,'localtime') 同口径转本地
                local_naive = u.ts.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
                at = local_naive.replace(hour=23, minute=59, second=59)  # 当天桶末匹配生效价
                cost = compute_cost(
                    {
                        "input": u.input_tokens,
                        "output": u.output_tokens,
                        "cache_read": u.cache_read_tokens,
                        "cache_write": u.cache_write_tokens,
                    },
                    resolve_prices_for(prices, u.model_id, u.raw_model_id, at),
                )
            rows.append({
                "ts": u.ts.isoformat() if u.ts else None,
                "model_id": u.model_id,
                "raw_model_id": u.raw_model_id,
                "provider": u.provider,
                "role": u.role,
                "source": u.source,
                "input_tokens": u.input_tokens,
                "output_tokens": u.output_tokens,
                "cache_read_tokens": u.cache_read_tokens,
                "cache_write_tokens": u.cache_write_tokens,
                "reasoning_tokens": u.reasoning_tokens,
                "duration_ms": u.duration_ms,
                "cost": cost,
            })
        return rows

    # ---- 单价维护（单行制：一个 (model, kind) 只有一条，保存即 upsert 覆盖）----

    async def list_pricing(self) -> list[ModelPrice]:
        result = await self.session.execute(
            select(ModelPrice).order_by(ModelPrice.model, ModelPrice.kind)
        )
        return list(result.scalars().all())

    async def add_pricing(
        self, *, model: str, kind: str, price_per_1m: float,
        effective_from: datetime | None = None, note: str = "",
    ) -> ModelPrice:
        if kind not in ("input", "output", "cache_read", "cache_write"):
            raise ValueError(f"非法 kind: {kind}")
        existing = await self.session.execute(
            select(ModelPrice).where(ModelPrice.model == model, ModelPrice.kind == kind)
        )
        price = existing.scalars().first()
        if price is None:
            price = ModelPrice(
                model=model,
                kind=kind,
                price_per_1m=price_per_1m,
                effective_from=effective_from or datetime.now(timezone.utc),
                note=note,
            )
            self.session.add(price)
        else:
            price.price_per_1m = price_per_1m
            price.note = note
        await self.session.commit()
        await self.session.refresh(price)
        return price
