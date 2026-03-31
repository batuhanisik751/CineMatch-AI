"""User API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import (
    get_cache_service,
    get_db,
    get_feed_service,
    get_movie_service,
    get_user_stats_service,
)
from cinematch.core.cache import CacheService
from cinematch.models.rating import Rating
from cinematch.models.user import User
from cinematch.schemas.movie import MovieSummary
from cinematch.schemas.user import (
    CollectionGroup,
    CompletionsResponse,
    FeedResponse,
    SurpriseResponse,
    UserResponse,
    UserStatsResponse,
)
from cinematch.services.feed_service import FeedService
from cinematch.services.movie_service import MovieService
from cinematch.services.user_stats_service import UserStatsService

router = APIRouter()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.get("/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    stats_service: UserStatsService = Depends(get_user_stats_service),
):
    stats = await stats_service.get_user_stats(user_id, db)
    return UserStatsResponse(**stats)


@router.get("/{user_id}/surprise", response_model=SurpriseResponse)
async def surprise_me(
    user_id: int,
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    stats_service: UserStatsService = Depends(get_user_stats_service),
    movie_service: MovieService = Depends(get_movie_service),
):
    """Get serendipitous movie recommendations outside the user's taste profile."""
    stats = await stats_service.get_user_stats(user_id, db)
    genre_dist = stats.get("genre_distribution", [])
    top_genres = [g["genre"] for g in genre_dist[:2]]

    rated_result = await db.execute(select(Rating.movie_id).where(Rating.user_id == user_id))
    rated_ids = [row[0] for row in rated_result.all()]

    movies = await movie_service.surprise_movies(
        db,
        excluded_genres=top_genres,
        excluded_movie_ids=rated_ids,
        limit=limit,
    )

    return SurpriseResponse(
        user_id=user_id,
        excluded_genres=top_genres,
        results=[MovieSummary.model_validate(m) for m in movies],
        limit=limit,
    )


@router.get("/{user_id}/completions", response_model=CompletionsResponse)
async def get_completions(
    user_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
):
    """Suggest unrated films by directors/actors the user has rated >= 3 films for."""
    groups = await movie_service.collection_completions(db, user_id=user_id, limit=limit)

    total_missing = sum(len(g["missing"]) for g in groups)
    return CompletionsResponse(
        user_id=user_id,
        groups=[
            CollectionGroup(
                creator_type=g["creator_type"],
                creator_name=g["creator_name"],
                rated_count=g["rated_count"],
                avg_rating=g["avg_rating"],
                total_by_creator=g["total_by_creator"],
                missing=[MovieSummary.model_validate(m) for m in g["missing"]],
            )
            for g in groups
        ],
        total_missing=total_missing,
    )


@router.get("/{user_id}/feed", response_model=FeedResponse)
async def get_user_feed(
    user_id: int,
    sections: int = Query(default=5, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    feed_service: FeedService = Depends(get_feed_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Personalized home feed with named sections tailored to the user's taste."""
    cache_key = f"feed:{user_id}:{sections}"
    if cache is not None:
        cached = await cache.get(cache_key)
        if cached is not None:
            return FeedResponse.model_validate_json(cached)

    response = await feed_service.generate_feed(user_id, db, sections=sections)

    if cache is not None:
        try:
            await cache.set(cache_key, response.model_dump_json(), ttl=600)
        except Exception:
            pass

    return response
