"""Pickle artifact integrity status endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from cinematch.api.deps import get_current_user
from cinematch.core.pickle_safety import get_all_artifact_statuses
from cinematch.schemas.pickle_safety import PickleArtifactStatus, PickleSafetyResponse

router = APIRouter()


@router.get("/pickle-safety", response_model=PickleSafetyResponse)
async def get_pickle_safety_status(
    _current_user=Depends(get_current_user),
):
    artifacts = get_all_artifact_statuses()
    artifact_models = [PickleArtifactStatus(**a) for a in artifacts]
    all_verified = all(a.status == "verified" for a in artifact_models)
    return PickleSafetyResponse(
        artifacts=artifact_models,
        all_verified=all_verified,
        checked_at=datetime.now(UTC),
    )
