"""Token 用量统计测试（docs/tasks/token_stats.md §8 验收）。"""

from datetime import datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text as sql_text
from sqlalchemy.exc import IntegrityError
from starlette.routing import Mount

from lc_agent.app import LcAgentApp
from lc_agent.config.runtime import reset_config, set_config
from lc_agent.db.engine import init_db, reset_engine
from lc_agent.db.models import SessionMeta
from lc_agent.db.models_usage import LlmUsage, ModelPrice
from lc_agent.db.repository import UsageRepository
from lc_agent.server import stream_utils
from lc_agent.server.routes.usage import router as usage_router
from lc_agent.server.usage_pricing import bucket_end, compute_cost, resolve_prices_for
from lc_agent.server.usage_recorder import record_usage
from tests.conftest import setup_test_auth


# ---------- 事件构造 ----------

class _FakeOutput:
    def __init__(self, usage: dict | None = None, model_name: str | None = None):
        if usage is not None:
            self.usage_metadata = usage
        if model_name is not None:
            self.response_metadata = {"model_name": model_name}


def _chat_event(usage: dict | None = None, model_name: str | None = None, checkpoint_ns: str = "") -> dict:
    metadata = {"langgraph_checkpoint_ns": checkpoint_ns}
    if model_name:
        metadata["ls_model_name"] = model_name
    return {
        "event": "on_chat_model_end",
        "data": {"output": _FakeOutput(usage, model_name)},
        "metadata": metadata,
    }


def _usage(input_t=1000, output_t=100, cache_read=0, cache_creation=0):
    return {
        "input_tokens": input_t,
        "output_tokens": output_t,
        "total_tokens": input_t + output_t,
        "input_token_details": {"cache_read": cache_read, "cache_creation": cache_creation},
    }


# ---------- accumulate_usage ----------

def test_accumulate_usage_main_role_and_model():
    rounds = []
    event = _chat_event(_usage(1000, 200, cache_read=50), model_name="test-model")
    stream_utils.accumulate_usage(event, rounds, default_model_id="test-model")
    assert len(rounds) == 1
    r = rounds[0]
    assert r["role"] == "main"
    assert r["sub_session_id"] == ""
    assert r["model_id"] == "test-model"
    assert r["input_tokens"] == 1000
    assert r["cache_read_tokens"] == 50
    assert "duration_ms" not in r  # duration 由调用方在 append 后补


def test_accumulate_usage_sub_role_tagged_not_skipped():
    """§1 问题 1：子 agent 的 LLM 调用不再被丢弃，而是打 role=sub 标记。"""
    rounds = []
    event = _chat_event(_usage(5000, 800), checkpoint_ns="tools:tc-123|agent")
    stream_utils.accumulate_usage(event, rounds, default_model_id="test-model")
    assert len(rounds) == 1
    r = rounds[0]
    assert r["role"] == "sub"
    assert r["sub_session_id"] == "tc-123"


def test_accumulate_usage_model_resolution_via_raw_name():
    """中转站回显上游原始名时，能通过 raw_model_id 反查配置条目。"""

    class _Info:
        model_id = "zzz-gpt-5.4"
        raw_model_id = "gpt-5.4"
        provider = "litellm"

    rounds = []
    event = _chat_event(_usage(), model_name="gpt-5.4")
    stream_utils.accumulate_usage(event, rounds, default_model_id="zzz-gpt-5.4", model_map={"gpt-5.4": _Info(), "zzz-gpt-5.4": _Info()})
    assert rounds[0]["model_id"] == "zzz-gpt-5.4"
    assert rounds[0]["raw_model_id"] == "gpt-5.4"
    assert rounds[0]["provider"] == "litellm"


def test_accumulate_usage_cache_write():
    rounds = []
    event = _chat_event(_usage(cache_creation=300))
    stream_utils.accumulate_usage(event, rounds, default_model_id="test-model")
    assert rounds[0]["cache_write_tokens"] == 300


