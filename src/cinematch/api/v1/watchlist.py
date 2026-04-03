"""Watchlist API endpoints (nested under /users)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import (
    get_cache_service,
    get_current_user,
    get_db,
    get_hybrid_recommender,
    get_movie_service,
    get_watchlist_service,
    require_same_user,
)
from cinematch.core.cache import CacheService
from cinematch.core.exceptions import ServiceUnavailableError
from cinematch.models.user import User
from cinematch.schemas.movie import MovieSummary
from cinematch.schemas.recommendation import RecommendationItem, RecommendationsResponse
from cinematch.schemas.watchlist import (
    WatchlistAdd,
    WatchlistBulkStatusResponse,
    WatchlistItemResponse,
    WatchlistResponse,
)
from cinematch.services.hybrid_recommender import HybridRecommender
from cinematch.services.movie_service import MovieService
from cinematch.services.watchlist_service import WatchlistService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/users/{user_id}/watchlist/recommendations",
    response_model=RecommendationsResponse,
)
async def get_watchlist_recommendations(
    user_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
    hybrid_rec: HybridRecommender | None = Depends(get_hybrid_recommender),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    """Recommend movies similar to what's on the user's watchlist."""
    require_same_user(current_user.id, user_id)
    if hybrid_rec is None:
        raise ServiceUnavailableError("Recommendation service")

    watchlist_movie_ids = await watchlist_service.get_watchlist_movie_ids(user_id, db)
    if not watchlist_movie_ids:
        return RecommendationsResponse(user_id=user_id, strategy="watchlist", recommendations=[])

    cache_key = f"watchlist_recs:{user_id}:{limit}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return RecommendationsResponse.model_validate_json(cached)

    results = await hybrid_rec.watchlist_recommend(watchlist_movie_ids, user_id, db, top_k=limit)

    rec_movie_ids = [mid for mid, _ in results]
    movies_map = await movie_service.get_movies_by_ids(rec_movie_ids, db)

    recommendations = []
    for mid, score in results:
        movie = movies_map.get(mid)
        if movie is not None:
            recommendations.append(
                RecommendationItem(
                    movie=MovieSummary.model_validate(movie),
                    score=score,
                    feature_explanations=["Based on your watchlist"],
                )
            )

    response = RecommendationsResponse(
        user_id=user_id, strategy="watchlist", recommendations=recommendations
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=600)
        except Exception:
            logger.warning("Failed to cache watchlist recommendations", exc_info=True)

    return response


@router.get(
    "/users/{user_id}/watchlist/check",
    response_model=WatchlistBulkStatusResponse,
)
async def bulk_check_watchlist(
    user_id: int,
    movie_ids: str = Query(..., description="Comma-separated movie IDs"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
):
    """Check which movies from a list are in the user's watchlist."""
    require_same_user(current_user.id, user_id)
    try:
        id_list = [int(x.strip()) for x in movie_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=422, detail="movie_ids must be comma-separated integers")

    in_watchlist = await watchlist_service.bulk_check(user_id, id_list, db)
    return WatchlistBulkStatusResponse(movie_ids=sorted(in_watchlist))


@router.post(
    "/users/{user_id}/watchlist",
    response_model=WatchlistItemResponse,
    status_code=201,
)
async def add_to_watchlist(
    user_id: int,
    body: WatchlistAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    """Add a movie to the user's watchlist."""
    require_same_user(current_user.id, user_id)
    movie = await movie_service.get_by_id(body.movie_id, db)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    item = await watchlist_service.add_to_watchlist(user_id, body.movie_id, db)

    if cache_service is not None:
        try:
            await cache_service.delete_pattern(f"watchlist_recs:{user_id}:*")
        except Exception:
            pass

    resp = WatchlistItemResponse.model_validate(item)
    resp.movie_title = movie.title
    resp.poster_path = movie.poster_path
    resp.genres = movie.genres or []
    resp.vote_average = movie.vote_average
    resp.release_date = str(movie.release_date) if movie.release_date else None
    return resp


@router.delete(
    "/users/{user_id}/watchlist/{movie_id}",
    status_code=204,
)
async def remove_from_watchlist(
    user_id: int,
    movie_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    """Remove a movie from the user's watchlist."""
    require_same_user(current_user.id, user_id)
    removed = await watchlist_service.remove_from_watchlist(user_id, movie_id, db)
    if not removed:
        raise HTTPException(status_code=404, detail="Movie not in watchlist")

    if cache_service is not None:
        try:
            await cache_service.delete_pattern(f"watchlist_recs:{user_id}:*")
        except Exception:
            pass


@router.get(
    "/users/{user_id}/watchlist",
    response_model=WatchlistResponse,
)
async def get_watchlist(
    user_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    watchlist_service: WatchlistService = Depends(get_watchlist_service),
):
    """Get a user's watchlist with movie details."""
    require_same_user(current_user.id, user_id)
    rows, total = await watchlist_service.get_watchlist(user_id, db, offset=offset, limit=limit)
    items = []
    for item, title, poster_path, genres, vote_average, release_date in rows:
        resp = WatchlistItemResponse.model_validate(item)
        resp.movie_title = title
        resp.poster_path = poster_path
        resp.genres = genres or []
        resp.vote_average = vote_average or 0.0
        resp.release_date = str(release_date) if release_date else None
        items.append(resp)
    return WatchlistResponse(
        user_id=user_id,
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )
