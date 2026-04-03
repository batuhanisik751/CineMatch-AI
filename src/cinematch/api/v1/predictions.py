"""Predicted match percentage endpoints."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import (
    get_cache_service,
    get_current_user,
    get_db,
    get_hybrid_recommender,
    require_same_user,
)
from cinematch.core.cache import CacheService
from cinematch.core.exceptions import ServiceUnavailableError
from cinematch.models.user import User
from cinematch.schemas.recommendation import (
    PredictedMatchBatchRequest,
    PredictedMatchItem,
    PredictedMatchResponse,
)
from cinematch.services.hybrid_recommender import HybridRecommender

logger = logging.getLogger(__name__)

router = APIRouter()

_CACHE_TTL = 900  # 15 minutes


@router.get(
    "/users/{user_id}/predicted-rating/{movie_id}",
    response_model=PredictedMatchResponse,
)
async def get_predicted_rating(
    user_id: int,
    movie_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    hybrid_rec: HybridRecommender | None = Depends(get_hybrid_recommender),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Get predicted match percentage for a single movie."""
    require_same_user(current_user.id, user_id)
    if hybrid_rec is None:
        raise ServiceUnavailableError("Recommendation service")

    # Check cache
    if cache is not None:
        cached = await cache.get(f"match:{user_id}:{movie_id}")
        if cached is not None:
            return PredictedMatchResponse(
                user_id=user_id,
                predictions=[PredictedMatchItem(**json.loads(cached))],
            )

    results = await hybrid_rec.predict_match(user_id, [movie_id], db)
    predictions = [
        PredictedMatchItem(
            movie_id=r.movie_id,
            match_percent=r.match_percent,
            content_score=r.content_score,
            collab_score=r.collab_score,
            alpha=r.alpha,
        )
        for r in results
    ]

    # Cache result
    if cache is not None and predictions:
        p = predictions[0]
        await cache.set(
            f"match:{user_id}:{movie_id}",
            p.model_dump_json(),
            ttl=_CACHE_TTL,
        )

    return PredictedMatchResponse(user_id=user_id, predictions=predictions)


@router.post(
    "/users/{user_id}/predicted-ratings",
    response_model=PredictedMatchResponse,
)
async def get_batch_predicted_ratings(
    user_id: int,
    body: PredictedMatchBatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    hybrid_rec: HybridRecommender | None = Depends(get_hybrid_recommender),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Get predicted match percentages for a batch of movies (up to 100)."""
    require_same_user(current_user.id, user_id)
    if hybrid_rec is None:
        raise ServiceUnavailableError("Recommendation service")

    cached_items: list[PredictedMatchItem] = []
    missing_ids: list[int] = []

    # Check cache for each movie
    if cache is not None:
        for mid in body.movie_ids:
            cached = await cache.get(f"match:{user_id}:{mid}")
            if cached is not None:
                cached_items.append(PredictedMatchItem(**json.loads(cached)))
            else:
                missing_ids.append(mid)
    else:
        missing_ids = list(body.movie_ids)

    # Compute missing predictions
    computed: list[PredictedMatchItem] = []
    if missing_ids:
        results = await hybrid_rec.predict_match(user_id, missing_ids, db)
        for r in results:
            item = PredictedMatchItem(
                movie_id=r.movie_id,
                match_percent=r.match_percent,
                content_score=r.content_score,
                collab_score=r.collab_score,
                alpha=r.alpha,
            )
            computed.append(item)
            # Cache individually
            if cache is not None:
                await cache.set(
                    f"match:{user_id}:{r.movie_id}",
                    item.model_dump_json(),
                    ttl=_CACHE_TTL,
                )

    return PredictedMatchResponse(
        user_id=user_id,
        predictions=cached_items + computed,
    )