def test_accumulate_usage_unknown_model_fallback():
    rounds = []
    event = _chat_event(_usage(), model_name="")
    stream_utils.accumulate_usage(event, rounds)  # 无默认、无 map
    assert rounds[0]["model_id"] == "unknown"


# ---------- usage_recorder ----------

@pytest.fixture
async def db_env(tmp_path):
    reset_engine()
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'usage.db'}"
    await init_db(db_url)
    set_config({"database": {"url": db_url}})
    yield db_url
    reset_engine()
    reset_config()


async def _add_sub_session(db_url: str, sub_id: str, parent_id: str, agent_id: str = "researcher", user_id: str = "u1"):
    from lc_agent.db.engine import get_async_session

    session = get_async_session(db_url)
    try:
        session.add(SessionMeta(
            id=sub_id, title="sub", agent_id=agent_id, model="", user_id=user_id,
            parent_session_id=parent_id, tool_call_id="tc-1",
        ))
        await session.commit()
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_record_usage_batch_and_sub_attribution(db_env):
    await _add_sub_session(db_env, "s-sub", "s-main")
    rows = [
        {"model_id": "m1", "raw_model_id": "r1", "provider": "p", "role": "main",
         "sub_session_id": "", "input_tokens": 10, "output_tokens": 5},
        {"model_id": "m1", "raw_model_id": "r1", "provider": "p", "role": "sub",
         "sub_session_id": "s-sub", "input_tokens": 100, "output_tokens": 50},
    ]
    inserted = await record_usage(
        rows, session_id="s-main", user_id="u1", agent_id="chat", run_id="run-1",
    )
    assert inserted == 2

    from lc_agent.db.engine import get_async_session

    session = get_async_session(db_env)
    try:
        result = await session.execute(sql_text("SELECT * FROM llm_usage ORDER BY seq"))
        all_rows = result.mappings().all()
        assert len(all_rows) == 2
        main_row, sub_row = all_rows
        assert main_row["role"] == "main" and main_row["agent_id"] == "chat"
        assert main_row["parent_session_id"] is None
        # 子 agent 归属：agent_id=子 agent，user_id=发起用户，parent=主会话（§9 第 12 条）
        assert sub_row["role"] == "sub" and sub_row["agent_id"] == "researcher"
        assert sub_row["user_id"] == "u1"
        assert sub_row["parent_session_id"] == "s-main"
        assert sub_row["run_id"] == "run-1" and sub_row["seq"] == 1
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_record_usage_run_seq_unique(db_env):
    """中断恢复重放：同 run_id+seq 二次提交不得产生重复行（§2.1 幂等键）。"""
    rows = [{"model_id": "m1", "raw_model_id": "r1", "provider": "p", "role": "main",
             "sub_session_id": "", "input_tokens": 10, "output_tokens": 5}]
    assert await record_usage(rows, session_id="s1", user_id="u1", agent_id="chat", run_id="run-x") == 1
    # 同 run_id 再次提交 → 唯一索引冲突，recorder 吞掉异常只记日志
    assert await record_usage(rows, session_id="s1", user_id="u1", agent_id="chat", run_id="run-x") == 0

    from lc_agent.db.engine import get_async_session

    session = get_async_session(db_env)
    try:
        count = (await session.execute(sql_text("SELECT count(*) FROM llm_usage"))).scalar()
        assert count == 1
    finally:
        await session.close()


# ---------- 定价 ----------

def _price(model, kind, price, effective_from=None):
    return ModelPrice(model=model, kind=kind, price_per_1m=price,
                      effective_from=effective_from or datetime(2026, 1, 1))


