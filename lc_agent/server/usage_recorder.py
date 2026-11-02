"""Token 用量落库（docs/tasks/token_stats.md §4.3）。

- 批量 insert（不做单条写，避免 SQLite 写放大）
- 只落原始 token，不查价格、不算钱（价格留给查询时算）
- role=sub 的行：从 sessions 表按 sub_session_id 反查子会话的 agent_id / user_id /
  parent_session_id（子会话由 SubAgentRunTracker 在流内创建，记录点在 drain 之后必然存在；
  查不到就退回主会话上下文）
- 失败只记日志，绝不能因为统计失败打断对话流
"""

import time
import uuid
from typing import Any

from sqlalchemy import select

from lc_agent.utils.error_text import safe_error_text
from lc_agent.utils.loggers import server_logger


def is_usage_stats_enabled() -> bool:
    """usage_stats.enabled 开关：False 只关采集，已落库数据照常可查（§3.4）。"""
    try:
        from lc_agent.config import get_config

        conf = get_config().get("usage_stats") or {}
        return bool(conf.get("enabled", True))
    except Exception:
        return True


def build_model_map(engine) -> dict[str, Any]:
    """构建 model_id / raw_model_id → ModelInfo 的双向查找表。

    中转站可能把上游原始模型名回显在 response_metadata 里，
    所以 raw_model_id 也要能映射回配置条目（token_stats.md §4.1）。
    """
    mapping: dict[str, Any] = {}
    try:
        for m in engine.get_models():
            mapping[m.model_id] = m
            if m.raw_model_id and m.raw_model_id not in mapping:
                mapping[m.raw_model_id] = m
    except Exception:
        server_logger.exception("Failed to build model map for usage recording")
    return mapping


async def record_usage(
    rows: list[dict],
    *,
    session_id: str,
    user_id: str,
    agent_id: str,
    source: str = "chat",
    run_id: str | None = None,
) -> int:
    """把一次 invoke 的 usage_rounds 批量落库，返回写入行数。

    rows 的每一项由 accumulate_usage 产出（含 model_id / role / sub_session_id /
    raw_model_id / provider），缺 model_id 的兜底为 "unknown" —— 宁可 unknown 也不能丢行。
    (run_id, seq) 已存在的行直接跳过，保证中断恢复/重放不会重复插入。
    """
    if not rows:
        return 0
    if not is_usage_stats_enabled():
        return 0

    run_id = run_id or str(uuid.uuid4())

    # role=sub 的行：从子会话记录反查归属（一次 IN 查询，不做逐行往返）
    sub_ids = {r.get("sub_session_id", "") for r in rows if r.get("role") == "sub" and r.get("sub_session_id")}
    sub_info: dict[str, dict] = {}
    if sub_ids:
        try:
            from lc_agent.db.engine import get_business_async_session
            from lc_agent.db.models import SessionMeta

            session = get_business_async_session()
            try:
                result = await session.execute(
                    select(SessionMeta).where(SessionMeta.id.in_(sub_ids))
                )
                for s in result.scalars().all():
                    sub_info[s.id] = {
                        "agent_id": s.agent_id or "subagent",
                        "user_id": s.user_id or user_id,
                        "parent_session_id": s.parent_session_id or session_id,
                    }
            finally:
                await session.close()
        except Exception as e:
            server_logger.error(
                "Failed to resolve sub-session info for usage recording: %s",
                safe_error_text(e),
            )

    from lc_agent.db.engine import get_business_async_session
    from lc_agent.db.models_usage import LlmUsage

    try:
        session = get_business_async_session()
        try:
            values = []
            for seq, r in enumerate(rows):
                role = r.get("role", "main")
                model_id = r.get("model_id") or "unknown"
                # 行内 source 优先（如摘要调用自带 source="summarize"），缺省用调用方传入的 source
                row_source = r.get("source") or source
                if role == "sub":
                    info = sub_info.get(r.get("sub_session_id", ""), {})
                    row_agent_id = info.get("agent_id", "subagent")
                    row_user_id = info.get("user_id", user_id)
                    row_parent = info.get("parent_session_id", session_id)
                else:
                    row_agent_id = agent_id
                    row_user_id = user_id
                    row_parent = None

                values.append({
                    "ts": r.get("ts") or _now(),
                    "user_id": row_user_id,
                    "session_id": session_id,
                    "parent_session_id": row_parent,
                    "agent_id": row_agent_id,
                    "model_id": model_id,
                    "raw_model_id": r.get("raw_model_id") or "",
                    "provider": r.get("provider") or "",
                    "role": role,
                    "sub_session_id": r.get("sub_session_id") or "",
                    "source": row_source,
                    "input_tokens": int(r.get("input_tokens") or 0),
                    "output_tokens": int(r.get("output_tokens") or 0),
                    "cache_read_tokens": int(r.get("cache_read_tokens") or 0),
                    "cache_write_tokens": int(r.get("cache_write_tokens") or 0),
                    "reasoning_tokens": int(r.get("reasoning_tokens") or 0),
                    "duration_ms": int(r.get("duration_ms") or 0),
                    "run_id": run_id,
                    "seq": seq,
                })

            # 先按 (run_id, seq) 过滤已落库的行：中断恢复/重放常把整批 usage 再提交一次，
            # 直接 add_all 会因唯一索引冲突丢掉同一批里的新行。
            existing = await session.execute(
                select(LlmUsage.seq).where(LlmUsage.run_id == run_id)
            )
            existing_seqs = set(existing.scalars().all())
            new_values = [v for v in values if v["seq"] not in existing_seqs]
            if not new_values:
                return 0

            session.add_all([LlmUsage(**v) for v in new_values])
            await session.commit()
            return len(new_values)
        finally:
            await session.close()
    except Exception as e:
        server_logger.error(
            "Failed to record usage rows (%d) for session %s: %s",
            len(rows), session_id, safe_error_text(e),
        )
        return 0


def _now():
    from lc_agent.db.models import utcnow

    return utcnow()
