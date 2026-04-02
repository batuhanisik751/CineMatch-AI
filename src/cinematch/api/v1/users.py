"""User API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import (
    get_achievement_service,
    get_bingo_service,
    get_blind_spot_service,
    get_cache_service,
    get_challenge_service,
    get_db,
    get_feed_service,
    get_movie_service,
    get_rating_comparison_service,
    get_rewatch_service,
    get_streak_service,
    get_taste_evolution_service,
    get_taste_profile_service,
    get_user_stats_service,
)
from cinematch.core.cache import CacheService
from cinematch.models.rating import Rating
from cinematch.models.user import User
from cinematch.schemas.achievement import AchievementResponse
from cinematch.schemas.bingo import BingoCardResponse
from cinematch.schemas.blind_spot import BlindSpotResponse
from cinematch.schemas.challenge import ChallengesProgressResponse
from cinematch.schemas.movie import MovieSummary
from cinematch.schemas.rating import DiaryResponse
from cinematch.schemas.rating_comparison import RatingComparisonResponse
from cinematch.schemas.rewatch import RewatchResponse
from cinematch.schemas.streak import StreakResponse
from cinematch.schemas.taste_evolution import TasteEvolutionResponse
from cinematch.schemas.taste_profile import TasteProfileResponse
from cinematch.schemas.user import (
    AffinitiesResponse,
    CollectionGroup,
    CompletionsResponse,
    FeedResponse,
    SurpriseResponse,
    UserResponse,
    UserStatsResponse,
)
from cinematch.services.achievement_service import AchievementService
from cinematch.services.bingo_service import BingoService
from cinematch.services.blind_spot_service import BlindSpotService
from cinematch.services.challenge_service import ChallengeService
from cinematch.services.feed_service import FeedService
from cinematch.services.movie_service import MovieService
from cinematch.services.rating_comparison_service import RatingComparisonService
from cinematch.services.rewatch_service import RewatchService
from cinematch.services.streak_service import StreakService
from cinematch.services.taste_evolution_service import TasteEvolutionService
from cinematch.services.taste_profile_service import TasteProfileService
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


@router.get("/{user_id}/diary", response_model=DiaryResponse)
async def get_user_diary(
    user_id: int,
    year: int = Query(default=2025, ge=2000, le=2100),
    db: AsyncSession = Depends(get_db),
    stats_service: UserStatsService = Depends(get_user_stats_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Film diary — daily rating activity calendar for a given year."""
    cache_key = f"diary:{user_id}:{year}"
    if cache is not None:
        cached = await cache.get(cache_key)
        if cached is not None:
            return DiaryResponse.model_validate_json(cached)

    data = await stats_service.get_diary(user_id, year, db)
    response = DiaryResponse(**data)

    if cache is not None:
        try:
            await cache.set(cache_key, response.model_dump_json(), ttl=300)
        except Exception:
            pass

    return response


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