def test_pricing_two_level_single_row():
    """单行制：一个 (model, kind) 只有一条，model_id 精确优先、raw 兜底。"""
    at = datetime(2026, 9, 7, 12, 0, 0)
    prices = [
        _price("gpt-5.4", "input", 2.0),
        _price("zzz-gpt-5.4", "input", 5.0),   # model_id 精确永远优先
    ]
    got = resolve_prices_for(prices, "zzz-gpt-5.4", "gpt-5.4", at)
    assert got["input"] == 5.0      # 两级链第 1 级命中即停
    got2 = resolve_prices_for(prices, "other-model", "gpt-5.4", at)
    assert got2["input"] == 2.0     # 兜底层命中
    assert got2["output"] is None   # 没配 output → None


def test_pricing_zero_means_free():
    """价格改成 0 = 明确免费（compute_cost 算出 0.0 而非 None）。"""
    prices = [_price("m", "input", 0.0), _price("m", "output", 0.0)]
    got = resolve_prices_for(prices, "m", "m")
    assert got["input"] == 0.0
    assert compute_cost({"input": 100, "output": 0, "cache_read": 0, "cache_write": 0}, got) == 0.0


def test_compute_cost_cache_read_replaces_full_price():
    """回归（2026-09-07 线上实锤）：input_tokens 已含 cache_read，
    命中缓存部分必须按缓存价**替代**输入全价，不是全价之外另加。
    93% 命中时旧公式多算 10 倍（¥1.20 → 实际 ¥0.13）。"""
    prices = {"input": 1.0, "output": 2.0, "cache_read": 0.02, "cache_write": 0.05}

    # 旧 bug 形态：1_000_000 输入全按 1.0 计 + 930_000 缓存又按 0.02 计 → ¥1.0186
    # 正确口径：净输入 70_000×1.0 + 缓存 930_000×0.02 → ¥0.0886
    cost = compute_cost(
        {"input": 1_000_000, "output": 0, "cache_read": 930_000, "cache_write": 0},
        prices,
    )
    assert cost == round((70_000 / 1e6) * 1.0 + (930_000 / 1e6) * 0.02, 4)

    # 写入缓存也属于 input_tokens 的明细，同样按写入缓存价**替代**输入全价：
    # 净输入 500_000×1.0 + 命中 300_000×0.02 + 写入 200_000×0.05
    cost4 = compute_cost(
        {"input": 1_000_000, "output": 0, "cache_read": 300_000, "cache_write": 200_000},
        prices,
    )
    assert cost4 == round(
        (500_000 / 1e6) * 1.0 + (300_000 / 1e6) * 0.02 + (200_000 / 1e6) * 0.05, 4
    )

    # 全命中：净输入为 0，只出缓存费
    cost2 = compute_cost(
        {"input": 100_000, "output": 0, "cache_read": 100_000, "cache_write": 0},
        prices,
    )
    assert cost2 == round((100_000 / 1e6) * 0.02, 4)

    # 无缓存：退化为净输入全价（与旧公式一致）
    cost3 = compute_cost(
        {"input": 100_000, "output": 0, "cache_read": 0, "cache_write": 0},
        prices,
    )
    assert cost3 == 0.1

    # 有 token 消耗但该维度没配价 → None（前端显示 —）
    assert compute_cost(
        {"input": 10, "output": 0, "cache_read": 0, "cache_write": 5_000},
        {"input": 1.0, "output": 2.0, "cache_read": 0.02, "cache_write": None},
    ) is None


def test_compute_cost_unpriced_returns_none():
    prices = {"input": 1.0, "output": None, "cache_read": 1.0, "cache_write": None}
    assert compute_cost({"input": 1_000_000}, prices) == 1.0
    assert compute_cost({"input": 1_000_000, "output": 100}, prices) is None  # 有消耗没价 → —
    assert compute_cost({"input": 0, "output": 0}, prices) == 0.0             # 全 0 = 免费


def test_bucket_end_day_and_month():
    assert bucket_end("2026-09-07", "day") == datetime(2026, 9, 7, 23, 59, 59)
    assert bucket_end("2026-09", "month") == datetime(2026, 9, 30, 23, 59, 59)
    assert bucket_end("2026-12", "month") == datetime(2026, 12, 31, 23, 59, 59)


