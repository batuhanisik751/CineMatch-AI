"""Challenges API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import get_cache_service, get_challenge_service, get_db
from cinematch.core.cache import CacheService
from cinematch.schemas.challenge import ChallengesCurrentResponse
from cinematch.services.challenge_service import ChallengeService, _week_key

router = APIRouter()


@router.get("/current", response_model=ChallengesCurrentResponse)
async def get_current_challenges(
    db: AsyncSession = Depends(get_db),
    challenge_service: ChallengeService = Depends(get_challenge_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Return this week's active challenges."""
    _, _, week_label = _week_key()
    cache_key = f"challenges:current:{week_label}"

    if cache is not None:
        cached = await cache.get(cache_key)
        if cached is not None:
            return ChallengesCurrentResponse.model_validate_json(cached)

    result = await challenge_service.get_current_challenges(db)
    response = ChallengesCurrentResponse(**result)

    if cache is not None:
        try:
            await cache.set(cache_key, response.model_dump_json(), ttl=86400)
        except Exception:
            pass

    return response
