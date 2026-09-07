from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from lc_agent.utils.loggers import db_logger

_engine = None
_async_session_factory = None

_MIGRATIONS_DIR = str(Path(__file__).parent / "migrations")


def get_async_engine(url: str = "sqlite+aiosqlite:///./lc_agent_data.db"):
    global _engine, _engine_url, _async_session_factory, _async_session_factory_url
    if _engine is None or _engine_url != url:
        _async_session_factory = None
        _async_session_factory_url = None
        engine_kwargs = {"echo": False}
        if url.endswith(":memory:"):
            engine_kwargs["poolclass"] = StaticPool
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_async_engine(url, **engine_kwargs)
        _engine_url = url
    return _engine


def get_async_session(url: str = "sqlite+aiosqlite:///./lc_agent_data.db") -> AsyncSession:
    global _async_session_factory, _async_session_factory_url
    if _async_session_factory is None or _async_session_factory_url != url:
        engine = get_async_engine(url)
        _async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        _async_session_factory_url = url
    return _async_session_factory()


_ASYNC_TO_SYNC_SCHEME = {
    "sqlite+aiosqlite": "sqlite",
    "postgresql+asyncpg": "postgresql+psycopg2",
    "mysql+aiomysql": "mysql+pymysql",
}


def _to_sync_url(url: str) -> str:
    """Convert async DB URL to sync for Alembic."""
    for async_scheme, sync_scheme in _ASYNC_TO_SYNC_SCHEME.items():
        if url.startswith(async_scheme + "://"):
            return sync_scheme + url[len(async_scheme):]
    return url


def _add_missing_columns(connection):
    """Inspect existing tables and ALTER TABLE ADD COLUMN for any missing columns.

    Handles the gap where create_all skips existing tables but migrations
    that would have added new columns failed.
    SQLite-specific: uses PRAGMA table_info.
    """
    from sqlalchemy import inspect as sa_inspect, text

    inspector = sa_inspect(connection)
    for table in SQLModel.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing_cols = {col["name"] for col in inspector.get_columns(table.name)}
        for col in table.columns:
            if col.name not in existing_cols:
                col_type = col.type.compile(connection.dialect)
                nullable = "" if col.nullable else " NOT NULL"
                default = ""
                if col.server_default is not None:
                    default = f" DEFAULT {col.server_default.arg}"
                ddl = f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}{nullable}{default}"
                try:
                    connection.execute(text(ddl))
                    db_logger.info("Added missing column: %s.%s (%s)", table.name, col.name, col_type)
                except Exception:
                    db_logger.exception("Failed to add column %s.%s", table.name, col.name)


async def init_db(url: str = "sqlite+aiosqlite:///./lc_agent_data.db"):
    """Run Alembic migrations to create / update all tables.

    Falls back to SQLModel.metadata.create_all if alembic has no revisions yet.
    After create_all, inspects existing tables and adds any missing columns
    (handles the case where migrations failed but tables already exist).
    """
    import lc_agent.db.models  # noqa: F401 — ensure models are registered

    sync_url = _to_sync_url(url)

    from alembic.config import Config
    from alembic import command
    from alembic.script import ScriptDirectory

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", _MIGRATIONS_DIR)
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

    script = ScriptDirectory.from_config(alembic_cfg)
    has_revisions = bool(list(script.walk_revisions()))

    if has_revisions:
        command.upgrade(alembic_cfg, "head")
        engine = get_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(_add_missing_columns)
        return

    engine = get_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.run_sync(_add_missing_columns)


def reset_engine():
    """Reset engine state (for testing)."""
    global _engine, _async_session_factory
    _engine = None
    _async_session_factory = None