# ---------- 聚合与 API ----------

async def _seed_usage(db_url: str):
    from lc_agent.db.engine import get_async_session

    session = get_async_session(db_url)
    try:
        session.add(LlmUsage(run_id="r1", seq=0, user_id="alice", session_id="s1", agent_id="chat",
                             model_id="m-a", raw_model_id="base-a", provider="p", role="main",
                             input_tokens=1_000_000, output_tokens=100_000))
        session.add(LlmUsage(run_id="r1", seq=1, user_id="alice", session_id="s-sub", agent_id="researcher",
                             model_id="m-a", raw_model_id="base-a", provider="p", role="sub",
                             sub_session_id="s-sub", input_tokens=500_000, output_tokens=50_000))
        session.add(LlmUsage(run_id="r2", seq=0, user_id="bob", session_id="s2", agent_id="chat",
                             model_id="m-b", raw_model_id="base-b", provider="p", role="main",
                             input_tokens=2_000_000, output_tokens=200_000))
        # effective_from 显式给 2000-01-01：月桶测试在 at=2000-01-31 解析价格，
        # 若用默认 utcnow（2026）则价格"尚未生效"→ resolve 返回 None
        session.add(ModelPrice(model="base-a", kind="input", price_per_1m=1.0,
                               effective_from=datetime(2000, 1, 1)))
        session.add(ModelPrice(model="base-a", kind="output", price_per_1m=4.0,
                               effective_from=datetime(2000, 1, 1)))
        session.add(ModelPrice(model="base-a", kind="cache_read", price_per_1m=0.0,
                               effective_from=datetime(2000, 1, 1)))
        await session.commit()
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_summary_merged_view_totals_match(db_env):
    """§8 验收：按 raw_model_id 归并与按 model_id 分组的合计必须一致。"""
    await _seed_usage(db_env)
    from lc_agent.db.engine import get_async_session

    session = get_async_session(db_env)
    try:
        repo = UsageRepository(session)
        by_model = await repo.summary(date_from="2000-01-01", date_to="2099-12-31",
                                      group_by=["model_id"], granularity="month")
        merged = await repo.summary(date_from="2000-01-01", date_to="2099-12-31",
                                    group_by=["raw_model_id"], granularity="month")
        t1 = sum(r["input_tokens"] + r["output_tokens"] for r in by_model)
        t2 = sum(r["input_tokens"] + r["output_tokens"] for r in merged)
        assert t1 == t2 == 3_850_000
        assert len(merged) == 2  # base-a / base-b 各一行
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_summary_and_top_sessions_resolve_display_names(db_env):
    """看板显示用户名 / agent 展示名，而非 UUID（未知 id 回退原值）。"""
    from lc_agent.db.engine import get_async_session

    session = get_async_session(db_env)
    try:
        from lc_agent.db.models import AgentPresetDB, SessionMeta
        from lc_agent.db.models_auth import User
        from lc_agent.db.models_usage import LlmUsage as U

        session.add(User(id="uid-alice", username="alice", password_hash="x", role="user"))
        session.add(User(id="uid-bob", username="bob", password_hash="x", role="user"))
        session.add(AgentPresetDB(id="preset-1", name="helper", display_name="助手智能体"))
        session.add(SessionMeta(id="s1", title="主会话", agent_id="preset-1", model="", user_id="uid-alice"))
        session.add(U(run_id="rn-1", seq=0, user_id="uid-alice", session_id="s1", agent_id="preset-1",
                      model_id="m-a", raw_model_id="base-a", provider="p", role="main",
                      input_tokens=1000, output_tokens=100))
        session.add(U(run_id="rn-2", seq=0, user_id="uid-bob", session_id="s2", agent_id="builtin-chat",
                      model_id="m-a", raw_model_id="base-a", provider="p", role="main",
                      input_tokens=2000, output_tokens=200))
        await session.commit()

        repo = UsageRepository(session)

        # summary：user/agent 维度替换成可读名称；未知 id（builtin-chat）回退原值
        rows = await repo.summary(date_from="2000-01-01", date_to="2099-12-31",
                                  group_by=["user", "agent"], granularity="month")
        users = {r["user"] for r in rows}
        agents = {r["agent"] for r in rows}
        assert users == {"alice", "bob"}
        assert agents == {"助手智能体", "builtin-chat"}

        # top_sessions：返回 username / agent_name 附加字段
        srows = await repo.top_sessions(date_from="2000-01-01", date_to="2099-12-31")
        by_session = {r["session_id"]: r for r in srows}
        assert by_session["s1"]["username"] == "alice"
        assert by_session["s1"]["agent_name"] == "助手智能体"
        assert by_session["s2"]["agent_name"] == "builtin-chat"
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_month_bucket_filter_and_per_row_cost(db_env):
    """回归（2026-09-07 线上双 bug）：
    1. 月桶筛选：WHERE 必须按天切再归月，否则 "2026-09" < "2026-09-01" 恒漏行 → 总消耗恒 0
    2. 金额缓存：同 (bucket, model) 多行 token 数不同，金额必须各算各的（此前缓存了金额复用）
    """
    from datetime import datetime

    from lc_agent.server.usage_pricing import load_price_table

    await _seed_usage(db_env)
    from lc_agent.db.engine import get_async_session

    session = get_async_session(db_env)
    try:
        repo = UsageRepository(session)

        # bug1：窄日期范围 + 月粒度，旧行为返回 0 行
        rows = await repo.summary(date_from="2000-01-01", date_to="2000-01-31",
                                  group_by=["bucket"], granularity="month")
        assert len(rows) == 0  # 范围外无数据
        rows = await repo.summary(date_from="2000-01-01", date_to="2099-12-31",
                                  group_by=["bucket"], granularity="month")
        assert len(rows) >= 1  # 有数据时月桶必须出得来
        assert rows[0]["bucket"].count("-") == 1  # %Y-%m 格式

        # bug2：同 (bucket, model) 两行 token 不同 → 金额必须不同
        # m-a 走 base-a 兜底价 input 1.0 / output 4.0（_seed_usage 种的）
        prices = await load_price_table(session)
        two_rows = [
            {"bucket": "2000-01", "model_id": "m-a", "raw_model_id": "base-a",
             "input_tokens": 100, "output_tokens": 10, "cache_read_tokens": 0, "cache_write_tokens": 0},
            {"bucket": "2000-01", "model_id": "m-a", "raw_model_id": "base-a",
             "input_tokens": 5_000_000, "output_tokens": 500_000, "cache_read_tokens": 0, "cache_write_tokens": 0},
        ]
        at = datetime(2000, 1, 31, 23, 59, 59)
        for r in two_rows:
            from lc_agent.server.usage_pricing import compute_cost, resolve_prices_for
            kp = resolve_prices_for(prices, r["model_id"], r["raw_model_id"], at)
            r["cost"] = compute_cost({"input": r["input_tokens"], "output": r["output_tokens"],
                                      "cache_read": 0, "cache_write": 0}, kp)
        assert two_rows[0]["cost"] == 0.0001  # 100×1.0/1M + 10×4/1M = 0.00014 → round4 = 0.0001
        assert two_rows[1]["cost"] == 7.0     # 5×1.0 + 0.5M×4/1M=2.0
        assert two_rows[0]["cost"] != two_rows[1]["cost"]
    finally:
        await session.close()


