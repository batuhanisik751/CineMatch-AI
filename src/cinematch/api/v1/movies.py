"""Movie API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import get_content_recommender, get_db, get_movie_service
from cinematch.core.exceptions import ServiceUnavailableError
from cinematch.schemas.movie import (
    MovieResponse,
    MovieSearchResponse,
    MovieSummary,
    SimilarMovie,
    SimilarMoviesResponse,
)
from cinematch.services.content_recommender import ContentRecommender
from cinematch.services.movie_service import MovieService

router = APIRouter()


@router.get("/search", response_model=MovieSearchResponse)
async def search_movies(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
):
    movies, total = await movie_service.search_by_title(q, db, limit=limit)
    return MovieSearchResponse(
        results=[MovieSummary.model_validate(m) for m in movies],
        total=total,
        query=q,
    )


@router.get("/{movie_id}", response_model=MovieResponse)
async def get_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
):
    movie = await movie_service.get_by_id(movie_id, db)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return MovieResponse.model_validate(movie)


@router.get("/{movie_id}/similar", response_model=SimilarMoviesResponse)
async def get_similar_movies(
    movie_id: int,
    top_k: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    content_rec: ContentRecommender | None = Depends(get_content_recommender),
):
    if content_rec is None:
        raise ServiceUnavailableError("Content recommendation service")
    movie = await movie_service.get_by_id(movie_id, db)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    similar_pairs = await content_rec.get_similar_movies(movie_id, db, top_k=top_k)
    similar_ids = [mid for mid, _ in similar_pairs]
    movies_map = await movie_service.get_movies_by_ids(similar_ids, db)

    similar = []
    for mid, score in similar_pairs:
        m = movies_map.get(mid)
        if m is not None:
            similar.append(SimilarMovie(movie=MovieSummary.model_validate(m), similarity=score))

    return SimilarMoviesResponse(
        movie_id=movie.id,
        movie_title=movie.title,
        similar=similar,
    )
