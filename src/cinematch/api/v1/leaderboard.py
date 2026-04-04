"""Leaderboard endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query

from cinematch.api.deps import get_cache_service, get_db, get_tastemaker_score_service
from cinematch.schemas.tastemaker_score import TastemakerLeaderboardResponse

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from cinematch.core.cache import CacheService
    from cinematch.services.tastemaker_score_service import TastemakerScoreService

router = APIRouter()


@router.get("/tastemakers", response_model=TastemakerLeaderboardResponse)
async def get_tastemaker_leaderboard(
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    service: TastemakerScoreService = Depends(get_tastemaker_score_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Top users whose early high ratings predict community favorites."""
    cache_key = f"leaderboard:tastemakers:{limit}"
    if cache is not None:
        cached = await cache.get(cache_key)
        if cached is not None:
            return TastemakerLeaderboardResponse.model_validate_json(cached)

    result = await service.get_leaderboard(db, limit=limit)
    response = TastemakerLeaderboardResponse(**result)

    if cache is not None:
        try:
            await cache.set(cache_key, response.model_dump_json(), ttl=3600)
        except Exception:
            pass

    return response
