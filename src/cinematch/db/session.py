"""Async database engine and session management."""

from __future__ import annotations

import ssl as _ssl
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cinematch.config import get_settings

settings = get_settings()


def _build_connect_args() -> dict:
    """Build asyncpg-specific connect_args for SSL and server settings."""
    connect_args: dict = {}
    server_settings: dict[str, str] = {}

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
    # "disable" — no ssl key in connect_args

    if settings.database_statement_timeout > 0:
        server_settings["statement_timeout"] = str(settings.database_statement_timeout)

    if server_settings:
        connect_args["server_settings"] = server_settings

    return connect_args


# WARNING: echo=settings.debug logs ALL SQL queries (including parameter values)
# to stdout. CINEMATCH_DEBUG must NEVER be set to true in production as this
# can leak sensitive data (user IDs, emails, tokens) into log aggregators.
engine = create_async_engine(
    settings.database_url.get_secret_value(),
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=settings.db_pool_pre_ping,
    connect_args=_build_connect_args(),
    echo=settings.debug,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
