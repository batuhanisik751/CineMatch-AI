"""Recommendation API endpoints (nested under /users)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import (
    get_db,
    get_hybrid_recommender,
    get_llm_service,
    get_movie_service,
    get_rating_service,
)
from cinematch.core.exceptions import NotFoundError, ServiceUnavailableError
from cinematch.schemas.movie import MovieSummary
from cinematch.schemas.recommendation import (
    RecommendationExplanation,
    RecommendationItem,
    RecommendationsResponse,
)
from cinematch.services.hybrid_recommender import HybridRecommender
from cinematch.services.llm_service import LLMService
from cinematch.services.movie_service import MovieService
from cinematch.services.rating_service import RatingService

router = APIRouter()


@router.get(
    "/users/{user_id}/recommendations",
    response_model=RecommendationsResponse,
)
async def get_recommendations(
    user_id: int,
    top_k: int = Query(default=20, ge=1, le=100),
    strategy: str = Query(default="hybrid", pattern="^(hybrid|content|collab)$"),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    hybrid_rec: HybridRecommender = Depends(get_hybrid_recommender),
):
    try:
        rec_pairs = await hybrid_rec.recommend(user_id, db, top_k=top_k, strategy=strategy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Enrich with movie details
    movie_ids = [mid for mid, _ in rec_pairs]
    movies_map = await movie_service.get_movies_by_ids(movie_ids, db)

    recommendations = []
    for mid, score in rec_pairs:
        movie = movies_map.get(mid)
        if movie is not None:
            recommendations.append(
                RecommendationItem(
                    movie=MovieSummary.model_validate(movie),
                    score=score,
                )
            )

    return RecommendationsResponse(
        user_id=user_id,
        strategy=strategy,
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

    ratings, total = await rating_service.get_user_ratings(user_id, db, limit=10)
    if not ratings:
        raise NotFoundError("User", user_id)

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
