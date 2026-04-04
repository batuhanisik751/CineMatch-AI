"""Async database engine and session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cinematch.config import get_settings

settings = get_settings()

# WARNING: echo=settings.debug logs ALL SQL queries (including parameter values)
# to stdout. CINEMATCH_DEBUG must NEVER be set to true in production as this
# can leak sensitive data (user IDs, emails, tokens) into log aggregators.
engine = create_async_engine(
    settings.database_url.get_secret_value(),
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=settings.debug,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
