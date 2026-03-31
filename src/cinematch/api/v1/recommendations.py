"""Recommendation API endpoints (nested under /users)."""

from __future__ import annotations

import hashlib
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import (
    get_cache_service,
    get_db,
    get_hybrid_recommender,
    get_llm_service,
    get_movie_service,
    get_rating_service,
)
from cinematch.core.cache import CacheService
from cinematch.core.exceptions import NotFoundError, ServiceUnavailableError
from cinematch.schemas.movie import MovieSummary
from cinematch.schemas.recommendation import (
    DIVERSITY_LAMBDA_MAP,
    DiversityLevel,
    FromSeedRecommendationsResponse,
    MoodRecommendationItem,
    MoodRecommendationRequest,
    MoodRecommendationResponse,
    RecommendationExplanation,
    RecommendationItem,
    RecommendationsResponse,
    ScoreBreakdownSchema,
    SeedInfluenceSchema,
)
from cinematch.services.hybrid_recommender import HybridRecommender
from cinematch.services.llm_service import LLMService
from cinematch.services.movie_service import MovieService
from cinematch.services.rating_service import RatingService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/users/{user_id}/recommendations",
    response_model=RecommendationsResponse,
)
async def get_recommendations(
    user_id: int,
    top_k: int = Query(default=20, ge=1, le=100),
    strategy: str = Query(default="hybrid", pattern="^(hybrid|content|collab)$"),
    diversity: DiversityLevel = Query(default=DiversityLevel.medium),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    hybrid_rec: HybridRecommender | None = Depends(get_hybrid_recommender),
):
    if hybrid_rec is None:
        raise ServiceUnavailableError("Recommendation service")
    diversity_lambda = DIVERSITY_LAMBDA_MAP[diversity]
    try:
        rec_results = await hybrid_rec.recommend(
            user_id, db, top_k=top_k, strategy=strategy, diversity_lambda=diversity_lambda
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Enrich with movie details
    movie_ids = [r.movie_id for r in rec_results]
    movies_map = await movie_service.get_movies_by_ids(movie_ids, db)

    recommendations = []
    for r in rec_results:
        movie = movies_map.get(r.movie_id)
        if movie is not None:
            recommendations.append(
                RecommendationItem(
                    movie=MovieSummary.model_validate(movie),
                    score=r.score,
                    content_score=(r.score_breakdown.content_score if r.score_breakdown else None),
                    collab_score=(r.score_breakdown.collab_score if r.score_breakdown else None),
                    because_you_liked=(
                        SeedInfluenceSchema(
                            movie_id=r.because_you_liked.movie_id,
                            title=r.because_you_liked.title,
                            your_rating=r.because_you_liked.your_rating,
                        )
                        if r.because_you_liked
                        else None
                    ),
                    feature_explanations=r.feature_explanations,
                    score_breakdown=(
                        ScoreBreakdownSchema(
                            content_score=r.score_breakdown.content_score,
                            collab_score=r.score_breakdown.collab_score,
                            alpha=r.score_breakdown.alpha,
                        )
                        if r.score_breakdown
                        else None
                    ),
                )
            )

    return RecommendationsResponse(
        user_id=user_id,
        strategy=strategy,
        diversity=diversity.value,
        recommendations=recommendations,
    )


@router.get(
    "/users/{user_id}/recommendations/explain/{movie_id}",
    response_model=RecommendationExplanation,
)
async def explain_recommendation(
    user_id: int,
    movie_id: int,
    score: float | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    rating_service: RatingService = Depends(get_rating_service),
    llm_service: LLMService | None = Depends(get_llm_service),
):
    if llm_service is None:
        raise ServiceUnavailableError("LLM service")

    movie = await movie_service.get_by_id(movie_id, db)
    if movie is None:
        raise NotFoundError("Movie", movie_id)

    rows, total = await rating_service.get_user_ratings(user_id, db, limit=10)
    if not rows:
        raise NotFoundError("User", user_id)

    # Unpack tuples from get_user_ratings (rating, movie_title)
    ratings = [r for r, _title in rows]

    # Build top-rated list with movie titles
    rated_movie_ids = [r.movie_id for r in ratings]
    rated_movies_map = await movie_service.get_movies_by_ids(rated_movie_ids, db)

    user_top_rated = sorted(
        [
            (rated_movies_map[r.movie_id].title, r.rating)
            for r in ratings
            if r.movie_id in rated_movies_map
        ],
        key=lambda x: x[1],
        reverse=True,
    )[:5]

    effective_score = score if score is not None else 0.0
    explanation = await llm_service.explain_recommendation(movie, user_top_rated, effective_score)

    return RecommendationExplanation(
        movie_id=movie.id,
        title=movie.title,
        explanation=explanation,
        score=effective_score,
    )


@router.get(
    "/users/{user_id}/recommendations/from-seed/{movie_id}",
    response_model=FromSeedRecommendationsResponse,
)
async def get_from_seed_recommendations(
    user_id: int,
    movie_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    hybrid_rec: HybridRecommender | None = Depends(get_hybrid_recommender),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    """Recommend movies similar to a seed movie, personalized for the user."""
    if hybrid_rec is None:
        raise ServiceUnavailableError("Recommendation service")

    seed_movie = await movie_service.get_by_id(movie_id, db)
    if seed_movie is None:
        raise NotFoundError("Movie", movie_id)

    # Check cache
    cache_key = f"from_seed:{user_id}:{movie_id}:{limit}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return FromSeedRecommendationsResponse.model_validate_json(cached)

    rec_results = await hybrid_rec.from_seed_recommend(
        movie_id,
        user_id,
        db,
        top_k=limit,
    )

    # Enrich with movie details
    rec_movie_ids = [r.movie_id for r in rec_results]
    movies_map = await movie_service.get_movies_by_ids(rec_movie_ids, db)

    recommendations = []
    for r in rec_results:
        movie = movies_map.get(r.movie_id)
        if movie is not None:
            recommendations.append(
                RecommendationItem(
                    movie=MovieSummary.model_validate(movie),
                    score=r.score,
                    content_score=(r.score_breakdown.content_score if r.score_breakdown else None),
                    collab_score=(r.score_breakdown.collab_score if r.score_breakdown else None),
                    because_you_liked=(
                        SeedInfluenceSchema(
                            movie_id=r.because_you_liked.movie_id,
                            title=r.because_you_liked.title,
                            your_rating=r.because_you_liked.your_rating,
                        )
                        if r.because_you_liked
                        else None
                    ),
                    feature_explanations=r.feature_explanations,
                    score_breakdown=(
                        ScoreBreakdownSchema(
                            content_score=r.score_breakdown.content_score,
                            collab_score=r.score_breakdown.collab_score,
                            alpha=r.score_breakdown.alpha,
                        )
                        if r.score_breakdown
                        else None
                    ),
                )
            )

    response = FromSeedRecommendationsResponse(
        user_id=user_id,
        strategy="from-seed",
        seed_movie=MovieSummary.model_validate(seed_movie),
        recommendations=recommendations,
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=600)
        except Exception:
            logger.warning("Failed to cache from-seed recommendations", exc_info=True)

    return response


@router.post(
    "/recommendations/mood",
    response_model=MoodRecommendationResponse,
)
async def mood_recommendations(
    body: MoodRecommendationRequest,
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    hybrid_rec: HybridRecommender | None = Depends(get_hybrid_recommender),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    """Recommend movies matching a mood, optionally personalized to user taste."""
    if hybrid_rec is None:
        raise ServiceUnavailableError("Recommendation service")

    # Check cache
    mood_hash = hashlib.md5(body.mood.lower().encode()).hexdigest()[:8]  # noqa: S324
    cache_key = f"mood_rec:{body.user_id}:{mood_hash}:{body.alpha}:{body.limit}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return MoodRecommendationResponse.model_validate_json(cached)

    rec_pairs, is_personalized = await hybrid_rec.mood_recommend(
        body.mood, body.user_id, db, alpha=body.alpha, top_k=body.limit
    )

    movie_ids = [mid for mid, _ in rec_pairs]
    movies_map = await movie_service.get_movies_by_ids(movie_ids, db)

    results = []
    for mid, sim in rec_pairs:
        movie = movies_map.get(mid)
        if movie is not None:
            results.append(
                MoodRecommendationItem(
                    movie=MovieSummary.model_validate(movie),
                    similarity=sim,
                )
            )

    response = MoodRecommendationResponse(
        user_id=body.user_id,
        mood=body.mood,
        alpha=body.alpha,
        is_personalized=is_personalized,
        results=results,
        total=len(results),
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=600)
        except Exception:
            logger.warning("Failed to cache mood recommendations", exc_info=True)

    return response
