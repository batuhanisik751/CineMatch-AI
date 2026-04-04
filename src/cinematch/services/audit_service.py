"""Audit logging service — writes events to database and file."""

from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.core.audit import get_audit_file_handler
from cinematch.models.audit_log import AuditLog


class AuditService:
    """Records security-relevant events to the database and an optional JSON log file."""

    def __init__(self, log_file: str | None = None, enabled: bool = True) -> None:
        self._enabled = enabled
        self._file_logger: logging.Logger | None = None
        if log_file and enabled:
            logger = logging.getLogger("audit.file")
            if not logger.handlers:
                logger.addHandler(get_audit_file_handler(log_file))
                logger.setLevel(logging.INFO)
            self._file_logger = logger

    async def log(
        self,
        action: str,
        db: AsyncSession,
        *,
        user_id: int | None = None,
        detail: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        status: str = "success",
    ) -> None:
        """Record an audit event to the database and log file."""
        if not self._enabled:
            return

        detail_json = json.dumps(detail, default=str) if detail else None

        entry = AuditLog(
            action=action,
            user_id=user_id,
            detail=detail_json,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
        )
        db.add(entry)
        await db.commit()

        if self._file_logger:
            record = self._file_logger.makeRecord(
                "audit.file", logging.INFO, "", 0, action, (), None
            )
            record.audit_data = {  # type: ignore[attr-defined]
                "action": action,
                "user_id": user_id,
                "detail": detail,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "status": status,
            }
            self._file_logger.handle(record)

    async def query(
        self,
        db: AsyncSession,
        *,
        user_id: int | None = None,
        action: str | None = None,
        status: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """Query audit logs with optional filters. Returns (rows, total_count)."""
        conditions = []
        if user_id is not None:
            conditions.append(AuditLog.user_id == user_id)
        if action is not None:
            conditions.append(AuditLog.action == action)
        if status is not None:
            conditions.append(AuditLog.status == status)
        if from_date is not None:
            conditions.append(AuditLog.timestamp >= from_date)
        if to_date is not None:
            conditions.append(AuditLog.timestamp <= to_date)

        # Total count
        count_stmt = select(func.count(AuditLog.id)).where(*conditions)
        total = (await db.execute(count_stmt)).scalar_one()

        # Paginated rows
        stmt = (
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.timestamp.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = list(result.scalars().all())

        return rows, total
