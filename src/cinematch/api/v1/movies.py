"""Movie API endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import (
    get_cache_service,
    get_content_recommender,
    get_db,
    get_embedding_service,
    get_movie_service,
)
from cinematch.core.cache import CacheService
from cinematch.core.exceptions import ServiceUnavailableError
from cinematch.schemas.movie import (
    ActorFilmographyResponse,
    ActorFilmResult,
    ActorSearchResponse,
    ActorStats,
    ActorSummary,
    DecadeMovieResult,
    DecadeMoviesResponse,
    DecadesResponse,
    DecadeSummary,
    DirectorFilmographyResponse,
    DirectorFilmResult,
    DirectorSearchResponse,
    DirectorStats,
    DirectorSummary,
    GenreCount,
    GenresResponse,
    HiddenGemResult,
    HiddenGemsResponse,
    MovieListResponse,
    MovieResponse,
    MovieSearchResponse,
    MovieSummary,
    PopularActorsResponse,
    PopularDirectorsResponse,
    SemanticSearchResponse,
    SemanticSearchResult,
    SimilarMovie,
    SimilarMoviesResponse,
    SortOption,
    TopChartResult,
    TopChartsResponse,
    TrendingMovieResult,
    TrendingResponse,
)
from cinematch.services.content_recommender import ContentRecommender
from cinematch.services.embedding_service import EmbeddingService
from cinematch.services.movie_service import MovieService

logger = logging.getLogger(__name__)

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


@router.get("/trending", response_model=TrendingResponse)
async def trending_movies(
    window: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    cache_key = f"trending:{window}:{limit}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return TrendingResponse.model_validate_json(cached)

    trending_pairs = await movie_service.trending(db, window=window, limit=limit)

    response = TrendingResponse(
        results=[
            TrendingMovieResult(
                movie=MovieSummary.model_validate(movie),
                rating_count=count,
            )
            for movie, count in trending_pairs
        ],
        window=window,
        limit=limit,
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=3600)
        except Exception:
            logger.warning("Failed to cache trending movies", exc_info=True)

    return response


@router.get("/hidden-gems", response_model=HiddenGemsResponse)
async def hidden_gems(
    min_rating: float = Query(default=7.5, ge=0, le=10),
    max_votes: int = Query(default=100, ge=1, le=100000),
    genre: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    cache_key = f"hidden_gems:{round(min_rating, 1)}:{max_votes}:{genre}:{limit}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return HiddenGemsResponse.model_validate_json(cached)

    movies = await movie_service.hidden_gems(
        db, min_rating=min_rating, max_votes=max_votes, genre=genre, limit=limit
    )

    response = HiddenGemsResponse(
        results=[
            HiddenGemResult(
                movie=MovieSummary.model_validate(movie),
                vote_average=movie.vote_average,
                vote_count=movie.vote_count,
            )
            for movie in movies
        ],
        min_rating=min_rating,
        max_votes=max_votes,
        limit=limit,
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache hidden gems", exc_info=True)

    return response


@router.get("/top", response_model=TopChartsResponse)
async def top_charts_by_genre(
    genre: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    cache_key = f"top_charts:{genre}:{limit}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return TopChartsResponse.model_validate_json(cached)

    rows = await movie_service.top_by_genre(db, genre=genre, limit=limit)

    response = TopChartsResponse(
        results=[
            TopChartResult(
                movie=MovieSummary.model_validate(movie),
                avg_rating=round(avg, 4),
                rating_count=count,
            )
            for movie, avg, count in rows
        ],
        genre=genre,
        limit=limit,
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache top charts", exc_info=True)

    return response


@router.get("/decades", response_model=DecadesResponse)
async def get_decades(
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    cache_key = "decades"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return DecadesResponse.model_validate_json(cached)

    rows = await movie_service.get_decade_stats(db)

    response = DecadesResponse(
        decades=[
            DecadeSummary(decade=decade, movie_count=count, avg_rating=round(avg, 2))
            for decade, count, avg in rows
        ]
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache decades", exc_info=True)

    return response


@router.get("/decades/{decade}", response_model=DecadeMoviesResponse)
async def get_decade_movies(
    decade: int,
    genre: str | None = Query(default=None, min_length=1, max_length=100),
    offset: int = Query(default=0, ge=0, le=10000),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    if decade < 1880 or decade > 2020 or decade % 10 != 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid decade. Use format like 1990, 2000, 2010.",
        )

    cache_key = f"decade_movies:{decade}:{genre}:{offset}:{limit}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return DecadeMoviesResponse.model_validate_json(cached)

    rows, total = await movie_service.top_by_decade(
        db, decade=decade, genre=genre, offset=offset, limit=limit
    )

    response = DecadeMoviesResponse(
        results=[
            DecadeMovieResult(
                movie=MovieSummary.model_validate(movie),
                avg_rating=round(avg, 4),
                rating_count=count,
            )
            for movie, avg, count in rows
        ],
        decade=decade,
        genre=genre,
        total=total,
        offset=offset,
        limit=limit,
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache decade movies", exc_info=True)

    return response


@router.get("/directors/search", response_model=DirectorSearchResponse)
async def search_directors(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
):
    rows = await movie_service.search_directors(q, db, limit=limit)
    return DirectorSearchResponse(
        results=[
            DirectorSummary(name=name, film_count=count, avg_vote=round(avg, 2))
            for name, count, avg in rows
        ],
        query=q,
    )


@router.get("/directors/popular", response_model=PopularDirectorsResponse)
async def popular_directors(
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    cache_key = f"popular_directors:{limit}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return PopularDirectorsResponse.model_validate_json(cached)

    rows = await movie_service.popular_directors(db, limit=limit)

    response = PopularDirectorsResponse(
        results=[
            DirectorSummary(name=name, film_count=count, avg_vote=round(avg, 2))
            for name, count, avg in rows
        ],
        limit=limit,
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache popular directors", exc_info=True)

    return response


@router.get("/directors/filmography", response_model=DirectorFilmographyResponse)
async def director_filmography(
    name: str = Query(min_length=1, max_length=255),
    user_id: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    use_cache = user_id is None
    cache_key = f"director_filmography:{name.lower()}"

    if use_cache and cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return DirectorFilmographyResponse.model_validate_json(cached)

    films, stats = await movie_service.filmography_by_director(db, name=name, user_id=user_id)

    if not films:
        raise HTTPException(status_code=404, detail="Director not found")

    response = DirectorFilmographyResponse(
        director=name,
        stats=DirectorStats(**stats),
        filmography=[
            DirectorFilmResult(
                movie=MovieSummary.model_validate(movie),
                user_rating=rating,
            )
            for movie, rating in films
        ],
    )

    if use_cache and cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache director filmography", exc_info=True)

    return response


@router.get("/actors/search", response_model=ActorSearchResponse)
async def search_actors(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
):
    rows = await movie_service.search_actors(q, db, limit=limit)
    return ActorSearchResponse(
        results=[
            ActorSummary(name=name, film_count=count, avg_vote=round(avg, 2))
            for name, count, avg in rows
        ],
        query=q,
    )


@router.get("/actors/popular", response_model=PopularActorsResponse)
async def popular_actors(
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    cache_key = f"popular_actors:{limit}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return PopularActorsResponse.model_validate_json(cached)

    rows = await movie_service.popular_actors(db, limit=limit)

    response = PopularActorsResponse(
        results=[
            ActorSummary(name=name, film_count=count, avg_vote=round(avg, 2))
            for name, count, avg in rows
        ],
        limit=limit,
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache popular actors", exc_info=True)

    return response


@router.get("/actors/filmography", response_model=ActorFilmographyResponse)
async def actor_filmography(
    name: str = Query(min_length=1, max_length=255),
    user_id: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    use_cache = user_id is None
    cache_key = f"actor_filmography:{name.lower()}"

    if use_cache and cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return ActorFilmographyResponse.model_validate_json(cached)

    films, stats = await movie_service.filmography_by_actor(db, name=name, user_id=user_id)

    if not films:
        raise HTTPException(status_code=404, detail="Actor not found")

    response = ActorFilmographyResponse(
        actor=name,
        stats=ActorStats(**stats),
        filmography=[
            ActorFilmResult(
                movie=MovieSummary.model_validate(movie),
                user_rating=rating,
            )
            for movie, rating in films
        ],
    )

    if use_cache and cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache actor filmography", exc_info=True)

    return response


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
