from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

_engine = None
_async_session_factory = None


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


async def init_db(url: str = "sqlite+aiosqlite:///./lc_agent_data.db"):
    """Create all tables."""
    engine = get_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


def reset_engine():
    """Reset engine state (for testing)."""
    global _engine, _async_session_factory
    _engine = None
    _async_session_factory = None
