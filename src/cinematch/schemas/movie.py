"""Pydantic schemas for movie endpoints."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class MovieSummary(BaseModel):
    """Lightweight movie representation for lists."""

    id: int
    title: str
    genres: list[str]
    vote_average: float
    release_date: date | None
    poster_path: str | None

    model_config = ConfigDict(from_attributes=True)


class MovieResponse(BaseModel):
    """Full movie details."""

    id: int
    tmdb_id: int
    imdb_id: str | None
    title: str
    overview: str | None
    genres: list[str]
    keywords: list[str]
    cast_names: list[str]
    director: str | None
    release_date: date | None
    vote_average: float
    vote_count: int
    popularity: float
    poster_path: str | None

    model_config = ConfigDict(from_attributes=True)


class SimilarMovie(BaseModel):
    movie: MovieSummary
    similarity: float


class SimilarMoviesResponse(BaseModel):
    movie_id: int
    movie_title: str
    similar: list[SimilarMovie]


class MovieSearchResponse(BaseModel):
    results: list[MovieSummary]
    total: int
    query: str


class SortOption(StrEnum):
    popularity = "popularity"
    vote_average = "vote_average"
    release_date = "release_date"
    title = "title"


class MovieListResponse(BaseModel):
    results: list[MovieSummary]
    total: int
    offset: int
    limit: int


class GenreCount(BaseModel):
    genre: str
    count: int


class GenresResponse(BaseModel):
    genres: list[GenreCount]


class SemanticSearchResult(BaseModel):
    movie: MovieSummary
    similarity: float


class SemanticSearchResponse(BaseModel):
    results: list[SemanticSearchResult]
    total: int
    query: str


class TrendingMovieResult(BaseModel):
    movie: MovieSummary
    rating_count: int


class TrendingResponse(BaseModel):
    results: list[TrendingMovieResult]
    window: int
    limit: int


class HiddenGemResult(BaseModel):
    movie: MovieSummary
    vote_average: float
    vote_count: int


class HiddenGemsResponse(BaseModel):
    results: list[HiddenGemResult]
    min_rating: float
    max_votes: int
    limit: int


class TopChartResult(BaseModel):
    movie: MovieSummary
    avg_rating: float
    rating_count: int


class TopChartsResponse(BaseModel):
    results: list[TopChartResult]
    genre: str
    limit: int


class DecadeSummary(BaseModel):
    decade: int
    movie_count: int
    avg_rating: float


class DecadesResponse(BaseModel):
    decades: list[DecadeSummary]


class DecadeMovieResult(BaseModel):
    movie: MovieSummary
    avg_rating: float
    rating_count: int


class DecadeMoviesResponse(BaseModel):
    results: list[DecadeMovieResult]
    decade: int
    genre: str | None
    total: int
    offset: int
    limit: int


class DirectorSummary(BaseModel):
    name: str
    film_count: int
    avg_vote: float


class DirectorSearchResponse(BaseModel):
    results: list[DirectorSummary]
    query: str


class PopularDirectorsResponse(BaseModel):
    results: list[DirectorSummary]
    limit: int


class DirectorFilmResult(BaseModel):
    movie: MovieSummary
    user_rating: float | None


class DirectorStats(BaseModel):
    total_films: int
    avg_vote: float
    genres: list[str]
    user_avg_rating: float | None
    user_rated_count: int


class DirectorFilmographyResponse(BaseModel):
    director: str
    stats: DirectorStats
    filmography: list[DirectorFilmResult]


class ActorSummary(BaseModel):
    name: str
    film_count: int
    avg_vote: float


class ActorSearchResponse(BaseModel):
    results: list[ActorSummary]
    query: str


class PopularActorsResponse(BaseModel):
    results: list[ActorSummary]
    limit: int


class ActorFilmResult(BaseModel):
    movie: MovieSummary
    user_rating: float | None


class ActorStats(BaseModel):
    total_films: int
    avg_vote: float
    genres: list[str]
    user_avg_rating: float | None
    user_rated_count: int


class ActorFilmographyResponse(BaseModel):
    actor: str
    stats: ActorStats
    filmography: list[ActorFilmResult]


class KeywordSummary(BaseModel):
    keyword: str
    count: int


class PopularKeywordsResponse(BaseModel):
    results: list[KeywordSummary]
    limit: int


class KeywordSearchResponse(BaseModel):
    results: list[KeywordSummary]
    query: str


class KeywordStats(BaseModel):
    total_movies: int
    avg_vote: float
    top_genres: list[str]


class KeywordMovieResult(BaseModel):
    movie: MovieSummary
    vote_average: float


class KeywordMoviesResponse(BaseModel):
    results: list[KeywordMovieResult]
    keyword: str
    stats: KeywordStats
    total: int
    offset: int
    limit: int


class AdvancedSearchResult(BaseModel):
    movie: MovieSummary
    vote_average: float
    director: str | None


class AdvancedSearchResponse(BaseModel):
    results: list[AdvancedSearchResult]
    total: int
    offset: int
    limit: int


class RatingHistogramBucket(BaseModel):
    rating: int
    count: int


class ControversialMovieResult(BaseModel):
    movie: MovieSummary
    avg_rating: float
    stddev_rating: float
    rating_count: int
    histogram: list[RatingHistogramBucket]


class ControversialResponse(BaseModel):
    results: list[ControversialMovieResult]
    min_ratings: int
    limit: int


class MovieRatingStatsResponse(BaseModel):
    movie_id: int
    avg_rating: float
    median_rating: float
    total_ratings: int
    distribution: list[RatingHistogramBucket]
    user_rating: int | None
