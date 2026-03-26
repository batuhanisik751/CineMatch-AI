"""Recommendation API endpoints (nested under /users)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import get_db, get_hybrid_recommender, get_movie_service
from cinematch.schemas.movie import MovieSummary
from cinematch.schemas.recommendation import RecommendationItem, RecommendationsResponse
from cinematch.services.hybrid_recommender import HybridRecommender
from cinematch.services.movie_service import MovieService

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
