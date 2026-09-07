# lc_agent/core/checkpointer.py
"""Checkpointer factory for LangGraph — SQLite (WAL) or PostgreSQL.

LangGraph ships no generic SQLAlchemy checkpointer: the official implementations
live in separate namespace packages (`langgraph-checkpoint-sqlite` /
`langgraph-checkpoint-postgres`). So switching databases means picking a
different saver class, not just changing a URL. This module hides that.
"""

import logging

logger = logging.getLogger(__name__)

POSTGRES_SCHEMES = (
    "postgres://",
    "postgresql://",
    "postgresql+psycopg://",
    "postgresql+asyncpg://",
)

_SQLALCHEMY_PG_PREFIXES = (
    "postgresql+asyncpg://",
    "postgresql+psycopg://",
    "postgresql+psycopg2://",
)


def is_postgres_url(value: str) -> bool:
    """True when the value looks like a PostgreSQL URL rather than a file path."""
    return value.startswith(POSTGRES_SCHEMES)


def to_psycopg_conninfo(url: str) -> str:
    """Strip the SQLAlchemy driver suffix: psycopg only understands `postgresql://`."""
    for prefix in _SQLALCHEMY_PG_PREFIXES:
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix):]
    return url


class CheckpointerBundle:
    """A checkpointer plus the resources that must be released on shutdown."""

    def __init__(self, saver, closer=None):
        self.saver = saver
        self._closer = closer

    async def aclose(self):
        if self._closer is None:
            return
        try:
            await self._closer()
        except Exception:
            logger.exception("Failed to close checkpointer resources")


async def build_checkpointer(checkpoint_url: str, pool_max_size: int = 10) -> CheckpointerBundle:
    """Build a checkpointer from a SQLite file path or a PostgreSQL URL.

    Args:
        checkpoint_url: SQLite file path (may be `:memory:`) or PostgreSQL URL.
        pool_max_size: PostgreSQL connection pool size; ignored for SQLite.

    Returns:
        CheckpointerBundle: call `.aclose()` during application shutdown.
    """
    if is_postgres_url(checkpoint_url):
        return await _build_postgres(checkpoint_url, pool_max_size)
    return await _build_sqlite(checkpoint_url)


async def _build_sqlite(path: str) -> CheckpointerBundle:
    import aiosqlite
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    conn = await aiosqlite.connect(path)
    # WAL lets the automation scheduler and concurrent sessions write without
    # blocking readers; busy_timeout makes writers wait instead of failing
    # instantly with "database is locked".
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA busy_timeout=5000")
    saver = AsyncSqliteSaver(conn)
    await saver.setup()
    return CheckpointerBundle(saver, conn.close)


async def _build_postgres(url: str, pool_max_size: int) -> CheckpointerBundle:
    # Imported lazily so that psycopg stays an optional dependency.
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool

    pool = AsyncConnectionPool(
        conninfo=to_psycopg_conninfo(url),
        max_size=pool_max_size,
        # autocommit=True is required by setup() (it runs CREATE INDEX CONCURRENTLY,
        # which cannot run inside a transaction). row_factory=dict_row is required
        # or checkpoint reads fail with "tuple indices must be integers".
        kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": 0},
        open=False,
    )
    await pool.open()
    saver = AsyncPostgresSaver(pool)
    await saver.setup()
    return CheckpointerBundle(saver, pool.close)