@pytest.fixture
async def app_with_usage(tmp_path):
    reset_engine()
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'usage_api.db'}"
    await init_db(db_url)
    await _seed_usage(db_url)
    config = {
        "provider": {
            "default": {
                "base_url": "https://api.example.com/v1",
                "api_key": "sk-test",
                "models": [{"model_id": "m-a", "raw_model_id": "base-a", "context_limit": 8000}],
            }
        },
        "agent": {"default_model": "m-a", "system_prompt": "Test"},
        "database": {"url": db_url, "checkpoint_path": ":memory:"},
    }
    app_instance = LcAgentApp(config)
    headers = await setup_test_auth(app_instance.fastapi_app)
    routes = app_instance.fastapi_app.router.routes
    mounts = [r for r in routes if isinstance(r, Mount)]
    app_instance.fastapi_app.router.routes = [r for r in routes if not isinstance(r, Mount)]
    app_instance.fastapi_app.include_router(usage_router, prefix="/api")
    app_instance.fastapi_app.router.routes.extend(mounts)
    yield app_instance, headers
    reset_engine()


@pytest.mark.asyncio
async def test_summary_merges_models_when_not_grouped(db_env):
    """回归：只按用户分组时，同天同用户的多模型行必须合并成一行
    （SQL 永远按最细粒度返回，归并在 _annotate_cost 按勾选维度做）。"""
    from lc_agent.db.engine import get_async_session
    from lc_agent.server.routes.usage import _annotate_cost

    session = get_async_session(db_env)
    try:
        session.add(LlmUsage(run_id="g1", seq=0, user_id="alice", session_id="s1", agent_id="chat",
                             model_id="m-a", raw_model_id="base-a", provider="p", role="main",
                             input_tokens=1000, output_tokens=100))
        session.add(LlmUsage(run_id="g2", seq=0, user_id="alice", session_id="s1", agent_id="chat",
                             model_id="m-b", raw_model_id="base-b", provider="p", role="main",
                             input_tokens=2000, output_tokens=200))
        session.add(ModelPrice(model="base-a", kind="input", price_per_1m=1.0,
                               effective_from=datetime(2000, 1, 1)))
        session.add(ModelPrice(model="base-a", kind="output", price_per_1m=4.0,
                               effective_from=datetime(2000, 1, 1)))
        session.add(ModelPrice(model="base-b", kind="input", price_per_1m=2.0,
                               effective_from=datetime(2000, 1, 1)))
        session.add(ModelPrice(model="base-b", kind="output", price_per_1m=1.0,
                               effective_from=datetime(2000, 1, 1)))
        await session.commit()

        repo = UsageRepository(session)
        rows = await repo.summary(date_from="2000-01-01", date_to="2099-12-31",
                                  group_by=["user"], granularity="month")
        # SQL 侧仍是两行（按模型拆开）
        assert len(rows) == 2
        merged = await _annotate_cost(session, rows, "month", ["user"])
        # 归并后同月同用户只剩一行，token 求和、金额按各模型分别算后相加
        assert len(merged) == 1
        assert merged[0]["unpriced_models"] == []  # 两个模型都配了价 → 名单为空
        assert merged[0]["input_tokens"] == 3000
        assert merged[0]["output_tokens"] == 300
        assert merged[0]["cost"] == round(1000 / 1e6 * 1.0 + 100 / 1e6 * 4.0
                                          + 2000 / 1e6 * 2.0 + 200 / 1e6 * 1.0, 4)
        assert "model_id" not in merged[0]
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_admin_summary_api(app_with_usage):
    app, headers = app_with_usage
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/admin/usage/summary",
            params={"from": "2000-01-01", "to": "2099-12-31", "group_by": "user,bucket,model_id", "granularity": "month"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["rows"]) >= 2
        for row in data["rows"]:
            assert "cost" in row
        # m-a 配了价 → 金额算得出；m-b 没配 → None
        costs = {r["model_id"]: r["cost"] for r in data["rows"]}
        assert costs["m-a"] is not None
        assert costs["m-b"] is None


