"""Global platform statistics endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import get_cache_service, get_db, get_global_stats_service
from cinematch.schemas.global_stats import GlobalStatsResponse

logger = logging.getLogger(__name__)

router = APIRouter()

_CACHE_KEY = "global_stats"
_CACHE_TTL = 3600  # 1 hour


@router.get("/global", response_model=GlobalStatsResponse)
async def global_stats(
    db: AsyncSession = Depends(get_db),
    stats_service=Depends(get_global_stats_service),
    cache_service=Depends(get_cache_service),
):
    """Public platform-wide statistics."""

    # 1. Try cache
    if cache_service is not None:
        cached = await cache_service.get(_CACHE_KEY)
        if cached is not None:
            return GlobalStatsResponse.model_validate_json(cached)

    # 2. Compute from database
    data = await stats_service.get_global_stats(db)
    response = GlobalStatsResponse(**data)

    # 3. Store in cache (non-blocking)
    if cache_service is not None:
        try:
            await cache_service.set(_CACHE_KEY, response.model_dump_json(), ttl=_CACHE_TTL)
        except Exception:
            logger.warning("Failed to cache global stats", exc_info=True)

    return response
