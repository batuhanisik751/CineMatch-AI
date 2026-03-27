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
