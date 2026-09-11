"""Token 用量统计 API（docs/tasks/token_stats.md §5）。

/admin/usage/* 全部 require_admin；/me/usage 走普通登录态且 user_id 服务端强制锁定。
金额在查询时按当时生效价计算（§3.2），未配价显示 null（前端渲染 `—`，绝不用 0）。
"""

import csv
import io
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from lc_agent.db.models_auth import User
from lc_agent.db.repository import UsageRepository
from lc_agent.server.auth_middleware import get_current_user, require_admin
from lc_agent.server.dependencies import get_db_session
from lc_agent.server.usage_pricing import (
    bucket_end,
    compute_cost,
    load_price_table,
    resolve_prices_for,
)

router = APIRouter(tags=["usage"])

VALID_GROUP_BY = {"user", "agent", "model_id", "raw_model_id", "bucket"}


def _parse_range(from_d: str, to_d: str) -> tuple[str, str]:
    try:
        date.fromisoformat(from_d)
        date.fromisoformat(to_d)
    except ValueError:
        raise HTTPException(status_code=422, detail="日期格式必须为 YYYY-MM-DD")
    if from_d > to_d:
        raise HTTPException(status_code=422, detail="from 不能晚于 to")
    return from_d, to_d


def _parse_group_by(group_by: str) -> list[str]:
    items = [g.strip() for g in group_by.split(",") if g.strip()]
    bad = [g for g in items if g not in VALID_GROUP_BY]
    if bad:
        raise HTTPException(status_code=422, detail=f"非法 group_by 值: {','.join(bad)}")
    return items


async def _price_rows(db: AsyncSession):
    return await load_price_table(db)


async def _annotate_cost(
    db: AsyncSession,
    rows: list[dict],
    granularity: str,
    group_by: list[str] | None = None,
) -> list[dict]:
    """换算金额。SQL 永远按最细粒度返回（见 UsageRepository.summary），
    这里按调用方实际勾选的维度归并：token 求和，金额按行内各模型分别算好再相加；
    任一模型没配价则整行 cost 为 None（前端显示 —），
    同时把没配价的模型名写进该行 unpriced_models，供页面提示"是哪个模型没设价"。"""
    prices = await _price_rows(db)
    # 缓存解析出的"各 kind 单价"而非金额——同 (bucket, model) 的多行 token 数不同，金额必须各算各的
    price_cache: dict[tuple, dict[str, float | None]] = {}
    group_by = group_by or []

    def _cost_of(row: dict) -> float | None:
        key = (row["bucket"], row["model_id"])
        if key not in price_cache:
            at = bucket_end(row["bucket"], granularity)
            price_cache[key] = resolve_prices_for(prices, row["model_id"], row["raw_model_id"], at)
        return compute_cost(
            {
                "input": row["input_tokens"],
                "output": row["output_tokens"],
                "cache_read": row["cache_read_tokens"],
                "cache_write": row["cache_write_tokens"],
            },
            price_cache[key],
        )

    # 没勾模型维度时：同 (bucket + 勾选维度) 的多行合并，金额按各模型分别算后相加
    if "model_id" not in group_by:
        merged: dict[tuple, dict] = {}
        for row in rows:
            mkey = (row["bucket"], *(row.get(g, "") for g in group_by if g != "bucket"))
            agg = merged.get(mkey)
            if agg is None:
                agg = merged[mkey] = {
                    "bucket": row["bucket"],
                    **({g: row.get(g, "") for g in group_by if g != "bucket"}),
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read_tokens": 0,
                    "cache_write_tokens": 0,
                    "reasoning_tokens": 0,
                    "calls": 0,
                    "cost": 0.0,
                    "_missing": False,
                    "_unpriced": set(),
                }
            agg["input_tokens"] += row["input_tokens"] or 0
            agg["output_tokens"] += row["output_tokens"] or 0
            agg["cache_read_tokens"] += row["cache_read_tokens"] or 0
            agg["cache_write_tokens"] += row["cache_write_tokens"] or 0
            agg["reasoning_tokens"] += row["reasoning_tokens"] or 0
            agg["calls"] += row["calls"] or 0
            c = _cost_of(row)
            if c is None:
                agg["_missing"] = True
                agg["_unpriced"].add(row["model_id"] or row["raw_model_id"])
            else:
                agg["cost"] += c
        out = []
        for agg in merged.values():
            if agg.pop("_missing"):
                agg["cost"] = None
            else:
                agg["cost"] = round(agg["cost"], 4)
            agg["unpriced_models"] = sorted(agg.pop("_unpriced"))
            out.append(agg)
        out.sort(key=lambda r: r["bucket"])
        return out

    for row in rows:
        cost = _cost_of(row)
        row["cost"] = cost
        row["unpriced_models"] = [row["model_id"] or row["raw_model_id"]] if cost is None else []
    return rows


