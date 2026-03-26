"""Rating API endpoints (nested under /users)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import get_db, get_movie_service, get_rating_service
from cinematch.schemas.rating import RatingCreate, RatingResponse, UserRatingsResponse
from cinematch.services.movie_service import MovieService
from cinematch.services.rating_service import RatingService

router = APIRouter()


@router.post(
    "/users/{user_id}/ratings",
    response_model=RatingResponse,
    status_code=201,
)
async def add_rating(
    user_id: int,
    body: RatingCreate,
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    rating_service: RatingService = Depends(get_rating_service),
):
    movie = await movie_service.get_by_id(body.movie_id, db)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    rating = await rating_service.add_rating(user_id, body.movie_id, body.rating, db)
    return RatingResponse.model_validate(rating)


@router.get("/users/{user_id}/ratings", response_model=UserRatingsResponse)
async def get_user_ratings(
    user_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    rating_service: RatingService = Depends(get_rating_service),
):
    ratings, total = await rating_service.get_user_ratings(user_id, db, offset=offset, limit=limit)
    return UserRatingsResponse(
        user_id=user_id,
        ratings=[RatingResponse.model_validate(r) for r in ratings],
        total=total,
        offset=offset,
        limit=limit,
    )
