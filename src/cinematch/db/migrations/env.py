"""Alembic environment configuration with async support."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from cinematch.config import get_settings
from cinematch.db.base import Base

# Import all models so Alembic can detect them
from cinematch.models import (  # noqa: F401
    Dismissal,
    Movie,
    Rating,
    RecommendationCache,
    User,
    UserList,
    UserListItem,
    WatchlistItem,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url.get_secret_value())


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def _build_connect_args() -> dict:
    """Build asyncpg-specific connect_args for SSL (mirrors session.py)."""
    import ssl as _ssl

    connect_args: dict = {}
    mode = settings.database_ssl_mode
    if mode == "require":
        ssl_ctx = _ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = _ssl.CERT_NONE
        connect_args["ssl"] = ssl_ctx
    elif mode == "verify-ca":
        ssl_ctx = _ssl.create_default_context()
        ssl_ctx.check_hostname = False
        connect_args["ssl"] = ssl_ctx
    elif mode == "verify-full":
        ssl_ctx = _ssl.create_default_context()
        connect_args["ssl"] = ssl_ctx
    elif mode == "prefer":
        connect_args["ssl"] = "prefer"
    return connect_args


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=_build_connect_args(),
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