def collect_unpriced_models(rows: list[dict]) -> list[str]:
    """本次查询里所有没配单价的模型（去重排序），供页面提示"是哪个模型没设价"。"""
    names: set[str] = set()
    for row in rows:
        names.update(row.get("unpriced_models") or [])
    return sorted(names)


@router.get("/admin/usage/summary")
async def admin_usage_summary(
    from_d: str = Query(alias="from"),
    to_d: str = Query(alias="to"),
    group_by: str = Query(default="bucket"),
    granularity: str = Query(default="day", pattern="^(day|month)$"),
    include_sub: bool = Query(default=True),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """通用聚合，group_by 支持多值组合（user,agent,model_id,raw_model_id,bucket）。"""
    date_from, date_to = _parse_range(from_d, to_d)
    dims = _parse_group_by(group_by)
    repo = UsageRepository(db)
    rows = await repo.summary(
        date_from=date_from, date_to=date_to,
        group_by=dims, granularity=granularity, include_sub=include_sub,
    )
    rows = await _annotate_cost(db, rows, granularity, dims)
    return {
        "rows": rows, "group_by": dims, "granularity": granularity,
        "unpriced_models": collect_unpriced_models(rows),
    }


async def _compute_total_cost(
    repo: UsageRepository,
    db: AsyncSession,
    *,
    date_from: str,
    date_to: str,
    include_sub: bool,
    user_id: str | None = None,
) -> tuple[float | None, list[str]]:
    """总金额 + 未配价模型名单。金额按月归桶逐桶算钱后求和（口径与明细一致）；
    None = 有模型没配价（前端显示 —，并提示是哪些模型没设价）。"""
    rows = await repo.summary(
        date_from=date_from, date_to=date_to,
        group_by=["bucket"], granularity="month", include_sub=include_sub,
        user_id=user_id,
    )
    rows = await _annotate_cost(db, rows, "month", ["bucket"])
    costs = [r["cost"] for r in rows]
    cost = None if any(c is None for c in costs) else round(sum(costs), 4)
    return cost, collect_unpriced_models(rows)


@router.get("/admin/usage/totals")
async def admin_usage_totals(
    from_d: str = Query(alias="from"),
    to_d: str = Query(alias="to"),
    include_sub: bool = Query(default=True),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """全局总量（看板顶部卡片：token 合计 / 活跃人数 / 调用次数）。"""
    date_from, date_to = _parse_range(from_d, to_d)
    repo = UsageRepository(db)
    totals = await repo.totals(date_from=date_from, date_to=date_to, include_sub=include_sub)
    totals["cost"], totals["unpriced_models"] = await _compute_total_cost(
        repo, db, date_from=date_from, date_to=date_to, include_sub=include_sub,
    )
    return totals


@router.get("/admin/usage/by-user")
async def admin_usage_by_user(
    from_d: str = Query(alias="from"),
    to_d: str = Query(alias="to"),
    include_sub: bool = Query(default=True),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """按人小计（token 求和 + 调用次数 + 金额）。"""
    date_from, date_to = _parse_range(from_d, to_d)
    repo = UsageRepository(db)
    rows = await repo.summary(
        date_from=date_from, date_to=date_to,
        group_by=["user"], granularity="month", include_sub=include_sub,
    )
    rows = await _annotate_cost(db, rows, "month", ["user"])
    rows.sort(key=lambda x: x["input_tokens"] + x["output_tokens"], reverse=True)
    return {"rows": rows, "unpriced_models": collect_unpriced_models(rows)}


@router.get("/admin/usage/by-agent")
async def admin_usage_by_agent(
    from_d: str = Query(alias="from"),
    to_d: str = Query(alias="to"),
    include_sub: bool = Query(default=True),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """按 agent 小计，支持含/仅主 agent 开关。"""
    date_from, date_to = _parse_range(from_d, to_d)
    repo = UsageRepository(db)
    rows = await repo.summary(
        date_from=date_from, date_to=date_to,
        group_by=["agent"], granularity="month", include_sub=include_sub,
    )
    rows = await _annotate_cost(db, rows, "month", ["agent"])
    rows.sort(key=lambda x: x["input_tokens"] + x["output_tokens"], reverse=True)
    return {"rows": rows, "unpriced_models": collect_unpriced_models(rows)}


@router.get("/admin/usage/top-sessions")
async def admin_usage_top_sessions(
    from_d: str = Query(alias="from"),
    to_d: str = Query(alias="to"),
    limit: int = Query(default=50, ge=1, le=500),
    include_sub: bool = Query(default=True),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """消费最高的会话（按金额降序）。"""
    date_from, date_to = _parse_range(from_d, to_d)
    repo = UsageRepository(db)
    return {
        "rows": await repo.top_sessions(
            date_from=date_from, date_to=date_to,
            limit=limit, include_sub=include_sub,
        )
    }


@router.get("/admin/usage/session/{session_id}")
async def admin_usage_session_detail(
    session_id: str,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """下钻：该会话每次调用明细。"""
    repo = UsageRepository(db)
    return {"rows": await repo.session_detail(session_id)}


@router.get("/admin/usage/export.csv")
async def admin_usage_export_csv(
    from_d: str = Query(alias="from"),
    to_d: str = Query(alias="to"),
    group_by: str = Query(default="user,bucket"),
    granularity: str = Query(default="day", pattern="^(day|month)$"),
    include_sub: bool = Query(default=True),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """CSV 导出，参数同 summary，含用户名/agent 名/金额。"""
    date_from, date_to = _parse_range(from_d, to_d)
    dims = _parse_group_by(group_by)
    repo = UsageRepository(db)
    rows = await repo.summary(
        date_from=date_from, date_to=date_to,
        group_by=dims, granularity=granularity, include_sub=include_sub,
    )
    rows = await _annotate_cost(db, rows, granularity, dims)
    for r in rows:
        r.pop("unpriced_models", None)  # 内部提示字段，不进 CSV

    buf = io.StringIO()
    writer = csv.writer(buf)
    header = list(rows[0].keys()) if rows else ["bucket"]
    writer.writerow(header)
    for r in rows:
        writer.writerow(["" if r.get(k) is None else r.get(k) for k in header])
    buf.seek(0)
    filename = f"usage_{date_from}_{date_to}.csv"
    return StreamingResponse(
        iter([buf.getvalue().encode("utf-8-sig")]),  # BOM：Excel 直接打开不乱码
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


class PriceCreateRequest(BaseModel):
    model: str = Field(min_length=1)
    kind: str = Field(pattern="^(input|output|cache_read|cache_write)$")
    price_per_1m: float = Field(ge=0)
    # 兼容旧前端字段：单行制无版本概念，传了也忽略
    effective_from: str = Field(default="", description="已废弃：单行制无生效日期，传了忽略")
    note: str = ""


def _serialize_price(p) -> dict:
    return {
        "id": p.id,
        "model": p.model,
        "kind": p.kind,
        "price_per_1m": p.price_per_1m,
        "currency": p.currency,
        "effective_from": p.effective_from.date().isoformat() if p.effective_from else None,
        "note": p.note,
    }


@router.get("/admin/usage/pricing")
async def list_pricing(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """当前价（单行制：一个 (model, kind) 只有一条）。"""
    repo = UsageRepository(db)
    return {"rows": [_serialize_price(p) for p in await repo.list_pricing()]}


@router.post("/admin/usage/pricing", status_code=201)
async def add_pricing(
    body: PriceCreateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """保存价格（单行制 upsert：同 (model, kind) 直接覆盖，无版本概念）。"""
    repo = UsageRepository(db)
    price = await repo.add_pricing(
        model=body.model,
        kind=body.kind,
        price_per_1m=body.price_per_1m,
        note=body.note,
    )
    return _serialize_price(price)


@router.get("/me/usage")
async def me_usage(
    from_d: str = Query(alias="from"),
    to_d: str = Query(alias="to"),
    group_by: str = Query(default="bucket"),
    granularity: str = Query(default="day", pattern="^(day|month)$"),
    include_sub: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """个人用量：与 admin 同源同口径，但 user_id 服务端强制锁为当前用户。"""
    date_from, date_to = _parse_range(from_d, to_d)
    dims = _parse_group_by(group_by)
    if "user" in dims:
        raise HTTPException(status_code=422, detail="个人用量不支持按 user 分组")
    repo = UsageRepository(db)
    rows = await repo.summary(
        date_from=date_from, date_to=date_to,
        group_by=dims, granularity=granularity,
        include_sub=include_sub,
        user_id=current_user.id,
    )
    rows = await _annotate_cost(db, rows, granularity, dims)
    totals = await repo.totals(
        date_from=date_from, date_to=date_to,
        include_sub=include_sub, user_id=current_user.id,
    )
    totals["cost"], totals["unpriced_models"] = await _compute_total_cost(
        repo, db, date_from=date_from, date_to=date_to,
        include_sub=include_sub, user_id=current_user.id,
    )
    return {
        "rows": rows, "totals": totals, "group_by": dims, "granularity": granularity,
        "unpriced_models": totals["unpriced_models"],
    }
