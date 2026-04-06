"""Movie API endpoints."""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.api.deps import (
    get_cache_service,
    get_collab_recommender,
    get_content_recommender,
    get_db,
    get_embedding_service,
    get_movie_service,
    get_rating_service,
    get_thematic_collection_service,
)
from cinematch.config import get_settings
from cinematch.core.cache import CacheService
from cinematch.core.exceptions import ServiceUnavailableError
from cinematch.core.rate_limit import limiter
from cinematch.schemas.movie import (
    ActorFilmographyResponse,
    ActorFilmResult,
    ActorSearchResponse,
    ActorStats,
    ActorSummary,
    AdvancedSearchResponse,
    AdvancedSearchResult,
    ALSPrediction,
    AutocompleteResponse,
    AutocompleteSuggestion,
    CastCombinationResponse,
    ControversialMovieResult,
    ControversialResponse,
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
    KeywordMovieResult,
    KeywordMoviesResponse,
    KeywordSearchResponse,
    KeywordStats,
    KeywordSummary,
    LanguageCount,
    LanguagesResponse,
    MovieActivityResponse,
    MovieComparisonResponse,
    MovieConnection,
    MovieConnectionsResponse,
    MovieDNAResponse,
    MovieListResponse,
    MoviePathResponse,
    MovieRatingStatsResponse,
    MovieResponse,
    MovieSearchResponse,
    MovieSummary,
    PathStep,
    PopularActorsResponse,
    PopularDirectorsResponse,
    PopularKeywordsResponse,
    RatingComparison,
    RatingHistogramBucket,
    SeasonalMovieResult,
    SeasonalResponse,
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
from cinematch.schemas.thematic_collection import (
    ThematicCollectionDetailResponse,
    ThematicCollectionsResponse,
)
from cinematch.services.movie_service import MovieService

if TYPE_CHECKING:
    from cinematch.services.collab_recommender import CollabRecommender
    from cinematch.services.content_recommender import ContentRecommender
    from cinematch.services.embedding_service import EmbeddingService
from cinematch.services.rating_service import RatingService
from cinematch.services.thematic_collection_service import ThematicCollectionService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search", response_model=MovieSearchResponse)
@limiter.limit(get_settings().rate_limit_search)
async def search_movies(
    request: Request,
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    user_id: int | None = Query(default=None, ge=1),
    exclude_rated: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    rating_service: RatingService = Depends(get_rating_service),
):
    movies, total = await movie_service.search_by_title(q, db, limit=limit)
    results = [MovieSummary.model_validate(m) for m in movies]
    if user_id is not None and exclude_rated:
        rated_ids = await rating_service.get_rated_movie_ids(user_id, db)
        results = [r for r in results if r.id not in rated_ids]
    return MovieSearchResponse(
        results=results,
        total=len(results) if (user_id is not None and exclude_rated) else total,
        query=q,
    )


@router.get("/genres", response_model=GenresResponse)
async def get_genres(
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
):
    rows = await movie_service.get_genre_counts(db)
    return GenresResponse(genres=[GenreCount(genre=g, count=c) for g, c in rows])


@router.get("/languages", response_model=LanguagesResponse)
async def get_languages(
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    cache_key = "languages_list"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return LanguagesResponse.model_validate_json(cached)

    rows = await movie_service.get_language_counts(db)
    response = LanguagesResponse(
        languages=[LanguageCount(code=code, name=code, count=count) for code, count in rows]
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=86400)
        except Exception:
            logger.warning("Failed to cache languages list", exc_info=True)

    return response


@router.get("/discover", response_model=MovieListResponse)
async def discover_movies(
    genre: str | None = Query(default=None),
    year_min: int | None = Query(default=None, ge=1888, le=2030),
    year_max: int | None = Query(default=None, ge=1888, le=2030),
    language: str | None = Query(default=None, max_length=10),
    min_runtime: int | None = Query(default=None, ge=1, description="Minimum runtime in minutes"),
    max_runtime: int | None = Query(default=None, ge=1, description="Maximum runtime in minutes"),
    sort_by: SortOption = Query(default=SortOption.popularity),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    user_id: int | None = Query(default=None, ge=1),
    exclude_rated: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    rating_service: RatingService = Depends(get_rating_service),
):
    movies, total = await movie_service.list_movies(
        db,
        genre=genre,
        year_min=year_min,
        year_max=year_max,
        language=language,
        min_runtime=min_runtime,
        max_runtime=max_runtime,
        sort_by=sort_by.value,
        sort_order="asc" if sort_by == SortOption.title else "desc",
        offset=offset,
        limit=limit,
    )
    results = [MovieSummary.model_validate(m) for m in movies]
    if user_id is not None and exclude_rated:
        rated_ids = await rating_service.get_rated_movie_ids(user_id, db)
        results = [r for r in results if r.id not in rated_ids]
    return MovieListResponse(
        results=results,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/semantic-search", response_model=SemanticSearchResponse)
@limiter.limit(get_settings().rate_limit_search)
async def semantic_search(
    request: Request,
    q: str = Query(min_length=1, max_length=200),
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
    user_id: int | None = Query(default=None, ge=1),
    exclude_rated: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    rating_service: RatingService = Depends(get_rating_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    cache_key = f"trending:{window}:{limit}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            response = TrendingResponse.model_validate_json(cached)
            if user_id is not None and exclude_rated:
                rated_ids = await rating_service.get_rated_movie_ids(user_id, db)
                response.results = [r for r in response.results if r.movie.id not in rated_ids]
            return response

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

    if user_id is not None and exclude_rated:
        rated_ids = await rating_service.get_rated_movie_ids(user_id, db)
        response.results = [r for r in response.results if r.movie.id not in rated_ids]

    return response


@router.get("/hidden-gems", response_model=HiddenGemsResponse)
async def hidden_gems(
    min_rating: float = Query(default=7.5, ge=0, le=10),
    max_votes: int = Query(default=100, ge=1, le=100000),
    genre: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    user_id: int | None = Query(default=None, ge=1),
    exclude_rated: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    rating_service: RatingService = Depends(get_rating_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    cache_key = f"hidden_gems:{round(min_rating, 1)}:{max_votes}:{genre}:{limit}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            response = HiddenGemsResponse.model_validate_json(cached)
            if user_id is not None and exclude_rated:
                rated_ids = await rating_service.get_rated_movie_ids(user_id, db)
                response.results = [r for r in response.results if r.movie.id not in rated_ids]
            return response

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

    if user_id is not None and exclude_rated:
        rated_ids = await rating_service.get_rated_movie_ids(user_id, db)
        response.results = [r for r in response.results if r.movie.id not in rated_ids]

    return response


@router.get("/seasonal", response_model=SeasonalResponse)
async def seasonal_movies(
    month: int | None = Query(default=None, ge=1, le=12),
    limit: int = Query(default=20, ge=1, le=100),
    user_id: int | None = Query(default=None, ge=1),
    exclude_rated: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    rating_service: RatingService = Depends(get_rating_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    from datetime import UTC, datetime

    resolved_month = month if month is not None else datetime.now(UTC).month
    cache_key = f"seasonal:{resolved_month}:{limit}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            response = SeasonalResponse.model_validate_json(cached)
            if user_id is not None and exclude_rated:
                rated_ids = await rating_service.get_rated_movie_ids(user_id, db)
                response.results = [r for r in response.results if r.movie.id not in rated_ids]
            return response

    movies, ctx = await movie_service.seasonal(db, month=resolved_month, limit=limit)

    response = SeasonalResponse(
        results=[
            SeasonalMovieResult(
                movie=MovieSummary.model_validate(movie),
                vote_average=movie.vote_average,
                popularity=movie.popularity,
            )
            for movie in movies
        ],
        season_name=ctx.season_name,
        theme_label=ctx.theme_label,
        month=resolved_month,
        genres=ctx.genres,
        keywords=ctx.keywords,
        limit=limit,
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache seasonal movies", exc_info=True)

    if user_id is not None and exclude_rated:
        rated_ids = await rating_service.get_rated_movie_ids(user_id, db)
        response.results = [r for r in response.results if r.movie.id not in rated_ids]

    return response


@router.get("/top", response_model=TopChartsResponse)
async def top_charts_by_genre(
    genre: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    user_id: int | None = Query(default=None, ge=1),
    exclude_rated: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    rating_service: RatingService = Depends(get_rating_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    cache_key = f"top_charts:{genre}:{limit}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            response = TopChartsResponse.model_validate_json(cached)
            if user_id is not None and exclude_rated:
                rated_ids = await rating_service.get_rated_movie_ids(user_id, db)
                response.results = [r for r in response.results if r.movie.id not in rated_ids]
            return response

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

    if user_id is not None and exclude_rated:
        rated_ids = await rating_service.get_rated_movie_ids(user_id, db)
        response.results = [r for r in response.results if r.movie.id not in rated_ids]

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
@limiter.limit(get_settings().rate_limit_search)
async def search_directors(
    request: Request,
    q: str = Query(min_length=1, max_length=200),
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
    cache_key = f"director_filmography:{hashlib.sha256(name.lower().encode()).hexdigest()[:16]}"

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
@limiter.limit(get_settings().rate_limit_search)
async def search_actors(
    request: Request,
    q: str = Query(min_length=1, max_length=200),
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
    cache_key = f"actor_filmography:{hashlib.sha256(name.lower().encode()).hexdigest()[:16]}"

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


@router.get("/by-cast", response_model=CastCombinationResponse)
async def movies_by_cast(
    actors: str = Query(min_length=3, description="Comma-separated actor names, 2-5 required"),
    sort_by: str = Query(
        default="popularity",
        pattern=r"^(popularity|vote_average|release_date|title)$",
    ),
    sort_order: str = Query(default="desc", pattern=r"^(asc|desc)$"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    actor_list = list(dict.fromkeys(name.strip() for name in actors.split(",") if name.strip()))

    if len(actor_list) < 2:
        raise HTTPException(status_code=400, detail="At least 2 actor names are required")
    if len(actor_list) > 5:
        raise HTTPException(status_code=400, detail="At most 5 actor names are allowed")

    sorted_actors = ",".join(sorted(a.lower() for a in actor_list))
    cache_key = f"by_cast:{sorted_actors}:{sort_by}:{sort_order}:{offset}:{limit}"

    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return CastCombinationResponse.model_validate_json(cached)

    movies, total = await movie_service.movies_by_cast_combination(
        db,
        actors=actor_list,
        sort_by=sort_by,
        sort_order=sort_order,
        offset=offset,
        limit=limit,
    )

    response = CastCombinationResponse(
        actors=actor_list,
        results=[
            AdvancedSearchResult(
                movie=MovieSummary.model_validate(m),
                vote_average=m.vote_average,
                director=m.director,
            )
            for m in movies
        ],
        total=total,
        offset=offset,
        limit=limit,
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=3600)
        except Exception:
            logger.warning("Failed to cache cast combination results", exc_info=True)

    return response


@router.get("/keywords/popular", response_model=PopularKeywordsResponse)
async def popular_keywords(
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    cache_key = f"popular_keywords:{limit}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return PopularKeywordsResponse.model_validate_json(cached)

    rows = await movie_service.popular_keywords(db, limit=limit)

    response = PopularKeywordsResponse(
        results=[KeywordSummary(keyword=kw, count=count) for kw, count in rows],
        limit=limit,
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache popular keywords", exc_info=True)

    return response


@router.get("/keywords/search", response_model=KeywordSearchResponse)
async def search_keywords(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
):
    rows = await movie_service.search_keywords(q, db, limit=limit)
    return KeywordSearchResponse(
        results=[KeywordSummary(keyword=kw, count=count) for kw, count in rows],
        query=q,
    )


@router.get("/keywords/movies", response_model=KeywordMoviesResponse)
async def keyword_movies(
    keyword: str = Query(min_length=1, max_length=255),
    offset: int = Query(default=0, ge=0, le=10000),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    kw_hash = hashlib.sha256(keyword.lower().encode()).hexdigest()[:16]
    cache_key = f"keyword_movies:{kw_hash}:{offset}:{limit}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return KeywordMoviesResponse.model_validate_json(cached)

    movies, total, stats = await movie_service.movies_by_keyword(
        db, keyword=keyword, offset=offset, limit=limit
    )

    response = KeywordMoviesResponse(
        results=[
            KeywordMovieResult(
                movie=MovieSummary.model_validate(movie),
                vote_average=movie.vote_average,
            )
            for movie in movies
        ],
        keyword=keyword,
        stats=KeywordStats(**stats),
        total=total,
        offset=offset,
        limit=limit,
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache keyword movies", exc_info=True)

    return response


@router.get("/advanced-search", response_model=AdvancedSearchResponse)
@limiter.limit(get_settings().rate_limit_search)
async def advanced_search(
    request: Request,
    genre: str | None = Query(default=None, max_length=100),
    decade: str | None = Query(default=None, pattern=r"^\d{4}s$"),
    min_rating: float | None = Query(default=None, ge=0, le=10),
    max_rating: float | None = Query(default=None, ge=0, le=10),
    director: str | None = Query(default=None, max_length=255),
    keyword: str | None = Query(default=None, max_length=255),
    cast: str | None = Query(default=None, max_length=255),
    language: str | None = Query(default=None, max_length=10),
    min_runtime: int | None = Query(default=None, ge=1, description="Minimum runtime in minutes"),
    max_runtime: int | None = Query(default=None, ge=1, description="Maximum runtime in minutes"),
    sort_by: SortOption = Query(default=SortOption.popularity),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    raw_key = (
        f"adv_search:{genre}:{decade}:{min_rating}:{max_rating}"
        f":{director}:{keyword}:{cast}:{language}:{min_runtime}:{max_runtime}:{sort_by.value}:{offset}:{limit}"
    )
    cache_key = f"adv_search:{hashlib.sha256(raw_key.encode()).hexdigest()[:16]}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return AdvancedSearchResponse.model_validate_json(cached)

    movies, total = await movie_service.advanced_search(
        db,
        genre=genre,
        decade=decade,
        min_rating=min_rating,
        max_rating=max_rating,
        director=director,
        keyword=keyword,
        cast_name=cast,
        language=language,
        min_runtime=min_runtime,
        max_runtime=max_runtime,
        sort_by=sort_by.value,
        offset=offset,
        limit=limit,
    )

    response = AdvancedSearchResponse(
        results=[
            AdvancedSearchResult(
                movie=MovieSummary.model_validate(m),
                vote_average=m.vote_average,
                director=m.director,
            )
            for m in movies
        ],
        total=total,
        offset=offset,
        limit=limit,
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=3600)
        except Exception:
            logger.warning("Failed to cache advanced search results", exc_info=True)

    return response


@router.get("/controversial", response_model=ControversialResponse)
async def controversial_movies(
    min_ratings: int = Query(default=100, ge=10, le=10000),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    cache_key = f"controversial:{min_ratings}:{limit}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return ControversialResponse.model_validate_json(cached)

    rows = await movie_service.controversial(db, min_ratings=min_ratings, limit=limit)

    response = ControversialResponse(
        results=[
            ControversialMovieResult(
                movie=MovieSummary.model_validate(movie),
                avg_rating=round(avg, 4),
                stddev_rating=round(stddev, 4),
                rating_count=count,
                histogram=[
                    RatingHistogramBucket(rating=r, count=hist.get(r, 0)) for r in range(1, 11)
                ],
            )
            for movie, avg, stddev, count, hist in rows
        ],
        min_ratings=min_ratings,
        limit=limit,
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache controversial movies", exc_info=True)

    return response


# ------------------------------------------------------------------
# Thematic collections
# ------------------------------------------------------------------


@router.get("/thematic-collections", response_model=ThematicCollectionsResponse)
async def list_thematic_collections(
    collection_type: str | None = Query(default=None, pattern="^(genre_decade|director|year)$"),
    db: AsyncSession = Depends(get_db),
    thematic_service: ThematicCollectionService = Depends(get_thematic_collection_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    """List available auto-generated thematic collections."""
    cache_key = f"thematic_list:{collection_type or 'all'}"

    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return ThematicCollectionsResponse.model_validate_json(cached)

    response = await thematic_service.list_collections(db, collection_type=collection_type)

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache thematic collections list", exc_info=True)

    return response


@router.get(
    "/thematic-collections/{collection_id:path}",
    response_model=ThematicCollectionDetailResponse,
)
async def get_thematic_collection(
    collection_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    thematic_service: ThematicCollectionService = Depends(get_thematic_collection_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    """Get ranked movies for a specific thematic collection."""
    cache_key = f"thematic_detail:{collection_id}:{limit}"

    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return ThematicCollectionDetailResponse.model_validate_json(cached)

    result = await thematic_service.get_collection(db, collection_id=collection_id, limit=limit)
    if result is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, result.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache thematic collection detail", exc_info=True)

    return result


@router.get("/compare", response_model=MovieComparisonResponse)
async def compare_movies(
    ids: str = Query(..., description="Two movie IDs separated by comma, e.g. '42,108'"),
    user_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    rating_service: RatingService = Depends(get_rating_service),
    collab_recommender: CollabRecommender | None = Depends(get_collab_recommender),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    """Compare two movies side-by-side with computed overlaps and similarity."""
    parts = ids.split(",")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Exactly two movie IDs required")
    try:
        id1, id2 = int(parts[0].strip()), int(parts[1].strip())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid movie IDs")
    if id1 == id2:
        raise HTTPException(status_code=400, detail="Must compare two different movies")

    lo, hi = min(id1, id2), max(id1, id2)
    cache_key = f"comparison:{lo}:{hi}"
    if user_id is not None:
        cache_key += f":u{user_id}"

    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return MovieComparisonResponse.model_validate_json(cached)

    movie1 = await movie_service.get_by_id(id1, db)
    movie2 = await movie_service.get_by_id(id2, db)
    if movie1 is None or movie2 is None:
        missing = id1 if movie1 is None else id2
        raise HTTPException(status_code=404, detail=f"Movie {missing} not found")

    shared_genres = sorted(set(movie1.genres or []) & set(movie2.genres or []))
    shared_actors = sorted(set(movie1.cast_names or []) & set(movie2.cast_names or []))
    shared_keywords = sorted(set(movie1.keywords or []) & set(movie2.keywords or []))
    same_director = bool(movie1.director and movie2.director and movie1.director == movie2.director)

    embedding_similarity = await movie_service.embedding_cosine_similarity(id1, id2, db)

    rating_stats = await rating_service.get_rating_stats_pair(id1, id2, db)
    m1_avg, m1_count = rating_stats.get(id1, (0.0, 0))
    m2_avg, m2_count = rating_stats.get(id2, (0.0, 0))

    als_prediction = None
    if user_id is not None and collab_recommender is not None:
        scores = collab_recommender.score_items(user_id, [id1, id2])
        if scores:
            s1 = scores.get(id1)
            s2 = scores.get(id2)
            preferred = None
            if s1 is not None and s2 is not None:
                preferred = id1 if s1 >= s2 else id2
            elif s1 is not None:
                preferred = id1
            elif s2 is not None:
                preferred = id2
            als_prediction = ALSPrediction(
                user_id=user_id,
                movie1_score=round(s1, 4) if s1 is not None else None,
                movie2_score=round(s2, 4) if s2 is not None else None,
                preferred_movie_id=preferred,
            )

    response = MovieComparisonResponse(
        movie1=MovieResponse.model_validate(movie1),
        movie2=MovieResponse.model_validate(movie2),
        shared_genres=shared_genres,
        shared_actors=shared_actors,
        shared_keywords=shared_keywords,
        same_director=same_director,
        embedding_similarity=embedding_similarity,
        rating_comparison=RatingComparison(
            movie1_avg=m1_avg,
            movie1_count=m1_count,
            movie2_avg=m2_avg,
            movie2_count=m2_count,
        ),
        als_prediction=als_prediction,
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache movie comparison", exc_info=True)

    return response


@router.get("/{movie_id}/connection/{other_id}", response_model=MovieConnectionsResponse)
async def get_movie_connections(
    movie_id: int,
    other_id: int,
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    """Find shared attributes between two movies."""
    lo, hi = min(movie_id, other_id), max(movie_id, other_id)
    cache_key = f"connections:{lo}:{hi}"

    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return MovieConnectionsResponse.model_validate_json(cached)

    movie1, movie2, connections = await movie_service.find_direct_connections(
        movie_id, other_id, db
    )
    if movie1 is None or movie2 is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    response = MovieConnectionsResponse(
        movie1=MovieSummary.model_validate(movie1),
        movie2=MovieSummary.model_validate(movie2),
        connections=[MovieConnection(**c) for c in connections],
        connection_count=len(connections),
    )

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache movie connections", exc_info=True)

    return response


@router.get("/{movie_id}/path/{other_id}", response_model=MoviePathResponse)
async def get_movie_path(
    movie_id: int,
    other_id: int,
    max_depth: int = Query(default=6, ge=1, le=6),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    """Find shortest path between two movies through shared cast/directors."""
    lo, hi = min(movie_id, other_id), max(movie_id, other_id)
    cache_key = f"path:{lo}:{hi}:{max_depth}"

    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return MoviePathResponse.model_validate_json(cached)

    movie1, movie2, path, found = await movie_service.find_shortest_path(
        movie_id, other_id, db, max_depth=max_depth
    )
    if movie1 is None or movie2 is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    response = MoviePathResponse(
        movie1=MovieSummary.model_validate(movie1),
        movie2=MovieSummary.model_validate(movie2),
        path=[
            PathStep(
                movie=MovieSummary.model_validate(s["movie"]),
                linked_by=s["linked_by"],
            )
            for s in path
        ],
        degrees=max(0, len(path) - 1),
        found=found,
    )

    if cache_service is not None and found:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache movie path", exc_info=True)

    return response


@router.get("/autocomplete", response_model=AutocompleteResponse)
@limiter.limit(get_settings().rate_limit_search)
async def autocomplete_movies(
    request: Request,
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=8, ge=1, le=8),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    """Fast autocomplete suggestions for movie titles."""
    cache_key = f"autocomplete:{q.lower().strip()}:{limit}"

    if cache_service is not None:
        try:
            cached = await cache_service.get(cache_key)
            if cached:
                return AutocompleteResponse.model_validate_json(cached)
        except Exception:
            logger.warning("Failed to read autocomplete cache", exc_info=True)

    rows = await movie_service.autocomplete(q.strip(), db, limit=limit)
    results = [
        AutocompleteSuggestion(
            id=row[0],
            title=row[1],
            year=row[2].year if row[2] else None,
            poster_path=row[3],
        )
        for row in rows
    ]
    response = AutocompleteResponse(results=results, query=q)

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=300)
        except Exception:
            logger.warning("Failed to cache autocomplete results", exc_info=True)

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


@router.get("/{movie_id}/rating-stats", response_model=MovieRatingStatsResponse)
async def get_movie_rating_stats(
    movie_id: int,
    user_id: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
    rating_service: RatingService = Depends(get_rating_service),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    """Get community rating distribution for a movie, with optional user comparison."""
    cache_key = f"movie_rating_stats:{movie_id}"

    # Try cache for movie-level stats
    cached_data: dict | None = None
    if cache_service is not None:
        try:
            cached = await cache_service.get(cache_key)
            if cached is not None:
                import json

                cached_data = json.loads(cached)
        except Exception:
            logger.warning("Failed to read movie rating stats cache", exc_info=True)

    if cached_data is not None:
        # Attach user rating separately (not cached)
        if user_id is not None:
            user_ratings = await rating_service.bulk_check(user_id, [movie_id], db)
            cached_data["user_rating"] = user_ratings.get(movie_id)
        else:
            cached_data["user_rating"] = None
        return MovieRatingStatsResponse(**cached_data)

    result = await rating_service.get_movie_rating_stats(movie_id, db)

    # Cache movie-level stats (without user_rating)
    if cache_service is not None:
        try:
            import json

            cache_payload = {**result, "user_rating": None}
            await cache_service.set(cache_key, json.dumps(cache_payload), ttl=3600)
        except Exception:
            logger.warning("Failed to cache movie rating stats", exc_info=True)

    # Attach user rating if requested
    if user_id is not None:
        user_ratings = await rating_service.bulk_check(user_id, [movie_id], db)
        result["user_rating"] = user_ratings.get(movie_id)

    return MovieRatingStatsResponse(**result)


@router.get("/{movie_id}/dna", response_model=MovieDNAResponse)
async def get_movie_dna(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    content_rec: ContentRecommender | None = Depends(get_content_recommender),
    cache_service: CacheService | None = Depends(get_cache_service),
):
    """Get a movie's DNA breakdown: genre weights, keywords, decade, and mood tags."""
    if content_rec is None:
        raise ServiceUnavailableError("Content recommendation service")

    cache_key = f"movie_dna:{movie_id}"
    if cache_service is not None:
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return MovieDNAResponse.model_validate_json(cached)

    result = await movie_service.get_movie_dna(movie_id, db, content_rec)
    if result is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    response = MovieDNAResponse(**result)

    if cache_service is not None:
        try:
            await cache_service.set(cache_key, response.model_dump_json(), ttl=21600)
        except Exception:
            logger.warning("Failed to cache movie DNA", exc_info=True)

    return response


@router.get("/{movie_id}/activity", response_model=MovieActivityResponse)
async def get_movie_activity(
    movie_id: int,
    granularity: str = Query(default="month", pattern="^(month|week)$"),
    db: AsyncSession = Depends(get_db),
    movie_service: MovieService = Depends(get_movie_service),
    rating_service: RatingService = Depends(get_rating_service),
):
    """Get the popularity timeline for a movie — rating counts grouped by time period."""
    movie = await movie_service.get_by_id(movie_id, db)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    result = await rating_service.get_movie_activity(movie_id, granularity, db)
    return MovieActivityResponse(**result)