@router.get("/{user_id}/taste-profile", response_model=TasteProfileResponse)
async def get_taste_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    taste_service: TasteProfileService = Depends(get_taste_profile_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Natural-language summary of the user's movie taste."""
    cache_key = f"taste_profile:{user_id}"
    if cache is not None:
        cached = await cache.get(cache_key)
        if cached is not None:
            return TasteProfileResponse.model_validate_json(cached)

    result = await taste_service.get_taste_profile(user_id, db)
    response = TasteProfileResponse(**result)

    if cache is not None:
        try:
            await cache.set(cache_key, response.model_dump_json(), ttl=600)
        except Exception:
            pass

    return response


@router.get("/{user_id}/affinities", response_model=AffinitiesResponse)
async def get_affinities(
    user_id: int,
    limit: int = Query(default=15, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    stats_service: UserStatsService = Depends(get_user_stats_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Director and actor affinity rankings weighted by rating enthusiasm."""
    cache_key = f"affinities:{user_id}:{limit}"
    if cache is not None:
        cached = await cache.get(cache_key)
        if cached is not None:
            return AffinitiesResponse.model_validate_json(cached)

    data = await stats_service.get_affinities(user_id, db, limit=limit)
    response = AffinitiesResponse(**data)

    if cache is not None:
        try:
            await cache.set(cache_key, response.model_dump_json(), ttl=600)
        except Exception:
            pass

    return response


@router.get("/{user_id}/rating-comparison", response_model=RatingComparisonResponse)
async def get_rating_comparison(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    comparison_service: RatingComparisonService = Depends(get_rating_comparison_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Compare user's ratings against community averages."""
    cache_key = f"rating_comparison:{user_id}"
    if cache is not None:
        cached = await cache.get(cache_key)
        if cached is not None:
            return RatingComparisonResponse.model_validate_json(cached)

    result = await comparison_service.get_rating_comparison(user_id, db)
    response = RatingComparisonResponse(**result)

    if cache is not None:
        try:
            await cache.set(cache_key, response.model_dump_json(), ttl=600)
        except Exception:
            pass

    return response


@router.get("/{user_id}/streaks", response_model=StreakResponse)
async def get_streaks(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    streak_service: StreakService = Depends(get_streak_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Rating streak and milestone data for a user."""
    cache_key = f"streaks:{user_id}"
    if cache is not None:
        cached = await cache.get(cache_key)
        if cached is not None:
            return StreakResponse.model_validate_json(cached)

    result = await streak_service.get_streaks(user_id, db)
    response = StreakResponse(**result)

    if cache is not None:
        try:
            await cache.set(cache_key, response.model_dump_json(), ttl=300)
        except Exception:
            pass

    return response


@router.get("/{user_id}/taste-evolution", response_model=TasteEvolutionResponse)
async def get_taste_evolution(
    user_id: int,
    granularity: str = Query(default="quarter", pattern=r"^(month|quarter|year)$"),
    db: AsyncSession = Depends(get_db),
    service: TasteEvolutionService = Depends(get_taste_evolution_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Genre distribution over time for a user."""
    cache_key = f"taste_evolution:{user_id}:{granularity}"
    if cache is not None:
        cached = await cache.get(cache_key)
        if cached is not None:
            return TasteEvolutionResponse.model_validate_json(cached)

    result = await service.get_taste_evolution(user_id, db, granularity=granularity)
    response = TasteEvolutionResponse(**result)

    if cache is not None:
        try:
            await cache.set(cache_key, response.model_dump_json(), ttl=3600)
        except Exception:
            pass

    return response


@router.get("/{user_id}/achievements", response_model=AchievementResponse)
async def get_achievements(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    achievement_service: AchievementService = Depends(get_achievement_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Achievement badges computed from rating history."""
    cache_key = f"achievements:{user_id}"
    if cache is not None:
        cached = await cache.get(cache_key)
        if cached is not None:
            return AchievementResponse.model_validate_json(cached)

    result = await achievement_service.get_achievements(user_id, db)
    response = AchievementResponse(**result)

    if cache is not None:
        try:
            await cache.set(cache_key, response.model_dump_json(), ttl=3600)
        except Exception:
            pass

    return response


@router.get("/{user_id}/challenges/progress", response_model=ChallengesProgressResponse)
async def get_challenge_progress(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    challenge_service: ChallengeService = Depends(get_challenge_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Weekly challenge progress for a user."""
    cache_key = f"challenges:progress:{user_id}"
    if cache is not None:
        cached = await cache.get(cache_key)
        if cached is not None:
            return ChallengesProgressResponse.model_validate_json(cached)

    result = await challenge_service.get_user_progress(user_id, db)
    response = ChallengesProgressResponse(**result)

    if cache is not None:
        try:
            await cache.set(cache_key, response.model_dump_json(), ttl=120)
        except Exception:
            pass

    return response


@router.get("/{user_id}/bingo", response_model=BingoCardResponse)
async def get_user_bingo(
    user_id: int,
    seed: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: AsyncSession = Depends(get_db),
    bingo_service: BingoService = Depends(get_bingo_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Monthly Movie Bingo card with user progress."""
    cache_key = f"bingo:{user_id}:{seed}"
    if cache is not None:
        cached = await cache.get(cache_key)
        if cached is not None:
            return BingoCardResponse.model_validate_json(cached)

    result = await bingo_service.get_user_bingo(user_id, seed, db)
    response = BingoCardResponse(**result)

    if cache is not None:
        try:
            await cache.set(cache_key, response.model_dump_json(), ttl=3600)
        except Exception:
            pass

    return response


@router.get("/{user_id}/rewatch", response_model=RewatchResponse)
async def get_rewatch_suggestions(
    user_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    min_rating: int = Query(default=8, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    rewatch_service: RewatchService = Depends(get_rewatch_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Suggest highly-rated movies worth revisiting."""
    cache_key = f"rewatch:{user_id}:{limit}:{min_rating}"
    if cache is not None:
        cached = await cache.get(cache_key)
        if cached is not None:
            return RewatchResponse.model_validate_json(cached)

    result = await rewatch_service.get_rewatch_suggestions(
        user_id,
        db,
        limit=limit,
        min_rating=min_rating,
    )
    response = RewatchResponse(**result)

    if cache is not None:
        try:
            await cache.set(cache_key, response.model_dump_json(), ttl=600)
        except Exception:
            pass

    return response


@router.get("/{user_id}/blind-spots", response_model=BlindSpotResponse)
async def get_blind_spots(
    user_id: int,
    limit: int = Query(default=20, ge=1, le=50),
    genre: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    blind_spot_service: BlindSpotService = Depends(get_blind_spot_service),
    cache: CacheService | None = Depends(get_cache_service),
):
    """Popular, highly-regarded movies the user has never rated."""
    cache_key = f"blind-spots:{user_id}:{limit}:{genre or 'all'}"
    if cache is not None:
        cached = await cache.get(cache_key)
        if cached is not None:
            return BlindSpotResponse.model_validate_json(cached)

    result = await blind_spot_service.get_blind_spots(
        user_id,
        db,
        limit=limit,
        genre=genre,
    )
    response = BlindSpotResponse(**result)

    if cache is not None:
        try:
            await cache.set(cache_key, response.model_dump_json(), ttl=3600)
        except Exception:
            pass

    return response
