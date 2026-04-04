"""Audit log query endpoint — users can view their own audit trail."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import get_audit_service, get_current_user, get_db
from cinematch.models.user import User
from cinematch.schemas.audit import AuditLogListResponse, AuditLogResponse
from cinematch.services.audit_service import AuditService

router = APIRouter()


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    action: str | None = Query(default=None),
    status: str | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> AuditLogListResponse:
    """Return the current user's audit log entries with optional filters."""
    logs, total = await audit.query(
        db,
        user_id=current_user.id,
        action=action,
        status=status,
        from_date=from_date,
        to_date=to_date,
        offset=offset,
        limit=limit,
    )

    return AuditLogListResponse(
        logs=[
            AuditLogResponse(
                id=log.id,
                timestamp=log.timestamp,
                user_id=log.user_id,
                action=log.action,
                detail=json.loads(log.detail) if log.detail else None,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                status=log.status,
            )
            for log in logs
        ],
        total=total,
        offset=offset,
        limit=limit,
    )
