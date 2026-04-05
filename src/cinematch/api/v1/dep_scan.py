"""Dependency vulnerability scanning endpoint."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from cinematch.api.deps import get_current_user
from cinematch.core.dep_scan import run_full_scan
from cinematch.schemas.dep_scan import (
    BanditResult,
    DepScanResponse,
    DepScanSummary,
    PipAuditResult,
    SafetyResult,
)

router = APIRouter()


@router.get("/dep-scan", response_model=DepScanResponse)
async def get_dep_scan(_current_user=Depends(get_current_user)):
    result = await asyncio.to_thread(run_full_scan)
    return DepScanResponse(
        pip_audit=PipAuditResult(**result["pip_audit"]),
        bandit=BanditResult(**result["bandit"]),
        safety=SafetyResult(**result["safety"]),
        summary=DepScanSummary(**result["summary"]),
        scanned_at=datetime.now(UTC),
    )
