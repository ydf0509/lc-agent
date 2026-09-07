# tests/test_checkpointer.py
import aiosqlite

import pytest

from lc_agent.core.checkpointer import (
    CheckpointerBundle,
    build_checkpointer,
    is_postgres_url,
    to_psycopg_conninfo,
)
from lc_agent.db.engine import _to_sync_url


class TestUrlDetection:
    @pytest.mark.parametrize("value", [
        "postgresql://user:pw@localhost:5432/lcagent",
        "postgres://user:pw@localhost:5432/lcagent",
        "postgresql+asyncpg://user:pw@localhost:5432/lcagent",
        "postgresql+psycopg://user:pw@localhost:5432/lcagent",
    ])
    def test_postgres_urls_detected(self, value):
        assert is_postgres_url(value) is True

    @pytest.mark.parametrize("value", [
        "./lc_agent_checkpoints.db",
        "/abs/path/checkpoints.db",
        ":memory:",
        "sqlite+aiosqlite:///./x.db",
    ])
    def test_sqlite_values_not_detected(self, value):
        assert is_postgres_url(value) is False


class TestConninfoNormalization:
    @pytest.mark.parametrize("value, expected", [
        ("postgresql+asyncpg://u:p@h:5432/db", "postgresql://u:p@h:5432/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql://u:p@h/db"),
        ("postgresql+psycopg2://u:p@h/db", "postgresql://u:p@h/db"),
        ("postgresql://u:p@h/db", "postgresql://u:p@h/db"),
    ])
    def test_strips_sqlalchemy_driver_suffix(self, value, expected):
        # psycopg only understands plain postgresql:// conninfo strings.
        assert to_psycopg_conninfo(value) == expected


class TestAlembicSyncUrl:
    @pytest.mark.parametrize("value, expected", [
        ("sqlite+aiosqlite:///./a.db", "sqlite:///./a.db"),
        ("postgresql+asyncpg://u:p@h:5432/db", "postgresql+psycopg2://u:p@h:5432/db"),
        ("mysql+aiomysql://u:p@h/db", "mysql+pymysql://u:p@h/db"),
    ])
    def test_async_driver_swapped_for_sync(self, value, expected):
        assert _to_sync_url(value) == expected

    def test_non_async_url_untouched(self):
        assert _to_sync_url("postgresql+psycopg://u:p@h/db") == "postgresql+psycopg://u:p@h/db"


class TestSQLiteCheckpointer:
    async def test_wal_and_busy_timeout_enabled(self, tmp_path):
        bundle = await build_checkpointer(str(tmp_path / "cp.db"))
        try:
            conn = bundle.saver.conn
            journal = await conn.execute("PRAGMA journal_mode")
            assert (await journal.fetchone())[0] == "wal"
            timeout = await conn.execute("PRAGMA busy_timeout")
            assert (await timeout.fetchone())[0] == 5000
        finally:
            await bundle.aclose()

    async def test_setup_creates_checkpoint_tables(self, tmp_path):
        path = str(tmp_path / "cp.db")
        bundle = await build_checkpointer(path)
        await bundle.aclose()

        conn = await aiosqlite.connect(path)
        try:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = {row[0] for row in await cursor.fetchall()}
        finally:
            await conn.close()
        assert {"checkpoints", "writes"} <= tables

    async def test_in_memory_db_works(self):
        bundle = await build_checkpointer(":memory:")
        try:
            assert bundle.saver is not None
        finally:
            await bundle.aclose()


class TestPostgresWithoutDependency:
    async def test_missing_psycopg_raises_import_error(self, monkeypatch):
        """Without the [postgres] extra, the failure must surface as ImportError.

        app.py catches this during startup and falls back to checkpointer=None,
        so the message needs to be actionable rather than a silent no-op.
        """
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name.startswith("psycopg"):
                raise ImportError("No module named 'psycopg'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(ImportError):
            await build_checkpointer("postgresql://u:p@localhost:5432/db")


class TestCheckpointerBundle:
    async def test_aclose_without_closer_is_noop(self):
        bundle = CheckpointerBundle(saver=object())
        await bundle.aclose()

    async def test_aclose_swallows_closer_errors(self):
        async def boom():
            raise RuntimeError("close failed")

        bundle = CheckpointerBundle(saver=object(), closer=boom)
        await bundle.aclose()