@pytest.mark.asyncio
async def test_me_usage_locked_to_current_user(app_with_usage):
    """/me/usage 只能看到自己的；user_id 服务端锁定（§8 验收）。"""
    app, headers = app_with_usage
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/me/usage",
            params={"from": "2000-01-01", "to": "2099-12-31", "group_by": "model_id", "granularity": "month"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # 测试管理员（testadmin）没有用量行 —— alice/bob 的数据不可见
        assert data["rows"] == []
        assert data["totals"]["input_tokens"] == 0


@pytest.mark.asyncio
async def test_admin_endpoints_require_admin(app_with_usage):
    """无 token 访问 admin 端点必须被拒。"""
    app, _ = app_with_usage
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/admin/usage/summary", params={"from": "2026-01-01", "to": "2026-12-31"})
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_pricing_post_then_summary_shows_cost(app_with_usage):
    """录价后金额从 — 变为有值；有消耗的维度缺价则整体仍为 —。单行制 upsert 可覆盖。"""
    app, headers = app_with_usage
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 只配 input：m-b 的 output 有消耗但没价 → 金额仍是 —
        resp = await client.post(
            "/api/admin/usage/pricing",
            json={"model": "base-b", "kind": "input", "price_per_1m": 2.0},
            headers=headers,
        )
        assert resp.status_code == 201
        resp = await client.get(
            "/api/admin/usage/summary",
            params={"from": "2000-01-01", "to": "2099-12-31", "group_by": "model_id", "granularity": "month"},
            headers=headers,
        )
        costs = {r["model_id"]: r["cost"] for r in resp.json()["rows"]}
        assert costs["m-b"] is None

        # 补上 output 价后金额算得出：2M×2.0 + 0.2M×1.0 = 4.2
        resp = await client.post(
            "/api/admin/usage/pricing",
            json={"model": "base-b", "kind": "output", "price_per_1m": 1.0},
            headers=headers,
        )
        assert resp.status_code == 201
        # 同 key 再保存一次 = 覆盖而非新增（单行制 upsert）
        resp = await client.post(
            "/api/admin/usage/pricing",
            json={"model": "base-b", "kind": "output", "price_per_1m": 1.0},
            headers=headers,
        )
        assert resp.status_code == 201
        resp = await client.get(
            "/api/admin/usage/summary",
            params={"from": "2000-01-01", "to": "2099-12-31", "group_by": "model_id", "granularity": "month"},
            headers=headers,
        )
        costs = {r["model_id"]: r["cost"] for r in resp.json()["rows"]}
        assert costs["m-b"] == 4.2


@pytest.mark.asyncio
async def test_merged_rows_report_unpriced_models(app_with_usage):
    """回归（2026-09-10）：不按模型分组时，归并行不能丢"哪个模型没配价"的信息。

    此前归并只回 cost=None，前端拿不到模型名 → 页面显示 — 却没有提示；
    现在每行（含归并行）都带 unpriced_models，summary / totals 响应顶层再带一份汇总。
    """
    app, headers = app_with_usage
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/admin/usage/summary",
            params={"from": "2000-01-01", "to": "2099-12-31", "group_by": "user", "granularity": "month"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["rows"]) == 2  # alice / bob 各一行（已归并）
        for row in data["rows"]:
            assert "model_id" not in row  # 归并行不带模型列
            assert "unpriced_models" in row
        by_user = {r["user"]: r for r in data["rows"]}
        assert by_user["alice"]["cost"] is not None
        assert by_user["alice"]["unpriced_models"] == []
        assert by_user["bob"]["cost"] is None
        assert by_user["bob"]["unpriced_models"] == ["m-b"]
        assert data["unpriced_models"] == ["m-b"]

        resp = await client.get(
            "/api/admin/usage/totals",
            params={"from": "2000-01-01", "to": "2099-12-31"},
            headers=headers,
        )
        assert resp.status_code == 200
        totals = resp.json()
        assert totals["cost"] is None
        assert totals["unpriced_models"] == ["m-b"]
