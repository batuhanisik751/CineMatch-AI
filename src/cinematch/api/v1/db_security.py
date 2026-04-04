"""Database connection security status endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import get_current_user, get_db
from cinematch.config import get_settings
from cinematch.db.session import engine
from cinematch.schemas.db_security import DbSecurityStatusResponse

router = APIRouter()


@router.get("/db-security", response_model=DbSecurityStatusResponse)
async def get_db_security_status(
    _current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()

    # Query active SSL status from PostgreSQL
    try:
        ssl_result = await db.execute(
            text("SELECT ssl, version FROM pg_stat_ssl WHERE pid = pg_backend_pid()")
        )
        ssl_row = ssl_result.first()
        ssl_active = bool(ssl_row and ssl_row[0])
        ssl_version = ssl_row[1] if ssl_row else None
    except Exception:
        ssl_active = False
        ssl_version = None

    # Query current statement_timeout
    try:
        timeout_result = await db.execute(text("SHOW statement_timeout"))
        timeout_row = timeout_result.first()
        timeout_active = timeout_row[0] if timeout_row else "unknown"
    except Exception:
        timeout_active = "unknown"

    # Query current user and database
    try:
        user_result = await db.execute(text("SELECT current_user, current_database()"))
        user_row = user_result.first()
        db_user = user_row[0] if user_row else "unknown"
        db_name = user_row[1] if user_row else "unknown"
    except Exception:
        db_user = "unknown"
        db_name = "unknown"

    # Pool stats from SQLAlchemy
    pool = engine.pool
    pool_status = {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "pool_recycle": settings.db_pool_recycle,
        "pool_pre_ping": settings.db_pool_pre_ping,
    }

    return DbSecurityStatusResponse(
        ssl={
            "configured_mode": settings.database_ssl_mode,
            "active": ssl_active,
            "protocol_version": ssl_version,
        },
        statement_timeout={
            "configured_ms": settings.database_statement_timeout,
            "active": timeout_active,
        },
        connection={
            "current_user": db_user,
            "current_database": db_name,
        },
        pool=pool_status,
    )
