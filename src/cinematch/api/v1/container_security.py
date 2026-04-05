"""Container security status endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from cinematch.api.deps import get_current_user
from cinematch.core.container_security import get_container_security_status
from cinematch.schemas.container_security import (
    ContainerSecurityCheck,
    ContainerSecurityResponse,
)

router = APIRouter()


@router.get("/container-security", response_model=ContainerSecurityResponse)
async def get_container_security(
    _current_user=Depends(get_current_user),
):
    status = get_container_security_status()
    check_models = [ContainerSecurityCheck(**c) for c in status["checks"]]
    return ContainerSecurityResponse(
        runtime=status["runtime"],
        filesystem=status["filesystem"],
        image=status["image"],
        checks=check_models,
        all_passed=status["all_passed"],
        checked_at=datetime.now(UTC),
    )
