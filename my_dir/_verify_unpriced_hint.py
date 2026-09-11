# 用真实 bfzs 数据验证：金额为 — 时能说清是哪个模型没配价（2026-09-10）
import asyncio
import sys

sys.path.insert(0, r'D:\codes\lc-agent')

from lc_agent.db.engine import get_async_session
from lc_agent.db.repository import UsageRepository
from lc_agent.server.routes.usage import (
    _annotate_cost,
    _compute_total_cost,
    collect_unpriced_models,
)

DB = 'sqlite+aiosqlite:///D:/codes/lc-agent-bfzs/bfzs_data.db'


async def main():
    session = get_async_session(DB)
    try:
        repo = UsageRepository(session)

        # 1) 复刻截图参数：按用户分组、按天
        rows = await repo.summary(date_from='2026-09-01', date_to='2026-09-10',
                                  group_by=['user'], granularity='day', include_sub=True)
        rows = await _annotate_cost(session, rows, 'day', ['user'])
        print('--- 按用户分组（截图同款）---')
        for r in rows:
            cost = '—' if r['cost'] is None else r['cost']
            print(f"  {r['bucket']} {str(r.get('user','')):20s} cost={str(cost):>8s} unpriced={r['unpriced_models']}")
        print('  顶层名单:', collect_unpriced_models(rows))

        # 2) 总消耗卡片数据
        cost, unpriced = await _compute_total_cost(
            repo, session, date_from='2026-09-01', date_to='2026-09-10', include_sub=True)
        print('--- totals（总消耗卡片）---')
        print('  cost =', cost, '  unpriced =', unpriced)

        # 3) 按模型分组
        rows2 = await repo.summary(date_from='2026-09-01', date_to='2026-09-10',
                                   group_by=['model_id'], granularity='day', include_sub=True)
        rows2 = await _annotate_cost(session, rows2, 'day', ['model_id'])
        print('--- 按模型分组（只列金额为 — 的）---')
        for r in rows2:
            if r['cost'] is None:
                print(f"  {r['bucket']} {r['model_id']:38s} cost=— unpriced={r['unpriced_models']}")

        # 4) 会话表
        srows = await repo.top_sessions(date_from='2026-09-01', date_to='2026-09-10', include_sub=True)
        print('--- 消费最高会话（只列金额为 — 的）---')
        for r in srows:
            if r['cost'] is None:
                print(f"  {str(r['title'])[:26]:28s} cost=— unpriced={r['unpriced_models']}")
    finally:
        await session.close()


asyncio.run(main())
