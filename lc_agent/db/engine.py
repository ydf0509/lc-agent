from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

_engine = None
_async_session_factory = None

_MIGRATIONS_DIR = str(Path(__file__).parent / "migrations")


def get_async_engine(url: str = "sqlite+aiosqlite:///./lc_agent_data.db"):
    global _engine
    if _engine is None:
        engine_kwargs = {"echo": False}
        if url.endswith(":memory:"):
            engine_kwargs["poolclass"] = StaticPool
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_async_engine(url, **engine_kwargs)
    return _engine


def get_async_session(url: str = "sqlite+aiosqlite:///./lc_agent_data.db") -> AsyncSession:
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_async_engine(url)
        _async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return _async_session_factory()


def _to_sync_url(url: str) -> str:
    """Convert async DB URL to sync for Alembic."""
    if "+aiosqlite" in url:
        return url.replace("+aiosqlite", "")
    return url


async def init_db(url: str = "sqlite+aiosqlite:///./lc_agent_data.db"):
    """Run Alembic migrations to create / update all tables.

    Falls back to SQLModel.metadata.create_all if alembic has no revisions yet.
    """
    import lc_agent.db.models  # noqa: F401 — ensure models are registered

    sync_url = _to_sync_url(url)

    try:
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
            return
    except Exception as e:
        print(f"[DB] Alembic migration failed, falling back to create_all: {e}")

    engine = get_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


def reset_engine():
    """Reset engine state (for testing)."""
    global _engine, _async_session_factory
    _engine = None
    _async_session_factory = None
