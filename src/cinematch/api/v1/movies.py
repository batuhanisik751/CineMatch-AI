"""Movie API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import (
    get_content_recommender,
    get_db,
    get_embedding_service,
    get_movie_service,
)
from cinematch.core.exceptions import ServiceUnavailableError
from cinematch.schemas.movie import (
    GenreCount,
    GenresResponse,
    MovieListResponse,
    MovieResponse,
    MovieSearchResponse,
    MovieSummary,
    SemanticSearchResponse,
    SemanticSearchResult,
    SimilarMovie,
    SimilarMoviesResponse,
    SortOption,
)
from cinematch.services.content_recommender import ContentRecommender
from cinematch.services.embedding_service import EmbeddingService
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


@router.get("/genres", response_model=GenresResponse)
async def get_genres(
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
):
    rows = await movie_service.get_genre_counts(db)
    return GenresResponse(genres=[GenreCount(genre=g, count=c) for g, c in rows])


@router.get("/discover", response_model=MovieListResponse)
async def discover_movies(
    genre: str | None = Query(default=None),
    year_min: int | None = Query(default=None, ge=1888, le=2030),
    year_max: int | None = Query(default=None, ge=1888, le=2030),
    sort_by: SortOption = Query(default=SortOption.popularity),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
):
    movies, total = await movie_service.list_movies(
        db,
        genre=genre,
        year_min=year_min,
        year_max=year_max,
        sort_by=sort_by.value,
        sort_order="asc" if sort_by == SortOption.title else "desc",
        offset=offset,
        limit=limit,
    )
    return MovieListResponse(
        results=[MovieSummary.model_validate(m) for m in movies],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/semantic-search", response_model=SemanticSearchResponse)
async def semantic_search(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    embedding_service: EmbeddingService | None = Depends(get_embedding_service),
):
    if embedding_service is None:
        raise ServiceUnavailableError("Embedding service")

    query_embedding = embedding_service.embed_text(q).tolist()
    results = await movie_service.semantic_search(query_embedding, db, limit=limit)

    return SemanticSearchResponse(
        results=[
            SemanticSearchResult(
                movie=MovieSummary.model_validate(movie),
                similarity=round(score, 4),
            )
            for movie, score in results
        ],
        total=len(results),
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
