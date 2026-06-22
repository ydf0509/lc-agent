import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from alembic import context

import lc_agent.db.models  # noqa: F401  — register all table models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def _resolve_url() -> str:
    """Return a *synchronous* database URL for Alembic to use.

    Priority: env-var > alembic -x db_url=... > alembic.ini sqlalchemy.url
    """
    url = (
        os.environ.get("LC_AGENT_DB_URL")
        or config.get_main_option("sqlalchemy.url", "")
    )
    cmd_opts = context.get_x_argument(as_dictionary=True)
    if "db_url" in cmd_opts:
        url = cmd_opts["db_url"]
    # Alembic CLI needs a sync driver; convert aiosqlite → pysqlite
    if "+aiosqlite" in url:
        url = url.replace("+aiosqlite", "")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_resolve_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _resolve_url()

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
